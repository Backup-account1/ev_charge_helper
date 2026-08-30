import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

TARGETS = {
    "malanka": ("https://customer.malankabn.by/map/", "data/auth/malanka.json"),
    "evika": ("https://evika.by/map/", "data/auth/evika.json"),
}

async def check(name, url, state):
    if not Path(state).exists():
        print(f"{name}: MISSING {state}")
        return False
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=state)
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        print(f"{name}: URL={page.url}")
        print(f"{name}: title={await page.title()}")
        await browser.close()
        return True

async def main():
    results = [await check(n, u, s) for n, (u, s) in TARGETS.items()]
    raise SystemExit(0 if all(results) else 1)

asyncio.run(main())
