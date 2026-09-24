# Extract lecture-cycle place and date information from the first pages of a GA volume.
# Preferred case: one or more cities plus one or more full day.month(.year) ranges.
# Fallback, when no full range is found: one or more cities and/or one or more bare
# years, e.g. "gehalten in Berlin, Köln und Nürnberg in den Jahren 1904, 1905 und 1907".
# Everything is comma-separated; each full range is hyphen-separated.

import json
import re
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / 'data'
CYCLE_INFO_PATH = ROOT / 'index' / 'cycle_info.json'
FIRST_PAGES = 6

MONTHS = {
    'januar': 1, 'februar': 2, 'marz': 3, 'märz': 3, 'maerz': 3,
    'april': 4, 'mai': 5, 'juni': 6, 'juli': 7, 'august': 8,
    'september': 9, 'oktober': 10, 'november': 11, 'dezember': 12,
}
MONTH = (
    r'januar|februar|märz|maerz|marz|april|mai|juni|juli|'
    r'august|september|oktober|november|dezember'
)
YEAR = r'(?:1[89]\d{2}|20\d{2})'
RANGE_RE = re.compile(
    rf'(\d{{1,2}})\.?\s*(?:({MONTH})\.?\s*)?(?:({YEAR})\s*)?'
    rf'(?:bis|und)\s+(?:dem\s+|zum\s+)?'
    rf'(\d{{1,2}})\.?\s*({MONTH})\.?\s*({YEAR})',
    re.IGNORECASE,
)
# A chain of bare years, e.g. "1901 bis 1905", "1904, 1905 und 1907", "1912/1913",
# "1903 - 1906" (a plain hyphen, not the en-dash "normalize" already rewrites to "bis").
YEAR_CHAIN = rf'{YEAR}(?:\s*(?:,\s*und|,|/|und|bis|-)\s*{YEAR})*'
# "in/aus den Jahren X", "im Jahre X", "aus dem Jahre X" - a year named by a cue phrase,
# whether or not it is tied to a "gehalten".
CUE_YEARS_RE = re.compile(
    rf'(?:in\s+den\s+Jahren|aus\s+den\s+Jahren|im\s+Jahre|aus\s+dem\s+Jahre)\s+({YEAR_CHAIN})',
    re.IGNORECASE,
)
# A bare year (or chain) directly after "gehalten", e.g. "gehalten 1912/1913 in ...".
GEHALTEN_YEARS_RE = re.compile(rf'^\s*({YEAR_CHAIN})')
# "gehalten zwischen Januar und Dezember 1912" - a month span within a single year.
MONTH_SPAN_YEAR_RE = re.compile(
    rf'zwischen\s+(?:{MONTH})\s+und\s+(?:{MONTH})\s+({YEAR})',
    re.IGNORECASE,
)
# OCR sometimes spaces out "VERLAG" into individual letters, e.g. "V E R L AG".
VERLAG_RE = re.compile(r'V\s*E\s*R\s*L\s*A\s*G', re.IGNORECASE)
CITY = r'(?:Den Haag|[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]{2,}(?:\s+\([^)]{2,40}\))?)'
CITY_LIST = rf'{CITY}(?:\s*,\s*{CITY})*(?:\s+und\s+{CITY})?'
CITY_RE = re.compile(rf'(?:(?<![A-Za-zÄÖÜäöüß])(?:in|zu))\s+({CITY_LIST})')
NOT_CITIES = {
    'Architektenhaus', 'Auflage', 'August', 'Band', 'Berliner', 'Buch',
    'Das', 'Dem', 'Den', 'Der', 'Die', 'Diese', 'Dieser', 'Dieses',
    'Ein', 'Eine', 'Einem', 'Einen', 'Einer', 'Erste', 'Ersten',
    'Gesamtausgabe', 'Goetheanum', 'Goetheanumbau', 'Jahr', 'Jahre', 'Jahren',
    'Januar', 'Juli', 'Juni', 'Mai', 'Nach', 'November', 'Oktober',
    'Anknüpfung', 'Beziehung', 'Ergänzung', 'Ergänzungen', 'For', 'Form',
    'Orte', 'Orten', 'Ostern',
    'Pfingsten', 'Rudolf', 'Schweiz', 'September', 'Städte', 'Städten',
    'Stadten', 'Steiner', 'Teil', 'Verlag', 'Vortrag', 'Vortrage',
    'Vorträge', 'Vorträgen', 'Weihnachten', 'Zwischen',
}


