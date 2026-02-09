@echo off
REM シンプル起動スクリプト
REM Cloudflare Tunnel と Flask を同時起動

setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo ==================================================
echo    シフト作成ツール - 外部アクセス起動
echo ==================================================
echo.

REM Cloudflareがインストールされているかチェック
where cloudflared >nul 2>&1
if errorlevel 1 (
    echo [必須] cloudflared がインストールされていません
    echo.
    echo 以下からダウンロードしてインストール:
    echo https://developers.cloudflare.com/cloudflare-one/connections/connect-applications/install-and-setup/installation/
    echo.
    echo ※ Windows 版: cloudflared-windows-amd64.msi を実行
    echo.
    pause
    exit /b 1
)

echo ✓ Cloudflare Tunnel を起動しています...
echo.
echo Flask サーバーを起動した後、自動的にトンネルが接続されます
echo.
echo ターミナルに表示される URL をコピーして、
echo スマホなど外部デバイスのブラウザで開いてください
echo.
echo 例: https://shift-tool-xxxxx.trycloudflare.com
echo.
echo ==================================================
echo.

REM Flask を起動
python -u app.py

pause
