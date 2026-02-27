@echo off
setlocal
cd /d %~dp0

py -3.14 cashout.py
if errorlevel 1 (
  py -3 cashout.py
)
pause
