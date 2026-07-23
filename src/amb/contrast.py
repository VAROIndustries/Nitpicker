"""DDC/CI contrast control via the Windows dxva2 API.

``screen_brightness_control`` only exposes brightness, so contrast is handled here with
raw ctypes calls. External monitors are correlated to physical-monitor handles by display
order — verified on this hardware to match ``screen_brightness_control``'s enumeration order.
Only imported at runtime on the real backend; unit tests use the fake backend and never
touch this module.
"""
import ctypes
import logging
from ctypes import wintypes

log = logging.getLogger(__name__)


class _PHYSICAL_MONITOR(ctypes.Structure):
    _fields_ = [("hPhysicalMonitor", wintypes.HANDLE),
                ("szPhysicalMonitorDescription", wintypes.WCHAR * 128)]


def _enum_hmonitors():
    result = []
    proc = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HMONITOR, wintypes.HDC,
                              ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)

    def _cb(hmon, hdc, lprect, lparam):
        result.append(hmon)
        return 1

    ctypes.windll.user32.EnumDisplayMonitors(0, 0, proc(_cb), 0)
    return result


def _physical_monitors(hmon):
    count = wintypes.DWORD()
    if not ctypes.windll.dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR(hmon, ctypes.byref(count)):
        return []
    arr = (_PHYSICAL_MONITOR * count.value)()
    if not ctypes.windll.dxva2.GetPhysicalMonitorsFromHMONITOR(hmon, count.value, arr):
        return []
    return [arr[i].hPhysicalMonitor for i in range(count.value)]


def _get_contrast(h):
    mn, cur, mx = wintypes.DWORD(), wintypes.DWORD(), wintypes.DWORD()
    ok = ctypes.windll.dxva2.GetMonitorContrast(h, ctypes.byref(mn), ctypes.byref(cur),
                                                ctypes.byref(mx))
    return bool(ok), cur.value, mx.value


def _set_contrast(h, value):
    return bool(ctypes.windll.dxva2.SetMonitorContrast(h, int(value)))


def _destroy(h):
    try:
        ctypes.windll.dxva2.DestroyPhysicalMonitor(h)
    except Exception:
        pass


def open_contrast_handles():
    """Physical-monitor handles that support DDC/CI contrast, in display order.

    The internal laptop panel is naturally excluded (it fails GetMonitorContrast). The
    caller MUST pass the result to close_contrast_handles() when done.
    """
    handles = []
    for hmon in _enum_hmonitors():
        for pm in _physical_monitors(hmon):
            ok, _, _ = _get_contrast(pm)
            if ok:
                handles.append(pm)
            else:
                _destroy(pm)
    return handles


def close_contrast_handles(handles):
    for h in handles:
        _destroy(h)


def count_contrast_handles():
    handles = open_contrast_handles()
    n = len(handles)
    close_contrast_handles(handles)
    return n


def set_contrast_by_position(pos, value):
    """Set contrast (0-100) on the pos-th DDC-capable external monitor in display order."""
    handles = open_contrast_handles()
    try:
        if pos < 0 or pos >= len(handles):
            log.warning("contrast position %d out of range (have %d handles)", pos, len(handles))
            return False
        h = handles[pos]
        ok, _, mx = _get_contrast(h)
        mx = mx or 100
        device_value = max(0, min(mx, round(value / 100.0 * mx)))
        return _set_contrast(h, device_value)
    finally:
        close_contrast_handles(handles)
