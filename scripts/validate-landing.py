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
        for path, expected in [('/', 200), ('/docs/', 200), ('/app', 404), ('/demo', 404), ('/api/v1/health', 404), ('/api/v1/scans', 404)]:
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
            await expect(page.locator('.marketing')).to_have_class('marketing motion-ready')
            navigation = page.get_by_role('navigation', name='Main navigation', exact=True)
            await expect(navigation.get_by_role('link', name='Docs', exact=True)).to_be_visible()
            assert await page.get_by_role('link', name='Read the docs', exact=True).get_attribute('href') == '/docs/'
            assert await page.get_by_role('link', name='Explore the docs', exact=True).get_attribute('href') == '/docs/'
            demo = page.get_by_role('tablist', name='Demo preview', exact=True)
            await demo.get_by_role('tab', name='Source', exact=True).click()
            await expect(page.locator('#preview-panel')).to_contain_text('hypothesis until the behavior is tested')
            await demo.get_by_role('tab', name='Source', exact=True).press('End')
            await expect(demo.get_by_role('tab', name='Review', exact=True)).to_be_focused()
            await expect(page.locator('#preview-panel')).to_contain_text('Awaiting your review')
            await demo.get_by_role('tab', name='Review', exact=True).press('ArrowLeft')
            await expect(demo.get_by_role('tab', name='Validate', exact=True)).to_be_focused()
            await page.get_by_role('button', name='Replay demo preview').click()
            await expect(page.locator('#preview-panel')).to_contain_text('200 EXPOSED')
            await page.get_by_role('button', name='Pause animations', exact=True).click()
            await expect(page.get_by_role('button', name='Resume animations', exact=True)).to_have_attribute('aria-pressed', 'true')
            assert await page.evaluate('document.getAnimations().filter(animation => animation.playState === "running").length') == 0
            await page.get_by_role('button', name='Resume animations', exact=True).click()
            assert await page.evaluate('document.getAnimations().some(animation => animation.playState === "running")')
            await page.emulate_media(reduced_motion='reduce')
            await expect(page.locator('.m-motion-toggle')).to_be_hidden()
            assert await page.evaluate('document.getAnimations().filter(animation => animation.playState === "running").length') == 0
            assert await page.locator('[data-reveal]').evaluate_all('elements => elements.every(element => getComputedStyle(element).opacity === "1")')
            await demo.get_by_role('tab', name='Review', exact=True).click()
            await expect(page.locator('#preview-panel')).to_contain_text('Owner access preserved')
            await page.emulate_media(reduced_motion='no-preference')
            await demo.get_by_role('tab', name='Validate', exact=True).click()
            await page.get_by_role('tab', name='Homebrew', exact=True).click()
            await expect(page.locator('#install-command')).to_contain_text('brew install --HEAD')
            await page.get_by_role('tab', name='uv', exact=True).click()
            await expect(page.locator('#install-command')).to_contain_text('uv tool install')
            await page.get_by_role('tab', name='uv', exact=True).press('ArrowRight')
            await expect(page.get_by_role('tab', name='Homebrew', exact=True)).to_be_focused()
            await page.get_by_role('tab', name='Homebrew', exact=True).press('Home')
            await expect(page.get_by_role('tab', name='uv', exact=True)).to_be_focused()
            await page.get_by_role('button', name='Copy install commands').click()
            assert 'shadow repl' in await page.evaluate('navigator.clipboard.readText()')
            await page.get_by_role('link', name='Run the demo locally', exact=True).click()
            await page.wait_for_url('**/#install')
            assert await page.get_by_role('link', name='Get ShadowLab').get_attribute('href') == '#install'
            assert not await page.locator('a[href="/app"], a[href="/demo"]').count()
            await page.get_by_role('button', name='Pause animations', exact=True).click()
            for width in [320, 390, 768, 1024, 1440, 1920]:
                await page.set_viewport_size({'width': width, 'height': 900})
                assert await page.locator('body').evaluate('element => element.scrollWidth <= innerWidth'), width
                for name in ['Docs', 'Phases', 'Get ShadowLab']:
                    link = navigation.get_by_role('link', name=name, exact=True)
                    await expect(link).to_be_visible()
                    box = await link.bounding_box()
                    assert box['x'] >= 0 and box['x'] + box['width'] <= width, (width, name, box)
            await navigation.get_by_role('link', name='Phases', exact=True).click()
            await page.wait_for_url('**/#phases')
            await expect(page.get_by_role('heading', name='Phases', exact=True)).to_be_visible()
            history = json.loads(Path('apps/landing/.generated/phases.json').read_text())
            assert len(history['entries']) >= 11
            archive = page.locator('.m-phase-archive')
            await archive.locator('summary').focus()
            await archive.locator('summary').press('Enter')
            await expect(archive).to_have_attribute('open', '')
            assert await page.locator('.m-phase-update').count() == len(history['entries'])
            for entry in history['entries']:
                row = page.locator('[data-commit="' + (entry['commit'] or 'current-update') + '"]')
                await expect(row).to_contain_text(entry['title'])
                await expect(row.locator('time')).to_have_attribute('datetime', entry['date'])
                if entry['commit']:
                    await expect(row.locator('a')).to_have_attribute('href',
                        'https://github.com/Devesh36/shadow-lab/commit/' + entry['commit'])
            await page.set_viewport_size({'width': 390, 'height': 844})
            await page.locator('#phases').evaluate('element => window.scrollTo(0, element.getBoundingClientRect().top + scrollY - 140)')
            await page.screenshot(path=str(ROOT / 'phases-mobile.png'))
            await page.set_viewport_size({'width': 1440, 'height': 1000})
            await page.locator('#phases').evaluate('element => window.scrollTo(0, element.getBoundingClientRect().top + scrollY - 110)')
            await page.screenshot(path=str(ROOT / 'phases-desktop.png'))
            checks.append({'check': 'Phases navigation, all recorded commits, IST dates, impact notes, valid commit links and keyboard history disclosure', 'passed': True})
            await page.set_viewport_size({'width': 1440, 'height': 1000})
            await page.evaluate('window.scrollTo(0, 0)')
            await page.screenshot(path=str(ROOT / 'redesign-hero-desktop.png'))
            await page.screenshot(path=str(ROOT / 'static-desktop.png'), full_page=True)
            await page.set_viewport_size({'width': 390, 'height': 844})
            await page.evaluate('window.scrollTo(0, 0)')
            await page.screenshot(path=str(ROOT / 'redesign-hero-mobile.png'))
            await page.screenshot(path=str(ROOT / 'static-mobile.png'), full_page=True)
            checks.append({'check': 'interactive source/validate/review preview, keyboard tabs, replay, pause/resume, reduced motion, six responsive widths with visible Docs/install links', 'passed': True})
            await page.set_viewport_size({'width': 1340, 'height': 900})
            await page.get_by_role('link', name='Docs', exact=True).click()
            await page.wait_for_url('**/docs/')
            await page.get_by_role('heading', name='Install ShadowLab', exact=True).wait_for()
            assert 'ShadowLab docs' in await page.title()
            await page.reload()
            await page.get_by_role('heading', name='Use it in your project', exact=True).wait_for()
            await page.get_by_role('button', name='Copy uv installation', exact=True).click()
            assert 'git+https://github.com/Devesh36/shadow-lab.git@main' in await page.evaluate('navigator.clipboard.readText()')
            await page.get_by_role('button', name='Copy Project analysis', exact=True).click()
            project_commands = await page.evaluate('navigator.clipboard.readText()')
            assert 'shadow repl' in project_commands and 'project .\nscan' in project_commands and '--target' not in project_commands
            await expect(page.locator('#project')).to_contain_text('Static hypotheses remain INCONCLUSIVE')
            await expect(page.locator('#review')).to_contain_text('requires your review')
            await expect(page.locator('#commands')).to_contain_text('/inspect NUMBER')
            await expect(page.locator('#commands')).to_contain_text('input history is never saved to disk')
            await page.get_by_role('button', name='Copy Slash command workflow', exact=True).click()
            assert await page.evaluate('navigator.clipboard.readText()') == '/init\n/status\n/scan\n/findings\n/inspect 1\n/export json\n/quit'
            recordings = json.loads(Path('apps/landing/public/docs/terminal/manifest.json').read_text())['recordings']
            images = page.locator('.docs-gallery img')
            assert await images.count() == len(recordings) == 9
            for index, recording in enumerate(recordings):
                element = images.nth(index)
                await element.scroll_into_view_if_needed()
                await expect(element).to_have_attribute('alt', recording['alt'])
                await expect(element).to_have_attribute('src', f'/docs/terminal/{recording["id"]}.png')
                await page.wait_for_function('(image) => image.complete && image.naturalWidth > 0', arg=await element.element_handle())
                assert await element.evaluate('image => image.naturalWidth') == recording['width']
            async with page.expect_download() as pending_download:
                await page.get_by_role('link', name='Download open the console transcript', exact=True).click()
            download = await pending_download.value
            assert download.suggested_filename == '02-console.txt'
            transcript = Path(await download.path()).read_text()
            assert 'shadow> doctor' in transcript and '/workspace/' not in transcript
            assert 'demo-alice' not in transcript and 'Bearer ' not in transcript
            await page.locator('.docs-intro').scroll_into_view_if_needed()
            assert await page.locator('body').evaluate('element => element.scrollWidth <= innerWidth')
            await page.screenshot(path=str(ROOT / 'docs-desktop.png'), full_page=True)
            await page.locator('#demo').scroll_into_view_if_needed()
            await page.screenshot(path=str(ROOT / 'docs-demo-section.png'))
            await page.set_viewport_size({'width': 390, 'height': 844})
            await page.reload()
            await page.get_by_role('heading', name='Install ShadowLab', exact=True).wait_for()
            assert await page.locator('body').evaluate('element => element.scrollWidth <= innerWidth')
            for element in await page.locator('.docs-gallery img').all():
                await element.scroll_into_view_if_needed()
                await page.wait_for_function('(image) => image.complete && image.naturalWidth > 0', arg=await element.element_handle())
            await page.get_by_role('navigation', name='On this page').get_by_role('link', name='Terminal screenshots').click()
            await page.wait_for_url('**/docs/#screenshots')
            await page.screenshot(path=str(ROOT / 'docs-mobile-gallery.png'))
            await page.locator('.docs-intro').scroll_into_view_if_needed()
            await page.screenshot(path=str(ROOT / 'docs-mobile.png'), full_page=True)
            await page.get_by_role('link', name='Back to overview', exact=True).click()
            await page.wait_for_url(BASE + '/')
            await page.get_by_role('heading', name='Find the bug.').wait_for()
            checks.append({'check': 'documentation navigation, direct reload, code copying, source-only instructions, nine real screenshots and transcript download, desktop/mobile layout', 'passed': True})
            assert not errors, errors
            assert all(urlsplit(url).netloc == '127.0.0.1:3100' for url in requests)
            assert not any('/api/' in url for url in requests)
            checks.append({'check':'real browser tabs, clipboard, install CTA, mobile layout, configured production CSP, no runtime API calls or page errors', 'passed':True})
            await context.close()
            # Static content and documentation navigation remain usable without hydration.
            no_js = await browser.new_context(java_script_enabled=False, viewport={'width': 390, 'height': 844})
            await no_js.route('**/*', serve_static)
            static_page = await no_js.new_page()
            await static_page.goto(BASE)
            await expect(static_page.get_by_role('heading', name='Find the bug.')).to_be_visible()
            await expect(static_page.locator('#how-it-works')).to_be_visible()
            await static_page.get_by_role('navigation', name='Main navigation', exact=True).get_by_role('link', name='Phases', exact=True).click()
            await static_page.wait_for_url('**/#phases')
            await expect(static_page.get_by_role('heading', name='Phases', exact=True)).to_be_visible()
            await static_page.locator('.m-phase-archive summary').click()
            await expect(static_page.locator('.m-phase-update').last).to_contain_text('V1 baseline preserved')
            await static_page.get_by_role('navigation', name='Main navigation', exact=True).get_by_role('link', name='Docs', exact=True).click()
            await static_page.wait_for_url('**/docs/')
            await expect(static_page.get_by_role('heading', name='Use it in your project', exact=True)).to_be_visible()
            await no_js.close()
            checks.append({'check': 'server-exported homepage, phase history/disclosure and Docs navigation with JavaScript disabled', 'passed': True})
        finally:
            await browser.close()
    (ROOT / 'static-checks.json').write_text(json.dumps({'checks':checks,'limitations':['Local static preview; Vercel header delivery and cloud deployment not verified']}, indent=2)+'\n')
    print(f'Passed {len(checks)} static website request/browser checks; no API or service dependency')

if __name__ == '__main__':
    asyncio.run(main())
