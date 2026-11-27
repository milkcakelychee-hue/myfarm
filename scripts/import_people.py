#!/usr/bin/env python3
"""People importer: npc (Infobox villager pages), gift_taste (item pages' {{GiftsByItem}}), calendar_event
(birthdays + festivals from the "Festivals" page), bundle + bundle_item (standard Community Center bundles from "Bundles").
Output: data/{npc,gift_taste,calendar_event,bundle,bundle_item,entity_source}.people.json
Usage: python3 scripts/import_people.py"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from wikitext import ROOT, SEASONS, all_pages, page, infobox, infobox_type, clean, slug, src, write_fragments, icon_ids
ICONS = icon_ids()

ORD = {'1st': 1}  # numbers parsed via regex below


def known_items():
    return {r['id'] for r in json.load(open(os.path.join(ROOT, 'data', 'item.items.json'), encoding='utf-8'))}


def birthday(raw):
    """{{Season|Fall|13}} or {{Season|Fall}} 13 -> ('Fall', 13); anything else -> (None, None)."""
    m = re.search(r'\{\{Season\|(\w+)(?:\|(\d+))?[^}]*\}\}\s*(\d+)?', raw or '')
    if not m or m.group(1) not in SEASONS: return None, None
    d = m.group(2) or m.group(3)
    return m.group(1), (int(d) if d and 1 <= int(d) <= 28 else None)


def home(ib):
    """Villager infobox 'address' (else 'residence'), cleaned; None when the wiki gives none / 'N/A' / 'Unknown'."""
    h = clean(re.sub(r'\[\[File:HeartIcon[^\]]*\]\]', ' hearts', ib.get('address') or ib.get('residence') or ''))
    return None if h in ('N/A', 'Unknown') else h


def main():
    items = known_items()
    R = {k: [] for k in ('npc', 'gift_taste', 'calendar_event', 'bundle', 'bundle_item', 'entity_source')}
    skipped, unknown_npc = [], set()

    # ---- npc + birthdays
    npcs, npc_pages, favorites = {}, {}, {}
    for pg in all_pages():
        wt = pg['wikitext']
        if infobox_type(wt) != 'Infobox villager': continue
        ib = infobox(wt); nid = slug(pg['title'])
        season, day = birthday(ib.get('birthday'))
        npcs[nid] = pg['title']; npc_pages[nid] = pg
        favorites[nid] = {slug(n) for n, _ in [(m, 1) for m in re.findall(r'\{\{Name\|([^|}]+)', ib.get('favorites') or '')]}
        R['npc'].append({'id': nid, 'name_en': pg['title'], 'name_th': None, 'birthday_season': season, 'birthday_day': day,
                         'marriageable': 1 if (ib.get('marriage') or '').strip() == 'Yes' else 0, 'image_id': f'img_npc_{nid}' if f'img_npc_{nid}' in ICONS else None,
                         'content_pack': 'vanilla', 'home': home(ib)})
        R['entity_source'].append(src('npc', nid, pg))
        if season and day:
            eid = f'birthday_{nid}'
            R['calendar_event'].append({'id': eid, 'season': season, 'day_start': day, 'day_end': None, 'kind': 'birthday',
                                        'name_en': f"{pg['title']}'s Birthday", 'npc_id': nid, 'notes': None})
            R['entity_source'].append(src('calendar_event', eid, pg))

    # ---- gift tastes from item pages
    taste_of = {}
    for pg in all_pages():
        for m in re.finditer(r'\{\{GiftsByItem(.*?)\}\}', pg['wikitext'], re.S):
            ib = infobox(pg['wikitext']) if 'Infobox' in pg['wikitext'] else {}
            iid = slug(clean(ib.get('eng') or ib.get('name')) or pg['title'])
            if iid not in items: skipped.append(f'gift_taste: {pg["title"]}'); continue
            for taste, names in re.findall(r'\|\s*(love|like|neutral|dislike|hate)\s*=([^|]*)', m.group(1)):
                for n in [x.strip() for x in names.split(',') if x.strip()]:
                    nid = slug(n)
                    if nid not in npcs: unknown_npc.add(n); continue
                    if (nid, iid) in taste_of: continue
                    taste_of[(nid, iid)] = taste
                    R['gift_taste'].append({'npc_id': nid, 'item_id': iid, 'taste': taste})
                    R['entity_source'].append(src('gift_taste', f'{nid}@{iid}', pg))
    conflicts = [(n, i, taste_of[(n, i)]) for n, fav in favorites.items() for i in fav if (n, i) in taste_of and taste_of[(n, i)] != 'love']
    missing_love = [(n, i) for n, fav in favorites.items() for i in fav if (n, i) not in taste_of]

    # ---- festivals
    fp = page('Festivals')
    nfest = 0
    if fp:
        wt = fp['wikitext']; season = None
        for m in re.finditer(r'^(==+)\s*([^=]+?)\s*\1\s*$', wt, re.M):
            title = clean(m.group(2))
            if len(m.group(1)) == 2: season = title if title in SEASONS else None; continue
            if not season: continue
            body = wt[m.end():m.end() + 800]
            s = re.search(r'takes place[^.]*\.', body)
            if not s: print('festival without date sentence:', title); continue
            s = s.group(0)
            r = re.search(rf'{season} (\d+)\s*[-–]\s*(\d+)', s)
            one = re.search(r'on the (\d+)(?:st|nd|rd|th) of (?:every )?\[\[(\w+)\]\]', s)
            if r: d1, d2 = int(r.group(1)), int(r.group(2))
            elif one and one.group(2) == season: d1, d2 = int(one.group(1)), None
            else: print('festival date unclear:', title, '|', s); continue
            eid = slug(title)
            R['calendar_event'].append({'id': eid, 'season': season, 'day_start': d1, 'day_end': d2, 'kind': 'festival',
                                        'name_en': title, 'npc_id': None, 'notes': None})
            R['entity_source'].append(src('calendar_event', eid, fp))
            own = page(title)
            if own: R['entity_source'].append(src('calendar_event', eid, own, 'low'))
            nfest += 1

    # ---- bundles (standard only: between "==Standard Bundles==" and the next level-2 heading)
    bp = page('Bundles'); nb = 0
    if bp:
        wt = bp['wikitext']
        i = wt.find('==Standard Bundles=='); j = wt.find('\n==Remixed Bundles==')
        std = wt[i:j]
        print('remixed bundles section skipped (separate page, not imported)')
        rooms = [(m.start(), clean(m.group(1))) for m in re.finditer(r'^===\s*([^=]+?)\s*===\s*$', std, re.M)]
        blocks = list(re.finditer(r'^!\s*id="[^"]*"[^\n]*\|([^|\n]+)$', std, re.M))
        for k, b in enumerate(blocks):
            name = clean(b.group(1).split(']]')[-1])
            room = [r for p, r in rooms if p < b.start()][-1]
            end = blocks[k + 1].start() if k + 1 < len(blocks) else len(std)
            nxt = [p for p, _ in rooms if p > b.start()]
            if nxt: end = min(end, nxt[0])
            body = std[b.end():end]
            bid = slug(name)
            slots = body.count('Bundle Slot.png') or None
            reward = None
            rm = re.search(r'Reward:?[^\n]*\n([^\n]+)', body)
            if rm:
                cell = rm.group(1)
                rn = re.search(r'\{\{Name\|([^|}]+)(?:\|(\d+))?', cell)
                reward = (f"{rn.group(1).strip()} ×{rn.group(2)}" if rn and rn.group(2) else rn.group(1).strip()) if rn \
                    else clean(re.sub(r'^\|(?:[^|\[{]*\|)?', '', cell))
            price = re.search(r'Bundle Purchase\.png[^\n]*\{\{Price\|([\d,]+)\}\}', body)
            R['bundle'].append({'id': bid, 'room': room, 'name_en': name, 'reward_text': reward,
                                'required_count': slots})
            R['entity_source'].append(src('bundle', bid, bp))
            agg = {}
            for chunk in re.split(r'\n\|-', body.split('Reward:')[0]):
                q = re.search(r'\{\{Quality\|([^|}]+)\|(\w+)', chunk)
                n = re.search(r'\{\{Name\|([^|}]+)(?:\|(\d+))?', chunk)
                if q:
                    iname, qual = q.group(1).strip(), q.group(2).lower()
                    qm = re.search(r'\((\d+)\)', chunk); qty = int(qm.group(1)) if qm else 1
                elif n:
                    iname, qual, qty = n.group(1).strip(), 'normal', int(n.group(2) or 1)
                else: continue
                if qual not in ('normal', 'silver', 'gold', 'iridium'): print('odd quality', name, qual); continue
                iid = slug(iname)
                if iid not in items: skipped.append(f'bundle_item: {name} -> {iname}'); continue
                agg[(iid, qual)] = agg.get((iid, qual), 0) + qty   # e.g. Construction Bundle lists Wood 99 twice
            for (iid, qual), qty in agg.items():
                R['bundle_item'].append({'bundle_id': bid, 'item_id': iid, 'qty': qty, 'min_quality': qual})
                R['entity_source'].append(src('bundle_item', f'{bid}@{iid}@{qual}', bp))
            nb += 1
            if price and not agg: pass  # Vault bundles: gold only, no items
    write_fragments('people', R)
    print(f'festivals {nfest}, bundles {nb}')
    print(f'favorites conflicting with item pages (item-page kept): {len(conflicts)} {conflicts[:10]}')
    print(f'NPC favorites with no item-page taste: {len(missing_love)} {missing_love[:10]}')
    print('names in GiftsByItem not an npc page:', sorted(unknown_npc))
    print(f'skipped (unknown item): {len(skipped)}'); [print('  ', s) for s in skipped]


if __name__ == '__main__':
    main()
