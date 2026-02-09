@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Flaskをインストール中...
.venv\Scripts\pip.exe install -r requirements.txt -q
echo.
echo サーバーを起動しています...
echo ブラウザで http://localhost:5000 を開いてください
echo またはスマホで http://(あなたのPCのIPアドレス):5000 を開いてください
echo.
.venv\Scripts\python.exe app.py
pause
