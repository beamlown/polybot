@echo off
setlocal
cd /d %~dp0

echo This will DELETE trades_v4.db and reset PnL history.
set /p CONFIRM=Type RESET to continue: 
if /I not "%CONFIRM%"=="RESET" (
  echo Cancelled.
  pause
  exit /b 1
)

if exist trades_v4.db del /f /q trades_v4.db
echo trades_v4.db removed. Fresh history on next bot run.
pause
