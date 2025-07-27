#!/bin/bash

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
source venv/bin/activate

# Install required packages if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "Installing required packages..."
    pip install -r requirements.txt
fi

# Create data directory if it doesn't exist
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
python regenerate_index.py

# Start the Flask server
python app.py
