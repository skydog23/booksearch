from flask import Flask, render_template, request, jsonify, Response, send_file, send_from_directory
import os
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID, STORED
from whoosh.qparser import QueryParser
import pdfplumber
from pathlib import Path
import json

app = Flask(__name__)

# Schema for our search index
schema = Schema(
    path=ID(stored=True),
    filename=STORED,
    page_num=STORED,
    content=TEXT(stored=True)
)

def init_index():
    """Initialize or open the search index"""
    if not os.path.exists("index"):
        os.mkdir("index")
        return create_in("index", schema)
    return open_dir("index")

def get_indexed_files():
    """Get set of filenames that are already indexed"""
    ix = init_index()
    with ix.searcher() as searcher:
        # Get unique filenames from the index
        return {doc['filename'] for doc in searcher.all_stored_fields()}

def index_pdf(pdf_path):
    """Extract text from PDF and add to search index"""
    ix = init_index()
    writer = ix.writer()

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if text:  # Only index pages with content
                writer.add_document(
                    path=str(pdf_path),
                    filename=pdf_path.name,
                    page_num=page_num,
                    content=text
                )
    writer.commit()

def clean_index(data_dir):
    """Remove index entries for books that no longer exist in the data directory"""
    ix = init_index()
    existing_files = set(f.name for f in data_dir.glob('*.pdf'))
    indexed_files = get_indexed_files()
    removed_files = indexed_files - existing_files
    
    if removed_files:
        writer = ix.writer()
        for filename in removed_files:
            # Delete all documents with this path (using the ID field from our schema)
            writer.delete_by_term('path', str(data_dir / filename))
        writer.commit()
        
        # Verify deletion
        with ix.searcher() as searcher:
            remaining = {doc['filename'] for doc in searcher.all_stored_fields()}
            if any(f in remaining for f in removed_files):
                print(f"Warning: Some files were not properly removed from the index: {removed_files & remaining}")
    
    return removed_files

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/pdf/<path:filename>/<int:page>')
def serve_pdf(filename, page):
    """Serve a PDF file"""
    try:
        # Add .pdf extension if not present
        if not filename.lower().endswith('.pdf'):
            filename = filename + '.pdf'
            
        pdf_path = Path('data') / filename
        if not pdf_path.exists():
            return {"error": f"PDF file '{filename}' not found in data directory"}, 404
        
        return send_file(pdf_path, mimetype='application/pdf')
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/pdfjs/<path:filename>')
def serve_pdfjs(filename):
    """Serve PDF.js viewer files"""
    return send_from_directory('static/pdfjs', filename)

@app.route('/index_books')
def index_books():
    """Index only new PDFs in the data directory with progress updates"""
    def generate_updates():
        data_dir = Path('data')
        if not data_dir.exists():
            yield json.dumps({"error": "Data directory not found"}) + "\n"
            return

        # Clean up index first
        removed_files = clean_index(data_dir)
        if removed_files:
            yield json.dumps({
                "status": "cleanup",
                "message": f"Removed {len(removed_files)} deleted book{'s' if len(removed_files) != 1 else ''} from index"
            }) + "\n"

        # Get list of all PDF files and already indexed files
        pdf_files = list(data_dir.glob('*.pdf'))
        indexed_files = get_indexed_files()
        
        # Filter for new files only
        new_files = [f for f in pdf_files if f.name not in indexed_files]
        total_files = len(new_files)

        if total_files == 0:
            yield json.dumps({
                "status": "complete",
                "message": "No new books to index"
            }) + "\n"
            return
        
        for i, pdf_file in enumerate(new_files, 1):
            try:
                yield json.dumps({
                    "status": "indexing",
                    "current": i,
                    "total": total_files,
                    "filename": pdf_file.name
                }) + "\n"
                
                index_pdf(pdf_file)
                
            except Exception as e:
                yield json.dumps({
                    "error": f"Error indexing {pdf_file.name}: {str(e)}"
                }) + "\n"

        yield json.dumps({
            "status": "complete",
            "message": f"Indexed {total_files} new book{'s' if total_files != 1 else ''}"
        }) + "\n"

    return Response(generate_updates(), mimetype='text/event-stream')

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])

    ix = init_index()
    with ix.searcher() as searcher:
        query_parser = QueryParser("content", ix.schema)
        q = query_parser.parse(query)
        results = searcher.search(q, limit=None)
        
        # Group results by filename
        books = {}
        for r in results:
            filename = r['filename']
            if filename not in books:
                books[filename] = {
                    'filename': filename,
                    'pages': [],
                    'snippets': {},
                    'score': 0
                }
            books[filename]['pages'].append(r['page_num'])
            books[filename]['snippets'][r['page_num']] = r.highlights("content")
            books[filename]['score'] += 1

        # Convert to list and sort by score
        hits = list(books.values())
        hits.sort(key=lambda x: x['score'], reverse=True)
        
        # Ensure pages are sorted numerically within each book
        for hit in hits:
            hit['pages'].sort()
        
        return jsonify(hits)

if __name__ == '__main__':
    app.run(debug=True, port=8087) 