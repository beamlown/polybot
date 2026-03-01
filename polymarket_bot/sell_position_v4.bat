@echo off
setlocal
cd /d %~dp0

echo Sell latest open V4 paper position...
if not "%~1"=="" (
  py -3.14 sell_position_v4.py %~1
  if errorlevel 1 py -3 sell_position_v4.py %~1
) else (
  py -3.14 sell_position_v4.py
  if errorlevel 1 py -3 sell_position_v4.py
)
pause
