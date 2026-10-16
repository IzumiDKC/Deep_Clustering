@echo off
cd /d "%~dp0"
set PYTHONDONTWRITEBYTECODE=1
if not exist ".venv\Scripts\python.exe" (
  py -3 --version >nul 2>&1
  if not errorlevel 1 (
    py -3 -m venv .venv
  ) else (
    python -m venv .venv
  )
)
if not exist ".venv\Scripts\python.exe" (
  echo Could not create .venv. Install Python with the Python launcher.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Could not install dependencies. Check network and Python environment.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" checks\check_gradients.py
if errorlevel 1 (
  echo Gradient checks failed. Read the error above.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" run_demo.py --seeds 0 1 2 3 4 --output "results\windows_%RANDOM%"
if errorlevel 1 (
  echo Demo failed. Read the error above.
  pause
  exit /b 1
)
echo Finished. See the results\windows folder printed above.
pause
