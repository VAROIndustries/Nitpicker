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
