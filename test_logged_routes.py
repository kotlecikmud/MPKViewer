
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("http://localhost:5000")
        await page.click("#logged-routes-btn")
        await page.wait_for_function("document.querySelector('#date-selector').options.length > 0")
        await page.select_option("#date-selector", index=0)
        await page.wait_for_selector("#logged-lines-container button")
        await page.click("#logged-lines-container button:first-child")
        await page.wait_for_timeout(2000) # Wait for map tiles to load
        await page.screenshot(path="logged_route.png")
        await browser.close()

asyncio.run(main())
