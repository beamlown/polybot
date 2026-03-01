@echo off
setlocal
cd /d %~dp0

py -3.14 dashboard_v4.py
if errorlevel 1 py -3 dashboard_v4.py
pause
