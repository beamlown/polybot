@echo off
setlocal
cd /d %~dp0

if exist trades_v2.db del /f /q trades_v2.db
echo Starting Bot V2...
py -3.14 bot_v2.py
if errorlevel 1 py -3 bot_v2.py
pause
