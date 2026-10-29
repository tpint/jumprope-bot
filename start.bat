@echo off
title Jump-Rope Auto-Jumper
cd /d "%~dp0"

rem Find Python: the "py" launcher comes with the python.org installer
set PY=
py -3 --version >nul 2>&1 && set PY=py -3
if not defined PY (
    python --version >nul 2>&1 && set PY=python
)
if not defined PY (
    echo.
    echo  Python is not installed.
    echo.
    echo  1. Download it from https://www.python.org/downloads/
    echo  2. In the installer, tick "Add python.exe to PATH"
    echo  3. Double-click start.bat again
    echo.
    start "" https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Checking required packages (first time can take a minute)...
%PY% -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
    echo.
    echo  Could not install the packages. Check your internet connection and try again.
    pause
    exit /b 1
)

echo.
%PY% jumprope_bot.py %*
echo.
pause
