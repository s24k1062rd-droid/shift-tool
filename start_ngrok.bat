@echo off
REM ngrokを使用してシフト作成ツールを外部アクセス可能にする
REM
REM 使い方:
REM 1. このファイルをダブルクリック
REM 2. 表示されるURLをスマホなどで開く
REM 3. 終了する場合は Ctrl+C を押す

echo.
echo ============================================================
echo   シフト作成ツール - 外部アクセス起動（ngrok版）
echo ============================================================
echo.

.venv\Scripts\python.exe start_ngrok.py

pause
