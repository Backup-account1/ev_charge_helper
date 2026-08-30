import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://evika.by/map/"
OUT = "data/auth/evika.json"

async def main():
    Path("data/auth").mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(URL)
        print("Log in manually if the site requests authentication.")
        input("After the map is ready, press ENTER here...")
        await context.storage_state(path=OUT)
        await browser.close()
        print(f"Saved Playwright state to {OUT}")

asyncio.run(main())
