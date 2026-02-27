@echo off
setlocal
cd /d %~dp0

py -3.14 status.py
if errorlevel 1 (
  py -3 status.py
)
pause
