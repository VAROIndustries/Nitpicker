# AutoMonitorBrightness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Windows system-tray app that syncs brightness across all six monitors from one master level with per-model offsets, plus optional auto day/night dimming (sun curve + webcam nudge), shipped as a standalone `.exe`.

**Architecture:** Seven single-purpose Python modules under `src/amb/`. Pure-logic modules (config, curve, offset, webcam mapping) are unit-tested directly. The hardware layer sits behind a `MonitorBackend` interface so the controller is tested against a fake backend — no physical displays needed. The tray/main layer is thin glue.

**Tech Stack:** Python 3.12, `screen_brightness_control` (WMI + DDC/CI), `astral` (sun curve), `opencv-python` (webcam), `pystray` + `Pillow` (tray), `tkinter` (slider popup), `pytest` (tests), `PyInstaller` (packaging).

## Global Constraints

- Target OS: Windows 11. Python 3.12.
- Brightness values are integers 0–100, always clamped to that range before any hardware write.
- Offsets are keyed by monitor **model** string; the internal laptop panel uses the reserved key `"internal"`.
- Config lives at `%APPDATA%\AutoMonitorBrightness\config.json`; log at `%APPDATA%\AutoMonitorBrightness\amb.log`.
- Autostart uses the `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` registry key, value name `AutoMonitorBrightness`.
- No hardware access in unit tests — all display/webcam I/O behind interfaces with fakes.
- Final deliverable is `dist/AutoMonitorBrightness.exe` built with `--onefile --noconsole`.

---

### Task 1: Project scaffolding + config module

**Files:**
- Create: `requirements.txt`, `src/amb/__init__.py`, `src/amb/paths.py`, `src/amb/config.py`
- Test: `tests/test_config.py`
- Create: `pytest.ini`

**Interfaces:**
- Produces:
  - `paths.appdata_dir() -> Path` (creates `%APPDATA%\AutoMonitorBrightness`)
  - `paths.config_path() -> Path`, `paths.log_path() -> Path`
  - `config.default_config() -> dict`
  - `config.load_config(path: Path) -> dict` (returns defaults merged if file missing/partial)
  - `config.save_config(cfg: dict, path: Path) -> None`
  - `config.ensure_model(cfg: dict, model: str) -> dict` (adds `{"offset": 0}` if model absent; returns cfg)

- [ ] **Step 1: Create `requirements.txt`**

```
screen_brightness_control==0.24.1
astral==3.2
opencv-python==4.11.0.86
pystray==0.19.5
Pillow==11.1.0
pytest==8.3.4
pyinstaller==6.11.1
```

- [ ] **Step 2: Create `pytest.ini`**

```ini
[pytest]
pythonpath = src
testpaths = tests
```

- [ ] **Step 3: Create `src/amb/__init__.py`** (empty file)

- [ ] **Step 4: Create `src/amb/paths.py`**

```python
import os
from pathlib import Path

APP_NAME = "AutoMonitorBrightness"


def appdata_dir() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home()))
    d = base / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path() -> Path:
    return appdata_dir() / "config.json"


def log_path() -> Path:
    return appdata_dir() / "amb.log"
```

- [ ] **Step 5: Write the failing test** — `tests/test_config.py`

