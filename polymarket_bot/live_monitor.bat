@echo off
setlocal
cd /d %~dp0

:loop
cls
echo Polymarket Paper Bot Monitor (refresh every 10s)
echo Press Ctrl+C to stop.
echo ----------------------------------------
py -3.14 status.py
if errorlevel 1 (
  py -3 status.py
)
timeout /t 10 >nul
goto loop
