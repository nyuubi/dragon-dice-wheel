@echo off
echo ===================================================
echo   Setting up environment & Starting Dragon Dice Wheel...
echo ===================================================

:: Check if Python virtual environment exists, if not create it
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

:: Activate environment and install dependencies
call .venv\Scripts\activate.bat
echo Installing dependencies...
pip install -r requirements.txt --quiet

:: Launch server and open browser automatically
echo.
echo Launching game server at http://127.0.0.1:8000 ...
start http://127.0.0.1:8000
python -m uvicorn app:app --reload --port 8000

pause