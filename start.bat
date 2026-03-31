@echo off
:: Change to the directory where this script lives
cd /d "%~dp0"

echo ============================================
echo  Torque Cell DAQ - Starting Dashboard
echo ============================================
echo.

:: Check venv exists
if not exist venv\Scripts\activate.bat (
    echo ERROR: Virtual environment not found.
    echo Run install.bat first.
    pause
    exit /b 1
)

:: Activate venv and run
call venv\Scripts\activate.bat

:: Start the dashboard on port 8060
python app.py --port 8060
pause
