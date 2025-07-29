from flask import Flask, render_template, request, jsonify, Response, send_file, send_from_directory
import os
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID, STORED
from whoosh.qparser import QueryParser, OrGroup
import pdfplumber
from pathlib import Path
import json
from PyPDF2 import PdfReader
from functools import lru_cache
import re

app = Flask(__name__)

# Schema for our search index
schema = Schema(
    path=ID(stored=True),
    filename=STORED,
    page_num=STORED,
    content=TEXT(stored=True)
)

@lru_cache(maxsize=1000)
def get_pdf_title(filename):
    """Extract title from PDF metadata with caching"""
    try:
        pdf_path = Path('data') / filename
        if not pdf_path.exists():
            return filename
        
        reader = PdfReader(pdf_path)
        metadata = reader.metadata
        if metadata and metadata.get('/Title'):
            title = metadata['/Title']
            # Strip off any "GA ..." prefix from the title string, e.g., "GA 261 - "
            cleaned_title = re.sub(r'^\s*GA\s+\d+\s*-\s*', '', title).strip()
            # If stripping the prefix results in an empty string, use the original title
            # return cleaned_title if cleaned_title else title
            return title
        
        # If no metadata title, return filename without .pdf
        return filename.replace('.pdf', '')
    except Exception as e:
        print(f"Error extracting title from {filename}: {e}")
        return filename

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

def highlight_phrases(text, phrases):
    """Manually highlight phrases in a text snippet."""
    # Create a context window around the first match
    first_match_pos = -1
    for phrase in phrases:
        pos = text.lower().find(phrase.lower())
        if pos != -1:
            first_match_pos = pos
            break
    
    if first_match_pos == -1:
        return text[:200] # Return start of text if no match found

    start = max(0, first_match_pos - 100)
    end = min(len(text), first_match_pos + 100)
    snippet = text[start:end]

    for phrase in phrases:
        # Escape special regex characters in the phrase
        escaped_phrase = re.escape(phrase)
        # Highlight all occurrences of the phrase in the snippet
        snippet = re.sub(
            f'({escaped_phrase})',
            r'<b class="match">\1</b>',
            snippet,
            flags=re.IGNORECASE
        )
    return f"...{snippet}..."

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

@app.route('/pdf/title/<path:filename>')
def get_title(filename):
    """Get the title of a PDF file"""
    if not filename.lower().endswith('.pdf'):
        filename = filename + '.pdf'
    title = get_pdf_title(filename)
    return jsonify({"title": title})

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
        query_parser = QueryParser("content", ix.schema, group=OrGroup)
        
        try:
            # Determine search type and extract terms for highlighting
            search_type = 'terms'
            highlight_terms = []
            
            # Regex to find quoted phrases
            phrases = re.findall(r'"([^"]*)"', query)
            if phrases:
                search_type = 'phrase'
                highlight_terms = [p.strip() for p in phrases if p.strip()]

            # Fallback to individual terms if no phrases found or query is not just phrases
            if not highlight_terms:
                highlight_terms = [
                    term for term in query.replace('"', '').split() 
                    if term.upper() not in ['AND', 'OR', 'NOT']
                ]

            q = query_parser.parse(query)
            results = searcher.search(q, limit=None)
            
            # Group results by filename
            books = {}
            for r in results:
                filename = r['filename']
                if filename not in books:
                    books[filename] = {
                        'filename': filename,
                        'title': get_pdf_title(filename),
                        'pages': set(),
                        'snippets': {},
                        'score': 0, # This is the page count
                        'match_count': 0, # This will be the total match count
                        'search_type': search_type,
                        'highlight_terms': highlight_terms
                    }
                
                books[filename]['pages'].add(r['page_num'])
                
                # Count matches on the current page
                page_content_lower = r['content'].lower()
                page_match_count = 0
                for term in highlight_terms:
                    page_match_count += page_content_lower.count(term.lower())
                books[filename]['match_count'] += page_match_count

                # Generate snippet
                snippet_text = ""
                if search_type == 'phrase':
                    # Use our custom phrase highlighter for snippets
                    snippet_text = highlight_phrases(r['content'], highlight_terms)
                else:
                    # Use Whoosh's default highlighter for term searches
                    snippet_text = r.highlights("content")
                
                # Clean up whitespace for better tooltip display
                cleaned_snippet = re.sub(r'\s+', ' ', snippet_text).strip()
                books[filename]['snippets'][r['page_num']] = cleaned_snippet

                books[filename]['score'] += 1 # Increment page count

            # Convert to list and sort by score
            hits = list(books.values())
            hits.sort(key=lambda x: x['score'], reverse=True)
            
            # Convert page sets to sorted lists
            for hit in hits:
                hit['pages'] = sorted(list(hit['pages']))
            
            return jsonify(hits)
        except Exception as e:
            print(f"Search error: {str(e)}")
            return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=8087) 