@echo off
setlocal enabledelayedexpansion

echo Book Search Setup for Windows
echo ================================

:: Check if Python 3 is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python 3 is required but not installed. Please install Python 3 and try again.
    echo Download from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

:: requirements.txt pins Flask 3.1 and Pillow 11, which need Python 3.9 or newer
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
if errorlevel 1 (
    echo Python 3.9 or newer is required.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Display Python version
echo Python version:
python --version

:: Create and activate virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate
if errorlevel 1 (
    echo Failed to activate virtual environment.
    pause
    exit /b 1
)

:: Verify we're using the correct Python
echo Using Python from: 
where python
echo Python version: 
python --version

:: Upgrade pip to latest version
echo Upgrading pip...
python -m pip install --upgrade pip

:: Install required packages if requirements.txt exists
if exist "requirements.txt" (
    echo Installing required packages...
    pip install -r requirements.txt -v
    if errorlevel 1 (
        echo Failed to install required packages.
        pause
        exit /b 1
    )
    echo Package installation complete.
) else (
    echo requirements.txt not found!
    pause
    exit /b 1
)

:: Verify Flask installation
echo Verifying Flask installation...
python -c "import flask; print('Flask version: ' + flask.__version__)" >nul 2>&1
if errorlevel 1 (
    echo Flask import failed. Trying to install Flask directly...
    pip install flask
    python -c "import flask; print('Flask version: ' + flask.__version__)" >nul 2>&1
    if errorlevel 1 (
        echo Flask installation failed. Please try installing manually:
        echo venv\Scripts\activate
        echo pip install flask
        pause
        exit /b 1
    )
)

:: Show installed packages
echo Installed packages:
pip list

:: Create data directory if it doesn't exist
echo Setting up directories...
if not exist "data" mkdir data

:: Download and setup PDF.js if not already present.
:: Version 3.11.174 is the one the viewer integration in templates\index.html
:: has been run against; 4.x ships ES modules (.mjs) and has not been tried.
set PDFJS_VERSION=3.11.174
set PDFJS_URL=https://github.com/mozilla/pdf.js/releases/download/v%PDFJS_VERSION%/pdfjs-%PDFJS_VERSION%-dist.zip

:: Test for the viewer itself, not just the folder, so a failed download is retried
if exist "static\pdfjs\web\viewer.html" goto pdfjs_done

echo Setting up PDF.js %PDFJS_VERSION%...
if not exist "static\pdfjs" mkdir static\pdfjs

:: Check if curl is available (Windows 10 version 1803+)
curl --version >nul 2>&1
if not errorlevel 1 (
    echo Downloading PDF.js using curl...
    curl -L %PDFJS_URL% -o pdfjs.zip
    if errorlevel 1 goto manual_pdfjs
) else (
    echo Downloading PDF.js using PowerShell...
    powershell -Command "Invoke-WebRequest -Uri '%PDFJS_URL%' -OutFile 'pdfjs.zip'"
    if errorlevel 1 goto manual_pdfjs
)

:: Extract PDF.js
echo Extracting PDF.js...
powershell -Command "Expand-Archive -Path 'pdfjs.zip' -DestinationPath 'static\pdfjs' -Force"
if errorlevel 1 goto manual_pdfjs

del pdfjs.zip
echo PDF.js setup complete
goto pdfjs_done

:manual_pdfjs
echo.
echo MANUAL SETUP REQUIRED:
echo 1. Download pdfjs-%PDFJS_VERSION%-dist.zip from:
echo    %PDFJS_URL%
echo 2. Extract the contents to the static\pdfjs directory
echo 3. Press any key when done...
pause

:pdfjs_done

:: Run the index regeneration script
echo Running index regeneration...
python regenerate_index.py
if errorlevel 1 (
    echo Failed to regenerate index.
    pause
    exit /b 1
)

:: Success message
echo.
echo Setup complete! To start the server, run: start.bat
echo Or manually run: python app.py
echo.
echo The application will be available at: http://localhost:8087
echo.
pause 