```python
import json
from amb import config


def test_default_config_has_required_keys():
    cfg = config.default_config()
    assert cfg["master_level"] == 70
    assert cfg["auto_dimming"] is True
    assert cfg["autostart"] is False
    assert cfg["monitors_by_model"] == {}
    assert cfg["curve"]["day_max"] == 100
    assert cfg["curve"]["night_min"] == 30
    assert cfg["webcam"]["enabled"] is False


def test_load_missing_file_returns_defaults(tmp_path):
    cfg = config.load_config(tmp_path / "nope.json")
    assert cfg == config.default_config()


def test_load_merges_partial_file(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"master_level": 42}))
    cfg = config.load_config(p)
    assert cfg["master_level"] == 42
    assert cfg["curve"]["day_max"] == 100  # filled from defaults


def test_save_then_load_roundtrip(tmp_path):
    p = tmp_path / "config.json"
    cfg = config.default_config()
    cfg["master_level"] = 55
    config.save_config(cfg, p)
    assert config.load_config(p)["master_level"] == 55


def test_ensure_model_adds_default_offset():
    cfg = config.default_config()
    config.ensure_model(cfg, "PHL 271V8LB")
    assert cfg["monitors_by_model"]["PHL 271V8LB"] == {"offset": 0}


def test_ensure_model_leaves_existing_untouched():
    cfg = config.default_config()
    cfg["monitors_by_model"]["TFG HD"] = {"offset": -15}
    config.ensure_model(cfg, "TFG HD")
    assert cfg["monitors_by_model"]["TFG HD"]["offset"] == -15
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError` / `AttributeError` (config functions not defined)

- [ ] **Step 7: Write `src/amb/config.py`**

```python
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
    if model not in cfg["monitors_by_model"]:
        cfg["monitors_by_model"][model] = {"offset": 0}
    return cfg
```

- [ ] **Step 8: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS (6 passed)

- [ ] **Step 9: Commit**

```bash
git add requirements.txt pytest.ini src/amb/__init__.py src/amb/paths.py src/amb/config.py tests/test_config.py
git commit -m "feat: config module and project scaffolding"
```

---

### Task 2: Offset + clamp math

**Files:**
- Create: `src/amb/offset.py`
- Test: `tests/test_offset.py`

**Interfaces:**
- Produces:
  - `offset.clamp(value: int) -> int` (clamps to 0..100)
  - `offset.apply_offset(master: int, offset: int) -> int` (`clamp(master + offset)`)
  - `offset.model_offset(cfg: dict, model: str) -> int` (offset for model, 0 if absent)

- [ ] **Step 1: Write the failing test** — `tests/test_offset.py`

```python
from amb import offset


def test_clamp_bounds():
    assert offset.clamp(-5) == 0
    assert offset.clamp(150) == 100
    assert offset.clamp(50) == 50


def test_apply_offset_positive_and_negative():
    assert offset.apply_offset(70, 5) == 75
    assert offset.apply_offset(70, -15) == 55


def test_apply_offset_clamps():
    assert offset.apply_offset(95, 20) == 100
    assert offset.apply_offset(10, -30) == 0


def test_model_offset_absent_is_zero():
    assert offset.model_offset({"monitors_by_model": {}}, "X") == 0


def test_model_offset_reads_value():
    cfg = {"monitors_by_model": {"TFG HD": {"offset": -15}}}
    assert offset.model_offset(cfg, "TFG HD") == -15
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_offset.py -v`
Expected: FAIL (`ModuleNotFoundError: amb.offset`)

- [ ] **Step 3: Write `src/amb/offset.py`**

```python
def clamp(value: int) -> int:
    return max(0, min(100, int(round(value))))


def apply_offset(master: int, offset: int) -> int:
    return clamp(master + offset)


def model_offset(cfg: dict, model: str) -> int:
    return cfg.get("monitors_by_model", {}).get(model, {}).get("offset", 0)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_offset.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/amb/offset.py tests/test_offset.py
git commit -m "feat: offset and clamp math"
```

---

### Task 3: Sun-curve baseline

**Files:**
- Create: `src/amb/curve.py`
- Test: `tests/test_curve.py`

**Interfaces:**
- Consumes: `offset.clamp`
- Produces:
  - `curve.elevation_to_level(elevation_deg: float, night_min: int, day_max: int, full_sun_deg: float = 15.0) -> int`
  - `curve.baseline_level(cfg: dict, now: datetime, sun_elevation=None) -> int` — uses `astral.sun.elevation` for the configured lat/lon at `now`; `sun_elevation` param allows injection in tests. If lat/lon are `None`, returns `cfg["master_level"]` unchanged (curve disabled).

