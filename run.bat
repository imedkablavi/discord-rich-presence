@echo off
setlocal
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.10+ is required and was not found in PATH.
    pause
    exit /b 1
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.10 or newer is required.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 goto :install_error
)

call .venv\Scripts\activate.bat

REM Validate both imports and the pypresence version whose URL/timestamp API we use.
python -c "import importlib.metadata as m; import yaml, customtkinter, pystray, PIL, psutil, win32gui; import winsdk.windows.media.control; assert m.version('pypresence') == '4.6.2'" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Repairing runtime dependencies...
    python -m pip install -r requirements.txt
    if errorlevel 1 goto :install_error
)

echo [INFO] Starting Discord Rich Presence...
start "" /min .venv\Scripts\pythonw.exe main.py --tray
exit /b 0

:install_error
echo [ERROR] Setup failed. Run: .venv\Scripts\python.exe -m pip install -r requirements.txt
pause
exit /b 1
