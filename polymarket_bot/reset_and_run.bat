@echo off
setlocal
cd /d %~dp0

if exist trades.db (
  del /f /q trades.db
  echo Deleted trades.db ^(fresh paper day^).
) else (
  echo No trades.db found - starting fresh anyway.
)

set /p SLUG_SUFFIX=Enter current slug suffix (example: 1772230800) or press Enter to keep defaults: 
if not "%SLUG_SUFFIX%"=="" (
  set "FORCE_MARKET_SLUG_CONTAINS=btc-updown-15m-%SLUG_SUFFIX%"
  set "FORCE_EVENT_SLUG=btc-updown-15m-%SLUG_SUFFIX%"
  echo Using runtime slug: btc-updown-15m-%SLUG_SUFFIX%
)
set "ENABLE_SLUG_PROMPT=false"

py -3.14 bot.py
if errorlevel 1 (
  echo Python 3.14 launcher failed, trying generic Python launcher...
  py -3 bot.py
)
pause
