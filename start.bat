@echo off
setlocal

echo Starting Book Search Application...
echo ==================================

:: Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found. Please run setup.bat first.
    pause
    exit /b 1
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate
if errorlevel 1 (
    echo Failed to activate virtual environment.
    pause
    exit /b 1
)

:: Kill any existing process on port 8087
echo Checking for existing processes on port 8087...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8087') do (
    set pid=%%a
    if defined pid (
        echo Killing existing process !pid! on port 8087...
        taskkill /F /PID !pid! >nul 2>&1
    )
)

:: Start the Flask server
echo Starting Flask server on http://localhost:8087...
echo Press Ctrl+C to stop the server
echo.
python app.py 