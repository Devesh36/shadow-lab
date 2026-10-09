import asyncio
import json
import os

import pytest

from packages.core.models import RepositoryCreate, ScanCreate, Settings, SyntheticFixture, Target
from packages.core.service import Service
from packages.execution.demo_browser import DEMO, DemoBrowser, DemoTransport, validate_browser
from packages.policies.engine import PolicyEngine

pytestmark = pytest.mark.e2e


@pytest.fixture
def browser_target():
    target = os.getenv('SHADOWLAB_TEST_TARGET')
    if not target:
        pytest.skip('Start the reviewed local demo and set SHADOWLAB_TEST_TARGET')
    return target


def settings_for(target):
    return Settings(targets=[Target(url=target, authorized=True, approved=True, allow_loopback=True)],
                    fixture=SyntheticFixture(), sandbox_mode='trusted-local', timeout_seconds=10,
                    request_budget=200, requests_per_second=10, scan_timeout_seconds=180)


async def test_context_separation_stale_identity_logout_relogin_and_repeated_runs(browser_target):
    for _ in range(2):
        runner = DemoBrowser(PolicyEngine(settings_for(browser_target), browser_target), asyncio.Event())
        async with runner:
            assert len({id(context) for context in runner.contexts.values()}) == 3
            assert not await runner.contexts['anonymous'].cookies()
            owner = runner.pages['owner']
            await owner.evaluate("localStorage.setItem('canary', 'owner-only'); sessionStorage.setItem('canary', 'owner-only')")
            for who in ('other', 'anonymous'):
                assert await runner.pages[who].evaluate("localStorage.getItem('canary') || sessionStorage.getItem('canary')") is None
            await runner.login('owner', 'bob')
            with pytest.raises(ValueError, match='Active server identity'):
                await runner.action('owner', '/api/records/alice-record', 'Open record', 'alice-record')
            await runner.logout('owner')
            await runner.verify_identity('other', 'bob')
            await runner.verify_identity('anonymous', 'anonymous')
            await runner.login('owner', 'alice')
            for category in ('authentication', 'bola', 'exposure'):
                result = await runner.case(category)
                assert result['status'] == 'completed' and result['verdict'] == 'CONFIRMED', result
                assert all(e['identity_check']['passed'] and e['ui_observed'] for e in result['evidence'])
                encoded = json.dumps(result)
                assert 'demo-alice' not in encoded and 'demo-bob' not in encoded
                assert 'synthetic-not-a-real' not in encoded and 'shadowlab-demo-session' not in encoded
        assert runner.closed and not runner.browser.is_connected()


async def test_browser_timeout_failure_cleanup_and_next_run(browser_target, monkeypatch):
    original = DemoTransport.forward
    async def fail_profile(self, url, method, data, headers, identity):
        if url.endswith('/api/profile'):
            raise TimeoutError('Simulated bounded transport timeout')
        return await original(self, url, method, data, headers, identity)
    instances = []
    original_close = DemoBrowser.close
    async def close(self):
        await original_close(self)
        instances.append(self)
    monkeypatch.setattr(DemoBrowser, 'close', close)
    monkeypatch.setattr(DemoTransport, 'forward', fail_profile)
    result = await validate_browser(PolicyEngine(settings_for(browser_target), browser_target), asyncio.Event(), ['exposure'])
    assert result['exposure']['status'] == 'timeout' and result['exposure']['verdict'] == 'INCONCLUSIVE'
    assert instances[-1].closed and not instances[-1].browser.is_connected()
    monkeypatch.setattr(DemoTransport, 'forward', original)
    repeated = await validate_browser(PolicyEngine(settings_for(browser_target), browser_target), asyncio.Event(), ['exposure'])
    assert repeated['exposure']['status'] == 'completed' and repeated['exposure']['verdict'] == 'CONFIRMED', repeated


