#!/usr/bin/env python3
"""
Test script to verify case-sensitive search is working correctly.
Run this AFTER rebuilding the index with rebuild_index.py
"""

from whoosh.index import open_dir
from whoosh.qparser import QueryParser
from pathlib import Path

def test_case_sensitive_search():
    """Test case-sensitive search functionality"""
    
    # Check if index exists
    index_dir = Path('index')
    if not index_dir.exists():
        print("ERROR: Index directory not found!")
        print("Please run: python rebuild_index.py")
        return
    
    # Open the index
    ix = open_dir(str(index_dir))
    
    print("=" * 80)
    print("CASE-SENSITIVE SEARCH TEST")
    print("=" * 80)
    print()
    
    # Test queries
    test_cases = [
        ("fest", "content", "Should match both 'fest' and 'Fest' (case-insensitive)"),
        ("content_case:fest", None, "Should match only lowercase 'fest'"),
        ("content_case:Fest", None, "Should match only capitalized 'Fest'"),
    ]
    
    with ix.searcher() as searcher:
        for query_str, field, description in test_cases:
            print(f"\nQuery: {query_str}")
            print(f"Description: {description}")
            print("-" * 80)
            
            try:
                # Parse query
                if field:
                    qp = QueryParser(field, ix.schema)
                else:
                    # When field is None, the query string includes the field (e.g., "content_case:fest")
                    qp = QueryParser("content", ix.schema)
                
                q = qp.parse(query_str)
                print(f"Parsed query: {q}")
                
                # Execute search
                results = searcher.search(q, limit=10)
                print(f"Found {len(results)} results")
                
                if len(results) > 0:
                    print("\nFirst few matches:")
                    for i, hit in enumerate(results[:3], 1):
                        # Get the actual text around the match
                        text = hit['content'][:200]  # First 200 chars
                        # Find 'fest' or 'Fest' in the text
                        fest_lower = text.count('fest')
                        fest_upper = text.count('Fest')
                        print(f"  {i}. {hit['filename']}, page {hit['page_num']}")
                        print(f"     Contains: 'fest' ({fest_lower}x), 'Fest' ({fest_upper}x)")
                        print(f"     Preview: {text[:100]}...")
                
            except Exception as e:
                print(f"ERROR: {e}")
            
            print()
    
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print()
    print("If you see matches for both 'fest' and 'Fest' when searching content_case:Fest,")
    print("then the case-sensitive search is NOT working correctly.")
    print()
    print("Expected behavior:")
    print("  - 'fest' (no field prefix): matches both 'fest' and 'Fest'")
    print("  - 'content_case:fest': matches only 'fest'")
    print("  - 'content_case:Fest': matches only 'Fest'")

if __name__ == '__main__':
    test_case_sensitive_search()

