from amb import monitors
from amb.monitors import MonitorInfo


def test_model_key_internal_for_wmi():
    info = MonitorInfo(id=0, model="Generic Monitor", method="wmi", manufacturer_id="SDC")
    assert monitors.model_key(info) == "internal"


def test_model_key_combines_manufacturer_and_model():
    info = MonitorInfo(id=1, model="271V8LB", method="vcp", manufacturer_id="PHL")
    assert monitors.model_key(info) == "PHL 271V8LB"


def test_identical_philips_share_one_key():
    a = MonitorInfo(id=1, model="271V8LB", method="vcp", manufacturer_id="PHL")
    b = MonitorInfo(id=2, model="271V8LB", method="vcp", manufacturer_id="PHL")
    assert monitors.model_key(a) == monitors.model_key(b)


def test_generic_usb_monitors_stay_distinct_by_manufacturer():
    tfg = MonitorInfo(id=4, model="Generic Monitor", method="vcp", manufacturer_id="TFG")
    hcd = MonitorInfo(id=5, model="Generic Monitor", method="vcp", manufacturer_id="HCD")
    assert monitors.model_key(tfg) != monitors.model_key(hcd)
    assert monitors.model_key(tfg) == "TFG Generic Monitor"


def test_fake_backend_records_writes():
    infos = [MonitorInfo(id=0, model="PHL 271V8LB", method="vcp")]
    be = monitors.FakeBackend(infos, {0: 90})
    assert be.get_brightness(0) == 90
    be.set_brightness(0, 55)
    assert be.get_brightness(0) == 55
    assert be.writes == [(0, 55)]


def test_fake_backend_lists_monitors():
    infos = [MonitorInfo(id=0, model="A", method="wmi")]
    be = monitors.FakeBackend(infos, {0: 50})
    assert be.list_monitors() == infos
