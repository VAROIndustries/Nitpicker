# Build AutoMonitorBrightness.exe (standalone, no Python required)
$py = if (Test-Path ".venv/Scripts/python.exe") { ".venv/Scripts/python.exe" } else { "python" }
& $py -m pip install -r requirements.txt
& $py -m PyInstaller --onefile --noconsole --name AutoMonitorBrightness `
  --paths src `
  --collect-all screen_brightness_control `
  --collect-all pystray `
  --collect-submodules win32com `
  run.py
Write-Output "Built dist/AutoMonitorBrightness.exe"
