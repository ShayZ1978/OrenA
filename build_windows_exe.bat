@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python is not installed. Please install Python 3 first.
  pause
  exit /b 1
)

python -m pip install --upgrade pip pyinstaller
if errorlevel 1 (
  echo Failed to install PyInstaller.
  pause
  exit /b 1
)

python -m PyInstaller --noconfirm --onefile --windowed --name NoCodeAndroidBuilder nocode_android_builder.py
if errorlevel 1 (
  echo EXE build failed.
  pause
  exit /b 1
)

echo.
echo Build finished.
echo Your Windows app is here: dist\NoCodeAndroidBuilder.exe
pause
