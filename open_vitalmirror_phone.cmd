@echo off
setlocal
set "ROOT=%~dp0"
set "PYTHON_EXE=C:\Users\USER\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

powershell -NoExit -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ip=(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' -and $_.PrefixOrigin -ne 'WellKnown' } | Select-Object -First 1 -ExpandProperty IPAddress); " ^
  "$env:PORT='8765'; $env:HOST='0.0.0.0'; " ^
  "Set-Location '%ROOT%'; " ^
  "Write-Host ''; Write-Host 'VitalMirror LAN mode'; " ^
  "Write-Host ('PC:    http://127.0.0.1:8765/'); " ^
  "if ($ip) { Write-Host ('Phone: http://' + $ip + ':8765/phone') } else { Write-Host 'Phone IP not found. Check Wi-Fi connection.' }; " ^
  "Write-Host ''; Start-Process 'http://127.0.0.1:8765/'; & '%PYTHON_EXE%' server.py"
