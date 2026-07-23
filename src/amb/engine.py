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

    def apply_contrast(self):
        """Set each connected monitor's contrast from its per-model config (skips None)."""
        for info in self._infos():
            key = monitors.model_key(info)
            c = self.cfg["monitors_by_model"].get(key, {}).get("contrast")
            if c is not None and self.backend.supports_contrast(info.id):
                try:
                    self.backend.set_contrast(info.id, int(c))
                except Exception:
                    pass

    def set_offset(self, model_key: str, value: int):
        entry = self.cfg.setdefault("monitors_by_model", {}).setdefault(model_key, {})
        entry["offset"] = max(-100, min(100, int(value)))
        config.save_config(self.cfg, self.path)
        self._apply_now(self.cfg["master_level"])

    def set_contrast(self, model_key: str, value):
        entry = self.cfg.setdefault("monitors_by_model", {}).setdefault(model_key, {})
        entry["contrast"] = None if value is None else max(0, min(100, int(value)))
        config.save_config(self.cfg, self.path)
        self.apply_contrast()

    def monitor_rows(self):
        """One row per connected monitor model group, for the settings UI."""
        rows = {}
        order = []
        for info in self._infos():
            key = monitors.model_key(info)
            if key not in rows:
                entry = self.cfg["monitors_by_model"].get(key, {})
                rows[key] = {
                    "key": key,
                    "count": 0,
                    "offset": entry.get("offset", 0),
                    "contrast": entry.get("contrast"),
                    "contrast_supported": self.backend.supports_contrast(info.id),
                }
                order.append(key)
            rows[key]["count"] += 1
        out = []
        for key in order:
            r = rows[key]
            label = "Laptop screen" if key == "internal" else key
            if r["count"] > 1:
                label += f"  (x{r['count']})"
            r["label"] = label
            out.append(r)
        return out
