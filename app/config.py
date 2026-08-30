from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    telegram_bot_token: str
    database_url: str = "sqlite+aiosqlite:///data/evcharge.db"
    poll_seconds: int = 60
    default_radius_km: float = 2.0
    malanka_auth_state: str = "data/auth/malanka.json"
    evika_auth_state: str = "data/auth/evika.json"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
Path("data/auth").mkdir(parents=True, exist_ok=True)
