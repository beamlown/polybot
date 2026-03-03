@echo off
setlocal
cd /d %~dp0

:loop
cls
echo ===============================================================
echo POLYMARKET BOT V3 - LIVE MONITOR
echo Refresh: every 5s ^| Ctrl+C to stop
echo ===============================================================
echo.

py -3.14 monitor_v3.py
if errorlevel 1 py -3 monitor_v3.py

echo.
timeout /t 5 >nul
goto loop
