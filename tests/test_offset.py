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
