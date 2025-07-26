# Book Search

A web application for searching and viewing PDF books. Features include:

- Full-text search across multiple PDF books
- Results grouped by book with page numbers
- Built-in PDF viewer with advanced features:
  - Page navigation
  - Zoom and rotate controls
  - Text search within PDFs
  - Thumbnail view
  - Document outline

## Setup

1. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Place PDF books in the `data` directory

3. Run the setup and start script:
```bash
./command.sh
```

This script will:
- Set up the virtual environment
- Download and install PDF.js viewer
- Create necessary directories
- Build the search index from your PDF files
- Start the Flask server

The application will be available at http://localhost:8087

## Development Notes

- The search index is stored in the `index` directory and is automatically rebuilt when running `command.sh`
- PDF.js viewer files are downloaded during first run and stored in `static/pdfjs`
- Both the index and PDF.js directories are excluded from git

## Technologies Used

- Flask: Web framework
- Whoosh: Full-text search engine
- PDF.js: PDF viewer
- pdfplumber: PDF text extraction
- TailwindCSS: Styling 