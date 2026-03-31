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

:: Try default port first, fall back to 8060 if blocked
python app.py --port 8050
if errorlevel 1 (
    echo.
    echo Port 8050 blocked. Trying port 8060...
    echo.
    python app.py --port 8060
)
pause
