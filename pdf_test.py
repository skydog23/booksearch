from flask import Flask, render_template, request, send_file, send_from_directory
from pathlib import Path
import os

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('pdf_test.html')

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

if __name__ == '__main__':
    app.run(debug=True, port=8092) 