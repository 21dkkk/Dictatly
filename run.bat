@echo off
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Please install requirements.
    pause
    exit /b 1
)
:: Terminate existing background instance if running to load updated code
"%~dp0venv\Scripts\python.exe" "%~dp0scripts\stop_existing.py" >nul 2>&1

start "" "venv\Scripts\pythonw.exe" main.py %*
