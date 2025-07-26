#!/bin/bash

# Activate virtual environment
source venv/bin/activate

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
