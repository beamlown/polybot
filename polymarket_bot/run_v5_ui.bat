@echo off
setlocal
cd /d %~dp0
py -3.14 ui_v5.py
if errorlevel 1 py -3 ui_v5.py
pause
