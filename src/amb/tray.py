import sys
from PIL import Image, ImageDraw
import pystray
from amb import autostart, slider, settings_window


def _icon_image():
    img = Image.new("RGB", (64, 64), "black")
    d = ImageDraw.Draw(img)
    d.ellipse((16, 16, 48, 48), fill="white")
    return img


def run(engine, cfg, exe_path):
    def open_slider(icon, item):
        val = slider.ask_master(cfg["master_level"])
        if val is not None:
            engine.set_master(val)

    def toggle_auto(icon, item):
        engine.set_auto(not cfg["auto_dimming"])
        icon.update_menu()

    def toggle_autostart(icon, item):
        new = not autostart.is_enabled()
        autostart.set_autostart(new, exe_path)
        cfg["autostart"] = new
        icon.update_menu()

    def open_settings(icon, item):
        rows = engine.monitor_rows()

        def on_save(results):
            for r in results:
                engine.set_offset(r["key"], r["offset"])
                engine.set_contrast(r["key"], r["contrast"])

        settings_window.open_settings(rows, on_save)

    def brighter(icon, item):
        engine.nudge(+10)

    def dimmer(icon, item):
        engine.nudge(-10)

    def quit_app(icon, item):
        icon.stop()
        sys.exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Set master brightness…", open_slider, default=True),
        pystray.MenuItem("Per-monitor settings…", open_settings),
        pystray.MenuItem("Brighter (+10)", brighter),
        pystray.MenuItem("Dimmer (−10)", dimmer),
        pystray.MenuItem("Auto dimming", toggle_auto,
                         checked=lambda i: cfg["auto_dimming"]),
        pystray.MenuItem("Start with Windows", toggle_autostart,
                         checked=lambda i: cfg["autostart"]),
        pystray.MenuItem("Quit", quit_app),
    )
    pystray.Icon("Nitpicker", _icon_image(),
                 "Nitpicker — monitor brightness & contrast", menu).run()
