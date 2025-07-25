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

3. Run the application:
```bash
python app.py  # For the main search application
# or
python pdf_test.py  # For the PDF viewer test application
```

4. Access the application at http://localhost:8080 (or the port shown in the console)

## Technologies Used

- Flask: Web framework
- Whoosh: Full-text search engine
- PDF.js: PDF viewer
- pdfplumber: PDF text extraction
- TailwindCSS: Styling 