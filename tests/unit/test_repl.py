import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from packages.core.demo_runtime import DemoRuntime, bundled_workspace, child_environment
from packages.core.repl import run

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
