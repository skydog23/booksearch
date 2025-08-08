# Windows Setup Guide for Book Search

This guide provides detailed instructions for setting up and running the Book Search application on Windows.

## Prerequisites

1. **Python 3.6 or higher**
   - Download from: https://www.python.org/downloads/
   - **IMPORTANT**: During installation, check "Add Python to PATH"
   - Verify installation by opening Command Prompt and typing: `python --version`

2. **Git for Windows** (optional, for cloning)
   - Download from: https://git-scm.com/download/win
   - Or download the repository as a ZIP file from GitHub

## Setup Instructions

1. **Get the Repository**
   ```batch
   git clone [repository-url]
   cd booksearch
   ```
   Or extract the ZIP file and navigate to the folder.

2. **Run Setup**
   ```batch
   setup.bat
   ```
   This will:
   - Create a Python virtual environment
   - Install all dependencies
   - Download PDF.js viewer
   - Set up directories
   - Build the search index

3. **Start the Application**
   ```batch
   start.bat
   ```

4. **Access the Application**
   - Open your web browser
   - Go to: http://localhost:8087

## Adding Your Books

1. Place your PDF files in the `data` folder
2. Restart the application (it will automatically reindex)

## Troubleshooting

### Python Not Found
- Make sure Python is installed and added to PATH
- Try using `py` instead of `python` if the command fails
- Restart Command Prompt after installing Python

### Permission Errors
- Run Command Prompt as Administrator
- Make sure the folder isn't in a restricted location

### PDF.js Download Fails
If the automatic download fails:
1. Download manually from: https://github.com/mozilla/pdf.js/releases/download/v4.0.379/pdfjs-4.0.379-dist.zip
2. Create folder: `static\pdfjs`
3. Extract the ZIP contents into `static\pdfjs`

### Port Already in Use
- The start.bat script automatically kills processes on port 8087
- If issues persist, restart your computer or use a different port

### Virtual Environment Issues
- Delete the `venv` folder and run `setup.bat` again
- Make sure you have sufficient disk space

## Manual Setup (If Batch Files Don't Work)

```batch
:: Create virtual environment
python -m venv venv

:: Activate virtual environment
venv\Scripts\activate

:: Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

:: Create data directory
mkdir data

:: Set up PDF.js (manual download required)
mkdir static\pdfjs
:: Download and extract PDF.js to static\pdfjs

:: Generate index
python regenerate_index.py

:: Start server
python app.py
```

## Stopping the Application

- Press `Ctrl+C` in the Command Prompt window
- Or close the Command Prompt window

## Updating

To update to a newer version:
1. Download/pull the latest code
2. Run `setup.bat` again (it will update dependencies)

## Support

If you encounter issues:
1. Check that Python is properly installed and in PATH
2. Make sure you're running Command Prompt from the booksearch folder
3. Try running the manual setup steps
4. Check the Windows Event Viewer for detailed error messages 