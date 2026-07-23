# AutoMonitorBrightness — Design Spec

_Date: 2026-07-23_

## Goal

A Windows system-tray app that keeps the brightness of all monitors on one machine
in sync from a single master level, with per-monitor-model calibration offsets, and an
optional automatic day/night dimming feature (time-of-day curve plus an optional webcam
light-meter nudge). Shipped as a standalone `.exe`.

## Verified hardware feasibility (probed on the target machine 2026-07-23)

| Component | Control path | Status |
|---|---|---|
| Internal laptop panel (Samsung/SDC) | WMI (`WmiMonitorBrightness`) | ✅ controllable |
| 3× Philips 271V8LB | DDC/CI (dxva2) | ✅ controllable |
| USB monitor TFG HD | DDC/CI (dxva2) | ✅ controllable |
| USB monitor MAGEDOK | DDC/CI (dxva2) | ✅ controllable |
| Ambient light sensor | — | ❌ none exists (Hello cam = IR facial recognition only) |

All six displays are controllable in hardware (0–100). No dimming-overlay fallback needed.
No OS-level ambient light sensor exists, so auto-sensing uses a webcam frame as a light meter.

## Stack

Python packaged to a standalone `.exe` via **PyInstaller** (`--onefile --noconsole`).

- `screen_brightness_control` — sets brightness for BOTH the internal (WMI) and external
  (DDC/CI) monitors through one API.
- `astral` — sunrise/sunset curve for the user's location.
- `opencv-python` — grab one webcam frame, compute average luminance.
- `pystray` + `Pillow` — tray icon and menu.
- Standard `tkinter` — small popup master-slider window (pystray menus can't host a slider).

## Components (seven single-purpose modules)

- **`monitors`** — hardware layer. Enumerates displays, identifies each by model, sets
  brightness. Applies per-model offset + clamps 0–100. Sits behind an interface so the
  controller can be tested against a fake backend.
- **`config`** — load/save `config.json` in `%APPDATA%\AutoMonitorBrightness\`.
- **`curve`** — given location + current time, returns baseline master level from a smooth
  sunrise→sunset curve (`day_max` at midday, `night_min` at night).
- **`webcam`** — optional. Grabs one frame from the chosen camera, computes average
  luminance, returns a bounded nudge (±`max_nudge`).
- **`controller`** — the brain. On a timer: `master = clamp(curve_baseline + webcam_nudge)`
  when auto is on; then per-monitor `clamp(master + offset)`; sets only changed values, with
  anti-flicker smoothing and DDC/CI rate-limiting.
- **`tray`** — pystray icon: master slider popup, ±nudge, Auto-dimming on/off, Autostart
  on/off, settings, quit.
- **`main`** — wires modules together; registers/removes Windows autostart.

## Config & data model

`config.json` — offsets keyed by monitor **model** so identical hardware shares one setting:

```json
{
  "master_level": 70,
  "auto_dimming": true,
  "autostart": true,
  "monitors_by_model": {
    "PHL 271V8LB": { "offset": 0 },
    "TFG HD":      { "offset": -15 },
    "MAGEDOK":     { "offset": -10 },
    "internal":    { "offset": 5 }
  },
  "curve":  { "day_max": 100, "night_min": 30, "location": "lat,lon" },
  "webcam": { "enabled": true, "camera_index": 0, "sample_every_sec": 300, "max_nudge": 15 }
}
```

On start the app enumerates displays, matches each to its model entry (creating a default
`offset: 0` for any new model), and handles unplug/replug automatically.

## Auto logic & the two switches

- **Autostart switch** — writes/removes an `HKCU\...\Run` registry entry pointing at the exe.
  Controls only whether the app launches at login.
- **Auto-dimming switch** — independent. Off ⇒ master stays where the user left it (manual);
  curve + webcam ignored. On ⇒ each tick `master = clamp(curve_baseline + webcam_nudge)`.
- **Manual override precedence** — dragging the master slider while auto is on snaps auto
  **off** so it won't fight the user. User re-enables auto to resume. No override timer.
- **Anti-flicker** — only write a change above a small threshold; ramp in a couple of steps;
  rate-limit DDC/CI writes so monitors are never spammed.

## Packaging, autostart & error handling

- **PyInstaller** → one self-contained `AutoMonitorBrightness.exe` with embedded icon; no
  Python needed on the machine.
- **Autostart** via the registry Run key (added/removed by the toggle).
- **Resilience** — a sleeping/unresponsive monitor's DDC/CI write is retried once then skipped
  for that tick and logged; never crashes the tray. Webcam-busy just skips that cycle's nudge
  and keeps the curve baseline. Rotating log file in `%APPDATA%`.

## Testing

Unit-tested pure logic: sun **curve** (deterministic for time+location), **offset+clamp**
math, **webcam luminance→nudge** mapping (synthetic frames), **config** load/save/migration.
The hardware layer sits behind an interface, so the **controller** is tested against a fake
monitor backend — no physical displays required for the suite.

## Out of scope (YAGNI)

- Per-physical-instance offsets (models group instead).
- Min/max range mapping per monitor (offset-only chosen).
- Real ambient light sensor integration (none exists on this hardware).
- Cross-machine / multi-user sync.
