# Case-Sensitive Search Fix

## Problem
The case-sensitive search feature using `+Term` syntax was not working correctly. For example, `+Fest` was matching both 'Fest' and 'fest', when it should only match 'Fest'.

## Root Causes

### 1. Analyzer Issue
The `content_case` field was using `RegexTokenizer()`, but the way it was configured, Whoosh's default TEXT field was still applying lowercase normalization during indexing and searching.

### 2. Query Parser Issue  
The search was using `MultifieldParser` with `OrGroup`, which meant that even when searching `content_case:Fest`, it was **also** searching the case-insensitive `content` field, causing case-insensitive matches to appear.

## Solutions Applied

### 1. Fixed the Schema (app.py, lines 16-29)
- Clarified that `RegexTokenizer()` preserves case (it doesn't lowercase)
- The regular `content` field uses Whoosh's default TEXT analyzer with LowercaseFilter
- The `content_case` field uses `RegexTokenizer()` without any lowercase filtering
- Added clear comments explaining this difference

### 2. Fixed the Query Parser (app.py, lines 285-290)
- Changed from `MultifieldParser(["content", "content_case"], ...)` to `QueryParser("content", ...)`
- Now by default searches only the case-insensitive `content` field
- When a field is explicitly specified (like `content_case:Fest`), it overrides the default
- This ensures `+Fest` (which gets converted to `content_case:Fest`) only searches the case-sensitive field

## How to Apply the Fix

Since the schema changed, the index must be completely rebuilt:

### Option 1: Use the rebuild script (Recommended)
```bash
cd /Users/gunn/Software/cursor/booksearch
python rebuild_index.py
```

This script will:
1. Delete the old index
2. Create a new index with the corrected schema
3. Re-index all PDFs in the `data/` directory

### Option 2: Manual rebuild
1. Delete the `index/` directory
2. Start the Flask app: `python app.py` (or use `start.bat` on Windows)
3. Click the "Index" button in the web interface

## Testing the Fix

After rebuilding the index, test with German words:

1. Search for `+fest` - should only match lowercase 'fest' (adjective: fixed/firm)
2. Search for `+Fest` - should only match capitalized 'Fest' (noun: party/festival)
3. Search for `fest` (without +) - should match both 'fest' and 'Fest' (case-insensitive)

## Technical Details

### Whoosh Analyzer Pipeline
- **Default TEXT field**: `RegexTokenizer() -> LowercaseFilter() -> ...`
- **Our content_case field**: `RegexTokenizer()` only (no LowercaseFilter)

### Query Transformation
When user enters: `+Fest`
1. Regex extracts: `Fest` as a case-sensitive term
2. Query is modified: `+Fest` → `content_case:Fest`
3. Parser searches only the `content_case` field for 'Fest' (exact case)

### Why This Matters for German
German capitalizes all nouns, so case distinction is semantically important:
- `fest` (adjective) = fixed, firm, solid
- `Fest` (noun) = party, festival, celebration
- `Feste` (noun) = fortress, fort

The case-sensitive search allows precise matching of the intended word class.

## Files Modified
- `app.py`: Fixed schema and query parser
- `rebuild_index.py`: New script for complete index rebuild (created)
- `CASE_SENSITIVE_SEARCH_FIX.md`: This documentation (created)

