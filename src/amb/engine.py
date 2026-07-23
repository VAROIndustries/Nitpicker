from amb import config, controller, monitors


class Engine:
    def __init__(self, cfg, backend, path, now_fn, luminance_fn):
        self.cfg = cfg
        self.backend = backend
        self.path = path
        self.now_fn = now_fn
        self.luminance_fn = luminance_fn
        self.last = {}

    def _infos(self):
        infos = self.backend.list_monitors()
        for info in infos:
            config.ensure_model(self.cfg, monitors.model_key(info))
        return infos

    def _sample_luminance(self):
        wc = self.cfg.get("webcam", {})
        if not wc.get("enabled"):
            return None
        return self.luminance_fn(wc.get("camera_index", 0))

    def tick(self):
        infos = self._infos()
        luminance = self._sample_luminance()
        master = controller.compute_master(self.cfg, self.now_fn(), luminance=luminance)
        targets = controller.targets_for(self.cfg, master, infos)
        self.last = controller.apply_targets(self.backend, targets, self.last)
        return master

    def _apply_now(self, master):
        infos = self._infos()
        targets = controller.targets_for(self.cfg, master, infos)
        self.last = controller.apply_targets(self.backend, targets, self.last)

    def set_master(self, level: int):
        self.cfg["master_level"] = max(0, min(100, int(level)))
        self.cfg["auto_dimming"] = False
        self._apply_now(self.cfg["master_level"])
        config.save_config(self.cfg, self.path)

    def set_auto(self, enabled: bool):
        self.cfg["auto_dimming"] = bool(enabled)
        config.save_config(self.cfg, self.path)

    def nudge(self, delta: int):
        self.set_master(self.cfg["master_level"] + delta)
