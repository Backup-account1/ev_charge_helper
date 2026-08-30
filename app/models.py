from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class Station:
    provider: str
    station_id: str
    name: str
    latitude: float
    longitude: float
    address: str = ""
    connectors: list[str] = field(default_factory=list)
    available: bool | None = None
    power_kw: float | None = None

@dataclass
class ChargingSession:
    provider: str
    station_id: str
    session_id: str
    status: str
    soc_percent: float | None
    power_kw: float | None
    connector: str | None = None
    started_at: Optional[datetime] = None
    observed_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class VehicleProfile:
    id: str
    make: str
    model: str
    battery_kwh: float
    chemistry: str
    connectors: list[str]
    nominal_dc_kw: float
    taper_start_soc: float = 80.0
    taper_floor_kw: float = 20.0
    taper_exponent: float = 1.5
