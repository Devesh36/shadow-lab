"""Fixed browser scenarios for the reviewed local demo; never a general browser tool."""
import asyncio
import hashlib
import json
import os
import re
import shutil
import time
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from playwright.async_api import Error as BrowserError
from playwright.async_api import TimeoutError as BrowserTimeout
from playwright.async_api import async_playwright, expect

from packages.core.models import FindingState, SyntheticFixture, TestPlan
from packages.evidence.sanitize import response_body, sensitive_keys
from packages.policies.engine import PolicyDenied, PolicyEngine, origin

PROJECT = Path(__file__).resolve().parents[2]
DEMO = PROJECT / 'examples/vulnerable-nextjs'
MANIFEST = PROJECT / 'infrastructure/sandbox/demo-manifest.json'
CASES = ('authentication', 'bola', 'exposure')
IDENTITIES = {'anonymous': 'anonymous', 'owner': 'alice', 'other': 'bob'}
PATHS = {'/', '/api/session', '/api/login', '/api/logout', '/api/unprotected', '/api/profile',
         '/api/records/alice-record', '/api/records/bob-record'}


def check_manifest(root: Path):
    for relative, expected in json.loads(MANIFEST.read_text()).items():
        source = root / relative
        if source.is_symlink() or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise PolicyDenied('Reviewed demo manifest does not match; browser execution denied')


def require_demo(root: Path, settings, target):
    if root.resolve() != DEMO.resolve():
        raise PolicyDenied('Browser validation supports only the shipped trusted demo')
    check_manifest(root)
    scheme, host, _ = origin(target)
    if scheme != 'http' or host != '127.0.0.1':
        raise PolicyDenied('Demo browser validation requires an exact IPv4 loopback HTTP origin')
    if settings.fixture != SyntheticFixture():
        raise PolicyDenied('Demo browser validation requires the unchanged synthetic Alice/Bob fixture')
    policy = PolicyEngine(settings, target)
    if (settings.sandbox_mode != 'trusted-local' or not policy.scope or not policy.scope.allow_loopback
            or not policy.scope.authorized or not policy.scope.approved):
        raise PolicyDenied('Explicit demo target authorization, approval, and loopback permission are required')


