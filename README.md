# AutoMonitorBrightness

A Windows system-tray app that keeps the brightness of **all your monitors** in sync from a
single master level, with per-monitor calibration offsets, plus an optional automatic
day/night dimming feature.

Verified working on: the laptop's internal panel (via WMI) and all five external monitors —
3× Philips 271V8LB and 2× USB monitors (TFG, MAGEDOK) — via DDC/CI.

## Features

- **One master level drives every monitor.** Set it from the tray; all six change together.
- **Per-model offsets.** Each monitor type can start higher or lower than the master (e.g.
  USB monitors −15). Identical hardware (the three Philips) shares one offset.
- **Auto dimming (toggleable).** A sunrise→sunset curve for your location sets a baseline,
  with an optional webcam light-meter nudge (there is no ambient light sensor on this
  hardware, so the webcam is the sensing option). Turn the whole thing on/off from the tray.
- **Start with Windows (toggleable).** A tray switch adds/removes the autostart entry.
- **Manual override.** Dragging the master slider turns auto off so it won't fight you.

## Build

    powershell -ExecutionPolicy Bypass -File build.ps1

Output: `dist/AutoMonitorBrightness.exe` — a standalone executable, no Python required.

## Run (from source)

    .venv/Scripts/python.exe -m amb

A tray icon appears. Right-click for: set master brightness, brighter/dimmer, auto-dimming
toggle, start-with-Windows toggle, quit.

## Configuration

`%APPDATA%\AutoMonitorBrightness\config.json` — offsets are keyed by monitor identity
(`manufacturer_id + model`, or `internal` for the laptop). Edit offsets there, or use the
tray. To enable the sun curve, set `curve.latitude` / `curve.longitude`. To enable the
webcam nudge, set `webcam.enabled` to `true` and pick `camera_index`.

Log file: `%APPDATA%\AutoMonitorBrightness\amb.log`.

## Tests

    .venv/Scripts/python.exe -m pytest