def normalize(text):
    text = text.replace('\u00ad', '')
    text = text.replace('Mündien', 'München')
    text = re.sub(r'(\d{1,2})\s*-\s+(?=[A-Za-zÄÖÜäöü])', r'\1. ', text)
    text = re.sub(r'(\d)\s*[–—]\s*(\d)', r'\1 bis \2', text)
    text = re.sub(r'\s+', ' ', text)
    for month in MONTHS:
        if len(month) < 5:
            continue
        for split_at in range(3, len(month) - 1):
            broken = month[:split_at] + ' ' + month[split_at:]
            text = re.sub(broken, month, text, flags=re.IGNORECASE)
    return text


def _month(name):
    return MONTHS[name.lower()]


def _complete(match):
    d1, m1, y1, d2, m2, y2 = match.groups()
    day1, day2 = int(d1), int(d2)
    if not (1 <= day1 <= 31 and 1 <= day2 <= 31):
        return None
    month2 = _month(m2)
    year2 = int(y2)
    month1 = _month(m1) if m1 else month2
    year1 = int(y1) if y1 else year2
    start = (year1, month1, day1)
    end = (year2, month2, day2)
    if start > end:
        return None
    return start, end


def _format_date(year, month, day, include_year):
    if include_year:
        return f'{day}.{month}.{year}'
    return f'{day}.{month}'


def _format_range(start, end):
    if start[0] == end[0]:
        return f'{_format_date(*start, False)} - {_format_date(*end, True)}'
    return f'{_format_date(*start, True)} - {_format_date(*end, True)}'


def _cities(zone):
    """City names found via "in <city>" / "zu <city>". Returns [] when the
    page only says "in verschiedenen Städten" (various cities, unnamed)."""
    found = []
    for blob in CITY_RE.findall(zone):
        for part in re.split(r'\s*,\s*|\s+und\s+', blob):
            name = part.strip()
            if name == 'DenHaag':
                name = 'Den Haag'
            if not name or name in NOT_CITIES or name in found:
                continue
            found.append(name)
    return found


def _boilerplate(text, start):
    before = text[max(0, start - 24):start].lower().rstrip()
    after = text[start:start + 14].lower()
    if before.endswith('frei') or before.endswith('fest') or before.endswith('fets'):
        return True
    if after.startswith('gehaltenen') or after.startswith('gehaltene '):
        return True
    return False


def _year_list(blob):
    """Distinct years in a matched year chain, in the order they appear."""
    years = []
    for year in re.findall(YEAR, blob):
        if year not in years:
            years.append(year)
    return years


def _bare_years(text, gstart, window):
    """A year or years tied to the cycle when no full date range is present.
    Returns (years, zone), where zone is the text to search for cities."""
    match = CUE_YEARS_RE.search(window)
    if match:
        return _year_list(match.group(1)), window[:match.end() + 80]
    # "gehalten 1912/1913 in ...": the year sits directly after "gehalten".
    tail = window[len('gehalten'):]
    match = GEHALTEN_YEARS_RE.match(tail)
    if match:
        return _year_list(match.group(1)), window[:len('gehalten') + match.end() + 80]
    match = MONTH_SPAN_YEAR_RE.search(window)
    if match:
        return _year_list(match.group(1)), window[:match.end() + 80]
    # "... aus dem Jahre 1921 gehalten in <cities>": the year cue precedes "gehalten",
    # and the cities follow it directly. Require the city half so that an unrelated
    # summary sentence ending in "... gehalten hat." doesn't win against a later,
    # better match on the actual title page.
    lookback = text[max(0, gstart - 80):gstart]
    match = CUE_YEARS_RE.search(lookback)
    if match:
        zone = window[:200]
        if _cities(zone):
            return _year_list(match.group(1)), zone
    return [], None


