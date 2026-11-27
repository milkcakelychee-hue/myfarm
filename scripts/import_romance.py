#!/usr/bin/env python3
"""npc_romance: marriage candidates split into bachelor / bachelorette.
Vanilla: wiki Marriage page, sections "Bachelors" and "Bachelorettes" (cache/wiki_official/Marriage.json).
SVE: the SVE wiki Villagers page lists marriage candidates without a split, so the owner (Blue) set them on 2026-11-27
(source 'owner'). Writes data/npc_romance.romance.json and data/entity_source.romance.json.
Usage: python3 scripts/import_romance.py && python3 scripts/build_db.py"""
import json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
page = json.load(open(os.path.join(ROOT, 'cache/wiki_official/Marriage.json'), encoding='utf-8'))
t = page['wikitext']
a = t.index('Bachelors'); b = t.index('Bachelorettes', a); c = t.index('\n==', b + 20)
names = lambda s: sorted(set(re.findall(r'\[\[([A-Z][a-z]+)\]\]', s)))
rows, src = [], []
for kind, seg in (('bachelor', t[a:b]), ('bachelorette', t[b:c])):
    for n in names(seg):
        rows.append({'npc_id': n.lower(), 'kind': kind, 'source': 'wiki'})
        src.append({'entity_type': 'npc_romance', 'entity_id': n.lower(), 'source_id': 'wiki_official', 'page_title': 'Marriage',
                    'url': 'https://stardewvalleywiki.com/Marriage', 'revision_ts': page['timestamp'], 'revision_id': page['revid'],
                    'accessed_at': page.get('accessed_at', '2026-11-27'), 'confidence': 'high', 'verified': False})
OWNER = {'claire': 'bachelorette', 'olivia': 'bachelorette', 'scarlett': 'bachelorette', 'sophia': 'bachelorette',
         'lance': 'bachelor', 'magnus': 'bachelor', 'victor': 'bachelor'}
rows += [{'npc_id': k, 'kind': v, 'source': 'owner'} for k, v in OWNER.items()]
json.dump(rows, open(os.path.join(ROOT, 'data/npc_romance.romance.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(src, open(os.path.join(ROOT, 'data/entity_source.romance.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(rows), 'rows')
