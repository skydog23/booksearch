from app import init_index, index_pdf, clean_index
from pathlib import Path
import os
import time

def get_latest_pdf_time(data_dir):
    """Get the most recent modification time of any PDF in the directory"""
    latest_time = 0
    pdf_files = list(data_dir.glob('*.pdf'))
    for pdf in pdf_files:
        mod_time = pdf.stat().st_mtime
        if mod_time > latest_time:
            latest_time = mod_time
    return latest_time, len(pdf_files)

def get_latest_index_time(index_dir):
    """Get the most recent modification time of any index file"""
    if not index_dir.exists():
        return 0
    
    latest_time = 0
    for file in index_dir.glob('*'):
        if file.name == 'MAIN_WRITELOCK':  # Skip lock file
            continue
        mod_time = file.stat().st_mtime
        if mod_time > latest_time:
            latest_time = mod_time
    return latest_time

def main():
    # Setup directories
    data_dir = Path('data')
    index_dir = Path('index')
    
    # Get timestamps
    latest_pdf_time, pdf_count = get_latest_pdf_time(data_dir)
    latest_index_time = get_latest_index_time(index_dir)
    
    # Initialize index if needed
    ix = init_index()
    
    # Clean up old entries (always do this as it's fast)
    removed_files = clean_index(data_dir)
    if removed_files:
        print(f"Removed {len(removed_files)} deleted book(s) from index")
    
    # Check if we need to regenerate
    if latest_pdf_time > latest_index_time:
        print(f"Found {pdf_count} PDF files, some newer than index. Regenerating...")
        pdf_files = list(data_dir.glob('*.pdf'))
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"Indexing {i}/{pdf_count}: {pdf_file.name}")
            index_pdf(pdf_file)
        print("Index regeneration complete")
    else:
        print(f"Index is up to date ({pdf_count} PDFs indexed)")

if __name__ == '__main__':
    main()
