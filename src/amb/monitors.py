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
    def __init__(self, infos, brightnesses, contrast_supported=None):
        self._infos = list(infos)
        self._b = dict(brightnesses)
        self.writes = []
        # default: every non-wmi (external) monitor supports contrast
        if contrast_supported is None:
            contrast_supported = [i.id for i in self._infos if i.method != "wmi"]
        self._contrast_supported = set(contrast_supported)
        self.contrast_writes = []

    def list_monitors(self):
        return list(self._infos)

    def get_brightness(self, monitor_id: int) -> int:
        return self._b[monitor_id]

    def set_brightness(self, monitor_id: int, value: int) -> None:
        self._b[monitor_id] = value
        self.writes.append((monitor_id, value))

    def supports_contrast(self, monitor_id: int) -> bool:
        return monitor_id in self._contrast_supported

    def set_contrast(self, monitor_id: int, value: int) -> None:
        if monitor_id not in self._contrast_supported:
            return
        self.contrast_writes.append((monitor_id, value))


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

    def _external_ids(self):
        return [info.id for info in self.list_monitors() if info.method != "wmi"]

    def supports_contrast(self, monitor_id: int) -> bool:
        # External (DDC/CI) monitors expose contrast; the internal WMI panel does not.
        return monitor_id in self._external_ids()

    def set_contrast(self, monitor_id: int, value: int) -> None:
        ext = self._external_ids()
        if monitor_id not in ext:
            return
        from amb import contrast
        contrast.set_contrast_by_position(ext.index(monitor_id), int(value))
