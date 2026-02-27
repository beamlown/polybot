@echo off
setlocal
cd /d %~dp0

echo Starting Polymarket paper bot...
py -3.14 bot.py
if errorlevel 1 (
  echo Python 3.14 launcher failed, trying generic Python launcher...
  py -3 bot.py
)
pause
