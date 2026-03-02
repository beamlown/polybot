@echo off
setlocal enabledelayedexpansion
cd /d %~dp0

if not exist backups mkdir backups
set TS=%DATE:~10,4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%
set TS=%TS: =0%

echo Choose profile:
echo   1) aggressive
echo   2) neutral
echo   3) conservative
set /p C=Enter 1/2/3: 

if "%C%"=="1" set P=aggressive
if "%C%"=="2" set P=neutral
if "%C%"=="3" set P=conservative
if "%P%"=="" (
  echo Invalid choice.
  exit /b 1
)

if exist .env copy /Y .env backups\env_%TS%.env >nul
copy /Y profiles\%P%.env .env >nul
echo Applied profile: %P%
echo Restart bot for changes to take effect.
