from .browser import BrowserProvider
from ..models import Station, ChargingSession

class MalankaProvider(BrowserProvider):
    name = "malanka"

    def __init__(self, auth_state: str):
        super().__init__("https://customer.malankabn.by/map", auth_state)

    async def list_stations(self) -> list[Station]:
        """DOM/API adapter placeholder.

        Keep selectors in this method/config so the provider can be updated
        independently when the authenticated web UI changes.
        """
        if not self.context:
            await self.start()
        page = await self.context.new_page()
        try:
            await page.goto(self.url, wait_until="domcontentloaded", timeout=30000)
            # Real selectors should be filled after inspecting the authenticated page.
            return []
        finally:
            await page.close()

    async def get_active_session(self) -> ChargingSession | None:
        if not self.context:
            await self.start()
        page = await self.context.new_page()
        try:
            # Navigate to the authenticated session page/route discovered in the account.
            # Return normalized data once selectors are confirmed.
            return None
        finally:
            await page.close()
