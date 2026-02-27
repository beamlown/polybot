@echo off
setlocal
cd /d %~dp0

echo [1/3] Installing requirements...
py -3.14 -m pip install -r requirements.txt
if errorlevel 1 (
  echo Python 3.14 launcher failed, trying generic Python launcher...
  py -3 -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Failed to install requirements.
    pause
    exit /b 1
  )
)

echo [2/3] Ensuring .env exists...
if not exist .env (
  copy /Y .env.example .env >nul
  echo Created .env from .env.example
) else (
  echo .env already exists
)

echo [3/3] Setup complete.
echo You can now run start_bot.bat (or reset_and_run.bat for a fresh day).
pause
