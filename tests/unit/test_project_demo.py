import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from packages.core.cli import main
from packages.core.project import ProjectSession
from packages.core.project_demo import run_project_demo
from packages.core.repl import run, run_bundled_demo


@pytest.fixture
def source(tmp_path, monkeypatch):
    root = tmp_path / 'Projects'
    project = root / 'My Project'
    route = project / 'app/api/profile/route.ts'
    route.parent.mkdir(parents=True)
    route.write_text('export function GET() { return Response.json({passwordHash: "synthetic"}); }')
    (project / 'package.json').write_text('{"scripts":{"postinstall":"touch MUST_NOT_RUN"}}')
    (project / 'sitecustomize.py').write_text('raise RuntimeError("PROJECT_EXECUTION_FORBIDDEN")')
    monkeypatch.setenv('SHADOWLAB_HOME', str(tmp_path / 'private'))
    monkeypatch.setenv('SHADOWLAB_REPOSITORY_ROOT', str(root))
    monkeypatch.setenv('SHADOWLAB_DATABASE_URL', 'invalid-operator-database')
    monkeypatch.chdir(project)
    return project


def test_real_project_demo_reports_coverage_and_keeps_source_unchanged(source):
    original = {p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()}
    session = ProjectSession(str(source), output=lambda _: None)
    try:
        result = run_project_demo(session, output=lambda _: None)
        payload = json.loads(Path(result['reports']['json']).read_text())
        assert payload['scan']['dynamic'] is False and payload['scan']['target'] is None
        assert payload['scan']['project_demo']['browser_validation']['status'] == 'unsupported'
        assert payload['scan']['project_demo']['patch_verification']['status'] == 'unsupported'
        assert payload['scan']['scanners']['osv']['status'] == 'disabled'
        assert payload['findings'] and all(f['state'] == 'INCONCLUSIVE' for f in payload['findings'])
        assert '## Project demo coverage' in Path(result['reports']['markdown']).read_text()
        assert all(Path(path).stat().st_mode & 0o777 == 0o600 for path in result['reports'].values())
        assert original == {p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()}
    finally:
        session.close()


def test_repl_demo_uses_selected_project_and_never_falls_back_to_bundled(source):
    output = []
    def forbidden(**kwargs):
        pytest.fail('Source project demo launched the bundled app')
    commands = iter(['/project "My Project"', '/demo', '/status', '/demo', '/history', '/quit'])
    run(input_fn=lambda _: next(commands), output=output.append, runtime_factory=forbidden)
    assert '\n'.join(output).count('Project demo finished') == 2
    reopened = ProjectSession(str(source), output=lambda _: None)
    try:
        assert len(reopened.history()) == 2
    finally:
        reopened.close()


def test_repl_demo_defaults_to_launch_directory_despite_broader_root(source):
    output = []
    commands = iter(['demo', 'quit'])
    run(input_fn=lambda _: next(commands), output=output.append,
        runtime_factory=lambda **kwargs: pytest.fail('Unexpected bundled runtime'))
    assert 'Project demo: ' + str(source) in output


def test_unsupported_layout_does_not_claim_a_clean_project(source):
    (source / 'app/api/profile/route.ts').unlink()
    output = []
    session = ProjectSession(str(source), output=lambda _: None)
    try:
        result = run_project_demo(session, output=output.append)
        assert result['coverage']['route_discovery']['status'] == 'unsupported'
        assert 'No hypotheses recorded. This does not establish that the repository is secure.' in output
    finally:
        session.close()


@pytest.mark.parametrize('failure', [ValueError('source analysis failed'), KeyboardInterrupt()])
def test_project_demo_failure_or_cancel_never_exports_prior_results(failure):
    class Project:
        path = '/synthetic'
        def analyze(self):
            raise failure
        def export(self, *args):
            pytest.fail('Failure exported a prior scan')
    with pytest.raises(type(failure)):
        run_project_demo(Project(), output=lambda _: None)


