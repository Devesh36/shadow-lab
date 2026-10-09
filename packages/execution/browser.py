import html
import json
import os
import shutil
from pathlib import Path

from playwright.async_api import async_playwright


async def screenshot_evidence(evidence: dict, destination: Path):
    """Render sanitized HTTP evidence with all browser networking disabled."""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True,
            executable_path=os.getenv("SHADOWLAB_CHROMIUM_PATH") or shutil.which("chromium"))
        try:
            context = await browser.new_context(java_script_enabled=False)
            await context.route("**/*", lambda route: route.abort())
            page = await context.new_page()
            await page.set_content("<html><body><pre>" + html.escape(json.dumps(evidence, indent=2))
                                   + "</pre></body></html>")
            await page.screenshot(path=str(destination), full_page=True, timeout=5000)
        finally:
            await browser.close()
