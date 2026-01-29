@echo off
setlocal
cd /d "%~dp0"

if not exist "venv" (
    echo Creating venv...
    python -m venv venv
)
call venv\Scripts\activate.bat

echo Installing requirements...
pip install -r requirements.txt -q

echo Starting FastAPI backend on port 8000...
start "Backend" cmd /c "cd /d "%~dp0" && venv\Scripts\activate.bat && set PYTHONPATH=%~dp0 && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak > nul

echo Starting Flask frontend on port 5000...
start "Frontend" cmd /c "cd /d "%~dp0" && venv\Scripts\activate.bat && set PYTHONPATH=%~dp0 && set BACKEND_URL=http://127.0.0.1:8000 && python frontend/app.py"

echo Backend: http://127.0.0.1:8000
echo Frontend: http://127.0.0.1:5000
echo Close the Backend and Frontend windows to stop.
endlocal