@pytest.mark.parametrize('cancellation_method', ['task', 'event'])
async def test_real_scan_cancellation_closes_browser_and_marks_incomplete(store, browser_target, monkeypatch, cancellation_method):
    started, release = asyncio.Event(), asyncio.Event()
    original = DemoTransport.forward
    instances = []
    async def blocked(self, url, method, data, headers, identity):
        if url.endswith('/api/unprotected'):
            started.set()
            await release.wait()
        return await original(self, url, method, data, headers, identity)
    original_close = DemoBrowser.close
    async def close(self):
        await original_close(self)
        instances.append(self)
    async def scanner(root):
        return {'status': 'completed', 'findings': []}
    monkeypatch.setattr(DemoTransport, 'forward', blocked)
    monkeypatch.setattr(DemoBrowser, 'close', close)
    monkeypatch.setattr('packages.agents.workflow.semgrep', scanner)
    monkeypatch.setattr('packages.agents.workflow.osv', scanner)
    store.save_settings(settings_for(browser_target))
    service = Service(store)
    repo = service.add_repository(RepositoryCreate(path=str(DEMO)))
    scan = service.create_scan(ScanCreate(repository_id=repo['id'], target=browser_target, dynamic=True, browser=True))
    service.start(scan['id'])
    try:
        await asyncio.wait_for(started.wait(), 30)
        if cancellation_method == 'task':
            assert service.cancel(scan['id'])
        else:
            service.cancellations[scan['id']].set()
        await asyncio.wait_for(service.tasks[scan['id']], 15)
        assert store.get('scan', scan['id'])['status'] == 'cancelled'
        findings = [f for f in store.list('finding', scan['id']) if f.get('browser')]
        assert findings and all(f['state'] == 'INCONCLUSIVE' and f['browser']['status'] == 'cancelled' for f in findings)
        assert instances[-1].closed and not instances[-1].browser.is_connected()
    finally:
        release.set()
        await service.close()


async def test_browser_out_of_scope_redirect_aborts_without_contact(browser_target):
    import httpx
    hits = []
    async def trap(reader, writer):
        hits.append(True)
        writer.close()
    other = await asyncio.start_server(trap, '127.0.0.1', 0)
    port = other.sockets[0].getsockname()[1]
    async def proxy(reader, writer):
        try:
            head = await reader.readuntil(b'\r\n\r\n')
            lines = head.decode().split('\r\n')
            method, path, _ = lines[0].split(' ')
            headers = dict(line.split(': ', 1) for line in lines[1:] if ': ' in line)
            length = int(next((v for k, v in headers.items() if k.lower() == 'content-length'), '0'))
            body = await reader.readexactly(length) if length else b''
            if path == '/api/profile':
                writer.write(f'HTTP/1.1 302 Found\r\nLocation: http://127.0.0.1:{port}/api/profile\r\nContent-Length: 0\r\n\r\n'.encode())
            else:
                forwarded = {k: v for k, v in headers.items() if k.lower() in ('cookie', 'content-type', 'accept-encoding')}
                async with httpx.AsyncClient(trust_env=False, follow_redirects=False) as client:
                    response = await client.request(method, browser_target + path, content=body or None, headers=forwarded)
                safe_headers = {k: v for k, v in response.headers.items() if k in ('content-type', 'set-cookie')}
                wire = f'HTTP/1.1 {response.status_code} OK\r\nContent-Length: {len(response.content)}\r\nConnection: close\r\n'
                wire += ''.join(f'{k}: {v}\r\n' for k, v in safe_headers.items())
                writer.write(wire.encode() + b'\r\n' + response.content)
            await writer.drain()
        finally:
            writer.close()
    server = await asyncio.start_server(proxy, '127.0.0.1', 0)
    target = f'http://127.0.0.1:{server.sockets[0].getsockname()[1]}'
    try:
        result = await validate_browser(PolicyEngine(settings_for(target), target), asyncio.Event(), ['exposure'])
        assert result['exposure']['status'] == 'blocked' and result['exposure']['verdict'] == 'INCONCLUSIVE'
        assert not hits
    finally:
        server.close()
        other.close()
        await server.wait_closed()
        await other.wait_closed()


async def test_exhausted_browser_budget_never_confirms(browser_target):
    settings = settings_for(browser_target)
    settings.request_budget = 1
    result = await validate_browser(PolicyEngine(settings, browser_target), asyncio.Event(), ['bola'])
    assert result['bola']['status'] == 'blocked' and result['bola']['verdict'] == 'INCONCLUSIVE'
    assert result['bola']['test_count'] == 0
