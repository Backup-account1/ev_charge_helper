from abc import ABC, abstractmethod

class ChargingProvider(ABC):
    name: str

    @abstractmethod
    async def list_stations(self):
        raise NotImplementedError

    @abstractmethod
    async def get_active_session(self):
        raise NotImplementedError
