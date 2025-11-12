#!/usr/bin/env python3
"""
Completely rebuild the search index from scratch.
Use this when the schema has changed or the index is corrupted.

IMPORTANT: Run this script with the virtual environment activated:
  - Linux/Mac: source venv/bin/activate
  - Windows: venv\\Scripts\\activate

Or run directly with:
  - venv/bin/python rebuild_index.py  (Linux/Mac)
  - venv\\Scripts\\python rebuild_index.py  (Windows)
"""

from pathlib import Path
import shutil
import os
import sys

def check_dependencies():
    """Check if required dependencies are available"""
    try:
        import flask
        import whoosh
        import pdfplumber
        return True
    except ImportError as e:
        print("ERROR: Required dependencies not found!")
        print(f"Missing module: {e.name}")
        print()
        print("Please activate the virtual environment first:")
        print()
        if sys.platform == "win32":
            print("  Windows:")
            print("    venv\\Scripts\\activate")
            print("  or run:")
            print("    venv\\Scripts\\python rebuild_index.py")
        else:
            print("  Linux/Mac:")
            print("    source venv/bin/activate")
            print("  or run:")
            print("    venv/bin/python rebuild_index.py")
        print()
        return False

def rebuild_index():
    """Delete and rebuild the entire search index"""
    # Import here to avoid issues if schema is invalid
    from app import index_pdf
    from whoosh.index import create_in
    from app import schema
    
    data_dir = Path('data')
    index_dir = Path('index')
    
    # Remove old index
    if index_dir.exists():
        print(f"Removing old index directory: {index_dir}")
        shutil.rmtree(index_dir)
    
    # Create fresh index directory
    print(f"Creating new index directory: {index_dir}")
    index_dir.mkdir(exist_ok=True)
    
    # Create new index with current schema
    print("Creating new index with updated schema...")
    ix = create_in(str(index_dir), schema)
    
    # Index all PDFs
    pdf_files = sorted(data_dir.glob('*.pdf'))
    total = len(pdf_files)
    
    if total == 0:
        print("No PDF files found in data directory!")
        return
    
    print(f"\nIndexing {total} PDF files...")
    print("-" * 60)
    
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"[{i:3d}/{total}] {pdf_file.name}")
        try:
            index_pdf(pdf_file)
        except Exception as e:
            print(f"  ERROR: {e}")
    
    print("-" * 60)
    print(f"\n✓ Index rebuild complete! Indexed {total} PDF files.")
    print("\nYou can now start the application and test the case-sensitive search.")
    print("Example: +Fest will match 'Fest' but not 'fest'")

if __name__ == '__main__':
    print("=" * 60)
    print("REBUILD SEARCH INDEX")
    print("=" * 60)
    print()
    
    # Check dependencies first
    if not check_dependencies():
        sys.exit(1)
    
    print("This will delete the current index and rebuild it from scratch.")
    print("This is necessary after changing the index schema.\n")
    
    response = input("Continue? (y/n): ")
    if response.lower() == 'y':
        rebuild_index()
    else:
        print("Cancelled.")