class DemoTransport:
    """Chromium never connects to a target: every route is aborted or fulfilled via pinned HTTPX.

    No proxies, redirects, arbitrary POSTs, WebSockets, service workers, or APIRequestContext.
    Cookies stay in their originating browser context; only fixed synthetic cookies can pass.
    """
    def __init__(self, policy, cancelled):
        self.policy = policy
        self.cancelled = cancelled
        self.lock = asyncio.Lock()
        self.last_request = 0
        self.total_bytes = 0
        self.assets = {}
        self.records = []
        self.failures = []
        self.category = next(c for c in CASES if c in policy.settings.categories)

    def validate(self, url, method, data, headers):
        parsed = urlsplit(url)
        if origin(f'{parsed.scheme}://{parsed.netloc}') != self.policy.target:
            raise PolicyDenied('Browser request outside approved demo origin')
        if parsed.query or parsed.fragment or len(url) > 2048:
            raise PolicyDenied('Browser query/fragment requests are unsupported')
        asset = bool(re.fullmatch(r'/_next/static/[A-Za-z0-9_./\[\]-]+\.(js|css|woff2)', parsed.path))
        if parsed.path not in PATHS and not asset:
            raise PolicyDenied('Browser route outside fixed demo adapter')
        if method != 'GET':
            if method != 'POST' or parsed.path not in ('/api/login', '/api/logout'):
                raise PolicyDenied('Only fixed synthetic demo login/logout POSTs are allowed')
            if len(data) > 256:
                raise PolicyDenied('Demo session request body exceeds budget')
            if parsed.path == '/api/login' and json.loads(data) not in ({'user': 'alice'}, {'user': 'bob'}):
                raise PolicyDenied('Only synthetic demo accounts are allowed')
            if parsed.path == '/api/logout' and data:
                raise PolicyDenied('Logout body must be empty')
        elif parsed.path in ('/api/login', '/api/logout'):
            raise PolicyDenied('Unsupported demo session method')
        cookie = headers.get('cookie', '')
        if cookie and cookie not in ('shadowlab-demo-session=demo-alice', 'shadowlab-demo-session=demo-bob'):
            raise PolicyDenied('Unexpected browser session cookie')
        if 'authorization' in headers:
            raise PolicyDenied('Browser adapter never injects bearer authentication')
        return parsed.path, asset

    async def forward(self, url, method, data, headers, identity):
        path, asset = self.validate(url, method, data, headers)
        async with self.lock:
            if self.cancelled.is_set():
                raise asyncio.CancelledError
            await asyncio.sleep(max(0, 1 / self.policy.settings.requests_per_second
                                    - (time.monotonic() - self.last_request)))
            if self.cancelled.is_set():
                raise asyncio.CancelledError
            # Includes session checks, static assets, and cached browser requests in the scan cap.
            ip = await self.policy.check(TestPlan(category=self.category, path=path, identity=identity))
            self.last_request = time.monotonic()
            if asset and path in self.assets:
                return self.assets[path]
            scheme, host, port = self.policy.target
            original = httpx.URL(f'{scheme}://{host}:{port}{path}')
            request_headers = {'Host': original.netloc.decode(), 'Accept-Encoding': 'identity'}
            if headers.get('cookie'):
                request_headers['Cookie'] = headers['cookie']
            if method == 'POST':
                request_headers['Content-Type'] = 'application/json'
            limit = 2 * 1024 * 1024 if asset else 65536
            async with asyncio.timeout(self.policy.settings.timeout_seconds):
                async with httpx.AsyncClient(trust_env=False, follow_redirects=False) as client:
                    async with client.stream(method, original.copy_with(host=ip), content=data or None,
                                             headers=request_headers, extensions={'sni_hostname': host}) as response:
                        if 300 <= response.status_code < 400:
                            raise PolicyDenied('All browser redirects are denied')
                        if response.headers.get('content-encoding', 'identity').lower() != 'identity':
                            raise PolicyDenied('Compressed browser responses are denied')
                        raw = bytearray()
                        async for chunk in response.aiter_raw(chunk_size=16384):
                            if self.cancelled.is_set():
                                raise asyncio.CancelledError
                            raw.extend(chunk)
                            self.total_bytes += len(chunk)
                            if len(raw) > limit or self.total_bytes > 32 * 1024 * 1024:
                                raise PolicyDenied('Browser response or cumulative byte budget exceeded')
                        body = bytes(raw)
                        safe_headers = {k: v for k, v in response.headers.items()
                                        if k in ('content-type', 'cache-control', 'set-cookie')}
                        result = (response.status_code, safe_headers, body)
                        if asset:
                            self.assets[path] = result
                        elif path.startswith('/api/'):
                            try:
                                fields = sorted(set(sensitive_keys(json.loads(body))))
                            except ValueError:
                                fields = []
                            self.records.append({'method': method, 'path': path, 'identity': identity,
                                                 'status': response.status_code, 'body': response_body(body),
                                                 'sensitive_fields': fields, 'channel': 'browser'})
                        return result

    async def route(self, route, identity):
        try:
            request = route.request
            result = await self.forward(request.url, request.method, request.post_data_buffer or b'',
                                        await request.all_headers(), identity)
            await route.fulfill(status=result[0], headers=result[1], body=result[2])
        except asyncio.CancelledError:
            await route.abort()
            raise
        except Exception as exc:
            # Exception messages, URLs, cookie headers, and raw response bodies are never retained.
            status = 'blocked' if isinstance(exc, PolicyDenied) else 'failed'
            if isinstance(exc, (TimeoutError, httpx.TimeoutException)):
                status = 'timeout'
            self.failures.append({'error_type': type(exc).__name__, 'status': status})
            await route.abort()

    def handler(self, identity):
        async def handle(route):
            await self.route(route, identity)
        return handle


