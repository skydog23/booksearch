from flask import Flask, render_template, request, jsonify, Response, send_file, send_from_directory
import os
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID, STORED
from whoosh.analysis import RegexTokenizer
from whoosh.qparser import QueryParser, OrGroup
import pdfplumber
from pathlib import Path
import json
from PyPDF2 import PdfReader
from functools import lru_cache
import re

app = Flask(__name__)

# Schema for our search index
# For case-sensitive search, we need an analyzer that does NOT lowercase the text
# Whoosh's default TEXT field uses StandardAnalyzer which includes LowercaseFilter
# We'll use RegexTokenizer which just splits on word boundaries without lowercasing
case_sensitive_analyzer = RegexTokenizer()  # Tokenizes but preserves case

schema = Schema(
    path=ID(stored=True),
    filename=STORED,
    page_num=STORED,
    content=TEXT(stored=True),  # Normal case-insensitive field (includes LowercaseFilter)
    content_case=TEXT(stored=True, analyzer=case_sensitive_analyzer)  # Case-sensitive field (no lowercasing)
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
                    content=text,
                    content_case=text  # Store same text for case-sensitive search
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

@app.route('/pdf/title_for_search/<path:filename>')
def get_title_for_search(filename):
    """Get the title of a PDF file for search purposes"""
    try:
        if not filename.lower().endswith('.pdf'):
            filename = filename + '.pdf'
        
        # Check if file exists
        pdf_path = Path('data') / filename
        if not pdf_path.exists():
            return jsonify({"error": f"PDF file '{filename}' not found"}), 404
            
        title = get_pdf_title(filename)
        
        # Strip off any "GA ..." prefix from the title string for search purposes
        # This removes patterns like "GA 261 - ", "GA_082 - ", etc.
        cleaned_title = re.sub(r'^\s*GA[_\s-]*\d+[A-Za-z]*\s*-\s*', '', title).strip()
        
        # If stripping the prefix results in an empty string, use the original title
        search_title = cleaned_title if cleaned_title else title
        
        return jsonify({"title": search_title, "filename": filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

# Favorites Storage
FAVORITES_FILE = 'favorites.json'

def load_favorites():
    if not os.path.exists(FAVORITES_FILE):
        return []
    try:
        with open(FAVORITES_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading favorites: {e}")
        return []

def save_favorites(favorites):
    try:
        with open(FAVORITES_FILE, 'w') as f:
            json.dump(favorites, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving favorites: {e}")
        return False

@app.route('/favorites', methods=['GET'])
def get_favorites():
    return jsonify(load_favorites())

@app.route('/favorites', methods=['POST'])
def add_favorite():
    data = request.json
    if not data or 'query' not in data:
        return jsonify({"error": "Missing query"}), 400
    
    favorites = load_favorites()
    new_favorite = {
        "id": str(len(favorites) + 1) + "_" + str(int(os.times()[4] * 100)), # Simple unique ID
        "query": data['query'],
        "annotation": data.get('annotation', ''),
        "timestamp": data.get('timestamp', '')
    }
    favorites.append(new_favorite)
    
    if save_favorites(favorites):
        return jsonify(new_favorite)
    else:
        return jsonify({"error": "Failed to save favorite"}), 500

@app.route('/favorites/<favorite_id>', methods=['DELETE'])
def delete_favorite(favorite_id):
    favorites = load_favorites()
    initial_len = len(favorites)
    favorites = [f for f in favorites if f['id'] != favorite_id]
    
    if len(favorites) == initial_len:
        return jsonify({"error": "Favorite not found"}), 404
        
    if save_favorites(favorites):
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Failed to save changes"}), 500

# Add at the top of the file, after the imports
debugSelectBooks = False  # When True, only search GA_004.pdf

def replace_placeholder_in_query(query_tree, placeholder, replacement):
    """
    Recursively traverse a Whoosh query tree and replace placeholder terms with actual queries.
    """
    from whoosh.query import Term, And, Or, Not, Phrase
    
    # If this is a Term node and matches our placeholder
    if isinstance(query_tree, Term):
        if query_tree.text == placeholder:
            return replacement
        return query_tree
    
    # If this is a compound query (And, Or, Not), recursively process children
    if isinstance(query_tree, (And, Or)):
        new_children = [replace_placeholder_in_query(child, placeholder, replacement) 
                       for child in query_tree.children()]
        if isinstance(query_tree, And):
            return And(new_children)
        else:
            return Or(new_children)
    
    if isinstance(query_tree, Not):
        return Not(replace_placeholder_in_query(query_tree.query, placeholder, replacement))
    
    # For other query types, return as-is
    return query_tree

@app.route('/search')
def search():
    query = request.args.get('q', '')
    print(f"\nSearch request received for query: {query}")
    if not query:
        return jsonify([])

    def generate_search_results():
        ix = init_index()
        with ix.searcher() as searcher:
            # Check for case-sensitive terms (prefixed with +)
            # Match + followed by word characters, *, and ? but stop at special operators and parens
            case_sensitive_terms = re.findall(r'\+([\w*?]+)', query)
            modified_query = query
            has_case_sensitive_wildcard = False
            case_sensitive_wildcard_queries = []  # Store programmatic queries
            
            # FIRST: Handle case-sensitive terms (replace + prefix with content_case: field)
            if case_sensitive_terms:
                print(f"Case-sensitive terms detected: {case_sensitive_terms}")
                # Check if any case-sensitive term has a wildcard
                # Whoosh wildcards are case-insensitive by default, so we need special handling
                for term in case_sensitive_terms:
                    if '*' in term:
                        has_case_sensitive_wildcard = True
                        print(f"WARNING: Case-sensitive wildcard detected: +{term}")
                        print(f"         Whoosh wildcards are inherently case-insensitive.")
                        print(f"         Converting to explicit OR + regex for case-sensitive matching...")
                        # For Fest*, we want to match: Fest, Feste, Festival, etc.
                        # Strategy: Build Whoosh query objects programmatically to avoid escaping issues
                        base_term = term.rstrip('*')  # Remove trailing *
                        
                        # Store the info for building the query programmatically later
                        case_sensitive_wildcard_queries.append({
                            'original': f'+{term}',
                            'base_term': base_term,
                            'type': 'wildcard'
                        })
                        
                        # For now, just replace with a placeholder that we'll handle specially
                        # Use a unique marker that won't appear in normal text
                        # Use lowercase because Whoosh lowercases terms in the default 'content' field
                        placeholder = f'cswild{len(case_sensitive_wildcard_queries)-1}marker'
                        modified_query = modified_query.replace(f'+{term}', placeholder)
                        print(f"         Base term: {base_term}")
                        print(f"         Will build programmatic query for case-sensitive wildcard")
                    elif '?' in term:
                        has_case_sensitive_wildcard = True
                        print(f"WARNING: Case-sensitive wildcard (?) detected: +{term}")
                        print(f"         Converting to regex for case-sensitive matching...")
                        # Replace each ? with exactly one word character
                        # Use \\w which matches any word character (letter, digit, underscore, Unicode letters)
                        # Using string literal to avoid escaping issues
                        regex_term = term.replace('?', '\\w')  # Literal backslash-w
                        modified_query = modified_query.replace(f'+{term}', f'content_case:/{regex_term}/')
                        print(f"         Converted to regex: content_case:/{regex_term}/")
                    else:
                        # No wildcard, use normal field specification
                        modified_query = modified_query.replace(f'+{term}', f'content_case:{term}')
                print(f"Modified query after case-sensitive replacement: {modified_query}")
            
            # SECOND: Expand wildcard terms: term* -> (term OR term*)
            # This makes wildcards more intuitive by including the base term
            # BUT: Don't expand wildcards that are part of field specifications (content_case:term*)
            # We need to match wildcards that are NOT preceded by "fieldname:"
            
            # Find wildcards that are NOT part of a field specification
            # Match word boundaries followed by word chars and *, but not when preceded by a colon
            wildcard_pattern = r'(?<![:\w])(\w+)\*'
            wildcards_found = re.findall(wildcard_pattern, modified_query)
            if wildcards_found:
                print(f"Wildcard terms detected (non-field-specific): {wildcards_found}")
                # Replace each standalone term* with (term OR term*)
                # This won't match content_case:Fest* because of the negative lookbehind
                modified_query = re.sub(wildcard_pattern, r'(\1 OR \1*)', modified_query)
                print(f"Expanded wildcards: {modified_query}")
            
            # Use appropriate parser
            from whoosh import qparser
            # For case-sensitive terms, we need to use QueryParser that doesn't automatically
            # search all fields. We'll use a single-field parser on 'content' by default,
            # but the content_case: field prefix will override it for case-sensitive terms.
            query_parser = qparser.QueryParser("content", ix.schema, group=OrGroup)
            
            # Enable regex plugin for case-sensitive wildcard support
            # This allows us to use /regex/ syntax in queries
            query_parser.add_plugin(qparser.RegexPlugin())
            
            try:
                # Determine search type and extract terms for highlighting
                search_type = 'terms'
                highlight_terms = []
                
                # First, extract quoted phrases
                phrases = re.findall(r'"([^"]*)"', query)
                if phrases:
                    search_type = 'phrase'
                    highlight_terms.extend([p.strip() for p in phrases if p.strip()])
                    print(f"Found phrases: {phrases}")

                # Also extract individual terms (after removing quoted sections)
                # This handles queries like: ("foo bar" OR boo)
                query_without_quotes = re.sub(r'"[^"]*"', '', query)
                individual_terms = [
                    term.lstrip('+').rstrip('*') for term in query_without_quotes.split() 
                    if term.upper() not in ['AND', 'OR', 'NOT', '(', ')']
                ]
                highlight_terms.extend(individual_terms)
                
                print(f"All highlight terms: {highlight_terms}")

                q = query_parser.parse(modified_query)
                print(f"Parsed query (before wildcard substitution): {q}")
                
                # If we have case-sensitive wildcard queries, build them programmatically
                if case_sensitive_wildcard_queries:
                    from whoosh.query import Term, Regex, Or
                    print(f"Building programmatic queries for {len(case_sensitive_wildcard_queries)} case-sensitive wildcards")
                    
                    # Build the replacement queries
                    for i, wq in enumerate(case_sensitive_wildcard_queries):
                        base_term = wq['base_term']
                        # Create an OR query: exact term OR regex match
                        exact_query = Term("content_case", base_term)
                        # For regex, we need to pass the pattern directly without / delimiters
                        regex_pattern = base_term + r'\w+'
                        regex_query = Regex("content_case", regex_pattern)
                        or_query = Or([exact_query, regex_query])
                        
                        print(f"   Placeholder {i}: {base_term}* → (Term:{base_term} OR Regex:{regex_pattern})")
                        
                        # Replace the placeholder in the parsed query
                        # We need to traverse the query tree and replace Term nodes that match our placeholder
                        # Use the same lowercase format we used when creating the placeholder
                        placeholder_term = f'cswild{i}marker'
                        q = replace_placeholder_in_query(q, placeholder_term, or_query)
                    
                    print(f"Parsed query (after wildcard substitution): {q}")
                
                results = searcher.search(q, limit=None)
                print(f"Found {len(results)} initial results")
                
                # Decide which highlighter to use based on result count
                # Whoosh's highlighter is better but VERY slow with wildcards on large result sets
                use_fast_highlighter = len(results) > 200
                if use_fast_highlighter:
                    print(f"Using fast highlighter (highlight_phrases) due to {len(results)} results")
                else:
                    print(f"Using Whoosh's highlighter for better quality with {len(results)} results")
                
                # First pass: count unique books for progress tracking
                unique_books = set()
                for r in results:
                    if debugSelectBooks and r['filename'] != 'GA_004.pdf':
                        continue
                    unique_books.add(r['filename'])
                total_books_to_process = len(unique_books)
                print(f"Total unique books with matches: {total_books_to_process}")
                
                # Send initial progress update
                initial_update = {
                    "status": "searching",
                    "message": "Starting search...",
                    "total_books": total_books_to_process,
                    "total_pages": 0
                }
                print(f"Sending initial update: {initial_update}")
                yield json.dumps(initial_update) + "\n"
                
                # Group results by filename
                books = {}
                processed_books = 0
                total_pages = 0
                
                for r in results:
                    try:
                        filename = r['filename']
                        
                        # If debug mode is on, only process GA_004.pdf
                        if debugSelectBooks and filename != 'GA_004.pdf':
                            continue
                            
                        if filename not in books:
                            processed_books += 1
                            # Send progress update BEFORE expensive operations
                            progress_update = {
                                "status": "searching",
                                "message": f"Processing book {processed_books} of {total_books_to_process}...",
                                "current_book": processed_books,
                                "total_books": total_books_to_process,
                                "total_pages": total_pages
                            }
                            print(f"Processing book {filename}")
                            yield json.dumps(progress_update) + "\n"
                            
                            # Now do the expensive operations
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
                        total_pages += 1
                        
                        # Count matches on the current page
                        page_content_lower = r['content'].lower()
                        page_match_count = 0
                        for term in highlight_terms:
                            page_match_count += page_content_lower.count(term.lower())
                        books[filename]['match_count'] += page_match_count

                        # Generate snippet using appropriate highlighter
                        snippet_text = ""
                        if use_fast_highlighter:
                            # Fast highlighter for large result sets
                            snippet_text = highlight_phrases(r['content'], highlight_terms)
                        else:
                            # Whoosh's highlighter for better quality on smaller result sets
                            if search_type == 'phrase' or case_sensitive_terms:
                                # For phrase/case-sensitive, must use highlight_phrases
                                snippet_text = highlight_phrases(r['content'], highlight_terms)
                            else:
                                # Use Whoosh's highlighter for better quality
                                snippet_text = r.highlights("content")
                        
                        if not snippet_text:
                            snippet_text = r['content'][:300] + "..."
                        
                        books[filename]['snippets'][r['page_num']] = snippet_text

                        books[filename]['score'] += 1 # Increment page count
                    except Exception as result_error:
                        print(f"Error processing result: {str(result_error)}")
                        continue

                # Convert to list and sort by score
                hits = list(books.values())
                hits.sort(key=lambda x: x['score'], reverse=True)
                
                # Convert page sets to sorted lists
                for hit in hits:
                    hit['pages'] = sorted(list(hit['pages']))
                
                # Send results in batches of 10 books
                batch_size = 10
                total_hits = len(hits)
                
                # Send initial completion status
                yield json.dumps({
                    "status": "complete",
                    "total_books": total_hits,
                    "total_pages": total_pages,
                    "batch_count": (total_hits + batch_size - 1) // batch_size
                }) + "\n"

                # Send results in batches
                for i in range(0, total_hits, batch_size):
                    batch = hits[i:i + batch_size]
                    yield json.dumps({
                        "status": "batch",
                        "batch_number": i // batch_size + 1,
                        "results": batch
                    }) + "\n"

                print(f"Search complete. Sent {total_hits} books in {(total_hits + batch_size - 1) // batch_size} batches")

            except Exception as e:
                print(f"Unexpected search error: {str(e)}")
                yield json.dumps({
                    "status": "complete",
                    "results": [],
                    "total_books": 0,
                    "total_pages": 0,
                    "error": str(e)
                }) + "\n"

    return Response(generate_search_results(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, port=8087) 