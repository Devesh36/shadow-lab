import os
import shutil
from urllib.parse import parse_qs, urlsplit

import pytest
from playwright.async_api import async_playwright


@pytest.mark.e2e
async def test_landing_and_guided_demo_use_real_api_without_reconfiguring_settings():
    url = os.getenv('SHADOWLAB_TEST_DASHBOARD')
    if not url:
        pytest.skip('Set SHADOWLAB_TEST_DASHBOARD with API, web and bundled demo running')
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True,
            executable_path=os.getenv('SHADOWLAB_CHROMIUM_PATH') or shutil.which('chromium'))
        try:
            context = await browser.new_context(permissions=['clipboard-read', 'clipboard-write'])
            page = await context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            await page.goto(url)
            await page.get_by_role('heading', name='Find the bug.').wait_for()
            await page.get_by_role('tab', name='Homebrew', exact=True).click()
            assert 'brew install --HEAD' in await page.get_by_role('tabpanel').inner_text()
            await page.get_by_role('tab', name='uv', exact=True).click()
            assert 'uv tool install' in await page.get_by_role('tabpanel').inner_text()
            await page.get_by_role('button', name='Copy install commands').click()
            assert 'shadow repl' in await page.evaluate('navigator.clipboard.readText()')
            await page.screenshot(path='.shadowlab/landing-desktop.png', full_page=True)
            await page.set_viewport_size({'width': 390, 'height': 844})
            assert await page.locator('body').evaluate('element => element.scrollWidth <= window.innerWidth')
            await page.screenshot(path='.shadowlab/landing-mobile.png', full_page=True)
            settings = await context.request.get(url.rstrip('/') + '/api/v1/settings')
            assert settings.ok
            before = await settings.json()
            await page.get_by_role('link', name='Try the local demo').click()
            async with page.expect_response(lambda response: response.url.endswith('/api/v1/demo/start')
                                             and response.request.method == 'POST') as started:
                await page.get_by_role('button', name='Start demo', exact=True).click()
            response = await started.value
            assert response.status == 202
            await page.wait_for_url('**/app?scan=*')
            # The guided screen navigates after consuming the response; Chromium may discard its body.
            scan_id = parse_qs(urlsplit(page.url).query)['scan'][0]
            await page.get_by_role('heading', name=f'Investigation {scan_id[:8]}', exact=True).wait_for()
            await page.locator('.flow .active', has_text='completed').wait_for(timeout=90000)
            scan = await context.request.get(url.rstrip('/') + '/api/v1/scans/' + scan_id)
            data = await scan.json()
            assert data['id'] == scan_id and data['demo'] is True
            for category in ('authentication', 'bola', 'exposure'):
                assert any(f['category'] == category and f['state'] == 'CONFIRMED' for f in data['findings'])
            after = await context.request.get(url.rstrip('/') + '/api/v1/settings')
            assert await after.json() == before
            assert not errors
            # Simulate an unavailable backend and ensure the guided screen reports failure.
            await page.goto(url.rstrip('/') + '/demo')
            await page.route('**/api/v1/demo/start', lambda route: route.fulfill(status=503, json={}))
            await page.get_by_role('button', name='Start demo', exact=True).click()
            await page.get_by_role('alert').filter(has_text='unavailable').wait_for()
            assert await page.get_by_role('button', name='Start demo', exact=True).is_enabled()
        finally:
            await browser.close()
