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
- Search result snippets showing matched text context
- Boolean search operators (AND, OR, NOT)
- Exact phrase matching with quotes

## Prerequisites

- Python 3.6 or higher
- For Ubuntu/Debian: `sudo apt-get install python3-venv`
- For macOS: Python 3 from Homebrew (`brew install python3`) or python.org
- For Windows: Python 3 from python.org (ensure "Add Python to PATH" is checked during installation)

## Quick Start

### For Windows Users

1. Clone the repository:
```batch
git clone [repository-url]
cd booksearch
```

2. Run the Windows setup script:
```batch
setup.bat
```

3. Start the application:
```batch
start.bat
```

The setup script will automatically:
- Create a Python virtual environment
- Install all required dependencies
- Download and set up the PDF.js viewer
- Create necessary directories
- Build the search index from your PDF files

### For macOS/Linux Users

1. Clone the repository:
```bash
git clone [repository-url]
cd booksearch
```

2. Make the setup script executable:
```bash
chmod +x command.sh
```

3. Run the setup script:
```bash
./command.sh
```

The script will automatically:
- Create a Python virtual environment if needed
- Install all required dependencies
- Download and set up the PDF.js viewer
- Create necessary directories
- Build the search index from your PDF files
- Start the Flask server

The application will be available at http://localhost:8087

## Package Versions

The application uses specific versions of key packages:
- Flask 3.1.1: Web framework
- Whoosh 2.7.4: Search engine
- pdfplumber 0.10.3: PDF text extraction
- PyPDF2 3.0.1: PDF metadata extraction

If you need to update packages in an existing installation:
```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt --upgrade
```

## Adding Books

1. Place your PDF files in the `data` directory
2. Restart the application (or click the "Index" button in the web interface)
3. The books will be automatically indexed and made searchable

## Search Features

- Basic search: Just type words to find them in any book
- Phrase search: Use quotes for exact phrases, e.g., `"machine learning"`
- Boolean operators: 
  - AND: `neural AND networks` (both terms must appear
  - OR: `python OR javascript` (either term)
  - NOT: `programming NOT basic` (exclude terms)
- Wildcards: `program*` matches programm:ing, programs, etc.

## Development Notes

- The search index is stored in the `index` directory and is automatically rebuilt when needed
- PDF.js viewer files are downloaded during first run and stored in `static/pdfjs`
- Both the index and PDF.js directories are excluded from git
- The application uses timestamp checking to avoid unnecessary reindexing

## Technologies Used

- Flask: Web framework
- Whoosh: Full-text search engine
- PDF.js: PDF viewer
- pdfplumber: PDF text extraction
- PyPDF2: PDF metadata extraction
- TailwindCSS: Styling 