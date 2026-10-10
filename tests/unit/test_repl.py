import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from packages.core.demo_runtime import DemoRuntime, bundled_workspace, child_environment
from packages.core.repl import run
from packages.core.repl_commands import complete, display, terminal_input

PROJECT = Path(__file__).resolve().parents[2]


def test_console_opens_outside_checkout_without_creating_state(tmp_path):
    result = subprocess.run([sys.executable, '-m', 'packages.core.cli', 'Repl'], cwd=tmp_path,
                            input='help\nquit\n', text=True, capture_output=True,
                            env={**os.environ, 'PYTHONPATH': str(PROJECT)}, timeout=15)
    assert result.returncode == 0
    assert 'Demo' in result.stdout and 'ShadowLab closed' in result.stdout
    assert not list(tmp_path.iterdir())


def test_bundle_is_independent_of_current_directory_and_ignores_private_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    workspace = bundled_workspace(tmp_path / 'cache')
    assert (workspace / 'apps/web/app/demo/page.tsx').is_file()
    assert (workspace / 'examples/vulnerable-nextjs/app/api/session/route.ts').is_file()
    assert not (workspace / '.shadowlab').exists()
    assert not (workspace / '.env').exists()
    assert not (workspace / 'apps/web/node_modules').exists()
    assert not (workspace / 'apps/web/.next').exists()
    (workspace / 'examples/vulnerable-nextjs/lib/data.ts').write_text('changed')
    assert bundled_workspace(tmp_path / 'cache') == workspace
    assert (workspace / 'examples/vulnerable-nextjs/lib/data.ts').read_bytes() == (PROJECT / 'examples/vulnerable-nextjs/lib/data.ts').read_bytes()


def test_demo_environment_does_not_inherit_operator_credentials(monkeypatch):
    for name in ('SHADOWLAB_API_TOKEN', 'SHADOWLAB_DATABASE_URL', 'SHADOWLAB_LLM_API_KEY', 'AWS_SECRET_ACCESS_KEY'):
        monkeypatch.setenv(name, 'operator-secret')
    monkeypatch.setenv('NODE_EXTRA_CA_CERTS', '/managed/ca.pem')
    env = child_environment()
    assert 'operator-secret' not in json.dumps(env)
    assert env['NODE_EXTRA_CA_CERTS'] == '/managed/ca.pem'


@pytest.mark.parametrize('failure', [ValueError('unsupported setup'), KeyboardInterrupt()])
def test_repl_failed_or_cancelled_setup_cleans_up_and_allows_retry(failure):
    instances = []
    class Runtime:
        def __init__(self, **kwargs):
            self.closed = False
            instances.append(self)
        def start(self):
            raise failure
        def close(self):
            self.closed = True
    commands = iter(['demo', 'demo', 'quit'])
    output = []
    run(input_fn=lambda _: next(commands), output=output.append, runtime_factory=Runtime)
    assert len(instances) == 2 and all(r.closed for r in instances)
    assert any('incomplete' in value or 'Cancelled' in value for value in output)


def test_repl_eof_closes_running_services_and_repeated_runs_are_fresh(monkeypatch, tmp_path):
    instances = []
    monkeypatch.setenv('SHADOWLAB_NO_OPEN', '1')
    class Runtime:
        def __init__(self, **kwargs):
            self.closed = False
            self.web_url = 'http://127.0.0.1:1234'
            self.run_dir = tmp_path
            instances.append(self)
        def start(self):
            return self
        def request(self, method, path, **kwargs):
            if path == '/demo/start':
                return SimpleNamespace(json=lambda: {'id': str(len(instances))})
            return SimpleNamespace(json=lambda: {'status': 'completed', 'stage': 'completed', 'findings': []})
        def close(self):
            self.closed = True
    commands = iter(['demo', 'stop', 'demo'])
    def read(_):
        try:
            return next(commands)
        except StopIteration:
            raise EOFError
    run(input_fn=read, output=lambda _: None, runtime_factory=Runtime)
    assert len(instances) == 2 and all(r.closed for r in instances)


def test_runtime_cleanup_terminates_its_process_group(tmp_path):
    runtime = DemoRuntime(base=tmp_path)
    process = runtime.launch([sys.executable, '-c', 'import time; time.sleep(60)'],
                             tmp_path, child_environment(), tmp_path / 'service.log')
    runtime.close()
    assert process.poll() is not None
    assert runtime.processes == []
    runtime.close()


