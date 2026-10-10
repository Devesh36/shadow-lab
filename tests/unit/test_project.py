import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from packages.core.project import ProjectSession, worker
from packages.core.models import ScanCreate
from packages.core.service import Service
from packages.core.repl import run


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = tmp_path / 'Source Projects'
    source = root / 'Mixed Case Project'
    route = source / 'app/api/profile/route.ts'
    route.parent.mkdir(parents=True)
    route.write_text('export async function GET() { return Response.json({ passwordHash: "synthetic" }); }')
    (source / 'package.json').write_text('{"scripts":{"postinstall":"touch SHOULD_NOT_RUN"}}')
    (source / 'sitecustomize.py').write_text('raise RuntimeError("PROJECT_CODE_MUST_NOT_RUN")')
    monkeypatch.setenv('SHADOWLAB_REPOSITORY_ROOT', str(root))
    monkeypatch.setenv('SHADOWLAB_HOME', str(tmp_path / 'private'))
    monkeypatch.setenv('SHADOWLAB_DATABASE_URL', 'invalid-operator-database')
    monkeypatch.setenv('SHADOWLAB_DATA_DIR', str(tmp_path / 'operator'))
    monkeypatch.setenv('SHADOWLAB_LLM_API_KEY', 'synthetic-operator-secret')
    session = ProjectSession('Mixed Case Project', output=lambda _: None)
    yield session
    session.close()


def test_real_scan_is_source_only_private_and_repeatable(project):
    before = {p.relative_to(project.path): p.read_bytes() for p in project.path.rglob('*') if p.is_file()}
    first = project.analyze()
    assert first['status'] == 'completed' and not first['dynamic'] and first['target'] is None
    assert first['scanners']['osv']['status'] == 'disabled'
    assert first['scanners']['semgrep']['status'] == 'completed'
    assert first['surface']['routes'][0]['path'] == '/api/profile'
    assert project.findings and all(f['state'] == 'INCONCLUSIVE' for f in project.findings)
    second = project.analyze()
    assert first['id'] != second['id'] and len(project.history()) == 2
    assert project.use(2)['id'] == first['id']
    export = project.export('json')
    assert 'synthetic-operator-secret' not in export.read_text()
    assert export.stat().st_mode & 0o777 == 0o600
    assert json.loads(export.read_text())['scan']['id'] == first['id']
    assert 'osv: disabled' in project.export().read_text()
    assert before == {p.relative_to(project.path): p.read_bytes() for p in project.path.rglob('*') if p.is_file()}
    assert not (project.directory.parents[2] / 'operator').exists()
    project.close()
    reopened = ProjectSession(str(project.path), output=lambda _: None)
    try:
        assert reopened.scan['id'] == second['id'] and len(reopened.history()) == 2
    finally:
        reopened.close()


def test_project_scope_and_separate_history(project, tmp_path):
    outside = tmp_path / 'Outside'
    outside.mkdir()
    with pytest.raises(ValueError, match='below'):
        ProjectSession(str(outside))
    link = project.allowed / 'Escaping'
    link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match='below'):
        ProjectSession('Escaping')
    with pytest.raises(ValueError, match='does not exist'):
        ProjectSession('Absent')
    other = project.allowed / 'Other'
    other.mkdir()
    second = ProjectSession('Other')
    try:
        assert second.directory != project.directory and second.history() == []
        with pytest.raises(ValueError, match='scan number'):
            second.use(1)
        with pytest.raises(ValueError, match='Run scan'):
            second.export()
    finally:
        second.close()


@pytest.mark.parametrize('failure', ['timeout', 'interrupt', 'exit', 'launch'])
def test_worker_failure_cleanup_and_retry(project, monkeypatch, failure):
    popen = subprocess.Popen
    processes = []
    def launch(*args, **kwargs):
        if failure == 'launch':
            raise OSError('Synthetic process launch failure')
        proc = popen([sys.executable, '-I', '-c',
                      'import time; time.sleep(30)' if failure != 'exit' else 'raise SystemExit(2)'], **kwargs)
        processes.append(proc)
        return proc
    with monkeypatch.context() as patch:
        patch.setattr('packages.core.project.subprocess.Popen', launch)
        if failure == 'interrupt':
            project.output = lambda _: (_ for _ in ()).throw(KeyboardInterrupt())
        with pytest.raises((TimeoutError, KeyboardInterrupt, ValueError, OSError)):
            project.analyze(timeout=0.05)
    assert project.scan['status'] == ('cancelled' if failure == 'interrupt' else 'failed')
    assert all(proc.poll() is not None for proc in processes)
    assert project.process is None and project.lock is None
    saved = project.scan_id
    assert json.loads(project.export('json').read_text())['scan']['status'] != 'completed'
    project.output = lambda _: None
    assert project.analyze()['status'] == 'completed'
    assert len(project.history()) == 2 and project.history()[1]['id'] == saved


