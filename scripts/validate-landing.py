"""Check the exported landing site on fixed loopback port 3100, without an API.

Start python3 -m http.server 3100 --bind 127.0.0.1 --directory apps/landing/out.
Requires project Python/browser dependencies; evidence excludes credentials and response bodies.
Configured Vercel headers are applied to browser responses locally; provider delivery is unverified.
"""
import asyncio
import json
import os
import shutil
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from playwright.async_api import async_playwright, expect

ROOT = Path('.shadowlab/vercel-validation')
BASE = 'http://127.0.0.1:3100'

async def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    checks = []
    async with httpx.AsyncClient(base_url=BASE, timeout=10, trust_env=False) as client:
        for path, expected in [('/', 200), ('/app', 404), ('/demo', 404), ('/api/v1/health', 404), ('/api/v1/scans', 404)]:
            response = await client.get(path)
            assert response.status_code == expected, (path, response.status_code)
            checks.append({'path': path, 'status': response.status_code, 'passed': True})
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=os.getenv('SHADOWLAB_CHROMIUM_PATH') or shutil.which('chromium'))
        try:
            context = await browser.new_context(permissions=['clipboard-read', 'clipboard-write'])
            security_headers = {header['key']: header['value'] for header in
                json.loads(Path('apps/landing/vercel.json').read_text())['headers'][0]['headers']}
            async def serve_static(route):
                if urlsplit(route.request.url).netloc != '127.0.0.1:3100':
                    await route.abort()
                    return
                response = await route.fetch(max_redirects=0)
                await route.fulfill(response=response, headers={**response.headers, **security_headers})
            await context.route('**/*', serve_static)
            page = await context.new_page()
            errors = []
            requests = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('request', lambda request: requests.append(request.url))
            await page.goto(BASE)
            await page.get_by_role('heading', name='Find the bug.').wait_for()
            await page.get_by_role('tab', name='Homebrew', exact=True).click()
            await expect(page.get_by_role('tabpanel')).to_contain_text('brew install --HEAD')
            await page.get_by_role('tab', name='uv', exact=True).click()
            await expect(page.get_by_role('tabpanel')).to_contain_text('uv tool install')
            await page.get_by_role('button', name='Copy install commands').click()
            assert 'shadow repl' in await page.evaluate('navigator.clipboard.readText()')
            await page.get_by_role('link', name='Run the demo locally', exact=True).click()
            await page.wait_for_url('**/#install')
            assert await page.get_by_role('link', name='Get ShadowLab').get_attribute('href') == '#install'
            assert not await page.locator('a[href="/app"], a[href="/demo"]').count()
            await page.screenshot(path=str(ROOT / 'static-desktop.png'), full_page=True)
            await page.set_viewport_size({'width':390, 'height':844})
            assert await page.locator('body').evaluate('element => element.scrollWidth <= innerWidth')
            await page.screenshot(path=str(ROOT / 'static-mobile.png'), full_page=True)
            assert not errors, errors
            assert all(urlsplit(url).netloc == '127.0.0.1:3100' for url in requests)
            assert not any('/api/' in url for url in requests)
            checks.append({'check':'real browser tabs, clipboard, install CTA, mobile layout, configured production CSP, no runtime API calls or page errors', 'passed':True})
            await context.close()
        finally:
            await browser.close()
    (ROOT / 'static-checks.json').write_text(json.dumps({'checks':checks,'limitations':['Local static preview; Vercel header delivery and cloud deployment not verified']}, indent=2)+'\n')
    print(f'Passed {len(checks)} static website request/browser checks; no API or service dependency')

if __name__ == '__main__':
    asyncio.run(main())
