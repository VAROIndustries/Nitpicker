from datetime import datetime
from amb import offset, curve, webcam, monitors


def compute_master(cfg, now: datetime, luminance=None, sun_elevation=None) -> int:
    if not cfg.get("auto_dimming", True):
        return offset.clamp(cfg["master_level"])
    baseline = curve.baseline_level(cfg, now, sun_elevation=sun_elevation)
    nudge = 0
    if cfg.get("webcam", {}).get("enabled") and luminance is not None:
        nudge = webcam.luminance_to_nudge(luminance, cfg["webcam"]["max_nudge"])
    return offset.clamp(baseline + nudge)


def targets_for(cfg, master: int, infos) -> dict:
    out = {}
    for info in infos:
        key = monitors.model_key(info)
        out[info.id] = offset.apply_offset(master, offset.model_offset(cfg, key))
    return out


def apply_targets(backend, targets: dict, last: dict, threshold: int = 2) -> dict:
    new_last = dict(last)
    for mid, value in targets.items():
        prev = last.get(mid)
        if prev is None or abs(value - prev) > threshold:
            try:
                backend.set_brightness(mid, value)
                new_last[mid] = value
            except Exception:
                pass  # monitor asleep/unplugged; skip this tick
    return new_last
