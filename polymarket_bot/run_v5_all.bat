@echo off
setlocal
cd /d %~dp0
start "BOT V5" cmd /k run_v5.bat
timeout /t 1 >nul
start "UI V5" cmd /k run_v5_ui.bat
