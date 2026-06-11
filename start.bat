@echo off
echo.
echo ============================================
echo   SnapAI - AI Event Photo Delivery Platform
echo ============================================
echo.

cd backend

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Installing dependencies (dlib may take several minutes)...
pip install -q --upgrade pip
pip install -r requirements.txt

echo.
echo Starting SnapAI server...
echo.
echo   Landing page:  http://localhost:5000
echo   Dashboard:     http://localhost:5000/dashboard
echo   Login:         http://localhost:5000/login
echo.
echo Press Ctrl+C to stop.
echo.

python app.py
pause