- [ ] **Step 1: Write the failing test** — `tests/test_curve.py`

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_curve.py -v`
Expected: FAIL (`ModuleNotFoundError: amb.curve`)

- [ ] **Step 3: Write `src/amb/curve.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_curve.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/amb/curve.py tests/test_curve.py
git commit -m "feat: sun-elevation brightness curve"
```

---

### Task 4: Webcam luminance → nudge mapping

**Files:**
- Create: `src/amb/webcam.py`
- Test: `tests/test_webcam.py`

**Interfaces:**
- Produces:
  - `webcam.luminance_to_nudge(luminance: float, max_nudge: int) -> int` — maps mean gray 0..255 to −max_nudge..+max_nudge (128 = neutral 0).
  - `webcam.measure_luminance(camera_index: int) -> float | None` — grabs one frame via OpenCV, returns mean gray, or `None` on failure. (Not unit-tested — hardware; kept tiny.)

- [ ] **Step 1: Write the failing test** — `tests/test_webcam.py`

```python
from amb import webcam


def test_neutral_luminance_is_zero_nudge():
    assert webcam.luminance_to_nudge(128, max_nudge=15) == 0


def test_bright_room_positive_nudge():
    assert webcam.luminance_to_nudge(255, max_nudge=15) == 15


def test_dark_room_negative_nudge():
    assert webcam.luminance_to_nudge(0, max_nudge=15) == -15


def test_midbright_scales():
    # (192-128)/128 = 0.5 -> +7 (rounded from 7.5)
    assert webcam.luminance_to_nudge(192, max_nudge=15) == 8
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_webcam.py -v`
Expected: FAIL (`ModuleNotFoundError: amb.webcam`)

- [ ] **Step 3: Write `src/amb/webcam.py`**

```python
def luminance_to_nudge(luminance: float, max_nudge: int) -> int:
    frac = (luminance - 128.0) / 128.0
    frac = max(-1.0, min(1.0, frac))
    return int(round(frac * max_nudge))


def measure_luminance(camera_index: int):
    try:
        import cv2
    except ImportError:
        return None
    cap = cv2.VideoCapture(camera_index)
    try:
        if not cap.isOpened():
            return None
        ok, frame = cap.read()
        if not ok or frame is None:
            return None
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return float(gray.mean())
    finally:
        cap.release()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_webcam.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/amb/webcam.py tests/test_webcam.py
git commit -m "feat: webcam luminance-to-nudge mapping"
```

---

### Task 5: Monitor backend interface + fake + real (SBC)

**Files:**
- Create: `src/amb/monitors.py`
- Test: `tests/test_monitors.py`

**Interfaces:**
- Produces:
  - `monitors.MonitorInfo` dataclass: `id: int`, `model: str`, `method: str`.
  - `monitors.model_key(info: MonitorInfo) -> str` — returns `"internal"` when `method` is `"wmi"`, else `info.model`.
  - `monitors.MonitorBackend` (Protocol/ABC): `list_monitors() -> list[MonitorInfo]`, `set_brightness(monitor_id: int, value: int) -> None`, `get_brightness(monitor_id: int) -> int`.
  - `monitors.FakeBackend(infos, brightnesses)` implementing the protocol, recording writes in `.writes` list of `(id, value)`.
  - `monitors.SBCBackend` implementing the protocol over `screen_brightness_control` (not unit-tested).

- [ ] **Step 1: Write the failing test** — `tests/test_monitors.py`

```python
from amb import monitors
from amb.monitors import MonitorInfo


def test_model_key_internal_for_wmi():
    info = MonitorInfo(id=0, model="Generic PnP", method="wmi")
    assert monitors.model_key(info) == "internal"


def test_model_key_uses_model_for_ddcci():
    info = MonitorInfo(id=1, model="PHL 271V8LB", method="ddcci")
    assert monitors.model_key(info) == "PHL 271V8LB"


def test_fake_backend_records_writes():
    infos = [MonitorInfo(id=0, model="PHL 271V8LB", method="ddcci")]
    be = monitors.FakeBackend(infos, {0: 90})
    assert be.get_brightness(0) == 90
    be.set_brightness(0, 55)
    assert be.get_brightness(0) == 55
    assert be.writes == [(0, 55)]


