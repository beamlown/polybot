@echo off
setlocal
cd /d %~dp0

if exist trades.db del /f /q trades.db
echo Fresh start ready.

set "SLUG_SUFFIX=%~1"
if "%SLUG_SUFFIX%"=="" goto no_slug
set "FORCE_MARKET_SLUG_CONTAINS=btc-updown-5m-%SLUG_SUFFIX%"
set "FORCE_EVENT_SLUG=btc-updown-5m-%SLUG_SUFFIX%"
set "USE_FILTER_ONLY=false"
set "AUTO_SLUG_FROM_URL=false"
set "AUTO_FORCE_SLUG_STEP=false"
set "STEP_ON_MISS=false"
echo Using runtime slug: btc-updown-5m-%SLUG_SUFFIX% (manual deterministic mode)
:no_slug
set "ENABLE_SLUG_PROMPT=false"

py -3.14 bot.py
if errorlevel 1 py -3 bot.py
pause
