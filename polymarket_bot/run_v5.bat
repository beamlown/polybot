@echo off
setlocal
cd /d %~dp0

set "V4_FORCE_SLUG="
if not "%~1"=="" set "V4_FORCE_SLUG=btc-updown-5m-%~1"
if not "%~1"=="" echo Using V4_FORCE_SLUG=%V4_FORCE_SLUG%

py -3.14 bot_v5.py
if errorlevel 1 py -3 bot_v5.py
pause
