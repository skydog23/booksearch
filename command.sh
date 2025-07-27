#!/bin/bash

# Exit on error
set -e

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed. Please install Python 3 and try again."
    exit 1
fi

# Create and activate virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment. Please install python3-venv package and try again."
        echo "On Ubuntu/Debian: sudo apt-get install python3-venv"
        echo "On macOS: brew install python3"
        exit 1
    fi
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "Failed to activate virtual environment."
    exit 1
fi

# Upgrade pip to latest version
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install required packages if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "Installing required packages..."
    pip install -r requirements.txt -v  # Added verbose flag
    if [ $? -ne 0 ]; then
        echo "Failed to install required packages."
        exit 1
    fi
    echo "Package installation complete."
else
    echo "requirements.txt not found!"
    exit 1
fi

# Create data directory if it doesn't exist
echo "Setting up directories..."
mkdir -p data

# Download and setup PDF.js if not already present
if [ ! -d "static/pdfjs" ]; then
    echo "Setting up PDF.js..."
    mkdir -p static/pdfjs
    # Get the latest stable version of PDF.js
    curl -L https://github.com/mozilla/pdf.js/releases/download/v4.0.379/pdfjs-4.0.379-dist.zip -o pdfjs.zip
    unzip pdfjs.zip -d static/pdfjs/
    rm pdfjs.zip
    echo "PDF.js setup complete"
fi

# Run the index regeneration script (now with timestamp checking)
echo "Running index regeneration..."
python regenerate_index.py
if [ $? -ne 0 ]; then
    echo "Failed to regenerate index."
    exit 1
fi

# Start the Flask server
echo "Starting Flask server..."
python app.py
