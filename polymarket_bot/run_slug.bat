@echo off
setlocal
cd /d %~dp0

if "%~1"=="" (
  echo Usage: run_slug.bat 1772233200
  pause
  exit /b 1
)

set "SLUG_SUFFIX=%~1"
set "FORCE_MARKET_SLUG_CONTAINS=btc-updown-5m-%SLUG_SUFFIX%"
set "FORCE_EVENT_SLUG=btc-updown-5m-%SLUG_SUFFIX%"
set "ENABLE_SLUG_PROMPT=false"
echo Using runtime slug: btc-updown-5m-%SLUG_SUFFIX%

if exist trades.db del /f /q trades.db

py -3.14 bot.py
if errorlevel 1 py -3 bot.py
pause
