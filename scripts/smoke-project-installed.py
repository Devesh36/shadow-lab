"""Exercise installed project REPL, history and reports outside the checkout."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    executable = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory(prefix='shadow-project-smoke-') as temporary:
        root = Path(temporary)
        project = root / 'Mixed Case Project'
        route = project / 'app/api/profile/route.ts'
        route.parent.mkdir(parents=True)
        route.write_text('export function GET() { return Response.json({passwordHash: "synthetic"}); }')
        (project / 'package.json').write_text('{"scripts":{"postinstall":"touch SHOULD_NOT_RUN"}}')
        before = hashlib.sha256(route.read_bytes()).hexdigest()
        env = {**os.environ, 'SHADOWLAB_HOME': str(root / 'private'),
               'SHADOWLAB_DATABASE_URL': 'invalid-operator-database',
               'SHADOWLAB_LLM_API_KEY': 'synthetic-operator-secret', 'SHADOWLAB_NO_OPEN': '1'}
        for name in ('PYTHONPATH', 'SHADOWLAB_REPOSITORY_ROOT'):
            env.pop(name, None)
        commands = '/project "Mixed Case Project"\n/status\n/demo\n/routes\n/findings\n/inspect 1\n/history\n/export json\n/stop\n'
        commands += 'project "Mixed Case Project"\nhistory\nuse 1\nreport\nquit\n'
        result = subprocess.run([executable], cwd=root, env=env, input=commands,
                                text=True, capture_output=True, timeout=180)
        assert result.returncode == 0, 'Installed console exited unsuccessfully'
        for expected in ('Source analysis completed', 'INCONCLUSIVE', 'GET /api/profile', 'Scanner semgrep: completed',
                         'Project report:', 'Selected scan:', 'ShadowLab closed', 'Context: project', 'Finding 1:'):
            assert expected in result.stdout, f'Missing workflow result: {expected}'
        assert 'incomplete' not in result.stdout.casefold()
        reports = list((root / 'private/projects').glob('*/reports/*.json'))
        assert len(reports) == 1
        payload = json.loads(reports[0].read_text())
        assert payload['scan']['status'] == 'completed'
        assert payload['scan']['target'] is None and payload['scan']['dynamic'] is False
        assert payload['scan']['scanners']['osv']['status'] == 'disabled'
        assert all(f['state'] == 'INCONCLUSIVE' for f in payload['findings'])
        assert 'synthetic-operator-secret' not in reports[0].read_text() + result.stdout + result.stderr
        assert reports[0].stat().st_mode & 0o777 == 0o600
        assert hashlib.sha256(route.read_bytes()).hexdigest() == before
        assert not (project / 'SHOULD_NOT_RUN').exists() and not (root / '.shadowlab').exists()
        initialized = subprocess.run([executable, 'repl'], cwd=project,
                                     env={**env, 'SHADOWLAB_REPOSITORY_ROOT': str(root)},
                                     input='/init\n/status\n/quit\n', text=True, capture_output=True, timeout=30)
        assert initialized.returncode == 0
        assert 'Project selected: ' + str(project) in initialized.stdout
        assert 'Context: project · ' + str(project) in initialized.stdout
        demo = subprocess.run([executable, 'demo'], cwd=project,
                              env={**env, 'SHADOWLAB_REPOSITORY_ROOT': str(root)},
                              text=True, capture_output=True, timeout=150)
        assert demo.returncode == 0 and 'Project demo finished' in demo.stdout
        exported = subprocess.run([executable, 'report', '--project', '.', '--format', 'json'], cwd=project,
                                  env={**env, 'SHADOWLAB_REPOSITORY_ROOT': str(root)},
                                  text=True, capture_output=True, timeout=30)
        assert exported.returncode == 0
        cli_payload = json.loads(exported.stdout)
        assert cli_payload['scan']['project_demo']['browser_validation']['status'] == 'unsupported'
        assert cli_payload['scan']['project_demo']['patch_verification']['status'] == 'unsupported'
        assert cli_payload['scan']['target'] is None
        assert 'synthetic-operator-secret' not in demo.stdout + exported.stdout
        assert hashlib.sha256(route.read_bytes()).hexdigest() == before and not (project / 'SHOULD_NOT_RUN').exists()
        print(json.dumps({'installed_project_repl': 'passed', 'history_reopen': 'passed',
                          'init_with_broader_allowed_root': 'passed',
                          'project_demo_repl_and_cli': 'passed', 'project_cli_report': 'passed',
                          'source_unchanged': True, 'operator_state_isolated': True,
                          'scanner': payload['scan']['scanners']['semgrep']['status'],
                          'findings': len(payload['findings']), 'verdict': 'INCONCLUSIVE'}))


if __name__ == '__main__':
    main()
