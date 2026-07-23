def clamp(value: int) -> int:
    return max(0, min(100, int(round(value))))


def apply_offset(master: int, offset: int) -> int:
    return clamp(master + offset)


def model_offset(cfg: dict, model: str) -> int:
    return cfg.get("monitors_by_model", {}).get(model, {}).get("offset", 0)
