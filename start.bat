@echo off
echo ========================================
echo   RECRUTO - Quick Start Script
echo ========================================
echo.

REM Check if .env file exists
if not exist .env (
    echo WARNING: .env file not found!
    echo Please create .env from .env.template and add your API keys
    pause
    exit /b 1
)

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed
    pause
    exit /b 1
)

echo Installing/Checking requirements...
pip install -r requirements.txt

echo.
echo Starting applications...
echo ========================================
echo.

REM Start CV Parser
echo Starting CV Parser on port 8501...
start "CV Parser" cmd /k streamlit run app1_cv_parser.py --server.port 8501

REM Wait a bit
timeout /t 3 /nobreak >nul

REM Start Job Matcher
echo Starting Job Matcher on port 8502...
start "Job Matcher" cmd /k streamlit run app2_job_matcher.py --server.port 8502

REM Wait a bit
timeout /t 3 /nobreak >nul

REM Start Interview Simulation
echo Starting Interview Simulation on port 8503...
start "Interview Simulation" cmd /k streamlit run app3_interview.py --server.port 8503

echo.
echo ========================================
echo All applications started successfully!
echo ========================================
echo.
echo Access the applications at:
echo   CV Parser:            http://localhost:8501
echo   Job Matcher:          http://localhost:8502
echo   Interview Simulation: http://localhost:8503
echo.
echo Close the command windows to stop the applications
echo.
pause