def test_second_console_cannot_steal_lock_or_overwrite_active_scan(project):
    project.acquire()
    scan = Service(project.store).create_scan(ScanCreate(repository_id=project.repo['id']))
    second = ProjectSession(str(project.path))
    try:
        assert second.scan['status'] == 'queued'
        with pytest.raises(ValueError, match='active scan'):
            second.analyze()
        assert project.store.get('scan', scan['id'])['status'] == 'queued'
    finally:
        second.close()
        project.release()
    recovered = ProjectSession(str(project.path))
    try:
        assert recovered.scan['status'] == 'failed'
        assert 'Interrupted session' in recovered.scan['coverage']
    finally:
        recovered.close()


def test_worker_refuses_dynamic_records(project):
    scan = project.store.put('scan', {'repository_id': project.repo['id'], 'dynamic': True, 'target': 'http://127.0.0.1:3001',
                                    'status': 'queued'})
    with pytest.raises(ValueError, match='source-only'):
        worker(project.directory, scan['id'])


def test_repl_preserves_path_case_history_and_failure_status(project):
    lines = iter(['PROJECT "Mixed Case Project"', 'scan', 'routes', 'history', 'use 1', 'findings', 'fix 1',
                  'scan --target http://127.0.0.1:3001', 'report json', 'stop', 'project "Mixed Case Project"',
                  'history', 'quit'])
    output = []
    run(input_fn=lambda _: next(lines), output=output.append)
    text = '\n'.join(output)
    assert 'Project selected: ' + str(project.path) in text
    assert 'GET /api/profile — app/api/profile/route.ts:1' in text
    assert 'Project patches are disabled' in text
    assert 'selected' in text and 'Project report:' in text
    assert len(project.history()) == 1


def test_bundle_generator_ignores_generated_assets(tmp_path):
    root = Path(__file__).resolve().parents[2]
    (tmp_path / 'scripts').mkdir()
    shutil.copyfile(root / 'scripts/update-bundle.py', tmp_path / 'scripts/update-bundle.py')
    for name in ('apps/api/.vercel/generated.py', 'packages/__pycache__/generated.py', 'packages/core/trusted.py'):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('')
    subprocess.run([sys.executable, str(tmp_path / 'scripts/update-bundle.py')], check=True)
    files = json.loads((tmp_path / 'packages/core/bundle-files.json').read_text())
    assert 'packages/core/trusted.py' in files
    assert not any('.vercel' in name or '__pycache__' in name for name in files)


def test_failed_new_scan_never_inherits_previous_completed_report(project, monkeypatch):
    completed = project.analyze()['id']
    def denied(*a, **k):
        raise OSError('Synthetic launch failure')
    monkeypatch.setattr('packages.core.project.subprocess.Popen', denied)
    with pytest.raises(OSError):
        project.analyze()
    assert project.scan_id != completed and project.scan['status'] == 'failed'
    assert project.findings == []
    assert json.loads(project.export('json').read_text())['scan']['status'] == 'failed'
    assert project.use(2)['id'] == completed


def test_timeout_kills_stubborn_scanner_descendant(project, monkeypatch, tmp_path):
    import time
    pid_file = tmp_path / 'scanner.pid'
    popen = subprocess.Popen
    script = ('import subprocess,sys,time,signal; signal.signal(signal.SIGTERM,signal.SIG_IGN); '
              'p=subprocess.Popen([sys.executable,"-I","-c",'
              '"import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)"]); '
              f'open({str(pid_file)!r},"w").write(str(p.pid)); time.sleep(60)')
    def launch(*a, **k):
        return popen([sys.executable, '-I', '-c', script], **k)
    monkeypatch.setattr('packages.core.project.subprocess.Popen', launch)
    with pytest.raises(TimeoutError):
        project.analyze(timeout=1)
    monkeypatch.setattr('packages.core.project.subprocess.Popen', popen)
    assert pid_file.exists()
    pid = pid_file.read_text()
    for _ in range(20):
        state = subprocess.run(['ps', '-p', pid, '-o', 'stat='], capture_output=True, text=True).stdout.strip()
        if not state or state.startswith('Z'):
            break
        time.sleep(0.05)
    assert not state or state.startswith('Z'), 'Scanner descendant is still running'
    assert project.process is None and project.lock is None


def test_worker_reported_failure_keeps_incomplete_coverage_and_allows_retry(project):
    manifest = project.path / 'package.json'
    manifest.write_text('{invalid synthetic manifest')
    with pytest.raises(ValueError, match='did not complete'):
        project.analyze()
    assert project.scan['status'] == 'failed' and 'Analysis incomplete' in project.scan['coverage']
    assert json.loads(project.export('json').read_text())['scan']['coverage']
    manifest.write_text('{}')
    assert project.analyze()['status'] == 'completed'
