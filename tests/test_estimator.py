from app.estimator import ChargingEstimator, Observation
from app.models import VehicleProfile

def profile():
    return VehicleProfile(
        id="demo",
        make="Demo",
        model="Demo EV",
        battery_kwh=60,
        chemistry="NMC",
        connectors=["CCS"],
        nominal_dc_kw=100,
        taper_start_soc=80,
        taper_floor_kw=30,
    )

def test_constant_power_estimate():
    e = ChargingEstimator(profile())
    minutes = e.estimate_minutes(50, 70, 100)
    assert 5 < minutes < 10

def test_target_already_reached():
    assert ChargingEstimator(profile()).estimate_minutes(80, 80, 100) == 0

def test_observed_rate_is_used():
    e = ChargingEstimator(profile())
    obs = [
        Observation(0, 40, 100),
        Observation(5, 50, 100),
        Observation(10, 60, 100),
    ]
    minutes = e.estimate_minutes(60, 70, 100, obs)
    assert 4 < minutes < 8