def test_fake_backend_lists_monitors():
    infos = [MonitorInfo(id=0, model="A", method="wmi")]
    be = monitors.FakeBackend(infos, {0: 50})
    assert be.list_monitors() == infos
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_monitors.py -v`
Expected: FAIL (`ModuleNotFoundError: amb.monitors`)

- [ ] **Step 3: Write `src/amb/monitors.py`**

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class MonitorInfo:
    id: int
    model: str
    method: str


def model_key(info: "MonitorInfo") -> str:
    return "internal" if info.method == "wmi" else info.model


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
            out.append(MonitorInfo(id=i, model=m.get("model") or m.get("name") or f"Display{i}",
                                   method=(m.get("method").__name__.lower()
                                           if not isinstance(m.get("method"), str)
                                           else str(m.get("method")).lower())))
        return out

    def get_brightness(self, monitor_id: int) -> int:
        import screen_brightness_control as sbc
        vals = sbc.get_brightness(display=monitor_id)
        return int(vals[0] if isinstance(vals, list) else vals)

    def set_brightness(self, monitor_id: int, value: int) -> None:
        import screen_brightness_control as sbc
        sbc.set_brightness(int(value), display=monitor_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_monitors.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/amb/monitors.py tests/test_monitors.py
git commit -m "feat: monitor backend interface with fake and SBC implementations"
```

---

### Task 6: Controller (the brain)

**Files:**
- Create: `src/amb/controller.py`
- Test: `tests/test_controller.py`

**Interfaces:**
- Consumes: `offset.apply_offset`, `offset.model_offset`, `curve.baseline_level`, `webcam.luminance_to_nudge`, `monitors.model_key`, `monitors.MonitorInfo`, `monitors.FakeBackend`.
- Produces:
  - `controller.compute_master(cfg, now, luminance=None, sun_elevation=None) -> int` — if `auto_dimming` is False, returns `cfg["master_level"]`; else `clamp(baseline + nudge)` where nudge comes from luminance (0 if luminance None or webcam disabled).
  - `controller.targets_for(cfg, master, infos) -> dict[int,int]` — per monitor `apply_offset(master, model_offset(cfg, model_key(info)))`.
  - `controller.apply_targets(backend, targets, last, threshold=2) -> dict[int,int]` — writes only monitors whose target differs from `last` by > `threshold` (or absent from `last`); returns the updated last-map.

- [ ] **Step 1: Write the failing test** — `tests/test_controller.py`

```python
from datetime import datetime, timezone
from amb import controller, monitors
from amb.monitors import MonitorInfo


def _cfg():
    return {
        "master_level": 70,
        "auto_dimming": True,
        "monitors_by_model": {"PHL 271V8LB": {"offset": 0}, "TFG HD": {"offset": -15},
                              "internal": {"offset": 5}},
        "curve": {"day_max": 100, "night_min": 30, "latitude": None, "longitude": None},
        "webcam": {"enabled": True, "camera_index": 0, "sample_every_sec": 300, "max_nudge": 15},
    }


def test_compute_master_auto_off_returns_master():
    cfg = _cfg(); cfg["auto_dimming"] = False; cfg["master_level"] = 42
    now = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)
    assert controller.compute_master(cfg, now) == 42


def test_compute_master_applies_webcam_nudge_on_master_baseline():
    # curve disabled (no lat/lon) so baseline == master_level 70; bright room 255 -> +15
    cfg = _cfg()
    now = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)
    assert controller.compute_master(cfg, now, luminance=255) == 85


def test_compute_master_ignores_luminance_when_webcam_disabled():
    cfg = _cfg(); cfg["webcam"]["enabled"] = False
    now = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)
    assert controller.compute_master(cfg, now, luminance=255) == 70


def test_targets_apply_model_offsets():
    cfg = _cfg()
    infos = [MonitorInfo(0, "Generic", "wmi"), MonitorInfo(1, "PHL 271V8LB", "ddcci"),
             MonitorInfo(2, "TFG HD", "ddcci")]
    t = controller.targets_for(cfg, 70, infos)
    assert t == {0: 75, 1: 70, 2: 55}


def test_apply_targets_writes_only_changed_beyond_threshold():
    infos = [MonitorInfo(0, "A", "ddcci"), MonitorInfo(1, "B", "ddcci")]
    be = monitors.FakeBackend(infos, {0: 50, 1: 50})
    last = controller.apply_targets(be, {0: 70, 1: 51}, last={0: 50, 1: 50}, threshold=2)
    assert be.writes == [(0, 70)]           # id 1 delta=1 <= threshold, skipped
    assert last == {0: 70, 1: 50}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_controller.py -v`
