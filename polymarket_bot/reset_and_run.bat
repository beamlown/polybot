@echo off
setlocal
cd /d %~dp0

if exist trades.db (
  del /f /q trades.db
  echo Deleted trades.db ^(fresh paper day^).
) else (
  echo No trades.db found - starting fresh anyway.
)

py -3.14 bot.py
if errorlevel 1 (
  echo Python 3.14 launcher failed, trying generic Python launcher...
  py -3 bot.py
)
pause
