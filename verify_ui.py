import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        page = await browser.new_page()
        
        try:
            print("Navigating to the page...")
            await page.goto("http://127.0.0.1:5000", timeout=60000)
            print("Page loaded.")

            # --- Step 1: Click a line and verify directions appear ---
            line_to_test = '10'
            print(f"Waiting for tram line '{line_to_test}' to be visible...")
            line_element_selector = f'#tram-list li[data-line-id="{line_to_test}"]'
            await page.wait_for_selector(line_element_selector, state='visible', timeout=30000)
            
            print("Taking screenshot of initial line list: 'lines_visible.png'...")
            await page.screenshot(path="lines_visible.png")

            print(f"Clicking on line '{line_to_test}'...")
            await page.click(line_element_selector)
            
            # Wait for the right sidebar to update with directions
            direction_header_selector = '#stops-container .direction h4'
            await page.wait_for_selector(direction_header_selector, state='visible', timeout=10000)
            
            print("Directions are visible. Taking screenshot 'directions_visible.png'...")
            await page.screenshot(path="directions_visible.png")

            # --- Step 2: Click a direction and verify stops appear ---
            first_direction_selector = f'{direction_header_selector}:first-of-type'
            direction_name = await page.inner_text(first_direction_selector)
            
            print(f"Clicking on first direction: '{direction_name}'...")
            await page.click(first_direction_selector)

            # Wait for the stops list to become visible
            stop_list_selector = '.stop-list[style*="display: block;"] li'
            await page.wait_for_selector(stop_list_selector, state='visible', timeout=10000)
            
            print("Stops are visible. Taking final screenshot 'final_stops_view.png'...")
            await page.screenshot(path="final_stops_view.png")
            print("Verification successful!")

        except Exception as e:
            print(f"An error occurred: {e}")
            await page.screenshot(path="error_screenshot.png")
            print("Error screenshot taken.")
        finally:
            await browser.close()
            print("Browser closed.")

if __name__ == "__main__":
    asyncio.run(main())
