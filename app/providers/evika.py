from .browser import BrowserProvider
from ..models import Station, ChargingSession

class EvikaProvider(BrowserProvider):
    name = "evika"

    def __init__(self, auth_state: str):
        super().__init__("https://evika.by/map/", auth_state)

    async def list_stations(self) -> list[Station]:
        if not self.context:
            await self.start()
        page = await self.context.new_page()
        try:
            await page.goto(self.url, wait_until="domcontentloaded", timeout=30000)
            return []
        finally:
            await page.close()

    async def get_active_session(self) -> ChargingSession | None:
        if not self.context:
            await self.start()
        page = await self.context.new_page()
        try:
            return None
        finally:
            await page.close()
