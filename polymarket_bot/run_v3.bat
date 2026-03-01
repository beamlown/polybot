@echo off
setlocal
cd /d %~dp0

echo Starting Bot V3...
py -3.14 bot_v3.py
if errorlevel 1 py -3 bot_v3.py
pause
