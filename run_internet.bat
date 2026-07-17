@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [run_internet.bat] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [run_internet.bat] Failed to create virtual environment. Please make sure Python is installed.
        pause
        exit /b 1
    )
)

if not exist ".venv\installed.flag" (
    echo [run_internet.bat] Installing dependencies - first run only, this may take a few minutes...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [run_internet.bat] Failed to install dependencies.
        pause
        exit /b 1
    )
    echo installed > ".venv\installed.flag"
)

".venv\Scripts\python.exe" scripts\check_credentials.py internet
if errorlevel 1 (
    pause
    exit /b 1
)

where cloudflared >nul 2>nul
if errorlevel 1 (
    echo.
    echo [run_internet.bat] cloudflared.exe が見つかりません。
    echo   以下のいずれかでインストールしてください。
    echo     winget install --id Cloudflare.cloudflared
    echo   または https://github.com/cloudflare/cloudflared/releases から
    echo   cloudflared.exe をダウンロードし、このフォルダか PATH の通った
    echo   場所に置いてください。
    echo.
    pause
    exit /b 1
)

echo.
echo [run_internet.bat] サーバーをこのPCだけからアクセス可能な状態
echo   （127.0.0.1）で起動し、別ウィンドウで Cloudflare Tunnel を起動します。
echo   数秒後、別ウィンドウに https://xxxxx.trycloudflare.com のような
echo   URLが表示されます。それがインターネットからのアクセス先です。
echo   （毎回ランダムなURLが発行されます。固定URLが必要な場合は README の
echo    「固定ドメインでの公開」を参照してください）
echo.
echo   アクセス時はユーザー名/パスワードの入力が求められます。
echo   Ctrl+C でこのウィンドウを閉じるとサーバーが停止します。
echo   （Cloudflare Tunnel側のウィンドウも手動で閉じてください）
echo.

start "Parking Counter - Cloudflare Tunnel" cloudflared tunnel --url http://127.0.0.1:8000

".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause

