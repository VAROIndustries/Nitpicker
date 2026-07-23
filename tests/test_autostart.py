from amb import autostart


def test_enable_and_disable_with_fake_backend():
    store = {}
    autostart.set_autostart(True, r"C:\x\Nitpicker.exe", _backend=store)
    assert autostart.is_enabled(_backend=store) is True
    assert store["Nitpicker"] == r"C:\x\Nitpicker.exe"
    autostart.set_autostart(False, r"C:\x\Nitpicker.exe", _backend=store)
    assert autostart.is_enabled(_backend=store) is False


def test_is_enabled_false_when_absent():
    assert autostart.is_enabled(_backend={}) is False
