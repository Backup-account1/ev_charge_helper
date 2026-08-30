from .malanka import MalankaProvider
from .evika import EvikaProvider
from ..config import settings

def build_providers():
    return {
        "malanka": MalankaProvider(settings.malanka_auth_state),
        "evika": EvikaProvider(settings.evika_auth_state),
    }
