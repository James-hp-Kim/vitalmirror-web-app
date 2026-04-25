@echo off
setlocal
set "ROOT=%~dp0.."
set "PYTHON_EXE=C:\Users\USER\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"
set "PORT=8765"
set "HOST=127.0.0.1"
cd /d "%ROOT%"
"%PYTHON_EXE%" server.py
