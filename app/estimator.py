from dataclasses import dataclass
from statistics import median
from .models import ChargingSession, VehicleProfile

@dataclass
class Observation:
    minutes_from_start: float
    soc: float
    power_kw: float

class ChargingEstimator:
    """Operational estimator, not a BMS simulator."""

    def __init__(self, profile: VehicleProfile):
        self.profile = profile

    def estimate_minutes(self, current_soc: float, target_soc: float, power_kw: float | None,
                         observations: list[Observation] | None = None) -> float | None:
        if target_soc <= current_soc:
            return 0.0
        if not (0 <= current_soc <= 100 and 0 <= target_soc <= 100):
            return None

        # Prefer observed recent charging rate.
        if observations and len(observations) >= 2:
            recent = observations[-min(6, len(observations)):]
            rates = []
            for a, b in zip(recent, recent[1:]):
                dsoc = b.soc - a.soc
                dt = b.minutes_from_start - a.minutes_from_start
                if dt > 0 and dsoc > 0:
                    rates.append(dsoc / dt)
            if rates:
                rate = median(rates)
                if rate > 0:
                    # Conservative taper adjustment above profile taper point.
                    if current_soc >= self.profile.taper_start_soc:
                        factor = max(
                            self.profile.taper_floor_kw / max(power_kw or 1, 1),
                            0.15,
                        )
                        rate *= factor
                    return (target_soc-current_soc) / rate

        p = max(power_kw or self.profile.nominal_dc_kw, 0.1)
        usable = self.profile.battery_kwh
        # Constant-power approximation below taper.
        energy_needed = usable * (target_soc-current_soc) / 100.0
        minutes = energy_needed / p * 60.0

        if current_soc >= self.profile.taper_start_soc:
            frac = (target_soc-current_soc) / max(100-current_soc, 1)
            minutes *= 1.0 + max(0.0, frac) ** self.profile.taper_exponent * 0.8
        return minutes