def test_repl_interrupt_cancels_active_scan_before_stopping_services(monkeypatch):
    monkeypatch.setenv('SHADOWLAB_NO_OPEN', '1')
    calls = []
    class Runtime:
        web_url = 'http://127.0.0.1:1234'
        def __init__(self, **kwargs):
            pass
        def start(self):
            pass
        def request(self, method, path, **kwargs):
            calls.append(path)
            if path == '/demo/start':
                return SimpleNamespace(json=lambda: {'id': 'active-scan'})
            if path.endswith('/cancel'):
                return SimpleNamespace(json=lambda: {'cancelled': True})
            raise KeyboardInterrupt
        def close(self):
            calls.append('closed')
    commands = iter(['demo', 'quit'])
    run(input_fn=lambda _: next(commands), output=lambda _: None, runtime_factory=Runtime)
    assert calls[-2:] == ['/scans/active-scan/cancel', 'closed']


def test_context_switch_and_invalid_input_preserve_the_correct_session(monkeypatch):
    monkeypatch.setenv('SHADOWLAB_NO_OPEN', '1')
    runtimes, projects = [], []
    class Runtime:
        web_url = 'http://127.0.0.1:1234'
        def __init__(self, **kwargs):
            self.closed = False
            runtimes.append(self)
        def start(self):
            pass
        def request(self, method, path, **kwargs):
            return SimpleNamespace(json=lambda: {'id': 'demo-scan', 'status': 'completed',
                                                'stage': 'completed', 'findings': []})
        def close(self):
            self.closed = True
    class Project:
        def __init__(self, path, **kwargs):
            if path == 'Missing':
                raise ValueError('Missing project')
            assert path == 'Mixed Case'
            self.path, self.closed = path, False
            projects.append(self)
        def close(self):
            self.closed = True
    output = []
    commands = iter(['demo', 'project "Missing"', 'findings', 'project "Unclosed',
                     'project "Mixed Case"', 'demo', 'quit'])
    run(input_fn=lambda _: next(commands), output=output.append, runtime_factory=Runtime, project_factory=Project)
    assert len(runtimes) == 2 and all(r.closed for r in runtimes)
    assert len(projects) == 1 and projects[0].closed
    assert 'Unclosed quote' in '\n'.join(output)
    assert '\n'.join(output).count('No findings in this investigation.') == 3


def test_slash_project_workflow_context_status_and_inspection_do_not_execute_evidence():
    calls, output, prompts = [], [], []
    finding = {'title': 'Ownership missing', 'state': 'INCONCLUSIVE', 'endpoint': '/api/items',
               'severity': 'high', 'category': 'bola', 'validation': 'Static hypothesis',
               'sources': [{'file': 'app/\033[2Jroute.ts', 'line': 3}],
               'evidence': [{'token': 'synthetic-hidden-token', 'body': 'sensitive-response'}]}
    class Project:
        path = 'Mixed Case'
        scan_id = 'saved-scan'
        scan = {'id': 'saved-scan', 'status': 'completed', 'stage': 'completed',
                'coverage': 'Source-only', 'scanners': {'osv': {'status': 'disabled'}}}
        findings = [finding]
        def __init__(self, path, **kwargs):
            calls.append(('project', path))
        def analyze(self):
            calls.append('scan')
        def history(self):
            return [{**self.scan, 'created_at': '2026-10-10'}]
        def use(self, number):
            calls.append(('use', number))
            return self.scan
        def export(self, format):
            calls.append(('report', format))
            return 'private/report.json'
        def close(self):
            calls.append('closed')
    commands = iter(['/status', '/PROJECT "Mixed Case"', '/context', '/scan', '/inspect 1',
                     '/history', '/use 1', '/export json', '/clear', '/fix 1', '/stop', '/status', '/exit'])
    def read(prompt):
        prompts.append(prompt)
        return next(commands)
    run(input_fn=read, output=output.append, project_factory=Project)
    text = '\n'.join(output)
    assert ('project', 'Mixed Case') in calls and ('report', 'json') in calls
    assert ('use', 1) in calls and calls.count('closed') == 1
    assert 'shadow[project]> ' in prompts and prompts[-1] == 'shadow> '
    assert 'Scanner osv: disabled' in text and 'Source-only' in text
    assert 'Source: app/\\u001b[2Jroute.ts:3' in text and '\033' not in text
    assert 'synthetic-hidden-token' not in text and 'sensitive-response' not in text
    assert 'Project patches are disabled' in text


@pytest.mark.parametrize('command', ['/demo extra', '/demo browser extra', '/fix 0', '/fix 1 extra',
                                     '/project', '/project a b', '/scan extra', '/quit extra',
                                     '/use -1', '/inspect ١', '/inspect 9999999', '/report yaml',
                                     '/doctor extra', '/init extra'])
def test_invalid_arguments_never_launch_or_approve_actions(command):
    output = []
    def forbidden(**kwargs):
        pytest.fail('Invalid input launched a runtime')
    commands = iter([command, '/quit'])
    run(input_fn=lambda _: next(commands), output=output.append, runtime_factory=forbidden,
        project_factory=forbidden)
    assert any(message.startswith('Use /') for message in output)


