@echo off
echo ============================================
echo  Torque Cell DAQ - Windows Setup
echo ============================================
echo.

:: Check Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Download from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

:: Create virtual environment
echo Creating virtual environment...
python -m venv venv
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
