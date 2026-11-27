#!/usr/bin/env python3
"""SVE importer (Stardew Valley Expanded wiki, cache/wiki_sve/*.json). Processes whatever pages are cached, so it can
be re-run as the cache grows. Never fetches.
Output: data/{item,image,item_season,crop,crop_season,shop_price,fish,monster,npc,gift_taste,calendar_event,
entity_source}.sve.json -- every item/npc row has content_pack='sve'; pages whose slug already exists as a vanilla
item / npc are skipped ("skipped (vanilla exists)"). References to vanilla things use the vanilla id.
Never guesses: unclear values -> NULL (+ notes where the table has a notes column).
Usage: python3 scripts/import_sve.py"""
import collections, glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from wikitext import ROOT, SEASONS, clean, first_int, seasons_in, slug, write_fragments, icon_ids
ICONS = icon_ids()

CACHE = os.path.join(ROOT, 'cache', 'wiki_sve')
WIKI = 'https://stardewvalleyexpanded.wiki.gg/wiki/'
ITEM_BOXES = {'Item Infobox', 'Cooking Infobox', 'Crafting Infobox', 'Artisan Infobox', 'Seeds Infobox', 'Fish Infobox'}
BOX_CATEGORY = {'Cooking Infobox': 'Cooking', 'Artisan Infobox': 'Artisan Goods', 'Seeds Infobox': 'Seed',
                'Fish Infobox': 'Fish', 'Crafting Infobox': 'Crafting'}
# infobox price field -> shop name (only fields whose value is a plain {{Price|N}})
SHOPS = {'HDwarfPrice': 'Highlands Dwarf', 'OrangeJuniPrice': 'Orange Junimo Shop', 'GuildLedgerPrice': 'Adventurer Ledger',
         'CamillaPrice': 'Camilla', 'AlesiaPrice': 'Alesia', 'IsaacPrice': 'Isaac', 'SophiaPrice': 'Sophia',
         'jePrice': 'Joja Emporium', 'tPrice': 'Traveling Cart', 'gPrice': "Pierre's General Store", 'jPrice': 'JojaMart'}
TABS = {'Loves': 'love', 'Likes': 'like', 'Neutrals': 'neutral', 'Neutral': 'neutral', 'Dislikes': 'dislike', 'Hates': 'hate'}


def src(entity_type, entity_id, pg, confidence='medium'):
    return {'entity_type': entity_type, 'entity_id': entity_id, 'source_id': 'wiki_sve', 'page_title': pg['title'],
            'url': WIKI + pg['title'].replace(' ', '_'), 'revision_ts': pg['timestamp'], 'revision_id': pg['revid'],
            'accessed_at': pg['accessed_at'], 'confidence': confidence, 'verified': False}


def box_of(wt):
    m = re.search(r'\{\{+\s*(?:1\|)?([\w ]*Infobox)\}*\s*\n', wt)
    if not m: return None, {}
    start, depth, i = m.end(), 0, m.end()
    while i < len(wt):
        if wt.startswith('{{', i): depth += 1; i += 2; continue
        if wt.startswith('}}', i):
            if depth == 0: break
            depth -= 1; i += 2; continue
        i += 1
    body, parts, buf, depth, j = wt[start:i], [], [], 0, 0
    while j < len(body):
        two = body[j:j + 2]
        if two in ('{{', '[['): depth += 1; buf.append(two); j += 2; continue
        if two in ('}}', ']]'): depth -= 1; buf.append(two); j += 2; continue
        if body[j] == '|' and depth == 0: parts.append(''.join(buf)); buf = []; j += 1; continue
        buf.append(body[j]); j += 1
    parts.append(''.join(buf))
    out = {}
    for p in parts:
        k = re.match(r'\s*([\w -]+?)\s*=(.*)', p, re.S)
        if k: out[k.group(1)] = k.group(2).strip()
    return m.group(1).strip(), out


def sve_clean(v):
    if v is None: return None
    v = re.sub(r'\{\{(?:NameSDV|NPCVanilla|NPC)\|([^|}]+)[^}]*\}\}', r'\1', v)
    v = re.sub(r'\[\[Stardew:([^\]|]+)\|([^\]]*)\]\]', r'\2', v)
    v = re.sub(r'\[\[Stardew:([^\]]+)\]\]', r'\1', v)
    return clean(v)


