@echo off
echo シフト作成ツール - 公開サーバー起動
echo.
echo 1. Flaskサーバーを起動しています...
start "Flask Server" cmd /k python app.py
timeout /t 3 /nobreak > nul

echo 2. ngrokで公開URLを作成しています...
echo    ngrokがインストールされていない場合は、以下のコマンドを実行してください：
echo    winget install ngrok
echo.

ngrok http 5000

pause
