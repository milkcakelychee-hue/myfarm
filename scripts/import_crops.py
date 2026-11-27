#!/usr/bin/env python3
"""Crops importer: crop + crop_season for every crop page (generic Infobox with `growth` and `seed`) and every
fruit tree (Infobox fruit tree, stored as a crop row with regrow_days=1), plus shop_price for seeds/saplings.
Output: data/{crop,crop_season,shop_price,entity_source}.crops.json
Only references items that exist in data/item.items.json; never guesses values (NULL + note instead).
Usage: python3 scripts/import_crops.py"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from wikitext import ROOT, names_in, all_pages, infobox, infobox_type, clean, first_int, seasons_in, slug, src, write_fragments

SHOPS = {'gPrice': "Pierre's General Store", 'jPrice': 'JojaMart', 'oPrice': 'Oasis', 'iPrice': 'Island Trader'}


def stages(wt):
    """'==Stages==' (or 'Stages of Growth') table: 'N Day(s)' cells, 'Total: N', 'Regrowth: N'."""
    sec = re.search(r'==\s*Stages[^=\n]*==(.*?)(\n==[^=]|\Z)', wt, re.S)
    if not sec: return None, None, None
    days, total, regrow = [], None, None
    for cell in re.findall(r'^\|(.*)$', sec.group(1), re.M):
        c = cell.strip()
        if re.fullmatch(r'\d+\s+Days?', c): days.append(int(c.split()[0]))
        m = re.search(r'Total:\s*(\d+)', c)
        if m: total = int(m.group(1))
        m = re.search(r'Regrowth:\s*(\d+)', c)
        if m: regrow = int(m.group(1))
    return (days or None), total, regrow


def fixed_yield(wt):
    """Only an explicit fixed number: 'Each harvest yields 3 X' / 'each X plant gives 2 X'."""
    m = re.search(r'(?:[Ee]ach harvest yields|plant gives)\s+(\d+)\s', wt)
    return int(m.group(1)) if m else None


def price_rows(ib, iid, pg, skipped):
    rows = []
    for k, shop in SHOPS.items():
        v = ib.get(k)
        if not v or 'Not Sold' in v: continue
        m = re.fullmatch(r'\{\{Price\|([\d,]+)\}\}\s*(?:\((Year \d\+)\))?', v.strip())
        if not m: skipped.append(f'{pg["title"]} {k}={clean(v)!r} (not a plain gold price)'); continue
        rows.append({'item_id': iid, 'shop': shop, 'price': int(m.group(1).replace(',', '')), 'currency': 'g',
                     'condition': m.group(2) or ''})
    v = ib.get('otherprice')
    if v:
        m = re.fullmatch(r'\[\[([^\]|]+)\]\]:\s*\{\{Price\|([\d,]+)\}\}', v.strip())
        if m: rows.append({'item_id': iid, 'shop': m.group(1).strip(), 'price': int(m.group(2).replace(',', '')),
                           'currency': 'g', 'condition': ''})
        else: skipped.append(f'{pg["title"]} otherprice={clean(v)!r} (not a single plain gold price at a named place)')
    return rows


def main():
    items = {r['id'] for r in json.load(open(os.path.join(ROOT, 'data', 'item.items.json'), encoding='utf-8'))}
    R = {'crop': [], 'crop_season': [], 'shop_price': [], 'entity_source': []}
    unknown, skipped, crops, fruit_pages = [], [], set(), set()

    def add_prices(iid, pg, rows):
        for r in rows:
            R['shop_price'].append(r)
            R['entity_source'].append(src('shop_price', f'{iid}@{r["shop"]}' + (f'#{r["condition"]}' if r['condition'] else ''), pg))

    for pg in all_pages():
        wt = pg['wikitext']; box = infobox_type(wt); ib = infobox(wt)
        if box == 'Infobox seed':
            iid = slug(clean(ib.get('eng') or ib.get('name')) or pg['title'])
            if iid not in items: unknown.append(f'{pg["title"]} (seed price rows)'); continue
            add_prices(iid, pg, price_rows(ib, iid, pg, skipped))
            continue
        if box == 'Infobox' and ib.get('growth') and ib.get('seed'):
            iid = slug(clean(ib.get('eng') or ib.get('name')) or pg['title'])
            seed = slug(clean(ib['seed']))
            notes = []
            sd, total, regrow = stages(wt)
            page_growth = ib['growth']
            season_v = ib.get('season')
            if len(names_in(ib['seed'])) > 1:   # e.g. Grape: Summer Seeds (7 days, Summer) / Grape Starter (10 days, Fall)
                pick = next((m.group(2) for m in re.finditer(r'(\d+) days? \(([^)]+)\)', ib['growth']) if int(m.group(1)) == total), None)
                if not pick: skipped.append(f'{pg["title"]}: several seeds, none matches the stages table -> skipped'); continue
                seed = slug(pick)
                ib = dict(ib, growth=str(total), season=' '.join(x for x in re.split(r'<br\s*/?>', season_v or '') if f'({pick})' in x))
                notes.append(f'wiki lists several seeds; row uses {pick}. Wiki growth: {clean(page_growth)}; season: {clean(season_v)}')
            if clean(season_v) == 'All':
                notes.append("infobox season is 'All' -> stored as all four seasons")
                ib = dict(ib, season='All Seasons')
            if iid not in items: unknown.append(f'{pg["title"]} (crop item {iid})'); continue
            if seed not in items: unknown.append(f'{pg["title"]} (seed {seed}) -> seed_item_id NULL'); seed = None
            growth = first_int(clean(ib['growth']))
            if total and growth and total != growth: notes.append(f'stages table total {total} differs from infobox growth {growth}')
            if regrow is None:
                m = re.search(r'continues? to produce (?:\w+ )*?every (\d+) days?', wt[:3000])
                if m: regrow = int(m.group(1))
            xpv = ib.get('xp'); xp = first_int(clean(xpv)) if xpv else None
            if xpv and xp is None: notes.append(f'xp not numeric on wiki: {clean(xpv)}')
            y = fixed_yield(wt)
            if y is None: notes.append('harvest quantity not stated as a fixed number; min/max left at default 1')
            if growth is None: skipped.append(f'{pg["title"]}: growth {ib["growth"]!r} not numeric (growth_days NOT NULL) -> crop skipped'); continue
            R['crop'].append({'item_id': iid, 'seed_item_id': seed, 'growth_days': growth, 'regrow_days': regrow, 'xp': xp,
                              'min_harvest': y or 1, 'max_harvest': y or 1, 'stage_days': json.dumps(sd) if sd else None,
                              'notes': '; '.join(notes) or None})
        elif box == 'Infobox fruit tree':
            iid = slug(clean(ib.get('produce')) or '')
            seed = slug(clean(ib.get('sapling')) or '')
            if iid not in items: unknown.append(f'{pg["title"]} (produce {iid})'); continue
            if seed not in items: unknown.append(f'{pg["title"]} (sapling {seed}) -> seed_item_id NULL'); seed = None
            sd, total, _ = stages(wt)
            growth = first_int(clean(ib.get('growth')))
            if growth is None: skipped.append(f'{pg["title"]}: growth not numeric -> skipped'); continue
            R['crop'].append({'item_id': iid, 'seed_item_id': seed, 'growth_days': growth, 'regrow_days': 1, 'xp': None,
                              'min_harvest': 1, 'max_harvest': 1, 'stage_days': json.dumps(sd) if sd else None,
                              'notes': 'fruit tree'})
            # fruit tree `price` is NOT used: it differs from the sapling page's gPrice (it is the sapling sell value);
            # sapling shop prices come from the sapling's Infobox seed instead.
        else:
            continue
        crops.add(iid)
        if box == 'Infobox': fruit_pages.add(pg['title'])
        ss = seasons_in(ib.get('season'))
        if not ss: R['crop'][-1]['notes'] = ((R['crop'][-1]['notes'] or '') + '; season not stated as named seasons: ' + str(clean(ib.get('season')))).lstrip('; ')
        R['crop_season'] += [{'crop_id': iid, 'season': s} for s in ss]
        R['entity_source'].append(src('crop', iid, pg))
        R['entity_source'] += [src('crop_season', f'{iid}@{s}', pg) for s in ss]

    trees = {r['item_id'] for r in R['crop'] if r['notes'] == 'fruit tree'}
    drop = {r['item_id'] for r in R['crop'] if r['item_id'] in trees and r['notes'] != 'fruit tree'}
    R['crop'] = [r for r in R['crop'] if not (r['item_id'] in drop and r['notes'] != 'fruit tree')]
    R['entity_source'] = [r for r in R['entity_source'] if not (r['entity_type'] in ('crop', 'crop_season') and
                          r['entity_id'].split('@')[0] in drop and r['page_title'] in fruit_pages)]
    if drop: print('fruit item pages superseded by their fruit tree page:', ', '.join(sorted(drop)))
    # dedupe shop_price by PK (fruit tree page and sapling page may both state the price)
    seen, sp = {}, []
    for r in R['shop_price']:
        k = (r['item_id'], r['shop'], r['condition'])
        if k in seen:
            if seen[k] != r['price']: skipped.append(f'conflicting price {k}: {seen[k]} vs {r["price"]} (kept first)')
            continue
        seen[k] = r['price']; sp.append(r)
    R['shop_price'] = sp
    write_fragments('crops', R)
    print(f'crops: {len(crops)}')
    print('skipped (unknown item):', *unknown, sep='\n  ')
    print('skipped (other):', *skipped, sep='\n  ')


if __name__ == '__main__':
    main()
