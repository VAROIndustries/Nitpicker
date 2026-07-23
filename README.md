# Nitpicker

**One brightness knob for every monitor on your PC.** Nitpicker is a Windows system-tray app
that keeps the brightness of *all* your displays in sync from a single master level — with
per-monitor calibration offsets and per-monitor contrast — plus optional automatic day/night
dimming. Ships as a standalone `.exe`; no Python required.

## Why "Nitpicker"?

A **nit** (short for *n_it_, from the Latin *nitere*, "to shine") is the real unit of screen
brightness — one nit is one candela per square metre (cd/m²). It's the number on the spec
sheet when a monitor claims "400 nits". Nitpicker is the tool that *picks the nits* for every
screen on your desk at once — and yes, it's for people who are a little particular about
getting their brightness *just right*. Nit-picking, done literally.

## The problem it solves

If you run several monitors, they never agree. The laptop panel is software-dimmable, but each
external monitor has its own clunky physical buttons — and they all start at different levels.
Matching them means walking down the row poking OSD menus. Nitpicker drives every one of them
from a single slider.

Verified working across a real 6-display setup: a laptop internal panel (via WMI) plus five
external monitors — 3× Philips and 2× USB monitors — all over DDC/CI.

## Features

- **One master level drives every monitor.** Set it from the tray; all displays change together.
- **Per-monitor settings window** (tray → "Per-monitor settings…"). One row per monitor group
  with a **brightness-offset** slider and a **contrast** slider — no config editing needed.
- **Per-model offsets.** Each monitor type can sit higher or lower than the master (e.g. USB
  monitors −15). Identical hardware (say, three of the same Philips) shares one offset.
- **Per-model contrast.** Absolute contrast per monitor group over DDC/CI (external monitors
  only — laptop panels have no contrast control). Leave "Set contrast" unchecked to not touch it.
- **Auto dimming (toggleable).** A sunrise→sunset curve for your location sets a baseline, with
  an optional webcam light-meter nudge. Turn the whole thing on/off from the tray.
- **Start with Windows (toggleable).** A tray switch adds/removes the autostart entry.
- **Manual override.** Dragging the master slider turns auto off so it won't fight you.

## Install

Download **Nitpicker.exe** from the [latest release](https://github.com/VAROIndustries/Nitpicker/releases/latest)
and run it — no installer needed. A tray icon appears; right-click for all controls.

## Run from source

Windows, Python 3.12+:

    git clone https://github.com/VAROIndustries/Nitpicker.git
    cd Nitpicker
    pip install -r requirements.txt
    python -m amb

## Build the exe

    powershell -ExecutionPolicy Bypass -File build.ps1

Output: `dist/Nitpicker.exe` — standalone, no Python required.

## Configuration

`%APPDATA%\Nitpicker\config.json` — offsets/contrast are keyed by monitor identity
(`manufacturer_id + model`, or `internal` for the laptop). Edit there or use the tray. To
enable the sun curve, set `curve.latitude` / `curve.longitude`. To enable the webcam nudge,
set `webcam.enabled` to `true` and pick `camera_index`. Log: `%APPDATA%\Nitpicker\amb.log`.

## How it works

- **Brightness**: [`screen_brightness_control`](https://pypi.org/project/screen-brightness-control/)
  drives both the internal panel (WMI) and external monitors (DDC/CI) through one API.
- **Contrast**: raw DDC/CI via the Windows `dxva2` API (external monitors only).
- **Auto**: [`astral`](https://pypi.org/project/astral/) sun elevation for the curve;
  OpenCV grabs a webcam frame for the optional ambient nudge.
- **Identity**: monitors are grouped by `manufacturer_id + model` so identical panels share
  settings while different ones stay independent.

## Tests

    .venv/Scripts/python.exe -m pytest

## License

MIT © VARØ Industries
