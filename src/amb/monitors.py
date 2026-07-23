from dataclasses import dataclass


@dataclass(frozen=True)
class MonitorInfo:
    id: int
    model: str
    method: str
    manufacturer_id: str = ""


def model_key(info: "MonitorInfo") -> str:
    """Stable identity that groups identical hardware but separates different hardware.

    The internal laptop panel is always ``"internal"``. External monitors are keyed by
    ``manufacturer_id + model`` so that three identical Philips share one offset while two
    different USB monitors that both report a generic model string stay distinct.
    """
    if info.method == "wmi":
        return "internal"
    mfr = (info.manufacturer_id or "").strip()
    model = (info.model or "").strip()
    key = f"{mfr} {model}".strip()
    return key or f"display-{info.id}"


class FakeBackend:
    def __init__(self, infos, brightnesses):
        self._infos = list(infos)
        self._b = dict(brightnesses)
        self.writes = []

    def list_monitors(self):
        return list(self._infos)

    def get_brightness(self, monitor_id: int) -> int:
        return self._b[monitor_id]

    def set_brightness(self, monitor_id: int, value: int) -> None:
        self._b[monitor_id] = value
        self.writes.append((monitor_id, value))


class SBCBackend:
    """Real backend over screen_brightness_control. Not unit-tested."""

    def list_monitors(self):
        import screen_brightness_control as sbc
        out = []
        for i, m in enumerate(sbc.list_monitors_info()):
            method = m.get("method")
            if method is None:
                method_name = ""
            elif isinstance(method, str):
                method_name = method.lower()
            else:
                method_name = getattr(method, "__name__", str(method)).lower()
            out.append(MonitorInfo(
                id=i,
                model=m.get("model") or m.get("name") or f"Display{i}",
                method=method_name,
                manufacturer_id=(m.get("manufacturer_id") or ""),
            ))
        return out

    def get_brightness(self, monitor_id: int) -> int:
        import screen_brightness_control as sbc
        vals = sbc.get_brightness(display=monitor_id)
        return int(vals[0] if isinstance(vals, list) else vals)

    def set_brightness(self, monitor_id: int, value: int) -> None:
        import screen_brightness_control as sbc
        sbc.set_brightness(int(value), display=monitor_id)
