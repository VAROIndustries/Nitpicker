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
