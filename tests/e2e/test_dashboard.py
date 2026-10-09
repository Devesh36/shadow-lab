import os
import shutil

import pytest
from playwright.async_api import async_playwright


@pytest.mark.e2e
async def test_real_dashboard_registers_repository_and_runs_analysis():
    url = os.getenv("SHADOWLAB_TEST_DASHBOARD")
    if not url:
        pytest.skip("Set SHADOWLAB_TEST_DASHBOARD with API and dashboard running")
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True,
            executable_path=os.getenv("SHADOWLAB_CHROMIUM_PATH") or shutil.which("chromium"))
        try:
            page = await browser.new_page(viewport={"width": 1440, "height": 1000})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            await page.goto(url)
            await page.get_by_text("API connected", exact=False).wait_for()
            await page.get_by_role("button", name="Repositories", exact=True).click()
            await page.get_by_role("button", name="Register repository", exact=True).click()
            await page.get_by_role("button", name="Investigate", exact=True).first.wait_for()
            await page.get_by_role("button", name="Investigate", exact=True).first.click()
            async with page.expect_response(lambda response: response.url.endswith('/api/v1/scans')
                                             and response.request.method == 'POST') as created:
                await page.get_by_role("button", name="Run investigation", exact=True).click()
            response = await created.value
            assert response.status == 202
            scan_id = (await response.json())["id"]
            await page.get_by_role("heading", name=f"Investigation {scan_id[:8]}", exact=True).wait_for()
            await page.locator(".flow .active", has_text="completed").wait_for(timeout=90000)
            await page.locator("td.mono").filter(has_text="/api/records/[id]").first.wait_for()
            await page.wait_for_function("document.querySelectorAll('.badge.INCONCLUSIVE').length >= 3")
            assert not errors
            # Next.js installs an empty ARIA route announcer. Check actual application errors.
            assert await page.locator('[role="alert"]:not(#__next-route-announcer__)').count() == 0
            await page.get_by_role("button", name="Overview", exact=True).click()
            await page.screenshot(path=".shadowlab/dashboard.png", full_page=True)
            await page.set_viewport_size({"width": 390, "height": 844})
            assert await page.locator("body").evaluate("element => element.scrollWidth <= window.innerWidth")
        finally:
            await browser.close()