def plain_int(v):
    """'{{Price|400}}' / '400' / '{{Qualityprice|X|55}}' -> int; anything else None."""
    v = (v or '').strip()
    m = re.fullmatch(r'\{\{[Pp]rice\|([\d,]+)\}\}|([\d,]+)|\{\{Qualityprice\|[^|}]+\|([\d,]+)\}\}', v)
    if not m: return None
    return int(next(g for g in m.groups() if g).replace(',', ''))


def hhmm(t):
    m = re.fullmatch(r'(\d{1,2}):(\d\d)\s*(am|pm)', t.strip().lower())
    if not m: return None
    h = int(m.group(1)) % 12 + (12 if m.group(3) == 'pm' else 0)
    if m.group(3) == 'am' and int(m.group(1)) in (1, 2) : h += 24   # 1-2 am = end of game day (2500/2600)
    return h * 100 + int(m.group(2))


def main():
    vitems = {r['id'] for r in json.load(open(os.path.join(ROOT, 'data', 'item.items.json'), encoding='utf-8'))}
    vnpcs = {r['id'] for r in json.load(open(os.path.join(ROOT, 'data', 'npc.people.json'), encoding='utf-8'))}
    pages = [json.load(open(f, encoding='utf-8')) for f in sorted(glob.glob(os.path.join(CACHE, '*.json')))]
    R = {k: [] for k in ('item', 'image', 'item_season', 'crop', 'crop_season', 'shop_price', 'fish', 'monster', 'npc',
                         'gift_taste', 'calendar_event', 'entity_source')}
    skipped = collections.defaultdict(list)
    parsed = [(pg,) + box_of(pg['wikitext']) for pg in pages]

    # ---- pass 1: id sets
    sitems = {slug(pg['title']) for pg, b, _ in parsed if b in ITEM_BOXES} - vitems
    snpcs = {slug(pg['title']) for pg, b, _ in parsed if b == 'Character Infobox'} - vnpcs
    all_items, all_npcs = vitems | sitems, vnpcs | snpcs

    def item_ref(name):
        i = slug(name)
        return i if i in all_items else None

    seed_info = {}  # crop item id -> (seed page, ib)
    item_pages = {}
    for pg, box, ib in parsed:
        t = pg['title']; wt = pg['wikitext']
        if wt.lstrip().upper().startswith('#REDIRECT'): skipped['redirect'].append(t); continue
        if box in ITEM_BOXES:
            iid = slug(t)
            if iid in vitems: skipped['vanilla exists (item)'].append(t); continue
            item_pages[iid] = (pg, box, ib)
            sp = ib.get('Sell Price'); price = plain_int(sp) if sp else None
            if price is None and box == 'Fish Infobox': price = plain_int(ib.get('base'))
            if price is None and not sp: price = plain_int(ib.get('dsvprice'))   # no 'Sell Price' field: data value
            cat = BOX_CATEGORY.get(box) or sve_clean(ib.get('Type')) or None
            ed = ib.get('Edibility'); edv = int(ed) if ed and re.fullmatch(r'-?\d+', ed.strip()) else None
            img = (sve_clean(ib.get('image')) or t).replace(' ', '_')
            R['image'].append({'id': f'img_sve_{iid}', 'file_path': None, 'origin': 'wiki', 'source_id': 'wiki_sve',
                               'source_url': f'{WIKI}File:{img}.png', 'status': 'pending'})
            R['item'].append({'id': iid, 'name_en': t, 'name_th': None, 'name_th_status': 'none', 'category': cat,
                              'sell_price': price, 'edibility': edv, 'description_en': None, 'image_id': f'img_sve_{iid}',
                              'content_pack': 'sve', 'is_approx': 0})
            R['entity_source'] += [src('item', iid, pg), src('image', f'img_sve_{iid}', pg)]
            if box != 'Seeds Infobox':
                R['item_season'] += [{'item_id': iid, 'season': s} for s in seasons_in(sve_clean(ib.get('Season')))]
            else:
                c = sve_clean(ib.get('Crop'))
                if c: seed_info[slug(c)] = (pg, iid, ib)
            for k, shop in SHOPS.items():
                v = ib.get(k)
                if not v or 'Not sold' in v: continue
                m = re.fullmatch(r'\{\{[Pp]rice\|([\d,]+)\}\}', v.strip())
                if not m: skipped['shop price not a plain {{Price}}'].append(f'{t} {k}={v.strip()}'); continue
                R['shop_price'].append({'item_id': iid, 'shop': shop, 'price': int(m.group(1).replace(',', '')),
                                        'currency': 'g', 'condition': ''})
                R['entity_source'].append(src('shop_price', f'{iid}@{shop}', pg))
            if box == 'Fish Infobox':
                tm = sve_clean(ib.get('Time')) or ''
                rng = re.fullmatch(r'(.+?)\s*[-–]\s*(.+)', tm)
                ts, te = (hhmm(rng.group(1)), hhmm(rng.group(2))) if rng else (None, None)
                locs = [sve_clean(x) for x in re.split(r'<br\s*/?>', ib.get('Location') or '') if sve_clean(x)]
                ss = seasons_in(sve_clean(ib.get('Season')))
                R['fish'].append({'item_id': iid, 'locations': json.dumps(locs) if locs else None,
                                  'seasons': json.dumps(ss) if ss else None, 'weather': sve_clean(ib.get('Weather')),
                                  'time_start': ts, 'time_end': te, 'difficulty': first_int(ib.get('Difficulty')),
                                  'behavior': sve_clean(ib.get('Behavior'))})
                R['entity_source'].append(src('fish', iid, pg))
        elif box == 'Character Infobox':
            nid = slug(t)
            if nid in vnpcs: skipped['vanilla exists (npc)'].append(t); continue
            b = re.fullmatch(r'\{\{Season\|(\w+)\}\}\s*(\d+)', (ib.get('Birthday') or '').strip())
            season, day = (b.group(1), int(b.group(2))) if b and b.group(1) in SEASONS and 1 <= int(b.group(2)) <= 28 else (None, None)
            status = sve_clean(ib.get('Status')) or ''
            R['npc'].append({'id': nid, 'name_en': t, 'name_th': None, 'birthday_season': season, 'birthday_day': day,
                             'marriageable': 1 if 'Marriageable' in status else 0, 'image_id': f'img_npc_{nid}' if f'img_npc_{nid}' in ICONS else None, 'content_pack': 'sve'})
            R['entity_source'].append(src('npc', nid, pg))
            if season:
                eid = f'birthday_{nid}'
                R['calendar_event'].append({'id': eid, 'season': season, 'day_start': day, 'day_end': None, 'kind': 'birthday',
                                            'name_en': f"{t}'s Birthday", 'npc_id': nid, 'notes': None})
                R['entity_source'].append(src('calendar_event', eid, pg))
        elif box == 'Monster Infobox':
            mid = slug(t)
            locs = [sve_clean(x) for x in re.split(r'<br\s*/?>|,', ib.get('location') or '') if sve_clean(x)]
            R['monster'].append({'id': mid, 'name_en': t, 'name_th': None, 'hp': plain_int(ib.get('hp')),
                                 'damage': plain_int(ib.get('dmg')), 'defense': plain_int(ib.get('def')),
                                 'speed': plain_int(ib.get('speed')), 'xp': plain_int(ib.get('XP')),
                                 'locations': json.dumps(locs) if locs else None, 'drops': None, 'image_id': None})
            R['entity_source'].append(src('monster', mid, pg))
        elif t == 'Festivals':
            if 'every month on the 22nd day' in wt:
                for name, cond in (('Community Day', 'after completing the Community Center'),
                                   ('Joja Day', 'after completing the Joja Community Development projects')):
                    for s in SEASONS:
                        eid = f'{slug(name)}_{s.lower()}'
                        R['calendar_event'].append({'id': eid, 'season': s, 'day_start': 22, 'day_end': None, 'kind': 'festival',
                                                    'name_en': name, 'npc_id': None,
                                                    'notes': f'SVE festival, only {cond}; Community Day and Joja Day are alternative variants'})
                        R['entity_source'].append(src('calendar_event', eid, pg))
            else: skipped['festival date unclear'].append(t)
        else:
            skipped[f'out of scope ({box or "no infobox"})'].append(t)

    # ---- crops (item page with Seed+Growth+Season; else seeds page with Crop)
    crop_ids = set(item_pages) | set(seed_info)
    for cid in sorted(crop_ids):
        ip = item_pages.get(cid); si = seed_info.get(cid)
        if cid not in sitems: continue
        if ip and ip[1] == 'Seeds Infobox': continue
        if ip and ip[2].get('Growth'): pg, ib, seed = ip[0], ip[2], ip[2].get('Seed')
        elif si and ip: pg, ib, seed = si[0], si[2], si[0]['title']
        else:
            if si and not ip: skipped['crop: harvest item page not cached / vanilla'].append(si[0]['title'])
            continue
        notes = []
        growth = re.fullmatch(r'(\d+)\s*days?', (sve_clean(ib.get('Growth')) or '').strip())
        if not growth: skipped['crop: growth not a plain number of days'].append(f'{pg["title"]}: {ib.get("Growth")}'); continue
        growth = int(growth.group(1))
        if growth > 28: skipped['crop: growth > 28 days'].append(pg['title']); continue
        ss = seasons_in(sve_clean(ib.get('Season')))
        if not ss: skipped['crop: no named season'].append(pg['title']); continue
        seed_id = item_ref(sve_clean(seed)) if seed else None
        if seed and not seed_id: notes.append(f'seed {sve_clean(seed)!r} not in db -> NULL')
        regrow = None
        for p in [x[0] for x in (ip, si) if x]:
            m = re.search(r'continues? to produce every (\d+) days?', p['wikitext'])
            if m: regrow = int(m.group(1))
        if si and ip and ip[2].get('Growth') and sve_clean(si[2].get('Growth')) != sve_clean(ip[2].get('Growth')):
            notes.append(f'seed page growth {sve_clean(si[2].get("Growth"))} differs')
        notes.append('harvest quantity not imported; min/max left at default 1')
        R['crop'].append({'item_id': cid, 'seed_item_id': seed_id, 'growth_days': growth, 'regrow_days': regrow, 'xp': None,
                          'min_harvest': 1, 'max_harvest': 1, 'stage_days': None, 'notes': '; '.join(notes)})
        R['crop_season'] += [{'crop_id': cid, 'season': s} for s in ss]
        R['entity_source'].append(src('crop', cid, pg))
        if si: R['entity_source'].append(src('crop', cid, si[0]))

    # ---- gift tastes: SVE NPC pages first, then item pages (SVE items: all NPCs; vanilla items: SVE NPCs only)
    taste_of, conflicts, unknown = {}, [], collections.Counter()

    def add_taste(nid, iid, taste, pg):
        if (nid, iid) in taste_of:
            if taste_of[(nid, iid)] != taste: conflicts.append((nid, iid, taste_of[(nid, iid)], taste, pg['title']))
            return
        taste_of[(nid, iid)] = taste
        R['gift_taste'].append({'npc_id': nid, 'item_id': iid, 'taste': taste})
        R['entity_source'].append(src('gift_taste', f'{nid}@{iid}', pg))

    for pg, box, ib in parsed:
        nid = slug(pg['title'])
        if box != 'Character Infobox' or nid not in snpcs: continue
        sec = re.search(r'==\s*Gift Tastes\s*==(.*?)(\n==[^=]|\Z)', pg['wikitext'], re.S)
        if not sec: continue
        for tab, body in re.findall(r'\|-\|\s*(\w+)\s*=(.*?)(?=\|-\||\Z)', sec.group(1), re.S):
            taste = TABS.get(tab)
            if not taste: continue
            for link in re.findall(r'\|imglink\s*=\s*\[\[([^\]|]+)', body):
                vanilla = link.startswith('Stardew:')
                name = link.split(':', 1)[1] if vanilla else link
                iid = slug(name)
                if iid not in (vitems if vanilla else all_items): unknown[name] += 1; continue
                add_taste(nid, iid, taste, pg)
    for pg, box, ib in parsed:
        iid = slug(pg['title'])
        if iid not in all_items: continue
        wt = pg['wikitext']
        g = re.search(r'\{\{Gifting(.*?)\}\}', wt, re.S)
        pairs = re.findall(r'\|\s*(love|like|neutral|dislike|hate)\s*=([^|}]*)', g.group(1), re.I) if g else \
            [(k, ib[k2]) for k in TABS.values() for k2 in (k, k.capitalize()) if ib.get(k2)]
        for taste, names in pairs:
            for n in [x.strip() for x in re.sub(r'\{\{|\}\}', '', names).split(',') if x.strip()]:
                nid = slug(sve_clean(n) or '')
                if nid not in all_npcs: unknown['npc:' + n] += 1; continue
                if iid in vitems and nid not in snpcs: continue
                add_taste(nid, iid, taste.lower(), pg)

    write_fragments('sve', R)
    print(f'gift taste conflicts (first source kept): {len(conflicts)} {conflicts[:8]}')
    print(f'unresolved gift names: {len(unknown)} {sorted(unknown)[:30]}')
    for reason, ts in sorted(skipped.items()):
        print(f'skipped ({reason}): {len(ts)}' + ('' if 'out of scope' in reason and len(ts) > 12 else f'  {ts}'))


if __name__ == '__main__':
    main()
