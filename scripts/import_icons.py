#!/usr/bin/env python3
"""Icons importer: image rows for every non-item icon slot in the app.
  img_map_sve                         SVE map picture (Locations page, wiki_sve)
  img_building_<building.id>          building infobox image / File:<Name>.png on Carpenter's Shop, Wizard's Tower, own page
  img_npc_<npc.id>                    villager infobox portrait (vanilla wiki_official, SVE wiki_sve 'image = X' -> File:X.png)
  img_animal_<animal.id>              animal infobox image
  img_quality_*, img_season_*, img_weather_*, img_skill_*, img_profession_<profession.id>, img_greenhouse, img_ginger_island
Only file names that appear in the cached wikitext are used (never invented); .gif files are skipped because the
downloader only keeps PNGs (a referenced <Name>.png is used instead when one exists).
The owning importers (import_crafting / import_people / import_sve / import_nature) set image_id from this
fragment via wikitext.icon_ids(), so run this first, then those importers, then download_images.py.
Output: data/{image,entity_source}.icons.json"""
import glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from wikitext import ROOT, WIKI, page, safe, src, infobox, write_fragments

SVE_CACHE = os.path.join(ROOT, 'cache', 'wiki_sve')
SVE_WIKI = 'https://stardewvalleyexpanded.wiki.gg/wiki/'
FILE_RE = re.compile(r'(?:File|Image):\s*([^|\]\n}]+?\.(?:png|gif|jpg))', re.I)

# every file name referenced in the official cache -> first page referencing it
REFS = {}
for f in sorted(glob.glob(os.path.join(ROOT, 'cache', 'wiki_official', '*.json'))):
    pg = json.load(open(f, encoding='utf-8'))
    for m in FILE_RE.finditer(pg['wikitext']):
        REFS.setdefault(m.group(1).strip().replace('_', ' '), pg)

R = {'image': [], 'entity_source': []}
MISSING = []


def norm(f): return f.strip().replace('_', ' ')


def add(iid, fname, pg, source_id='wiki_official'):
    base = WIKI if source_id == 'wiki_official' else SVE_WIKI
    R['image'].append({'id': iid, 'file_path': None, 'origin': 'wiki', 'source_id': source_id,
                       'source_url': base + 'File:' + norm(fname).replace(' ', '_'), 'status': 'pending'})
    s = src('image', iid, pg)
    if source_id != 'wiki_official':
        s.update(source_id=source_id, url=SVE_WIKI + pg['title'].replace(' ', '_'))
    R['entity_source'].append(s)


def official(iid, candidates, prefer_pages=()):
    """First candidate that is a PNG referenced in the cache; prefer a page from prefer_pages as provenance."""
    for c in candidates:
        if not c: continue
        c = norm(c)
        if not c.lower().endswith('.png'): continue
        for t in prefer_pages:
            pg = page(t)
            if pg and c in {norm(x) for x in FILE_RE.findall(pg['wikitext'])} | {norm(v) for v in infobox(pg['wikitext']).values()}:
                add(iid, c, pg); return c
        if c in REFS: add(iid, c, REFS[c]); return c
    MISSING.append(iid); return None


def sve_page(title):
    p = os.path.join(SVE_CACHE, safe(title) + '.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None


def load(name): return json.load(open(os.path.join(ROOT, 'data', name), encoding='utf-8'))


def main():
    # 1. SVE map: no cached SVE page shows a whole-valley map; the Locations page's Pelican Town (SVE) picture is the only map image.
    pg = sve_page('Locations')
    m = re.search(r'\[\[File:([^|\]]+)\|[^\]]*alt=Pelican Town in Expanded', pg['wikitext'])
    if not m: sys.exit('Locations: SVE map file not found')
    add('img_map_sve', m.group(1), pg, 'wiki_sve')

    # 2. buildings (all vanilla)
    for b in load('building.crafting.json'):
        n = b['name_en']; pg = page(n); ib = infobox(pg['wikitext']) if pg else {}
        official(f'img_building_{b["id"]}', [ib.get('image'), n + '.png'], [n, "Carpenter's Shop", "Wizard's Tower"])

    # 3. NPCs
    for f in ('npc.people.json', 'npc.sve.json'):
        for n in load(f):
            iid, name = f'img_npc_{n["id"]}', n['name_en']
            if n['content_pack'] == 'sve':
                pg = sve_page(name)
                wt = pg['wikitext'] if pg else ''
                m = re.search(r'^\s*\|\s*image\s*=\s*(.+?)\s*$', wt[wt.find('Character Infobox'):], re.M) if 'Character Infobox' in wt else None
                if not m or name == 'Wiki Style Guide NPC': MISSING.append(iid); continue
                fn = m.group(1) if m.group(1).lower().endswith('.png') else m.group(1) + '.png'
                add(iid, fn, pg, 'wiki_sve')
            else:
                pg = page(name); ib = infobox(pg['wikitext']) if pg else {}
                official(iid, [ib.get('portrait'), ib.get('image'), name + '.png'] + (['Junimo Icon.png'] if n['id'] == 'junimos' else []), [name])  # Junimos portrait is a .gif

    # 4. animals
    for a in load('animal.nature.json'):
        pg = page(a['name_en']); ib = infobox(pg['wikitext']) if pg else {}
        official(f'img_animal_{a["id"]}', [ib.get('image'), a['name_en'] + '.png'], [a['name_en']])

    # 5. small UI icons
    for q in ('Silver', 'Gold', 'Iridium'): official(f'img_quality_{q.lower()}', [f'{q} Quality.png'])
    for s in ('Spring', 'Summer', 'Fall', 'Winter'): official(f'img_season_{s.lower()}', [f'{s}.png'], [s, 'Seasons'])
    official('img_weather_sun', ['StatusSun.png'], ['Weather'])
    official('img_weather_rain', ['StatusRain.png'], ['Weather'])
    for k in ('Farming', 'Fishing', 'Foraging', 'Mining', 'Combat'):
        official(f'img_skill_{k.lower()}', [f'{k} Skill Icon.png'], ['Skills', k])
    for p in load('profession.skills.json'):
        official(f'img_profession_{p["id"]}', [p['name_en'] + '.png'], [f'{p["skill"]} Skill', 'Skills'])
    g = page('Greenhouse'); official('img_greenhouse', [infobox(g['wikitext']).get('image')], ['Greenhouse'])
    gi = page('Ginger Island'); official('img_ginger_island', [infobox(gi['wikitext']).get('building')], ['Ginger Island'])

    write_fragments('icons', R)
    print('no image:', MISSING or 'none')


if __name__ == '__main__':
    main()