Expected: FAIL (`ModuleNotFoundError: amb.controller`)

- [ ] **Step 3: Write `src/amb/controller.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_controller.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/amb/controller.py tests/test_controller.py
git commit -m "feat: controller combining curve, webcam, offsets"
```

---

### Task 7: Autostart registry helper

**Files:**
- Create: `src/amb/autostart.py`
- Test: `tests/test_autostart.py`

**Interfaces:**
- Produces:
  - `autostart.set_autostart(enabled: bool, exe_path: str, _backend=None) -> None`
  - `autostart.is_enabled(_backend=None) -> bool`
  - `_backend` is an injectable dict-like used in tests to avoid touching the real registry; default `None` uses `winreg`.

- [ ] **Step 1: Write the failing test** — `tests/test_autostart.py`

```python
from amb import autostart


def test_enable_and_disable_with_fake_backend():
    store = {}
    autostart.set_autostart(True, r"C:\x\AutoMonitorBrightness.exe", _backend=store)
    assert autostart.is_enabled(_backend=store) is True
    assert store["AutoMonitorBrightness"] == r"C:\x\AutoMonitorBrightness.exe"
    autostart.set_autostart(False, r"C:\x\AutoMonitorBrightness.exe", _backend=store)
    assert autostart.is_enabled(_backend=store) is False


def test_is_enabled_false_when_absent():
    assert autostart.is_enabled(_backend={}) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_autostart.py -v`
Expected: FAIL (`ModuleNotFoundError: amb.autostart`)

- [ ] **Step 3: Write `src/amb/autostart.py`**

```python
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "AutoMonitorBrightness"


def set_autostart(enabled: bool, exe_path: str, _backend=None) -> None:
    if _backend is not None:
        if enabled:
            _backend[VALUE_NAME] = exe_path
        else:
            _backend.pop(VALUE_NAME, None)
        return
    import winreg
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
    try:
        if enabled:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass
    finally:
        winreg.CloseKey(key)


def is_enabled(_backend=None) -> bool:
    if _backend is not None:
        return VALUE_NAME in _backend
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ)
    except FileNotFoundError:
        return False
    try:
        winreg.QueryValueEx(key, VALUE_NAME)
        return True
    except FileNotFoundError:
        return False
    finally:
        winreg.CloseKey(key)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_autostart.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/amb/autostart.py tests/test_autostart.py
git commit -m "feat: autostart registry helper"
```

---

### Task 8: App engine (background loop) + tray + main entry

**Files:**
- Create: `src/amb/engine.py`, `src/amb/tray.py`, `src/amb/slider.py`, `src/amb/__main__.py`
- Test: `tests/test_engine.py`

**Interfaces:**
- Consumes: everything above.
- Produces:
  - `engine.Engine(cfg, backend, path, now_fn, luminance_fn)` with:
    - `.tick()` — one auto cycle: compute master (sampling luminance if webcam due), sync targets, persist last-map. Returns the master used.
    - `.set_master(level: int)` — manual: sets `cfg["master_level"]`, turns `auto_dimming` off, applies immediately, saves config.
    - `.set_auto(enabled: bool)`, `.nudge(delta: int)`.
  - `tray.run(engine, cfg)` — pystray icon + menu (not unit-tested).
  - `slider.ask_master(initial) -> int|None` — tkinter popup (not unit-tested).
  - `__main__.py` — builds real backend + engine, starts loop thread, runs tray.

