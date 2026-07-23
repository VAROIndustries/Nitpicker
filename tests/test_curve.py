from datetime import datetime, timezone
from amb import curve


def test_elevation_below_horizon_gives_night_min():
    assert curve.elevation_to_level(-10, night_min=30, day_max=100) == 30


def test_elevation_at_full_sun_gives_day_max():
    assert curve.elevation_to_level(15, night_min=30, day_max=100) == 100
    assert curve.elevation_to_level(40, night_min=30, day_max=100) == 100


def test_elevation_midway_interpolates():
    # halfway to full sun (7.5 deg) -> midpoint of 30..100 = 65
    assert curve.elevation_to_level(7.5, night_min=30, day_max=100) == 65


def test_baseline_disabled_when_no_location_returns_master():
    cfg = {"master_level": 55, "curve": {"day_max": 100, "night_min": 30,
           "latitude": None, "longitude": None}}
    now = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)
    assert curve.baseline_level(cfg, now) == 55


def test_baseline_uses_injected_elevation():
    cfg = {"master_level": 55, "curve": {"day_max": 100, "night_min": 30,
           "latitude": 40.0, "longitude": -75.0}}
    now = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)
    assert curve.baseline_level(cfg, now, sun_elevation=-5) == 30
    assert curve.baseline_level(cfg, now, sun_elevation=15) == 100
