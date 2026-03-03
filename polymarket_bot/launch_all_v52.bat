@echo off
setlocal
cd /d %~dp0

echo ======================================================
echo Polymarket Bot V5.2 - Launch All
echo ======================================================
echo Starting bot + live UI in separate windows...

start "BOT V5.2" cmd /k run_v5.bat
timeout /t 1 >nul
start "UI V5.2" cmd /k run_v5_ui.bat

echo Done.
echo If windows did not open, run run_v5.bat and run_v5_ui.bat manually.
