@echo off
setlocal
set "ROOT=%~dp0"
set "PYTHON_EXE=C:\Users\USER\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"
set "PORT=8765"
set "HOST=127.0.0.1"

powershell -NoProfile -ExecutionPolicy Bypass -Command "if (-not (Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue)) { Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList 'server.py' -WorkingDirectory '%ROOT%' -WindowStyle Hidden; Start-Sleep -Seconds 3 }; Start-Process 'http://127.0.0.1:8765/'"
