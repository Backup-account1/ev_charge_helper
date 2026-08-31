import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


async def main():
    auth = Path("data/auth/malanka.json")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        #context = await browser.new_context(storage_state=str(auth))
        context = await browser.new_context(
            storage_state=str(auth),
            permissions=["geolocation"],
            geolocation={
                "latitude": 53.9006,
                "longitude": 27.5590,
            },
        )
        page = await context.new_page()
        await page.goto(
            "https://customer.malankabn.by/map/",
            wait_until="domcontentloaded",
            timeout=60000,
        )

        print("URL:", page.url)
        print("TITLE:", await page.title())

        print("\n--- PAGE TEXT ---")
        text = await page.locator("body").inner_text()
        print(text[:20000])

        input("\nPress Enter to close browser...")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())