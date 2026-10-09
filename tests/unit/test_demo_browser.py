import asyncio
from pathlib import Path

import pytest

from packages.core.models import RepositoryCreate, ScanCreate, Settings, SyntheticFixture, Target
from packages.core.service import Service
from packages.execution.demo_browser import DEMO, DemoTransport, require_demo, validate_browser
from packages.policies.engine import PolicyDenied, PolicyEngine


def browser_settings(target='http://127.0.0.1:3012', **kwargs):
    return Settings(targets=[Target(url=target, authorized=True, approved=True, allow_loopback=True)],
        sandbox_mode='trusted-local', fixture=SyntheticFixture(), request_budget=200,
        timeout_seconds=5, requests_per_second=10, scan_timeout_seconds=180, **kwargs)


def test_trusted_demo_origin_fixture_and_manifest_boundaries(tmp_path):
    settings = browser_settings()
    require_demo(DEMO, settings, 'http://127.0.0.1:3012')
    with pytest.raises(PolicyDenied, match='shipped'):
        require_demo(tmp_path, settings, 'http://127.0.0.1:3012')
    with pytest.raises(PolicyDenied, match='loopback'):
        require_demo(DEMO, settings, 'http://localhost:3012')
    settings.fixture.other_token = 'different'
    with pytest.raises(PolicyDenied, match='unchanged'):
        require_demo(DEMO, settings, 'http://127.0.0.1:3012')


@pytest.mark.parametrize('url,method,body,headers', [
    ('http://127.0.0.1:3013/api/session', 'GET', b'', {}),
    ('http://169.254.169.254/', 'GET', b'', {}),
    ('http://127.0.0.1:3012/api/session?x=1', 'GET', b'', {}),
    ('http://127.0.0.1:3012/other', 'GET', b'', {}),
    ('http://127.0.0.1:3012/api/profile', 'POST', b'', {}),
    ('http://127.0.0.1:3012/api/login', 'POST', b'{"user":"admin"}', {}),
    ('http://127.0.0.1:3012/api/session', 'GET', b'', {'cookie': 'other-session=stale'}),
    ('http://127.0.0.1:3012/api/session', 'GET', b'', {'authorization': 'Bearer demo-alice'}),
])
def test_fixed_browser_routes_and_sessions(url, method, body, headers):
    transport = DemoTransport(PolicyEngine(browser_settings(), 'http://127.0.0.1:3012'), asyncio.Event())
    with pytest.raises(PolicyDenied):
        transport.validate(url, method, body, headers)


async def test_redirect_never_reaches_other_origin_and_budget_is_shared():
    hits = []
    async def trap(reader, writer):
        hits.append(True)
        writer.close()
    other = await asyncio.start_server(trap, '127.0.0.1', 0)
    port = other.sockets[0].getsockname()[1]
    async def redirect(reader, writer):
        await reader.read(8192)
        writer.write(f'HTTP/1.1 302 Found\r\nLocation: http://127.0.0.1:{port}/api/session\r\nContent-Length: 0\r\n\r\n'.encode())
        await writer.drain()
        writer.close()
    server = await asyncio.start_server(redirect, '127.0.0.1', 0)
    target = f'http://127.0.0.1:{server.sockets[0].getsockname()[1]}'
    settings = browser_settings(target)
    settings.request_budget = 1
    policy = PolicyEngine(settings, target)
    transport = DemoTransport(policy, asyncio.Event())
    try:
        with pytest.raises(PolicyDenied, match='redirect'):
            await transport.forward(target + '/api/session', 'GET', b'', {}, 'anonymous')
        with pytest.raises(PolicyDenied, match='budget'):
            await transport.forward(target + '/api/session', 'GET', b'', {}, 'anonymous')
        assert not hits and policy.used == 1
    finally:
        server.close()
        other.close()
        await server.wait_closed()
        await other.wait_closed()


def test_browser_scan_requires_dynamic_approved_demo(store):
    service = Service(store)
    repo = service.add_repository(RepositoryCreate(path=str(DEMO)))
    with pytest.raises(ValueError, match='dynamic'):
        service.create_scan(ScanCreate(repository_id=repo['id'], browser=True))
    settings = browser_settings()
    store.save_settings(settings)
    app = service.add_repository(RepositoryCreate(path=str(Path('apps/web').resolve())))
    with pytest.raises(PolicyDenied, match='shipped'):
        service.create_scan(ScanCreate(repository_id=app['id'], browser=True, dynamic=True, target='http://127.0.0.1:3012'))


async def test_missing_chromium_is_unsupported(monkeypatch):
    from playwright.async_api import BrowserType, Error
    async def unavailable(*args, **kwargs):
        raise Error('Executable missing')
    monkeypatch.setattr(BrowserType, 'launch', unavailable)
    settings = browser_settings()
    result = await validate_browser(PolicyEngine(settings, 'http://127.0.0.1:3012'), asyncio.Event(), ['bola'])
    assert result['bola']['status'] == 'unsupported'
    assert result['bola']['verdict'] == 'INCONCLUSIVE'


@pytest.mark.parametrize('mode', ['timeout', 'large', 'compressed'])
async def test_browser_transport_response_bounds(mode):
    async def handler(reader, writer):
        try:
            await reader.read(8192)
            if mode == 'timeout':
                await asyncio.sleep(0.3)
            elif mode == 'compressed':
                writer.write(b'HTTP/1.1 200 OK\r\nContent-Encoding: gzip\r\nContent-Length: 0\r\n\r\n')
            else:
                writer.write(b'HTTP/1.1 200 OK\r\nContent-Length: 70000\r\n\r\n' + b'x' * 70000)
            await writer.drain()
        finally:
            writer.close()
    server = await asyncio.start_server(handler, '127.0.0.1', 0)
    target = f'http://127.0.0.1:{server.sockets[0].getsockname()[1]}'
    settings = browser_settings(target)
    settings.timeout_seconds = 0.1
    try:
        import httpx
        with pytest.raises((PolicyDenied, TimeoutError, httpx.TimeoutException)):
            await DemoTransport(PolicyEngine(settings, target), asyncio.Event()).forward(
                target + '/api/session', 'GET', b'', {}, 'anonymous')
    finally:
        server.close()
        await server.wait_closed()


async def test_cleanup_failure_cannot_pass_a_completed_browser_case(monkeypatch):
    class FaultingRunner:
        def __init__(self, *args):
            from types import SimpleNamespace
            self.results = {}
            self.transport = SimpleNamespace(failures=[], records=[])
            self.browser = object()
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            raise RuntimeError('Browser teardown failed')
        async def case(self, category):
            self.results[category] = {'status': 'completed', 'verdict': 'NOT_REPRODUCED',
                                      'validation': 'Controls passed', 'evidence': [], 'test_count': 5}
    monkeypatch.setattr('packages.execution.demo_browser.DemoBrowser', FaultingRunner)
    result = await validate_browser(PolicyEngine(browser_settings(), 'http://127.0.0.1:3012'), asyncio.Event(), ['bola'])
    assert result['bola']['status'] == 'failed'
    assert result['bola']['verdict'] == 'INCONCLUSIVE' and result['bola']['test_count'] == 0
