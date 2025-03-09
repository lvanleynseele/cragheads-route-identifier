@echo off
echo Starting Image Processing Service...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed. Please install Python and try again.
    exit /b 1
)

REM Check if virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo Installing dependencies...
pip install -r requirements.txt

REM Verify critical dependencies
echo Verifying dependencies...
python -c "import fastapi; import uvicorn; import psutil; import cv2; import numpy; import PIL" || (
    echo Failed to verify dependencies. Please check the installation.
    exit /b 1
)

REM Create necessary directories
echo Setting up directories...
if not exist logs mkdir logs

REM Start the service
echo Starting service on port 3020...
uvicorn main:app --host 0.0.0.0 --port 3020 --reload --log-level info 