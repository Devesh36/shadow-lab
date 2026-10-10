"""Source-only project sessions. Execute trusted analysis tools, never project code."""
import asyncio
import hashlib
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from packages.core.demo_runtime import child_environment, home
from packages.core.models import RepositoryCreate, ScanCreate, Settings
from packages.core.report import report
from packages.core.service import Service
from packages.db.store import Store

try:
    import fcntl
except ImportError:  # Keep help/doctor available on unsupported native Windows.
    fcntl = None


def source_settings():
    # No target, credentials, LLM calls or dependency-advisory network access.
    return Settings(categories=['bola', 'authentication', 'exposure', 'headers', 'injection'])


def open_store(directory):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    store = Store(f"sqlite:///{directory / 'shadowlab.db'}", data_dir=directory)
    store.initialize()
    return store


class ProjectSession:
    def __init__(self, path, output=print, base=None):
        if os.name != 'posix':
            raise ValueError('Project sessions require macOS or Linux; use WSL on Windows')
        self.allowed = Path(os.getenv('SHADOWLAB_REPOSITORY_ROOT', '.')).expanduser().resolve()
        raw = Path(path).expanduser()
        try:
            self.path = (raw if raw.is_absolute() else self.allowed / raw).resolve(strict=True)
        except OSError:
            raise ValueError('Project directory does not exist') from None
        if not self.path.is_dir() or not self.path.is_relative_to(self.allowed):
            raise ValueError('Project must be below SHADOWLAB_REPOSITORY_ROOT (defaults to the working directory)')
        self.output = output
        digest = hashlib.sha256(os.fsencode(self.path)).hexdigest()[:20]
        self.directory = (Path(base) if base else home()) / 'projects' / digest
        self.store = open_store(self.directory)
        self.repo = Service(self.store).add_repository(RepositoryCreate(path=str(self.path)))
        self.process = None
        self.scan_id = None
        self.lock = None
        try:
            self.acquire()
        except ValueError:
            pass  # Another console owns an active scan; history remains readable.
        else:
            try:
                for scan in self.store.list('scan'):
                    if scan['status'] in ('queued', 'running'):
                        self.finish(scan['id'], 'failed', 'Interrupted session; coverage incomplete')
            finally:
                self.release()
        scans = self.history()
        if scans:
            self.scan_id = scans[0]['id']

    def acquire(self):
        lock = (self.directory / 'scan.lock').open('a')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock.close()
            raise ValueError('This project already has an active scan in another console') from None
        self.lock = lock

    def release(self):
        if self.lock:
            self.lock.close()
            self.lock = None

    @property
    def scan(self):
        return self.store.get('scan', self.scan_id) if self.scan_id else None

    @property
    def findings(self):
        return self.store.list('finding', self.scan_id) if self.scan_id else []

    def history(self):
        return list(reversed(self.store.list('scan')))[0:10]

    def use(self, number):
        history = self.history()
        if not 1 <= number <= len(history):
            raise ValueError('Choose a scan number from history')
        self.scan_id = history[number - 1]['id']
        return self.scan

    def terminate(self):
        process, self.process = self.process, None
        if process is None:
            return
        # Kill the whole group even if the worker exited but a scanner remains.
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=3)

    def finish(self, scan_id, status, reason):
        self.store.put('scan', {'status': status, 'stage': status, 'coverage': reason}, id=scan_id)
        for finding in self.store.list('finding', scan_id):
            self.store.put('finding', {'state': 'INCONCLUSIVE', 'validation': reason}, id=finding['id'])
        self.store.event(scan_id, status, reason)

    def analyze(self, timeout=125):
        self.acquire()
        active_id = None
        try:
            scan = Service(self.store).create_scan(ScanCreate(repository_id=self.repo['id']))
            self.scan_id = scan['id']  # Failures must never display an earlier successful scan.
            active_id = self.scan_id
            env = child_environment()
            env.update(SHADOWLAB_DATA_DIR=str(self.directory), SHADOWLAB_REPOSITORY_ROOT=str(self.allowed))
            log = self.directory / (self.scan_id + '.log')
            with os.fdopen(os.open(log, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'w') as stream:
                self.process = subprocess.Popen(
                    [sys.executable, '-I', '-m', 'packages.core.project', str(self.directory), self.scan_id],
                    cwd=Path(__file__).resolve().parents[2], env=env, stdout=stream, stderr=stream,
                    start_new_session=True, pass_fds=(self.lock.fileno(),))
            deadline = time.monotonic() + timeout
            last = None
            while self.process.poll() is None:
                stage = self.scan['stage']
                if stage != last:
                    last = stage
                    self.output('Investigation: ' + stage)
                if time.monotonic() >= deadline:
                    raise TimeoutError('Project scan exceeded its time limit; coverage incomplete')
                time.sleep(0.1)
            if self.process.returncode or self.scan['status'] != 'completed':
                raise ValueError('Project analysis did not complete; inspect the private scan log')
            self.output('Source analysis completed. Static hypotheses remain INCONCLUSIVE.')
            for name, result in self.scan.get('scanners', {}).items():
                self.output(f"Scanner {name}: {result['status']}" +
                            (f" — {result['reason']}" if result.get('reason') else ''))
            return self.scan
        except BaseException as exc:
            self.terminate()  # Stop writers before recording the final verdict.
            if active_id:
                self.finish(active_id, 'cancelled' if isinstance(exc, KeyboardInterrupt) else 'failed',
                            'Cancelled; coverage incomplete' if isinstance(exc, KeyboardInterrupt)
                            else 'Analysis incomplete: ' + type(exc).__name__)
            raise
        finally:
            self.terminate()
            self.release()

    def export(self, format='markdown'):
        if not self.scan_id:
            raise ValueError('Run scan or select a saved scan with history and use NUMBER first')
        if format not in ('markdown', 'json'):
            raise ValueError('Use report or report json')
        directory = self.directory / 'reports'
        directory.mkdir(exist_ok=True, mode=0o700)
        path = directory / (self.scan_id + ('.json' if format == 'json' else '.md'))
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as stream:
            stream.write(report(self.store, self.scan_id, format))
        return path

    def close(self):
        self.terminate()
        self.release()
        self.store.engine.dispose()


def worker(directory, scan_id):
    from packages.agents.workflow import Workflow
    store = open_store(directory)
    try:
        scan = store.get('scan', scan_id)
        if not scan or scan['dynamic'] or scan.get('browser') or scan.get('target'):
            raise ValueError('Project worker admits source-only scans')
        repo = store.get('repository', scan['repository_id'])
        Service(store).add_repository(RepositoryCreate(path=repo['path']))
        asyncio.run(Workflow(store, scan_id, settings=source_settings()).run())
    finally:
        store.engine.dispose()


if __name__ == '__main__':
    worker(*sys.argv[1:])
