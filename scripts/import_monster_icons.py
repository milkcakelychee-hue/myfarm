#!/usr/bin/env python3
"""Monster icons: for every vanilla monster page in the cache, take the first static PNG referenced in its
Infobox monster (the portrait is often an animated GIF, so the first [[File:X.png]] in the stat rows is the
base sprite, e.g. Bats -> Bat.png). Writes pending rows to data/image.monsters.json + entity_source.monsters.json;
import_nature.py then sets monster.image_id = img_<id>, and download_images.py fetches the files.
Usage: python3 scripts/import_monster_icons.py && python3 scripts/import_nature.py && python3 scripts/download_images.py && python3 scripts/build_db.py"""
import json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, 'cache', 'wiki_official')
WIKI = 'https://stardewvalleywiki.com/'
slug = lambda t: re.sub(r'[^a-z0-9]+', '_', t.lower()).strip('_')
img, src, missing = [], [], []
for f in sorted(os.listdir(CACHE)):
    pg = json.load(open(os.path.join(CACHE, f), encoding='utf-8'))
    w = pg.get('wikitext') or ''
    m = re.search(r'\{\{Infobox monster(.*?)\n\}\}', w, re.S)
    if not m: continue
    box = m.group(1)
    portrait = re.search(r'\|\s*portrait\s*=\s*([^\n|]+\.png)', box, re.I)
    files = [portrait.group(1).strip()] if portrait else []
    files += [x.strip() for x in re.findall(r'\[\[File:([^|\]]+\.png)', box, re.I)]
    mid = slug(pg['title'])
    if not files:                      # fallback: the wiki's usual sprite name ("Grub.png", "Grub Dangerous.png")
        t = pg['title']
        files = [re.sub(r'\s*\(dangerous\)', ' Dangerous', t) + '.png']
        missing.append(t)
    name = files[0].replace(' ', '_')
    img.append({'id': f'img_{mid}', 'file_path': None, 'origin': 'wiki', 'source_id': 'wiki_official', 'source_url': WIKI + 'File:' + name, 'status': 'pending'})
    src.append({'entity_type': 'image', 'entity_id': f'img_{mid}', 'source_id': 'wiki_official', 'page_title': pg['title'], 'url': WIKI + pg['title'].replace(' ', '_'),
                'revision_ts': pg.get('timestamp'), 'revision_id': pg.get('revid'), 'accessed_at': pg.get('accessed_at'), 'confidence': 'medium', 'verified': False})
json.dump(img, open(os.path.join(ROOT, 'data', 'image.monsters.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(src, open(os.path.join(ROOT, 'data', 'entity_source.monsters.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(img), 'monster icons; guessed file name (no PNG in infobox):', len(missing))
