@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python is not installed. Please install Python 3 from https://www.python.org/downloads/
  pause
  exit /b 1
)

start "No-Code Android Builder" pythonw nocode_android_builder.py --gui
exit /b 0