class DemoBrowser:
    def __init__(self, policy, cancelled, artifact_dir=None):
        self.transport = DemoTransport(policy, cancelled)
        self.cancelled = cancelled
        scheme, host, port = policy.target
        self.target = f'{scheme}://{host}:{port}'
        self.artifact_dir = Path(artifact_dir) if artifact_dir else None
        self.contexts = {}
        self.pages = {}
        self.browser = None
        self.playwright = None
        self.closed = False
        self.results = {}

    async def __aenter__(self):
        if self.cancelled.is_set():
            raise asyncio.CancelledError
        require_demo(DEMO, self.transport.policy.settings, self.target)
        try:
            self.playwright = await async_playwright().start()
            # Dead proxy closes paths outside interception (background traffic, WebSocket handshakes).
            self.browser = await self.playwright.chromium.launch(headless=True,
                executable_path=os.getenv('SHADOWLAB_CHROMIUM_PATH') or shutil.which('chromium'),
                proxy={'server': 'http://127.0.0.1:9', 'bypass': '<-loopback>'},
                args=['--disable-background-networking', '--disable-quic', '--disable-dev-shm-usage'],
                env={'PATH': os.defpath, 'HOME': '/tmp', 'LANG': 'C.UTF-8'})
            for identity in IDENTITIES:
                context = await self.browser.new_context(service_workers='block', accept_downloads=False)
                self.contexts[identity] = context
                context.set_default_timeout(self.transport.policy.settings.timeout_seconds * 1000)
                await context.route('**/*', self.transport.handler(identity))
                await context.route_web_socket('**/*', lambda ws: ws.close())
                page = await context.new_page()
                self.pages[identity] = page
                page.on('popup', lambda popup: asyncio.create_task(popup.close()))
                await page.goto(self.target, wait_until='networkidle')
                await expect(page.get_by_test_id('identity')).to_have_text('anonymous')
                if identity != 'anonymous':
                    await self.login(identity, IDENTITIES[identity])
            # Establish all three server identities after all logins, detecting shared state.
            for identity in IDENTITIES:
                await self.verify_identity(identity, IDENTITIES[identity])
            return self
        except BaseException:
            await self.close()
            raise

    async def __aexit__(self, *_):
        await self.close()

    async def close(self):
        # shield cleanup even when a scan is cancelled during a page request.
        async def cleanup():
            try:
                if self.browser:
                    await self.browser.close()
            finally:
                if self.playwright:
                    await self.playwright.stop()
                self.closed = True
        task = asyncio.create_task(cleanup())
        try:
            await asyncio.wait_for(asyncio.shield(task), 10)
        except asyncio.CancelledError:
            await asyncio.wait_for(asyncio.shield(task), 10)
            raise

    async def login(self, identity, user):
        page = self.pages[identity]
        await page.get_by_role('button', name=f'Log in as {user.title()}').click()
        await expect(page.get_by_test_id('identity')).to_have_text(user)
        await expect(page.get_by_role('button', name='Check identity')).to_be_enabled()

    async def logout(self, identity):
        page = self.pages[identity]
        await page.get_by_role('button', name='Log out', exact=True).click()
        await expect(page.get_by_test_id('identity')).to_have_text('anonymous')
        await expect(page.get_by_role('button', name='Check identity')).to_be_enabled()
        await self.verify_identity(identity, 'anonymous')
        if await self.contexts[identity].cookies() or await page.evaluate('localStorage.length + sessionStorage.length'):
            raise ValueError('Logout did not clear isolated browser state')

    async def verify_identity(self, identity, expected):
        if self.cancelled.is_set():
            raise asyncio.CancelledError
        page = self.pages[identity]
        before = len(self.transport.records)
        async with page.expect_response(lambda response: urlsplit(response.url).path == '/api/session'):
            await page.get_by_role('button', name='Check identity', exact=True).click()
        await expect(page.get_by_role('button', name='Check identity')).to_be_enabled()
        records = self.transport.records[before:]
        probe = next((r for r in records if r['path'] == '/api/session' and r['identity'] == identity), None)
        if not probe or probe['status'] != 200 or probe['body'] != {'identity': expected}:
            raise ValueError('Active server identity did not match expected synthetic account')
        await expect(page.get_by_test_id('identity')).to_have_text(expected)
        # Retain a safe verification record immediately before every protected action.
        return {'context': identity, 'expected': expected, 'observed': probe['body']['identity'], 'passed': True}

    async def action(self, identity, path, button, record=None):
        check = await self.verify_identity(identity, IDENTITIES[identity])
        page = self.pages[identity]
        if record:
            await page.get_by_label('Record ID').fill(record)
        before = len(self.transport.records)
        async with page.expect_response(lambda response: urlsplit(response.url).path == path):
            await page.get_by_role('button', name=button, exact=True).click()
        await expect(page.get_by_role('button', name=button, exact=True)).to_be_enabled()
        response = next(r for r in self.transport.records[before:] if r['path'] == path and r['identity'] == identity)
        body = response['body']
        if not isinstance(body, dict):
            raise ValueError('UI response was not an identifiable JSON object')
        expected_projection = {
            'status': response['status'], 'id': body.get('id'), 'ownerId': body.get('ownerId'),
            'sensitive_fields': response['sensitive_fields'],
        }
        # Wait for this response's React render; response arrival/button state alone can precede it.
        await expect(page.get_by_test_id('result')).to_have_text(json.dumps(expected_projection, indent=2))
        shown = json.loads(await page.get_by_test_id('result').inner_text())
        if shown != expected_projection:
            raise ValueError('UI did not display the observed response projection')
        return {**response, 'identity_check': check, 'ui_observed': True}

    async def case(self, category):
        from packages.agents.workflow import classify
        self.transport.category = category
        evidence = []
        if category == 'bola':
            sequence = [('owner', 'alice-record'), ('other', 'bob-record'), ('other', 'alice-record'),
                        ('owner', 'bob-record'), ('anonymous', 'alice-record')]
            for identity, record in sequence:
                evidence.append(await self.action(identity, f'/api/records/{record}', 'Open record', record))
            state, explanation = classify(category, evidence[:3])
            reverse = classify(category, [evidence[1], evidence[0], evidence[3]])[0]
            controls = (evidence[4]['status'] in (401, 403, 404)
                and evidence[0]['body'].get('id') == 'alice-record' and evidence[0]['body'].get('ownerId') == 'alice'
                and evidence[1]['body'].get('id') == 'bob-record' and evidence[1]['body'].get('ownerId') == 'bob')
            if reverse != state or not controls:
                state, explanation = FindingState.INCONCLUSIVE, 'Bidirectional authorization or anonymous control was inconsistent'
            checks = ['owner A allowed', 'owner B allowed', 'B accessing A record', 'A accessing B record', 'anonymous denied']
        elif category == 'authentication':
            for identity in ('owner', 'anonymous', 'other'):
                evidence.append(await self.action(identity, '/api/unprotected', 'Open protected resource'))
            state, explanation = classify(category, evidence[:2])
            if (evidence[2]['status'] != 200 or evidence[2]['body'].get('id') != evidence[0]['body'].get('id')
                    or evidence[0]['body'].get('id') != 'alice-record' or evidence[0]['body'].get('ownerId') != 'alice'):
                state, explanation = FindingState.INCONCLUSIVE, 'Authenticated positive control failed'
            checks = ['authenticated A allowed', 'anonymous accessing same resource', 'authenticated B allowed']
        else:
            for identity in ('owner', 'other', 'anonymous'):
                evidence.append(await self.action(identity, '/api/profile', 'Open profile'))
            state, explanation = classify(category, evidence[:1])
            other_state = classify(category, evidence[1:2])[0]
            if (other_state != state or evidence[0]['body'].get('id') != 'alice'
                    or evidence[1]['body'].get('id') != 'bob' or evidence[2]['status'] not in (401, 403, 404)):
                state, explanation = FindingState.INCONCLUSIVE, 'Profile identities or anonymous control failed'
            checks = ['A own profile allowed and projected', 'B own profile allowed and projected', 'anonymous profile denied']
        result = {'status': 'completed', 'verdict': state, 'validation': explanation, 'evidence': evidence,
                  'checks': checks, 'test_count': len(evidence), 'coverage': 'fixed synthetic demo UI and cookie sessions'}
        if self.artifact_dir:
            self.artifact_dir.mkdir(parents=True, exist_ok=True)
            receipt_id = str(uuid4())
            result['artifact_id'] = receipt_id
            # Safe UI projects only IDs/status/field names. No HAR, trace, storage state, or raw DOM is saved.
            image_path = self.artifact_dir / f'{receipt_id}.png'
            await self.pages['owner'].locator('main').screenshot(path=str(image_path))
            result['screenshot_path'] = str(image_path)
            receipt_path = self.artifact_dir / f'{receipt_id}.json'
            result['evidence_path'] = str(receipt_path)
            receipt_path.write_text(json.dumps(result, indent=2))
            os.chmod(receipt_path, 0o600)
            os.chmod(image_path, 0o600)
        self.results[category] = result
        return result