- [ ] **Step 1: Write the failing test** — `tests/test_engine.py`

```python
from datetime import datetime, timezone
from amb import engine, monitors
from amb.monitors import MonitorInfo


def _cfg(tmp_path):
    return {
        "master_level": 70, "auto_dimming": True,
        "monitors_by_model": {"PHL 271V8LB": {"offset": 0}, "internal": {"offset": 5}},
        "curve": {"day_max": 100, "night_min": 30, "latitude": None, "longitude": None},
        "webcam": {"enabled": False, "camera_index": 0, "sample_every_sec": 300, "max_nudge": 15},
    }


def _engine(tmp_path, cfg, backend):
    now = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)
    return engine.Engine(cfg, backend, tmp_path / "config.json",
                         now_fn=lambda: now, luminance_fn=lambda idx: 255)


def test_tick_applies_master_with_offsets(tmp_path):
    cfg = _cfg(tmp_path)
    infos = [MonitorInfo(0, "Generic", "wmi"), MonitorInfo(1, "PHL 271V8LB", "ddcci")]
    be = monitors.FakeBackend(infos, {0: 10, 1: 10})
    eng = _engine(tmp_path, cfg, be)
    master = eng.tick()
    assert master == 70                     # webcam disabled, curve disabled
    assert set(be.writes) == {(0, 75), (1, 70)}


def test_set_master_turns_auto_off_and_applies(tmp_path):
    cfg = _cfg(tmp_path)
    infos = [MonitorInfo(1, "PHL 271V8LB", "ddcci")]
    be = monitors.FakeBackend(infos, {1: 10})
    eng = _engine(tmp_path, cfg, be)
    eng.set_master(40)
    assert cfg["auto_dimming"] is False
    assert cfg["master_level"] == 40
    assert (1, 40) in be.writes


def test_new_model_gets_default_offset_on_tick(tmp_path):
    cfg = _cfg(tmp_path)
    infos = [MonitorInfo(2, "MAGEDOK", "ddcci")]
    be = monitors.FakeBackend(infos, {2: 10})
    eng = _engine(tmp_path, cfg, be)
    eng.tick()
    assert cfg["monitors_by_model"]["MAGEDOK"] == {"offset": 0}
    assert (2, 70) in be.writes
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_engine.py -v`
Expected: FAIL (`ModuleNotFoundError: amb.engine`)

- [ ] **Step 3: Write `src/amb/engine.py`**

```python
from amb import config, controller, monitors


class Engine:
    def __init__(self, cfg, backend, path, now_fn, luminance_fn):
        self.cfg = cfg
        self.backend = backend
        self.path = path
        self.now_fn = now_fn
        self.luminance_fn = luminance_fn
        self.last = {}
        self._sec_since_sample = 10**9  # force first sample when webcam enabled

    def _infos(self):
        infos = self.backend.list_monitors()
        for info in infos:
            config.ensure_model(self.cfg, monitors.model_key(info))
        return infos

    def _sample_luminance(self):
        wc = self.cfg.get("webcam", {})
        if not wc.get("enabled"):
            return None
        self._sec_since_sample += 1  # coarse; real loop passes elapsed via tick cadence
        return self.luminance_fn(wc.get("camera_index", 0))

    def tick(self):
        infos = self._infos()
        luminance = self._sample_luminance()
        master = controller.compute_master(self.cfg, self.now_fn(), luminance=luminance)
        targets = controller.targets_for(self.cfg, master, infos)
        self.last = controller.apply_targets(self.backend, targets, self.last)
        return master

    def _apply_now(self, master):
        infos = self._infos()
        targets = controller.targets_for(self.cfg, master, infos)
        self.last = controller.apply_targets(self.backend, targets, self.last)

    def set_master(self, level: int):
        self.cfg["master_level"] = max(0, min(100, int(level)))
        self.cfg["auto_dimming"] = False
        self._apply_now(self.cfg["master_level"])
        config.save_config(self.cfg, self.path)

    def set_auto(self, enabled: bool):
        self.cfg["auto_dimming"] = bool(enabled)
        config.save_config(self.cfg, self.path)

    def nudge(self, delta: int):
        self.set_master(self.cfg["master_level"] + delta)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_engine.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Write `src/amb/slider.py`** (not unit-tested)

```python
def ask_master(initial: int):
    import tkinter as tk
    result = {"value": None}
    root = tk.Tk()
    root.title("Master Brightness")
    root.attributes("-topmost", True)
    var = tk.IntVar(value=initial)

    def commit():
        result["value"] = var.get()
        root.destroy()

    tk.Scale(root, from_=0, to=100, orient="horizontal", length=300,
             variable=var).pack(padx=12, pady=8)
    tk.Button(root, text="Apply", command=commit).pack(pady=(0, 10))
    root.mainloop()
    return result["value"]