def test_init_topic_help_unknown_commands_and_unselected_inspect_are_action_free(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    calls, output = [], []
    class Project:
        path = '.'
        def __init__(self, path, **kwargs):
            calls.append(path)
        def close(self):
            calls.append('closed')
    commands = iter(['/help /fix', '/help unknown', '/scna', '!touch PWNED',
                     '/inspect 1', '/help', '/init', '/quit'])
    run(input_fn=lambda _: next(commands), output=output.append, project_factory=Project)
    text = '\n'.join(output)
    assert calls == [str(tmp_path), 'closed']
    assert 'Did you mean /scan?' in text
    assert 'Choose a finding number' in text
    assert 'approves the experiment' in text and 'shell commands are not executed' in text
    assert all(group in output for group in ('Session', 'Project', 'Evidence', 'Demo'))


@pytest.mark.parametrize('outside', [False, True])
def test_init_selects_launch_directory_and_preserves_root_allowlist(monkeypatch, tmp_path, outside):
    allowed = tmp_path / 'allowed'
    launch = (tmp_path if outside else allowed) / 'Launch Project'
    allowed.mkdir()
    launch.mkdir()
    monkeypatch.chdir(launch)
    monkeypatch.setenv('SHADOWLAB_REPOSITORY_ROOT', str(allowed))
    monkeypatch.setenv('SHADOWLAB_HOME', str(tmp_path / 'private'))
    output = []
    commands = iter(['/init', '/status', '/quit'])
    run(input_fn=lambda _: next(commands), output=output.append)
    text = '\n'.join(output)
    if outside:
        assert 'Project command incomplete' in text and 'Context: none' in text
        assert not (tmp_path / 'private').exists()
    else:
        assert 'Project selected: ' + str(launch) in text
        assert 'Context: project · ' + str(launch) in text
        assert 'No selected scan' in text


def test_slash_demo_json_report_and_explicit_patch_request(monkeypatch, tmp_path):
    monkeypatch.setenv('SHADOWLAB_NO_OPEN', '1')
    calls, output = [], []
    finding = {'id': 'finding', 'state': 'CONFIRMED', 'title': 'Auth', 'endpoint': '/api/x',
               'category': 'authentication'}
    scan = {'id': 'demo-scan', 'status': 'completed', 'stage': 'completed', 'findings': [finding]}
    class Runtime:
        web_url = 'http://127.0.0.1:1234'
        run_dir = tmp_path
        def __init__(self, **kwargs):
            pass
        def start(self):
            pass
        def request(self, method, path, **kwargs):
            calls.append((method, path, kwargs))
            if path.startswith('/reports/'):
                return SimpleNamespace(text=json.dumps({'scan': scan, 'findings': [finding]}))
            if path.endswith('/propose-fix'):
                return SimpleNamespace(json=lambda: {'verification': {'passed': True}})
            return SimpleNamespace(json=lambda: scan)
        def close(self):
            calls.append('closed')
    commands = iter(['/demo', '/status', '/inspect 1', '/export json', '/fix 1 extra', '/fix 1', '/quit'])
    run(input_fn=lambda _: next(commands), output=output.append, runtime_factory=Runtime)
    patches = [call for call in calls if isinstance(call, tuple) and call[1].endswith('/propose-fix')]
    assert len(patches) == 1
    exported = tmp_path / 'report-demo-scan.json'
    assert json.loads(exported.read_text())['scan']['status'] == 'completed'
    assert exported.stat().st_mode & 0o777 == 0o600
    assert ('GET', '/reports/demo-scan', {'params': {'format': 'json'}}) in calls
    assert calls[-1] == 'closed'
    assert 'passed; awaiting review' in '\n'.join(output)


def test_completion_is_command_only_and_terminal_controls_are_escaped():
    assert complete('/sta', 0) == '/status'
    assert complete('sta', 0) == 'status'
    assert complete('/sta', 1) is None
    assert complete('/exp', 0) == '/export'
    assert complete('/etc/private', 0) is None
    assert display('file\n\033[2J\u202e.ts') == 'file\\u000a\\u001b[2J\\u202e.ts'


def test_line_editor_restores_state_and_does_not_persist_console_history():
    readline = pytest.importorskip('readline')
    before = [readline.get_history_item(i) for i in range(1, readline.get_current_history_length() + 1)]
    completer, delimiters = readline.get_completer(), readline.get_completer_delims()
    try:
        readline.add_history('external-history')
        with pytest.raises(ValueError), terminal_input(True):
            assert readline.get_current_history_length() == 0
            readline.add_history('/project "private-path"')
            raise ValueError('test cleanup')
        restored = [readline.get_history_item(i) for i in range(1, readline.get_current_history_length() + 1)]
        assert restored == before + ['external-history']
        assert readline.get_completer() == completer and readline.get_completer_delims() == delimiters
    finally:
        readline.clear_history()
        for item in before:
            readline.add_history(item)
