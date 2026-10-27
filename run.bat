@echo off
title LeadScraper Falcon
echo ===================================================
echo             LeadScraper Falcon Launcher
echo ===================================================
echo.

:: 1. Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your system PATH!
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check the box: "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: 2. Setup Virtual Environment if missing
if not exist "venv" (
    echo [INFO] Setting up your virtual environment for the first time...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [INFO] Installing required dependencies...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

:: 3. Run the Scraper (opens interactive menu)
python main.py

echo.
pause