@pytest.mark.parametrize('arguments', [['demo', '--browser'], ['demo', '.', '--bundled']])
def test_cli_invalid_demo_options_are_rejected_before_any_state(source, monkeypatch, arguments):
    monkeypatch.setattr(sys, 'argv', ['shadow', *arguments])
    with pytest.raises(SystemExit) as result:
        main()
    assert result.value.code == 2
    assert not (source.parents[1] / 'private').exists()


def test_cli_default_opens_console_without_creating_operator_state(source, monkeypatch):
    called = []
    monkeypatch.setattr('packages.core.repl.run', lambda: called.append('opened'))
    monkeypatch.setattr(sys, 'argv', ['shadow'])
    main()
    assert called == ['opened']
    assert not (source.parents[1] / 'private').exists()


def test_real_cli_demo_scans_launch_repo_and_exports_without_operator_db(source):
    env = {**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[2])}
    result = subprocess.run([sys.executable, '-I', '-m', 'packages.core.cli', 'demo'], cwd=source,
                            env=env, text=True, capture_output=True, timeout=150)
    assert result.returncode == 0, result.stderr
    assert 'Project demo: ' + str(source) in result.stdout and 'Project demo finished' in result.stdout
    assert 'PROJECT_EXECUTION_FORBIDDEN' not in result.stdout + result.stderr
    assert not (source / '.shadowlab').exists() and not (source / 'MUST_NOT_RUN').exists()
    def invoke(*arguments):
        return subprocess.run([sys.executable, '-I', '-m', 'packages.core.cli', *arguments],
                              cwd=source, env=env, text=True, capture_output=True, timeout=30)
    findings = invoke('findings', '--project', '.')
    assert findings.returncode == 0 and json.loads(findings.stdout)
    report = invoke('report', '--project', '.', '--format', 'json')
    assert report.returncode == 0
    payload = json.loads(report.stdout)
    assert payload['scan']['project_demo']['browser_validation']['status'] == 'unsupported'
    foreign = invoke('report', '--project', '.', '--scan-id', 'foreign-scan')
    assert foreign.returncode == 2 and 'not available in this project' in foreign.stderr


@pytest.mark.parametrize('failure,code', [(ValueError('failed scan'), 2), (KeyboardInterrupt(), 130)])
def test_cli_project_failure_and_cancellation_close_session(source, monkeypatch, failure, code):
    closed = []
    class Project:
        def __init__(self, *args, **kwargs):
            pass
        def close(self):
            closed.append(True)
    def fail(*args, **kwargs):
        raise failure
    monkeypatch.setattr('packages.core.project.ProjectSession', Project)
    monkeypatch.setattr('packages.core.project_demo.run_project_demo', fail)
    monkeypatch.setattr(sys, 'argv', ['shadow', 'demo'])
    with pytest.raises(SystemExit) as result:
        main()
    assert result.value.code == code and closed == [True]


@pytest.mark.parametrize('failure', [ValueError('unsupported setup'), KeyboardInterrupt()])
def test_cli_bundled_cleanup_on_setup_failure(failure):
    closed = []
    class Runtime:
        def __init__(self, **kwargs):
            pass
        def start(self):
            raise failure
        def close(self):
            closed.append(True)
    with pytest.raises(type(failure)):
        run_bundled_demo(output=lambda _: None, runtime_factory=Runtime)
    assert closed == [True]


def test_cli_bundled_cancels_known_scan_before_cleanup():
    calls = []
    class Runtime:
        def __init__(self, **kwargs):
            pass
        def start(self):
            pass
        def request(self, method, path, **kwargs):
            calls.append(path)
            if path == '/demo/start':
                return SimpleNamespace(json=lambda: {'id': 'active'})
            if path.endswith('/cancel'):
                return None
            raise KeyboardInterrupt()
        def close(self):
            calls.append('closed')
    with pytest.raises(KeyboardInterrupt):
        run_bundled_demo(output=lambda _: None, runtime_factory=Runtime)
    assert calls[-2:] == ['/scans/active/cancel', 'closed']
