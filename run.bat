@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"

REM --- Check Python ---
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from python.org
    pause
    exit /b 1
)

REM --- Virtual Environment Setup ---
if not exist ".venv" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
)

REM --- Activate Venv ---
call .venv\Scripts\activate.bat

REM --- Dependencies ---
echo [INFO] Checking dependencies...
pip install -r requirements.txt >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Failed to install some dependencies. Trying to proceed...
)

REM --- Run Application ---
echo [INFO] Starting Discord Rich Presence Manager...
echo [INFO] The application will run in the background if configured.
echo [INFO] Check the system tray icon to open settings.

REM Run in background (start w/o console window if possible in future exe, here we minimize)
start /min pythonw main.py --tray

exit