```

- [ ] **Step 6: Write `src/amb/tray.py`** (not unit-tested)

```python
import sys
from PIL import Image, ImageDraw
import pystray
from amb import autostart, slider


def _icon_image():
    img = Image.new("RGB", (64, 64), "black")
    d = ImageDraw.Draw(img)
    d.ellipse((16, 16, 48, 48), fill="white")
    return img


def run(engine, cfg, exe_path):
    def open_slider(icon, item):
        val = slider.ask_master(cfg["master_level"])
        if val is not None:
            engine.set_master(val)

    def toggle_auto(icon, item):
        engine.set_auto(not cfg["auto_dimming"])
        icon.update_menu()

    def toggle_autostart(icon, item):
        new = not autostart.is_enabled()
        autostart.set_autostart(new, exe_path)
        cfg["autostart"] = new
        icon.update_menu()

    def brighter(icon, item): engine.nudge(+10)
    def dimmer(icon, item): engine.nudge(-10)
    def quit_app(icon, item): icon.stop(); sys.exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Set master brightness…", open_slider, default=True),
        pystray.MenuItem("Brighter (+10)", brighter),
        pystray.MenuItem("Dimmer (−10)", dimmer),
        pystray.MenuItem("Auto dimming", toggle_auto,
                         checked=lambda i: cfg["auto_dimming"]),
        pystray.MenuItem("Start with Windows", toggle_autostart,
                         checked=lambda i: cfg["autostart"]),
        pystray.MenuItem("Quit", quit_app),
    )
    pystray.Icon("AutoMonitorBrightness", _icon_image(),
                 "Auto Monitor Brightness", menu).run()
```

- [ ] **Step 7: Write `src/amb/__main__.py`** (not unit-tested)

```python
import sys
import threading
import time
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from amb import paths, config, monitors, webcam, autostart
from amb.engine import Engine
from amb import tray


def _setup_logging():
    handler = RotatingFileHandler(paths.log_path(), maxBytes=512_000, backupCount=2)
    logging.basicConfig(level=logging.INFO, handlers=[handler],
                        format="%(asctime)s %(levelname)s %(message)s")


def _exe_path() -> str:
    return sys.executable if getattr(sys, "frozen", False) else sys.argv[0]


def main():
    _setup_logging()
    cfg = config.load_config(paths.config_path())
    exe_path = _exe_path()
    # keep registry in sync with saved preference
    autostart.set_autostart(cfg.get("autostart", False), exe_path)

    backend = monitors.SBCBackend()
    eng = Engine(cfg, backend, paths.config_path(),
                 now_fn=lambda: datetime.now(timezone.utc).astimezone(),
                 luminance_fn=webcam.measure_luminance)

    def loop():
        while True:
            try:
                if cfg.get("auto_dimming", True):
                    eng.tick()
            except Exception:
                logging.exception("tick failed")
            time.sleep(cfg.get("webcam", {}).get("sample_every_sec", 300)
                       if cfg.get("auto_dimming") else 30)

    threading.Thread(target=loop, daemon=True).start()
    tray.run(eng, cfg, exe_path)


