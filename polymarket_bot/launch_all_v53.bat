@echo off
setlocal
cd /d %~dp0
echo ======================================================
echo Polymarket Bot V5.3 - Launch All
echo ======================================================
start "BOT V5.3" cmd /k run_v5.bat
timeout /t 1 >nul
start "UI V5.3" cmd /k run_v5_ui.bat
