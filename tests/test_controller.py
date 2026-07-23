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
    infos = [MonitorInfo(0, "Generic", "wmi"), MonitorInfo(1, "PHL 271V8LB", "vcp"),
             MonitorInfo(2, "TFG HD", "vcp")]
    t = controller.targets_for(cfg, 70, infos)
    assert t == {0: 75, 1: 70, 2: 55}


def test_apply_targets_writes_only_changed_beyond_threshold():
    infos = [MonitorInfo(0, "A", "vcp"), MonitorInfo(1, "B", "vcp")]
    be = monitors.FakeBackend(infos, {0: 50, 1: 50})
    last = controller.apply_targets(be, {0: 70, 1: 51}, last={0: 50, 1: 50}, threshold=2)
    assert be.writes == [(0, 70)]           # id 1 delta=1 <= threshold, skipped
    assert last == {0: 70, 1: 50}
