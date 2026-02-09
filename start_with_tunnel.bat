@echo off
REM Cloudflare Tunnel + Flask スタートスクリプト
REM 
REM 使い方:
REM 1. このスクリプトをダブルクリック
REM 2. Cloudflareがログインページを表示したら、ブラウザで承認
REM 3. ターミナルに公開URL表示（例: https://shift-tool-xxxxx.trycloudflare.com）
REM 4. その URL をスマホなど外部デバイスで開く

echo.
echo ==================================================
echo   Cloudflare Tunnel + Flask シフト作成ツール
echo ==================================================
echo.
echo Flask サーバーを起動しています...
echo.

REM Cloudflareがインストールされているかチェック
where cloudflared >nul 2>&1
if errorlevel 1 (
    echo [エラー] cloudflared がインストールされていません
    echo.
    echo Cloudflareのセットアップページを開きます...
    echo https://developers.cloudflare.com/cloudflare-one/connections/connect-applications/install-and-setup/installation/
    start https://developers.cloudflare.com/cloudflare-one/connections/connect-applications/install-and-setup/installation/
    echo.
    echo インストール後、このスクリプトを再度実行してください。
    pause
    exit /b 1
)

REM Flaskサーバーをバックグラウンドで起動
start "Flask Server" cmd /k "cd /d "%cd%" && .venv\Scripts\python app.py"

REM 3秒待機（Flaskの起動を待つ）
timeout /t 3 /nobreak

REM Cloudflare Tunnel を起動（トンネル URL を自動表示）
echo.
echo Cloudflare Tunnel を接続中...
echo.
cloudflared tunnel --url http://localhost:5000

pause
