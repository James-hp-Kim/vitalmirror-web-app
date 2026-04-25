@echo off
setlocal
set "ROOT=%~dp0.."
set "PYTHON_EXE=C:\Users\USER\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"
powershell -NoExit -NoProfile -ExecutionPolicy Bypass -Command "$env:PORT='8765'; $env:HOST='127.0.0.1'; Set-Location '%ROOT%'; & '%PYTHON_EXE%' server.py"
