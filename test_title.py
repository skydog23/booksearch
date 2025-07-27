from PyPDF2 import PdfReader
import pdfplumber
from pathlib import Path

def extract_title(pdf_path):
    """Extract title from PDF using multiple methods"""
    print(f"\nAnalyzing {pdf_path.name}:")
    print("-" * 80)
    
    # Try metadata first
    reader = PdfReader(pdf_path)
    metadata = reader.metadata
    if metadata and metadata.get('/Title'):
        print("Title from metadata:", metadata['/Title'])
    
    # Try first page text
    with pdfplumber.open(pdf_path) as pdf:
        first_page = pdf.pages[0]
        
        # Extract all text blocks with their positions
        text_blocks = first_page.extract_text_lines()
        if text_blocks:
            print("\nFirst few text blocks:")
            for block in text_blocks[:5]:
                print(f"Text: {block['text']}")
                print(f"Position: top={block['top']}, bottom={block['bottom']}")
                print("-" * 40)

# Test with a sample PDF
sample_path = Path('data/GA_106.pdf')
if sample_path.exists():
    extract_title(sample_path)
else:
    print(f"File not found: {sample_path}") 