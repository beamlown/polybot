@echo off
setlocal enabledelayedexpansion
cd /d %~dp0

echo ======================================================
echo POLYMARKET BOT HARD RESET (v5.3.x)
echo ======================================================
echo.
echo [1/6] Stopping running bot/ui python processes...
taskkill /F /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq BOT V5*" >nul 2>nul
taskkill /F /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq UI V5*" >nul 2>nul
taskkill /F /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq BOT V5.3*" >nul 2>nul
taskkill /F /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq UI V5.3*" >nul 2>nul
taskkill /F /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq UI V5.3.1*" >nul 2>nul

echo [2/6] Fallback kill all python.exe (if still running)...
taskkill /F /IM python.exe >nul 2>nul

echo [3/6] Backing up DB...
if not exist backups mkdir backups
set TS=%DATE:~10,4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%
set TS=%TS: =0%
if exist trades_v4.db copy /Y trades_v4.db backups\trades_v4_pre_reset_%TS%.db >nul

echo [4/6] Clearing runtime state/cache files...
if exist runtime\state_v5.json del /F /Q runtime\state_v5.json >nul 2>nul
if exist runtime\state_v5.json.tmp del /F /Q runtime\state_v5.json.tmp >nul 2>nul
if exist __pycache__ rmdir /S /Q __pycache__ >nul 2>nul

echo [5/6] Optional clean trade reset...
set /p RESETDB=Type YES to delete all trade rows from trades_v4.db (or press Enter to keep): 
if /I "%RESETDB%"=="YES" (
  py -3.14 -c "import sqlite3; c=sqlite3.connect('trades_v4.db'); c.execute('DELETE FROM trades'); c.commit(); c.close(); print('trades cleared')" 2>nul
  if errorlevel 1 py -3 -c "import sqlite3; c=sqlite3.connect('trades_v4.db'); c.execute('DELETE FROM trades'); c.commit(); c.close(); print('trades cleared')"
)

echo [6/6] Relaunching bot + hybrid UI...
start "BOT V5.3.2" cmd /k run_v5.bat
timeout /t 1 >nul
start "UI V5.3.1 HYBRID" cmd /k run_v531_ui.bat

echo.
echo HARD RESET COMPLETE.
echo DB backup (if created) is in .\backups
echo.
pause