async def validate_browser(policy, cancelled, categories, artifact_dir=None, worktree=None, patched_category=None):
    scheme, host, port = policy.target
    require_demo(DEMO, policy.settings, f'{scheme}://{host}:{port}')
    if worktree:
        # Verify every executable fixture file against its reviewed baseline or exact trusted template.
        from packages.remediation.patches import FIXES
        file, before, after = FIXES[patched_category]
        for relative in json.loads(MANIFEST.read_text()):
            source = Path(worktree) / relative
            expected = (DEMO / relative).read_bytes()
            if relative == file:
                expected = expected.decode().replace(before, after).encode()
            if source.is_symlink() or source.read_bytes() != expected:
                raise PolicyDenied('Disposable patch copy differs from the reviewed template')
    runner = DemoBrowser(policy, cancelled, artifact_dir)
    categories = [c for c in CASES if c in categories and c in policy.settings.categories]
    if not categories:
        return {}
    error = None
    async def investigate():
        async with asyncio.timeout(policy.settings.scan_timeout_seconds):
            async with runner:
                for category in categories:
                    await runner.case(category)
    operation = asyncio.create_task(investigate())
    cancellation = asyncio.create_task(cancelled.wait())
    try:
        done, _ = await asyncio.wait((operation, cancellation), return_when=asyncio.FIRST_COMPLETED)
        if cancellation in done:
            raise asyncio.CancelledError
        await operation
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        if runner.transport.failures:
            error = runner.transport.failures[-1]
        else:
            status = 'timeout' if isinstance(exc, (TimeoutError, BrowserTimeout)) else 'failed'
            if isinstance(exc, BrowserError) and not runner.browser:
                status = 'unsupported'
            error = {'status': status, 'error_type': type(exc).__name__}
    finally:
        cancellation.cancel()
        if not operation.done():
            operation.cancel()
        await asyncio.shield(asyncio.gather(operation, cancellation, return_exceptions=True))
    cleanup_failed = error is not None and len(runner.results) == len(categories)
    for category in categories:
        if category not in runner.results or runner.transport.failures or cleanup_failed:
            runner.results[category] = {'status': (error or {'status': 'blocked'})['status'],
                'verdict': FindingState.INCONCLUSIVE, 'validation': 'Browser coverage incomplete',
                'error_type': (error or {}).get('error_type', 'PolicyDenied'), 'test_count': 0,
                'evidence': [r for r in runner.transport.records if r['path'] not in ('/api/login', '/api/logout')]}
    return runner.results
