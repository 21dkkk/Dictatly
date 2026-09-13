@echo off
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo Please install dependencies first:
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

if exist "%~dp0Dictatly.exe" (
    start "" "%~dp0Dictatly.exe" %*
) else (
    start "" "venv\Scripts\pythonw.exe" main.py %*
)

