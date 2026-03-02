@echo off
setlocal
cd /d %~dp0
echo ======================================================
echo Polymarket Bot V5.3.1 - Launch All
echo ======================================================
start "BOT V5.3.1" cmd /k run_v5.bat
timeout /t 1 >nul
start "UI V5.3.1 HYBRID" cmd /k run_v531_ui.bat