def _standalone_years(text):
    """A year reference with no "gehalten" nearby, for a writings volume titled
    e.g. "... aus den Jahren 1903 - 1906" or "... aus den Jahren 1907,1909 und 1911".
    Requires two or more years: nothing anchors a single bare year here the way
    "gehalten" does in label_from_text, and a lone year is too often an incidental
    one, e.g. "drei Aufsätze ... aus dem Jahre 1900" about an added essay rather
    than the volume itself."""
    verlag = VERLAG_RE.search(text)
    title_zone = text[:verlag.start()] if verlag else text[:700]
    if re.search(r'Bibliographie|Gesamtausgabe', title_zone):
        return None
    match = CUE_YEARS_RE.search(title_zone)
    if not match:
        return None
    years = _year_list(match.group(1))
    if len(years) < 2:
        return None
    cities = _cities(title_zone[:match.end() + 80])
    items = cities + years
    return ', '.join(items) if items else None


def label_from_text(text):
    """Return a cycle label built from the cities and dates found near "gehalten",
    or None when neither a city nor a year is found."""
    text = normalize(text)
    for match in re.finditer(r'gehalten', text, re.IGNORECASE):
        if _boilerplate(text, match.start()):
            continue
        window = text[match.start():match.start() + 700]
        # The title page names the publisher. A second "gehalten" before that
        # is another cycle of the same volume. Edition history comes after.
        verlag = VERLAG_RE.search(window)
        if verlag:
            window = window[:verlag.start()]
        # Catalogue entries cite a bibliography number instead of the publisher.
        if re.search(r'Bibliographie|Gesamtausgabe', window):
            continue

        ranges = []
        last_end = None
        for hit in RANGE_RE.finditer(window):
            rng = _complete(hit)
            if rng:
                ranges.append(rng)
                last_end = hit.end()

        if ranges:
            zone = window[:last_end + 80]
            cities = _cities(zone)
            date_items = [_format_range(start, end) for start, end in ranges]
        else:
            years, zone = _bare_years(text, match.start(), window)
            if not years:
                continue
            cities = _cities(zone) if zone else []
            date_items = years

        items = cities + date_items
        if not items:
            continue
        return ', '.join(items)
    return _standalone_years(text)


def first_pages_text(pdf_path, pages=FIRST_PAGES):
    parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:pages]:
            parts.append(page.extract_text() or '')
    return '\n'.join(parts)


def label_for_pdf(pdf_path):
    try:
        return label_from_text(first_pages_text(pdf_path))
    except Exception as exc:
        print(f'Cycle info skipped for {Path(pdf_path).name}: {exc}')
        return None


def load_cycle_info():
    if not CYCLE_INFO_PATH.exists():
        return {}
    try:
        with open(CYCLE_INFO_PATH, encoding='utf-8') as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        print(f'Error loading cycle info: {exc}')
        return {}


def save_cycle_info(labels):
    CYCLE_INFO_PATH.parent.mkdir(exist_ok=True)
    with open(CYCLE_INFO_PATH, 'w', encoding='utf-8') as handle:
        json.dump(labels, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write('\n')


def update_cycle_for_pdf(pdf_path):
    """Recompute one volume and store it. A volume that does not qualify is removed."""
    pdf_path = Path(pdf_path)
    labels = load_cycle_info()
    label = label_for_pdf(pdf_path)
    if label:
        labels[pdf_path.name] = label
    else:
        labels.pop(pdf_path.name, None)
    save_cycle_info(labels)
    return label


def forget_cycles(filenames):
    labels = load_cycle_info()
    changed = False
    for name in filenames:
        if labels.pop(name, None) is not None:
            changed = True
    if changed:
        save_cycle_info(labels)


def refresh_all(data_dir=DATA_DIR):
    """Rebuild the JSON from every PDF. Used when the label format changes."""
    labels = {}
    pdfs = sorted(Path(data_dir).glob('*.pdf'))
    for pdf in pdfs:
        label = label_for_pdf(pdf)
        if label:
            labels[pdf.name] = label
    save_cycle_info(labels)
    return labels
