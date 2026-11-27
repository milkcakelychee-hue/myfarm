#!/usr/bin/env python3
"""Nature importer: fish, animal, monster tables + item_location for fish, forage, minerals and gems.
Output: data/{fish,animal,monster,item_location,entity_source}.nature.json
Rules: values are taken only when the page states them unambiguously; anything else stays NULL.
Usage: python3 scripts/import_nature.py"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from wikitext import ROOT, all_pages, infobox, infobox_type, clean, seasons_in, slug, src, write_fragments, icon_ids
ICONS = icon_ids()

ITEMS = {i['id']: i for i in json.load(open(os.path.join(ROOT, 'data', 'item.items.json'), encoding='utf-8'))}
IMAGES = {i['id'] for f in ('image.json', 'image.items.json')
          for i in json.load(open(os.path.join(ROOT, 'data', f), encoding='utf-8'))}
skipped = []


def item_ref(name, ctx):
    iid = slug(name)
    if iid in ITEMS: return iid
    skipped.append(f'{ctx}: {name}')
    return None


def split_list(v):
    """Wikitext list value -> cleaned names. Uses {{Name|...}} targets if present, else splits on • / & / ,."""
    if not v: return []
    v = v.replace('{{!}}', '|')
    names = re.findall(r'\{\{[Nn]ame\|([^|}]+)', v)
    if names: return [re.sub(r' Icon$', '', n).strip() for n in names]
    c = clean(v) or ''
    return [re.sub(r'^and ', '', p.strip()) for p in re.split(r'•|&amp;|&|,', c) if p.strip()]


def clock(t):
    m = re.fullmatch(r'(\d{1,2})\s*(am|pm)', t.strip().lower())
    if not m: return None
    h = int(m.group(1)) % 12 + (12 if m.group(2) == 'pm' else 0)
    return h * 100


def times(v):
    c = clean(v) if v else None
    if not c: return None, None
    if c == 'Any': return 600, 2600
    m = re.fullmatch(r'(\S+)\s*[–-]\s*(\S+)', c)
    if not m: return None, None
    a, b = clock(m.group(1)), clock(m.group(2))
    if a is None or b is None: return None, None
    if b <= a: b += 2400
    return a, b


def fish_seasons(v):
    if not v: return None
    c = clean(v)
    plain = re.fullmatch(r'(?:(?:Spring|Summer|Fall|Winter|All Seasons|All seasons)\s*(?:•\s*)?)+', c or '')
    if plain: return json.dumps(seasons_in(c))
    first = v.strip().split('\n')[0]
    return json.dumps({'default': seasons_in(clean(first)), 'raw': c}, ensure_ascii=False)


def int_only(v):
    c = clean(v) if v else None
    return int(c.replace(',', '')) if c and re.fullmatch(r'\d[\d,]*', c) else None


def main():
    R = {'fish': [], 'animal': [], 'monster': [], 'item_location': [], 'entity_source': []}
    for pg in all_pages():
        wt = pg['wikitext']; box = infobox_type(wt); ib = infobox(wt)
        if box == 'Infobox fish':
            name = clean(ib.get('eng') or ib.get('name')) or pg['title']
            iid = item_ref(name, 'fish')
            if not iid: continue
            locs = split_list(ib.get('location'))
            ts, te = times(ib.get('time'))
            R['fish'].append({'item_id': iid, 'locations': json.dumps(locs, ensure_ascii=False) if locs else None,
                              'seasons': fish_seasons(ib.get('season')), 'weather': clean(ib.get('weather')),
                              'time_start': ts, 'time_end': te, 'difficulty': int_only(ib.get('difficulty')),
                              'behavior': clean(ib.get('behavior'))})
            R['item_location'] += [{'item_id': iid, 'location': l} for l in locs]
            R['entity_source'].append(src('fish', iid, pg))
            if locs: R['entity_source'].append(src('item_location', iid, pg))
        elif box == 'Infobox animal':
            aid = slug(pg['title']); notes = []
            b = split_list(ib.get('building'))
            bname = b[0] if b else ''
            building = 'Coop' if 'Coop' in bname else 'Barn' if 'Barn' in bname else 'Other'
            level = 3 if bname.startswith('Deluxe') else 2 if bname.startswith('Big') else 1 if bname in ('Coop', 'Barn') else None
            prod = split_list(ib.get('produce'))
            regular = [p for p in prod if not p.startswith('Large ')]
            large = [p for p in prod if p.startswith('Large ')]
            text = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', wt)
            # regular produce: the item named in "produces [[X]] every ..." (else the first non-Large infobox item);
            # deluxe produce: "may produce a [[X]] instead" (Rabbit's Foot, Duck Feather), else the first "Large " item
            m = re.search(r'produces (?:an? |a white or brown )?\[\[([^\]|]+)(?:\|[^\]]*)?\]\]s? every', wt)
            reg_name = m.group(1) if m else (regular[0] if regular else None)
            m = re.search(r'may produce an? \[\[([^\]|]+)(?:\|[^\]]*)?\]\] instead', wt)
            dlx_name = m.group(1) if m else (large[0] if large else None)
            produce = item_ref(reg_name, f'animal {aid}') if reg_name else None
            deluxe = item_ref(dlx_name, f'animal {aid}') if dlx_name else None
            if len(prod) > 1: notes.append('produce listed: ' + ', '.join(prod))
            m = re.search(r'mature after (\d+) nights', text)
            mature = int(m.group(1)) if m else None
            pd = None
            m = re.search(r'(?:produces|grows in its coat)[^.\n]*?every (\d+ days|day)\b', text)
            if m: pd = 1 if m.group(1) == 'day' else int(m.group(1).split()[0])
            img = f'img_animal_{aid}' if f'img_animal_{aid}' in ICONS else (f'img_{aid}' if f'img_{aid}' in IMAGES else None)
            R['animal'].append({'id': aid, 'name_en': pg['title'], 'name_th': None, 'building': building,
                                'building_level': level, 'price': int_only(ib.get('buyprice')),
                                'produce_item_id': produce, 'deluxe_item_id': deluxe, 'produce_days': pd,
                                'mature_days': mature, 'image_id': img, 'notes': '; '.join(notes) or None})
            R['entity_source'].append(src('animal', aid, pg))
        elif box == 'Infobox monster':
            mid = slug(pg['title'])
            drops = [{'item': n, 'chance': c} for n, c in re.findall(r'\{\{[Nn]ame\|([^|}]+)\|([\d.]+%)\}\}', ib.get('drops') or '')]
            locs = split_list(ib.get('location'))
            R['monster'].append({'id': mid, 'name_en': pg['title'], 'name_th': None,
                                 'hp': int_only(ib.get('hp')), 'damage': int_only(ib.get('dmg')),
                                 'defense': int_only(ib.get('def')), 'speed': int_only(ib.get('spd')),
                                 'xp': int_only(ib.get('exp')),
                                 'locations': json.dumps(locs, ensure_ascii=False) if locs else None,
                                 'drops': json.dumps(drops, ensure_ascii=False) if drops else None,
                                 'image_id': f'img_{mid}' if f'img_{mid}' in IMAGES else None})
            R['entity_source'].append(src('monster', mid, pg))
        elif box in ('Infobox', 'Infobox mineral'):
            name = clean(ib.get('eng') or ib.get('name')) or pg['title']
            iid = slug(name)
            if ITEMS.get(iid, {}).get('category') not in ('Forage', 'Mineral', 'Gem'): continue
            locs = split_list(ib.get('location') or ib.get('source'))
            R['item_location'] += [{'item_id': iid, 'location': l} for l in locs]
            if locs: R['entity_source'].append(src('item_location', iid, pg))
    write_fragments('nature', R)
    print('skipped (unknown item):', sorted(set(skipped)) or 'none')


if __name__ == '__main__':
    main()
