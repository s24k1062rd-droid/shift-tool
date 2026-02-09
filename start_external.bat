@echo off
REM 外部アクセス版シフト作成ツール起動スクリプト
REM ngrok authtoken設定済みの場合、自動的に外部アクセスURLを生成

echo.
echo ============================================================
echo   シフト作成ツール - 外部アクセス版
echo ============================================================
echo.

.venv\Scripts\python.exe app_external.py

pause
