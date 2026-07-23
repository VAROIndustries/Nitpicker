import copy
import json
from pathlib import Path


def default_config() -> dict:
    return {
        "master_level": 70,
        "auto_dimming": True,
        "autostart": False,
        "monitors_by_model": {},
        "curve": {"day_max": 100, "night_min": 30, "latitude": None, "longitude": None},
        "webcam": {"enabled": False, "camera_index": 0, "sample_every_sec": 300, "max_nudge": 15},
    }


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: Path) -> dict:
    if not Path(path).exists():
        return default_config()
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return _deep_merge(default_config(), data)


def save_config(cfg: dict, path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def ensure_model(cfg: dict, model: str) -> dict:
    cfg.setdefault("monitors_by_model", {})
    entry = cfg["monitors_by_model"].setdefault(model, {})
    entry.setdefault("offset", 0)
    entry.setdefault("contrast", None)  # None = leave the monitor's contrast untouched
    return cfg
