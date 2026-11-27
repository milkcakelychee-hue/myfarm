"""Shared helpers for importers: read cached wikitext, clean templates, slugs, provenance rows, fragment output.
Every importer writes ONLY its own fragment files data/<table>.<importer>.json (build_db.py merges them),
so importers never overwrite each other's rows and can run in any order."""
import json, os, re, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, 'cache', 'wiki_official')
WIKI = 'https://stardewvalleywiki.com/'
SEASONS = ['Spring', 'Summer', 'Fall', 'Winter']


def safe(t): return re.sub(r'[^\w.-]+', '_', t)
def slug(name): return re.sub(r'[^a-z0-9]+', '_', (name or '').lower()).strip('_')


def page(title):
    p = os.path.join(CACHE, safe(title) + '.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None


def all_pages():
    for f in sorted(glob.glob(os.path.join(CACHE, '*.json'))):
        yield json.load(open(f, encoding='utf-8'))


def infobox_type(wt):
    m = re.search(r'\{\{\{?\{?\{?\{?(?:1\|)?(Infobox[ \w]*?)\}*\s*\n', wt)
    return m.group(1).strip() if m else None


def infobox(wt):
    """Top-level fields of the first {{Infobox ...}} (handles nested templates and multi-line values)."""
    m = re.search(r'\{\{\{?\{?\{?\{?(?:1\|)?Infobox[ \w]*\}*\s*\n', wt)
    if not m: return {}
    # body = from the first field line up to the line that is exactly '}}' at nesting depth 0
    start, depth, i = m.end(), 0, m.end()
    while i < len(wt):
        if wt.startswith('{{', i): depth += 1; i += 2; continue
        if wt.startswith('}}', i):
            if depth == 0: break
            depth -= 1; i += 2; continue
        i += 1
    body = wt[start:i]
    out = {}
    j = 0
    # split on '|' at nesting depth 0
    parts, buf, depth = [], [], 0
    while j < len(body):
        two = body[j:j + 2]
        if two in ('{{', '[['): depth += 1; buf.append(two); j += 2; continue
        if two in ('}}', ']]'): depth -= 1; buf.append(two); j += 2; continue
        if body[j] == '|' and depth == 0: parts.append(''.join(buf)); buf = []; j += 1; continue
        buf.append(body[j]); j += 1
    parts.append(''.join(buf))
    for p in parts:
        k = re.match(r'\s*([\w-]+)\s*=(.*)', p, re.S)
        if k: out[k.group(1)] = k.group(2).strip()
    return out


def clean(v):
    """Wikitext -> plain text. {{Name|X|n}} -> 'X', {{Price|N}} -> 'Ng', [[a|b]] -> b, strips refs/html."""
    if v is None: return None
    v = re.sub(r'<ref[^>]*/>|<ref[^>]*>.*?</ref>', '', v, flags=re.S)
    v = re.sub(r'<br\s*/?>', ' • ', v)
    v = re.sub(r'<[^>]+>', '', v)
    for _ in range(4):
        v = re.sub(r'\{\{(?:Name|name)\|([^|}]+)\|(\d+)[^}]*\}\}', r'\1 ×\2', v)
        v = re.sub(r'\{\{(?:Name|name|Season|season|Bundle|NPC|Villager)\|([^|}]+)[^}]*\}\}', r'\1', v)
        v = re.sub(r'\{\{(?:Price|price|Tprice)\|([\d,]+)[^}]*\}\}', r'\1g', v)
        v = re.sub(r'\{\{[^{}|]+\|([^{}|]+)\}\}', r'\1', v)
        v = re.sub(r'\{\{[^{}]*\}\}', '', v)
    v = re.sub(r'\[\[(?:File|Image):[^\]]*\]\]', '', v)
    v = re.sub(r'\[\[[^\]|]*\|([^\]]*)\]\]', r'\1', v)
    v = re.sub(r'\[\[([^\]]*)\]\]', r'\1', v)
    v = re.sub(r"'''?", '', v)
    return re.sub(r'\s+', ' ', v).strip() or None


def first_int(v):
    m = re.search(r'-?\d[\d,]*', v or '')
    return int(m.group(0).replace(',', '')) if m else None


def seasons_in(v):
    v = v or ''
    if re.search(r'All Seasons|All seasons|Any Season', v): return SEASONS[:]
    return [s for s in SEASONS if s in v]


def names_in(v):
    """All {{Name|X}} targets (or [[X]] links) inside a wikitext value, in order, with optional quantity."""
    out = []
    for m in re.finditer(r'\{\{[Nn]ame\|([^|}]+)(?:\|(\d+))?[^}]*\}\}', v or ''):
        out.append((m.group(1).strip(), int(m.group(2)) if m.group(2) else 1))
    return out


def categories(wt): return re.findall(r'\[\[Category:([^\]|]+)', wt)


def src(entity_type, entity_id, pg, confidence='medium'):
    return {'entity_type': entity_type, 'entity_id': entity_id, 'source_id': 'wiki_official', 'page_title': pg['title'],
            'url': WIKI + pg['title'].replace(' ', '_'), 'revision_ts': pg['timestamp'], 'revision_id': pg['revid'],
            'accessed_at': pg['accessed_at'], 'confidence': confidence, 'verified': False}


def write_fragments(importer, tables):
    """tables = {table_name: [rows]} -> data/<table>.<importer>.json (deduped by full row key order)."""
    for t, rows in tables.items():
        seen, out = set(), []
        for r in rows:
            k = json.dumps(r, sort_keys=True, ensure_ascii=False)
            if k not in seen: seen.add(k); out.append(r)
        p = os.path.join(ROOT, 'data', f'{t}.{importer}.json')
        with open(p, 'w', encoding='utf-8') as f:
            f.write('[\n' + ',\n'.join(' ' + json.dumps(r, ensure_ascii=False) for r in out) + '\n]\n')
        print(f'{t}.{importer}.json  {len(out)} rows')


def icon_ids():
    """Image ids written by import_icons.py (data/image.icons.json); owning importers set image_id from these."""
    p = os.path.join(ROOT, 'data', 'image.icons.json')
    return {r['id'] for r in json.load(open(p, encoding='utf-8'))} if os.path.exists(p) else set()
