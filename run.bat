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

REM Only install when runtime imports are unavailable. This avoids a network/pip
REM operation on every normal launch while still self-healing incomplete environments.
python -c "import pypresence, yaml, customtkinter, pystray, PIL" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing runtime dependencies...
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
