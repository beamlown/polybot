@echo off
setlocal
cd /d %~dp0
echo ======================================================
echo Polymarket Bot V5.4 - Launch All (Hybrid + V4 Monitor)
echo ======================================================
start "BOT V5.4" cmd /k run_v5.bat
timeout /t 1 >nul
start "UI HYBRID V5.3.1" cmd /k run_v531_ui.bat
timeout /t 1 >nul
start "UI V4 Monitor" cmd /k pnl.bat
