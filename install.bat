@echo off
:: Change to the directory where this script lives
cd /d "%~dp0"

echo ============================================
echo  Torque Cell DAQ - Windows Setup
echo ============================================
echo.

:: Find Python - try "python" first, then "py" (Windows Launcher)
set PYTHON_CMD=
python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python
) else (
    py --version >nul 2>&1
    if not errorlevel 1 (
        set PYTHON_CMD=py
    )
)

if "%PYTHON_CMD%"=="" (
    echo ERROR: Python is not installed or not in PATH.
    echo Download from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

echo Found Python: %PYTHON_CMD%
%PYTHON_CMD% --version

:: Create virtual environment
echo Creating virtual environment...
%PYTHON_CMD% -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment.
    pause
    exit /b 1
)

:: Activate and install dependencies
echo Installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

:: Create data directories
if not exist data mkdir data
if not exist calibration_files mkdir calibration_files

echo.
echo ============================================
echo  Setup complete!
echo.
echo  Next steps:
echo    1. Install NI-DAQmx driver from ni.com
echo    2. Plug in NI USB-6002
echo    3. Run start.bat to launch the dashboard
echo ============================================
pause
