@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [run.bat] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [run.bat] Failed to create virtual environment. Please make sure Python is installed.
        pause
        exit /b 1
    )
)

if not exist ".venv\installed.flag" (
    echo [run.bat] Installing dependencies - first run only, this may take a few minutes...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [run.bat] Failed to install dependencies.
        pause
        exit /b 1
    )
    echo installed > ".venv\installed.flag"
) else (
    echo [run.bat] Dependencies already installed, skipping install.
)

echo.
echo [run.bat] Starting server.
echo   From this PC          : http://127.0.0.1:8000
echo   From a phone on Wi-Fi : http://THIS-PC-IP-ADDRESS:8000
echo   Press Ctrl+C to stop.
echo.

".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000

pause
