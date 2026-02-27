@echo off
setlocal
cd /d %~dp0

py -3.14 status.py | findstr /R /C:"^Total" /C:"^Portfolio" /C:"^POSITIONS" /C:"^[0-9][0-9][0-9]"
if errorlevel 1 (
  py -3 status.py | findstr /R /C:"^Total" /C:"^Portfolio" /C:"^POSITIONS" /C:"^[0-9][0-9][0-9]"
)
pause
