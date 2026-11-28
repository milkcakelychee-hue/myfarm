#!/usr/bin/env python3
"""place_icon: pictures for 'where to find' names that are not an item/monster/location in the database
(e.g. "Garbage Can", "Volcano Dungeon"). Each row names the wiki file it comes from (checked to exist on
stardewvalleywiki.com on 2026-11-28); download_images.py fetches them as img_place_<slug>.
Activity names (Fishing, Foraging, Mining, Tilling, Monster drop) reuse the skill icons already in the DB.
Usage: python3 scripts/import_place_icons.py && python3 scripts/download_images.py && python3 scripts/build_db.py"""
import json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI = 'https://stardewvalleywiki.com/'
slug = lambda t: re.sub(r'[^a-z0-9]+', '_', t.lower()).strip('_')
FILES = {   # display name in item_location  ->  wiki file
    'Copper Pan': 'Copper Pan.png', 'Garbage Can': 'Garbage Can.png', 'Frost Jelly': 'Frost Jelly.png',
    'Meteorite': 'Meteorite.png', 'Mystery Box': 'Mystery Box.png', 'Supply Crate': 'Supply Crate 1.png',
    'Statue Of Endless Fortune': 'Statue Of Endless Fortune.png', 'Statue Of True Perfection': 'Statue Of True Perfection.png',
    'Farm Cave': 'Cave Entrance.png', 'Trout Derby': 'Trout Derby.png', 'Volcano Dungeon': 'VolcanoDungeon Entryway.png',
}
SKILL = {'Fishing': 'img_skill_fishing', 'Foraging': 'img_skill_foraging', 'Mining': 'img_skill_mining', 'Panning': None,
         'Tilling': 'img_skill_farming', 'Monster drop': 'img_skill_combat'}
img, rows, src = [], [], []
for name, f in FILES.items():
    iid = f'img_place_{slug(name)}'
    img.append({'id': iid, 'file_path': None, 'origin': 'wiki', 'source_id': 'wiki_official', 'source_url': WIKI + 'File:' + f.replace(' ', '_'), 'status': 'pending'})
    rows.append({'name_en': name, 'image_id': iid})
    src.append({'entity_type': 'image', 'entity_id': iid, 'source_id': 'wiki_official', 'page_title': 'File:' + f, 'url': WIKI + 'File:' + f.replace(' ', '_'),
                'revision_ts': None, 'revision_id': None, 'accessed_at': '2026-11-28', 'confidence': 'medium', 'verified': False})
rows += [{'name_en': k, 'image_id': v} for k, v in SKILL.items() if v]
rows.append({'name_en': 'Panning', 'image_id': 'img_place_copper_pan'})
for p, data in (('image.places.json', img), ('place_icon.places.json', rows), ('entity_source.places.json', src)):
    json.dump(data, open(os.path.join(ROOT, 'data', p), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(img), 'images,', len(rows), 'place_icon rows')
