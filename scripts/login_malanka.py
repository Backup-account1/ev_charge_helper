import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://customer.malankabn.by/map/"
OUT = "data/auth/malanka.json"

async def main():
    Path("data/auth").mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(URL)
        print("Log in manually in the opened browser.")
        input("After the map is visible and you are authenticated, press ENTER here...")
        await context.storage_state(path=OUT)
        await browser.close()
        print(f"Saved Playwright state to {OUT}")

asyncio.run(main())
