from dataclasses import dataclass

@dataclass
class VehicleRecognition:
    make: str
    model: str
    year: int | None
    confidence: float

class VehicleRecognizer:
    """Interface for optional photo recognition.

    Keep this independent from charging providers. A future implementation can
    call a local vision model or an approved image API.
    """
    async def recognize(self, image_path: str) -> VehicleRecognition | None:
        return None
