#!/usr/bin/env python3
"""SVE locations importer (cache/wiki_sve/Locations.json, https://stardewvalleyexpanded.wiki.gg/wiki/Locations).
  location        one row per table row on the Locations page; category = the == / === heading it sits under
                  (page order kept in `sort`), name = link display text, picture = the row's [[File:...]],
                  description_en = first sentence of the row's Description, else of the location's own cached page.
                  EXTRA rows: SVE places named in fish.locations that the Locations page does not list
                  (own cached page, category = the page heading of the place it sits in).
  location_alias  fish.locations spellings that differ from location.name_en.
  image           img_loc_<slug> (wiki_sve, pending -> download_images.py)
Vanilla maps that SVE only changes (Pelican Town, Cindersap Forest, Secret Woods) get content_pack 'vanilla'.
Prints every fish.locations string that maps to no location row.
Output: data/{location,location_alias,image,entity_source}.locations.json"""
import glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from wikitext import ROOT, safe, slug, src, clean, write_fragments

SVE_CACHE = os.path.join(ROOT, 'cache', 'wiki_sve')
SVE_WIKI = 'https://stardewvalleyexpanded.wiki.gg/wiki/'
VANILLA = {'Pelican Town', 'Cindersap Forest', 'Secret Woods'}
# places that are not on the Locations page: name -> category (heading of the place they belong to)
EXTRA = {'Junimo Woods': 'Cindersap Forest', "Henchman's Backyard": 'The Railroad'}
ALIAS = {"Adventurer's Summit": 'Adventurer Summit', 'Highlands': 'The Highlands',
         'Blue Moon Vineyard River': 'Blue Moon Vineyard', 'Forest West (Summer)': 'Forest West',
         'Highlands Cavern': 'Crystal Cavern', 'Pelican Town River': 'Pelican Town', 'Town River': 'Pelican Town',
         'Cindersap Forest (Pond)': 'Cindersap Forest', 'Cindersap Forest Waterfalls': 'Cindersap Forest',
         'Forest Pond': 'Cindersap Forest', 'Forest River': 'Cindersap Forest'}   # Crystal Cavern infobox image = 'Highlands Cavern'


def sve_page(title):
    p = os.path.join(SVE_CACHE, safe(title) + '.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None


def sve_src(etype, eid, pg):
    s = src(etype, eid, pg); s.update(source_id='wiki_sve', url=SVE_WIKI + pg['title'].replace(' ', '_')); return s


def first_sentence(text):
    t = clean(text)
    if not t: return None
    t = re.sub(r'\s*•\s*', ' ', t).strip()
    m = re.match(r'(.+?[.!?])(?:\s|$)', t)
    return (m.group(1) if m else t).strip()


def page_sentence(pg):
    if not pg: return None
    wt = pg['wikitext'].replace('{{PAGENAME}}', pg['title'])
    wt = re.sub(r'\{\{(?:[Cc]onstruction|TOC[^}]*)\}\}', '', wt)
    i = wt.find('Location Infobox')
    if i >= 0:                       # skip past the infobox's closing }}
        j = wt.find('\n}}', i); wt = wt[j + 3:] if j >= 0 else wt
    body = wt.split('\n==')[0]
    for para in body.split('\n'):
        para = para.strip()
        if para and not para.startswith(('{|', '[[File', '{{', '<br', '[[Category')):
            return first_sentence(para)
    return None


def infobox_image(pg):
    m = re.search(r'\|\s*image\s*=\s*([^\n|]+)', pg['wikitext']) if pg else None
    if not m or not m.group(1).strip(): return None
    f = m.group(1).strip()
    return f if f.lower().endswith('.png') else f + '.png'


def main():
    pg = sve_page('Locations')
    if not pg: sys.exit('cache/wiki_sve/Locations.json missing - fetch it with fetch_wiki.py')
    R = {'location': [], 'location_alias': [], 'image': [], 'entity_source': []}
    rows, cat, sort = [], None, 0
    for block in re.split(r'\n(?===)', pg['wikitext']):
        h = re.match(r'(=+)\s*(.+?)\s*\1', block)
        if h: cat = h.group(2)
        for row in re.split(r'\n\|-', block)[1:]:
            f = re.search(r'\[\[File:\s*([^|\]]+)', row)
            n = re.search(r'^\|\s*\[\[(?!File:)([^\]|]+)(?:\|([^\]]+))?\]\]\s*$', row, re.M)
            if not (f and n): continue
            desc = row[n.end():].lstrip('\n')
            desc = re.sub(r'^\|', '', desc).split('\n|}')[0]
            sort += 10
            rows.append({'name': (n.group(2) or n.group(1)).strip(), 'target': n.group(1).strip(), 'file': f.group(1).strip(),
                         'cat': cat, 'sort': sort, 'desc': desc, 'pg': pg})
    cats = {r['name']: r['cat'] for r in rows}
    for name, near in EXTRA.items():
        p = sve_page(name)
        if not p: sys.exit(f'no cached page for {name}')
        img = infobox_image(p)   # no infobox -> no picture (other files on the page are shrine icons, not the place)
        sort += 10
        rows.append({'name': name, 'target': name, 'file': img, 'cat': cats.get(near, near), 'sort': sort, 'desc': '', 'pg': p})

    for r in rows:
        lid = slug(r['name']); own = sve_page(r['target'])
        d = first_sentence(r['desc']) if r['desc'].strip() and not r['desc'].strip().startswith('Additions') else None
        dpg = r['pg']
        if not d and own and own['title'] == r['name']:
            d = page_sentence(own); dpg = own if d else dpg
        iid = None
        if r['file']:
            iid = f'img_loc_{lid}'
            R['image'].append({'id': iid, 'file_path': None, 'origin': 'wiki', 'source_id': 'wiki_sve',
                               'source_url': SVE_WIKI + 'File:' + r['file'].replace(' ', '_'), 'status': 'pending'})
            R['entity_source'].append(sve_src('image', iid, r['pg']))
        R['location'].append({'id': lid, 'name_en': r['name'], 'name_th': None, 'category': r['cat'], 'sort': r['sort'],
                              'image_id': iid, 'description_en': d,
                              'content_pack': 'vanilla' if r['name'] in VANILLA else 'sve'})
        R['entity_source'].append(sve_src('location', lid, r['pg']))
        if dpg is not r['pg']: R['entity_source'].append(sve_src('location', lid, dpg))

    ids = {l['name_en'].lower(): l['id'] for l in R['location']}
    for a, n in ALIAS.items():
        R['location_alias'].append({'alias': a, 'location_id': ids[n.lower()]})
    write_fragments('locations', R)

    amap = {a.lower(): x['location_id'] for x in R['location_alias'] for a in [x['alias']]}
    fish_locs = set()
    for p in glob.glob(os.path.join(ROOT, 'data', 'fish*.json')):
        for r in json.load(open(p, encoding='utf-8')):
            l = r.get('locations'); l = json.loads(l) if isinstance(l, str) else l
            if isinstance(l, dict): l = l.get('default') or []
            fish_locs.update(l or [])
    unmapped = sorted(s for s in fish_locs if s.lower() not in ids and s.lower() not in amap)
    print('categories:'); seen = {}
    for l in R['location']: seen[l['category']] = seen.get(l['category'], 0) + 1
    for c, k in seen.items(): print(f'  {c}: {k}')
    print('unmapped fish locations:', unmapped)


if __name__ == '__main__':
    main()
