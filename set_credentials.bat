@echo off
chcp 65001 >nul
setlocal

echo 管理者ユーザー名とパスワードを設定します。
echo インターネット公開（run_internet.bat）や、LANでの利用でも
echo このユーザー名/パスワードでの認証が必要になります。
echo （入力した文字はそのまま画面に表示されます）
echo.

set /p ADMIN_USER="ユーザー名: "
if "%ADMIN_USER%"=="" (
    echo ユーザー名が空です。中止しました。
    pause
    exit /b 1
)

set /p ADMIN_PASS="パスワード: "
if "%ADMIN_PASS%"=="" (
    echo パスワードが空です。中止しました。
    pause
    exit /b 1
)

setx PARKING_ADMIN_USERNAME "%ADMIN_USER%" >nul
setx PARKING_ADMIN_PASSWORD "%ADMIN_PASS%" >nul

echo.
echo 設定しました。この設定はWindowsのユーザー環境変数に保存されます。
echo 反映するには、開いているコマンドプロンプトを閉じてから
echo run.bat / run_internet.bat を実行し直してください。
pause