if __name__ == "__main__":
    main()
```

- [ ] **Step 8: Run the full test suite**

Run: `pytest -v`
Expected: PASS (all tasks' tests green)

- [ ] **Step 9: Manual smoke test on hardware**

Run: `python -m amb`
Expected: tray icon appears; "Set master brightness…" opens a slider; applying it visibly changes all monitors; "Auto dimming" and "Start with Windows" toggles show checkmarks. Confirm all six displays respond.

- [ ] **Step 10: Commit**

```bash
git add src/amb/engine.py src/amb/slider.py src/amb/tray.py src/amb/__main__.py tests/test_engine.py
git commit -m "feat: engine loop, tray UI, and app entry point"
```

---

### Task 9: Package standalone .exe

**Files:**
- Create: `build.ps1`, `README.md`

**Interfaces:** none (build artifact).

- [ ] **Step 1: Create `build.ps1`**

```powershell
pip install -r requirements.txt
pyinstaller --onefile --noconsole --name AutoMonitorBrightness `
  --collect-all screen_brightness_control `
  --collect-all pystray `
  src/amb/__main__.py
Write-Output "Built dist/AutoMonitorBrightness.exe"
```

- [ ] **Step 2: Create `README.md`**

```markdown
# AutoMonitorBrightness

Windows tray app that syncs brightness across all monitors from one master level,
with per-model offsets and optional auto day/night dimming (sun curve + webcam nudge).

## Build
    powershell -ExecutionPolicy Bypass -File build.ps1
Output: `dist/AutoMonitorBrightness.exe` (standalone, no Python required).

## Run
Double-click the exe. A tray icon appears. Right-click for master brightness,
auto-dimming toggle, and start-with-Windows toggle. Config: `%APPDATA%\AutoMonitorBrightness\config.json`.
```

- [ ] **Step 3: Build the exe**

Run: `powershell -ExecutionPolicy Bypass -File build.ps1`
Expected: `dist/AutoMonitorBrightness.exe` created, no errors.

- [ ] **Step 4: Smoke test the exe**

Run: `dist/AutoMonitorBrightness.exe`
Expected: tray icon appears and controls work with no Python on PATH.

- [ ] **Step 5: Commit**

```bash
git add build.ps1 README.md
git commit -m "build: PyInstaller packaging and README"
```

---

## Self-Review

**Spec coverage:**
- Sync all monitors from master + per-model offsets → Tasks 2, 6, 8 ✅
- Internal (WMI) + DDC/CI control → Task 5 (`SBCBackend`, `model_key`) ✅
- Sun-curve baseline → Task 3 ✅
- Optional webcam nudge → Tasks 4, 6 ✅
- Auto-dimming on/off switch → Tasks 6, 8 (`compute_master`, `set_auto`) ✅
- Autostart on/off switch → Tasks 7, 8 ✅
- Model-grouped offsets, auto-add new models → Tasks 1, 8 (`ensure_model`) ✅
- Anti-flicker / rate limiting → Task 6 (`apply_targets` threshold) ✅
- Resilience (skip asleep/unplugged) → Task 6 (try/except in `apply_targets`), Task 8 (loop try/except) ✅
- Standalone exe → Task 9 ✅
- Config in %APPDATA% → Task 1 ✅

**Placeholder scan:** No TBD/TODO; every code step shows full code. ✅

**Type consistency:** `MonitorInfo(id, model, method)`, `model_key`, `apply_offset`, `model_offset`, `baseline_level`, `luminance_to_nudge`, `compute_master`, `targets_for`, `apply_targets`, `Engine` methods consistent across tasks. ✅

**Note on manual override precedence:** dragging the slider calls `set_master`, which sets `auto_dimming=False` — matches the spec's "snaps auto off." The tray "Auto dimming" checkbox re-enables it.
