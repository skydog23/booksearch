#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Create data directory if it doesn't exist
mkdir -p data

# Create a temporary Python script to regenerate index
cat > regenerate_index.py << 'EOL'
from app import init_index, index_pdf, clean_index
from pathlib import Path

# Initialize index
ix = init_index()

# Clean up old entries
data_dir = Path('data')
removed_files = clean_index(data_dir)
if removed_files:
    print(f"Removed {len(removed_files)} deleted book(s) from index")

# Index all PDFs
pdf_files = list(data_dir.glob('*.pdf'))
print(f"Found {len(pdf_files)} PDF files")

for i, pdf_file in enumerate(pdf_files, 1):
    print(f"Indexing {i}/{len(pdf_files)}: {pdf_file.name}")
    index_pdf(pdf_file)

print("Index regeneration complete")
EOL

# Run the index regeneration script
python regenerate_index.py

# Remove the temporary script
rm regenerate_index.py

# Start the Flask server
python app.py
