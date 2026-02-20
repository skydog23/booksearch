# Case-Sensitive Wildcard Fix

## The Problem

After fixing the basic case-sensitive search, we discovered that **wildcards with the `+` prefix were still case-insensitive**:

- `+Fest` correctly matched only 'Fest' ✓
- `+Fest*` incorrectly matched both 'Fest' and 'fest' ✗

For example:
- `+Fest*` should match: Feste, Festival, Festung (all starting with capital F)
- `+Fest*` should NOT match: fest, feste, festlich (starting with lowercase f)

## Root Cause

**Whoosh's wildcard queries (`*` and `?`) are inherently case-insensitive**, regardless of the analyzer used for the field. This is a known limitation of the Whoosh library.

When you search for `content_case:Fest*`, Whoosh:
1. Correctly uses the case-sensitive field
2. BUT applies case-insensitive matching for the wildcard portion
3. Results in matching both 'Fest*' and 'fest*'

## The Solution

Convert case-sensitive wildcards to **regular expressions**, which DO respect case sensitivity in Whoosh.

### Implementation (app.py, lines 273-293)

When a case-sensitive term contains wildcards:
1. Detect the wildcard: `+Fest*`
2. Extract base term: `Fest`
3. Convert to OR pattern with regex: `(content_case:Fest OR content_case:/Fest\w+/)`
4. Enable regex plugin in QueryParser (line 322)

This mirrors the expansion done for regular wildcards (`foo*` → `(foo OR foo*)`), ensuring the base term is always matched.

### Regex Pattern: `\w`

The regex uses `\w` which is a shorthand character class that matches:
- `a-z, A-Z` - English letters
- `0-9` - Digits
- `_` - Underscore
- **Unicode letters** - Including German umlauts (ä, ö, ü, ß, Ä, Ö, Ü) and other international characters

Using `\w` is cleaner than explicit character classes like `[a-zA-Z0-9_äöüßÄÖÜ]` and avoids parsing issues with square brackets in Whoosh query syntax.

## How It Works

### Example 1: Simple wildcard
```
User enters:  +Fest*
Detected:     case-sensitive term with wildcard
Base term:    Fest
Converted to: (content_case:Fest OR content_case:/Fest\w+/)
Result:       Matches Fest (exact), Feste, Festival, Festung
              Does NOT match fest, feste, festlich
```

### Example 2: Question mark wildcard
```
User enters:  +F?st
Detected:     case-sensitive term with ? wildcard
Converted to: content_case:/F\wst/
Result:       Matches Fast, Fest, Fist, Föst
              Does NOT match fest, fast, fist, föst
```

### Example 3: Regular case-insensitive wildcard
```
User enters:  fest*
No + prefix:  Regular case-insensitive search
Stays as:     fest*
Result:       Matches fest, Fest, feste, Feste, festlich, Festival, etc.
```

### Example 4: Complex query with parentheses
```
User enters:  (+Fest* OR +Feier*)
Detected:     Two case-sensitive wildcards
Converted to: (placeholder0 OR placeholder1)
After parse:  ((Fest OR /Fest\w+/) OR (Feier OR /Feier\w+/))
Result:       Matches Fest, Feste, Festival OR Feier, Feier, Feiertag
              Does NOT match fest, feier, etc.
```

## Performance Considerations

Regular expressions are slightly slower than wildcard queries, but:
- Only applied to case-sensitive wildcards (with `+` prefix)
- Most searches don't use case-sensitive wildcards
- The performance difference is negligible for typical query sizes
- The character class is limited to common characters for speed

## Limitations

### 1. Limited Character Set
The regex only includes Latin letters, numbers, and German umlauts. If you need other characters (e.g., French accents, Cyrillic), add them to the character class in line 281:

```python
regex_term = term.replace('*', r'[a-zA-Z0-9_äöüßÄÖÜéèêëàâùûîïôœçÉÈÊËÀÂÙÛÎÏÔŒÇ]*')
```

### 2. More Complex Wildcards
Currently supports:
- `*` (zero or more characters)
- `?` (exactly one character)

Does NOT support Whoosh's advanced wildcards:
- `**` (any number of words)
- Character classes like `[abc]`

### 3. Regex Metacharacters
If your search term contains regex metacharacters (`. ^ $ * + ? { } [ ] \ | ( )`), they may cause issues. The code could be enhanced to escape these.

## Testing

Test these queries:

```bash
# Should match only capitalized forms
+Fest*       → Feste, Festival, Festung (NOT fest, feste)
+Fest?       → Feste (NOT fest)

# Should match both cases (no + prefix)
fest*        → fest, Fest, feste, Feste, festlich, Festival

# Should match only lowercase forms
+fest*       → fest, feste, festlich (NOT Fest, Feste)
```

## Code Changes

### 1. app.py (lines 273-293)
Added logic to detect case-sensitive wildcards and convert them to OR patterns with regex:
- Extract base term (e.g., `Fest` from `Fest*`)
- Create exact match for base term: `content_case:Fest`
- Create regex for extended forms: `content_case:/Fest\w+/`
- Combine with OR: `(content_case:Fest OR content_case:/Fest\w+/)`

### 2. app.py (line 322)
Added `RegexPlugin` to the query parser to enable `/regex/` syntax.

### 3. Regex pattern: `\w`
Uses the `\w` shorthand which matches word characters: letters (including Unicode), digits, and underscores. This avoids issues with square bracket parsing in Whoosh queries.

### 4. Expansion strategy
The OR pattern `(base OR base+...)` mirrors the expansion used for regular wildcards (`foo*` → `(foo OR foo*)`), ensuring that:
- The exact base term is always matched (e.g., "Fest")
- Extended forms are matched case-sensitively (e.g., "Feste", "Festival")

## Future Enhancements

If needed, we could:
1. Add more character sets (French, Spanish, etc.)
2. Allow user-configurable character classes
3. Add escaping for regex metacharacters
4. Support more complex wildcard patterns
5. Add a UI indicator when case-sensitive wildcards are converted to regex

## Related Files

- `CASE_SENSITIVE_SEARCH_FIX.md` - Original case-sensitive search fix
- `FIX_SUMMARY.md` - Quick reference guide
- `test_case_sensitive.py` - Testing script (could be enhanced for wildcards)

