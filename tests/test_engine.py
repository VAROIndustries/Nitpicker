from datetime import datetime, timezone
from amb import engine, monitors
from amb.monitors import MonitorInfo


def _cfg():
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
    cfg = _cfg()
    infos = [MonitorInfo(0, "Generic", "wmi"), MonitorInfo(1, "PHL 271V8LB", "vcp")]
    be = monitors.FakeBackend(infos, {0: 10, 1: 10})
    eng = _engine(tmp_path, cfg, be)
    master = eng.tick()
    assert master == 70                     # webcam disabled, curve disabled
    assert set(be.writes) == {(0, 75), (1, 70)}


def test_set_master_turns_auto_off_and_applies(tmp_path):
    cfg = _cfg()
    infos = [MonitorInfo(1, "PHL 271V8LB", "vcp")]
    be = monitors.FakeBackend(infos, {1: 10})
    eng = _engine(tmp_path, cfg, be)
    eng.set_master(40)
    assert cfg["auto_dimming"] is False
    assert cfg["master_level"] == 40
    assert (1, 40) in be.writes


def test_new_model_gets_default_offset_on_tick(tmp_path):
    cfg = _cfg()
    infos = [MonitorInfo(2, "MAGEDOK", "vcp")]
    be = monitors.FakeBackend(infos, {2: 10})
    eng = _engine(tmp_path, cfg, be)
    eng.tick()
    assert cfg["monitors_by_model"]["MAGEDOK"] == {"offset": 0, "contrast": None}
    assert (2, 70) in be.writes


def test_apply_contrast_sets_external_but_skips_internal_and_none(tmp_path):
    cfg = _cfg()
    cfg["monitors_by_model"]["PHL 271V8LB"]["contrast"] = 65
    cfg["monitors_by_model"]["internal"]["contrast"] = 80  # internal can't do contrast
    infos = [MonitorInfo(0, "Generic", "wmi"), MonitorInfo(1, "PHL 271V8LB", "vcp")]
    be = monitors.FakeBackend(infos, {0: 10, 1: 10})  # only id 1 supports contrast
    eng = _engine(tmp_path, cfg, be)
    eng.apply_contrast()
    assert be.contrast_writes == [(1, 65)]  # internal skipped, external set


def test_set_offset_persists_and_applies(tmp_path):
    cfg = _cfg()
    infos = [MonitorInfo(1, "PHL 271V8LB", "vcp")]
    be = monitors.FakeBackend(infos, {1: 10})
    eng = _engine(tmp_path, cfg, be)
    eng.set_offset("PHL 271V8LB", -20)
    assert cfg["monitors_by_model"]["PHL 271V8LB"]["offset"] == -20
    assert (1, 50) in be.writes  # master 70 + (-20)


def test_set_contrast_persists_and_applies(tmp_path):
    cfg = _cfg()
    infos = [MonitorInfo(1, "PHL 271V8LB", "vcp")]
    be = monitors.FakeBackend(infos, {1: 10})
    eng = _engine(tmp_path, cfg, be)
    eng.set_contrast("PHL 271V8LB", 55)
    assert cfg["monitors_by_model"]["PHL 271V8LB"]["contrast"] == 55
    assert (1, 55) in be.contrast_writes


def test_monitor_rows_groups_and_reports_contrast_support(tmp_path):
    cfg = _cfg()
    infos = [MonitorInfo(0, "Generic", "wmi"),
             MonitorInfo(1, "271V8LB", "vcp", manufacturer_id="PHL"),
             MonitorInfo(2, "271V8LB", "vcp", manufacturer_id="PHL")]
    be = monitors.FakeBackend(infos, {0: 10, 1: 10, 2: 10})
    eng = _engine(tmp_path, cfg, be)
    rows = eng.monitor_rows()
    keys = {r["key"]: r for r in rows}
    assert set(keys) == {"internal", "PHL 271V8LB"}
    assert keys["PHL 271V8LB"]["count"] == 2
    assert keys["PHL 271V8LB"]["contrast_supported"] is True
    assert keys["internal"]["contrast_supported"] is False
