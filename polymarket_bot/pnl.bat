@echo off
setlocal
cd /d %~dp0

:loop
cls
echo ================================================================
echo POLYMARKET V4 PNL MONITOR
echo Refresh: every 2s ^| Ctrl+C to stop
echo ================================================================
echo.

py -3.14 pnl_v4.py
if errorlevel 1 py -3 pnl_v4.py

echo.
timeout /t 2 >nul
goto loop
