from amb import webcam


def test_neutral_luminance_is_zero_nudge():
    assert webcam.luminance_to_nudge(128, max_nudge=15) == 0


def test_bright_room_positive_nudge():
    assert webcam.luminance_to_nudge(255, max_nudge=15) == 15


def test_dark_room_negative_nudge():
    assert webcam.luminance_to_nudge(0, max_nudge=15) == -15


def test_midbright_scales():
    # (192-128)/128 = 0.5 -> +7.5 -> rounds to 8 (banker's rounding of 7.5 -> 8)
    assert webcam.luminance_to_nudge(192, max_nudge=15) == 8
