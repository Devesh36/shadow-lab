"""Screenshot already-sanitized, actual CLI transcripts for the static docs.

Run from the repo root with the project Playwright dependencies and Chromium:
  SHADOWLAB_CHROMIUM_PATH=/usr/bin/chromium .venv/bin/python scripts/render-terminal-docs.py
This renders recorded text, never runs commands in a transcript or contacts a target.
Capture provenance and excerpt filenames are in public/docs/terminal/manifest.json.
"""
import asyncio
import html
import json
import os
import shutil
from pathlib import Path

from playwright.async_api import async_playwright

ASSETS = Path('apps/landing/public/docs/terminal')
STYLE = """
* { box-sizing: border-box; }
body { margin: 0; background: #090e16; color: #d0dee9; }
.terminal { width: 1100px; border: 1px solid #2b414e; border-radius: 10px; overflow: hidden; }
header { display: flex; align-items: center; gap: 9px; background: #131f2b; padding: 19px 24px;
  font: 13px ui-monospace, monospace; border-bottom: 1px solid #263946; }
i { width: 9px; height: 9px; background: #516879; border-radius: 50%; }
header span { margin-left: 14px; color: #b1c7d5; }
header small { margin-left: auto; color: #65ded7; font-size: 11px; }
pre { margin: 0; padding: 28px; white-space: pre-wrap; overflow-wrap: anywhere;
  font: 15px/1.9 'DejaVu Sans Mono', ui-monospace, monospace; }
footer { border-top: 1px solid #263946; padding: 14px 24px; color: #809daf;
  font: 11px/1.8 ui-monospace, monospace; }
"""


async def main():
    manifest = json.loads((ASSETS / 'manifest.json').read_text())
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            executable_path=os.getenv('SHADOWLAB_CHROMIUM_PATH') or shutil.which('chromium'))
        try:
            context = await browser.new_context(viewport={'width': 1100, 'height': 800}, device_scale_factor=1)
            await context.route('**/*', lambda route: route.abort())
            page = await context.new_page()
            for recording in manifest['recordings']:
                transcript = (ASSETS / recording.get('screen', recording['id'] + '.txt')).read_text()
                assert '/workspace/' not in transcript and '\x1b' not in transcript
                label = 'ACTUAL CLI RECORDING' + (' · EXCERPT' if recording.get('screen') else '')
                await page.set_content(
                    '<!doctype html><html lang="en"><head><meta charset="utf-8"><style>' + STYLE +
                    '</style></head><body><div class="terminal"><header><i></i><i></i><i></i><span>' +
                    html.escape(recording['title']) + '</span><small>' + label + '</small></header><pre>' +
                    html.escape(transcript.rstrip()) + '</pre><footer>ShadowLab · Linux · ' +
                    html.escape(manifest['recordedAt']) + ' · Private paths and run identifiers normalized' +
                    '</footer></div></body></html>')
                terminal = page.locator('.terminal')
                box = await terminal.bounding_box()
                await terminal.screenshot(path=str(ASSETS / (recording['id'] + '.png')))
                recording.update(width=round(box['width']), height=round(box['height']))
            await context.close()
        finally:
            await browser.close()
    (ASSETS / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f"Rendered {len(manifest['recordings'])} sanitized terminal recordings; no commands executed or network requests allowed")


if __name__ == '__main__':
    asyncio.run(main())
