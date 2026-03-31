@echo off
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
python app.py
pause
