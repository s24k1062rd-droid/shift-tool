@echo off
REM localhost.runを使用してシフト作成ツールを外部アクセス可能にする
REM 認証不要・即座に使用可能

echo.
echo ============================================================
echo   シフト作成ツール - 外部アクセス起動
echo   （localhost.run使用・認証不要）
echo ============================================================
echo.

.venv\Scripts\python.exe start_localhostrun.py

pause
