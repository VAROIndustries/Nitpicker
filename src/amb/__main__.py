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
