from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext

class BrowserProvider:
    def __init__(self, url: str, auth_state: str):
        self.url = url
        self.auth_state = auth_state
        self._pw = None
        self._browser = None
        self.context: BrowserContext | None = None

    async def start(self):
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=True, channel="chrome")
        kwargs = {}
        if Path(self.auth_state).exists():
            kwargs["storage_state"] = self.auth_state
        self.context = await self._browser.new_context(**kwargs)
        return self.context

    async def stop(self):
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
