from datetime import datetime
from amb import offset


def elevation_to_level(elevation_deg: float, night_min: int, day_max: int,
                       full_sun_deg: float = 15.0) -> int:
    frac = elevation_deg / full_sun_deg
    frac = max(0.0, min(1.0, frac))
    return offset.clamp(night_min + (day_max - night_min) * frac)


def baseline_level(cfg: dict, now: datetime, sun_elevation=None) -> int:
    c = cfg["curve"]
    lat, lon = c.get("latitude"), c.get("longitude")
    if lat is None or lon is None:
        return cfg["master_level"]
    if sun_elevation is None:
        from astral import Observer
        from astral.sun import elevation as sun_elev
        sun_elevation = sun_elev(Observer(latitude=lat, longitude=lon), now)
    return elevation_to_level(sun_elevation, c["night_min"], c["day_max"])
