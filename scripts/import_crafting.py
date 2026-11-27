#!/usr/bin/env python3
"""Crafting importer: machines + processing rules, cooking/crafting recipes, Robin/Wizard buildings, tool upgrades.
Output: data/{machine,processing_rule,recipe,recipe_ingredient,building,building_material,tool_upgrade,entity_source}.crafting.json
Usage: python3 scripts/import_crafting.py

price_formula syntax (processing_rule.price_formula):
  An arithmetic expression over the single variable `price` = base sell price of ONE input item
  (normal quality), using only numbers, `price`, `*`, `+`. Examples: `price*3` (Wine), `price*2+50` (Jelly),
  `price*2.25` (Juice), `price*7.5+25` (Dried Fruit, 5 inputs; the wiki states it per single-item base price).
  A bare number (e.g. `200`) means a fixed base sell price stated by the wiki. NULL = wiki states no formula.
  Only formulas written on the wiki machine page are stored; nothing is derived.

time_minutes: the wiki's minutes when given ("1750 mins", "4000m"); "N Hours" -> N*60; "N day(s)/Night(s)" ->
  N*1440 with a note (machines finishing at a fixed morning time are not exact multiples of 1440).
The Furnace (smelting) is skipped by design."""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from wikitext import page, all_pages, infobox, infobox_type, clean, first_int, names_in, slug, src, write_fragments, icon_ids
ICONS = icon_ids()

import json
ITEMS = {r['id'] for r in json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'item.items.json'), encoding='utf-8'))}
SKIPPED = []

MACHINES = ['Keg', 'Preserves Jar', 'Cheese Press', 'Mayonnaise Machine', 'Loom', 'Oil Maker', 'Dehydrator', 'Fish Smoker', 'Bee House']
CAT_LINKS = [(r'\[\[Fruits\|', 'Fruit'), (r'\[\[Vegetables\|', 'Vegetable'), (r'\[\[:Category:Mushrooms\|', 'Mushroom'),
             (r'\[\[Foraging[#|]', 'Forage'), (r'Any \[\[Fish\]\]', 'Fish')]


def known(iid, ctx):
    if iid in ITEMS: return True
    SKIPPED.append(f'{ctx}: {iid}'); return False


def split_top(s, sep):
    """Split on `sep` at template/link depth 0."""
    out, buf, d, i = [], [], 0, 0
    while i < len(s):
        two = s[i:i + 2]
        if two in ('{{', '[['): d += 1; buf.append(two); i += 2; continue
        if two in ('}}', ']]'): d -= 1; buf.append(two); i += 2; continue
        if d == 0 and s.startswith(sep, i): out.append(''.join(buf)); buf = []; i += len(sep); continue
        buf.append(s[i]); i += 1
    out.append(''.join(buf)); return out


def table_rows(tbl):
    """Wikitable -> (headers, rows of cell strings), expanding rowspan."""
    lines = tbl.split('\n')
    headers = [clean(re.sub(r'<noinclude>.*?</noinclude>', '', l.lstrip('!'))) for l in lines if l.startswith('!')]
    headers = [h.split('|')[-1].strip() if h else h for h in headers]
    rows, pend = [], {}
    for chunk in re.split(r'\n\|-[^\n]*', tbl)[1:]:
        cells = []
        for l in chunk.split('\n'):
            if l.startswith('|}'): break
            if l.startswith('|'): cells += split_top(l[1:].lstrip('|'), '||')
            elif cells: cells[-1] += '\n' + l
        if not cells: continue
        parsed = []
        for c in cells:
            parts = split_top(c, '|')
            attr, body = (parts[0], '|'.join(parts[1:])) if len(parts) > 1 and '=' in parts[0] else ('', c)
            m = re.search(r'rowspan="?(\d+)', attr)
            parsed.append((body.strip(), int(m.group(1)) if m else 1))
        full, ci = [], 0
        for col in range(len(headers)):
            if col in pend and pend[col][1] > 0:
                full.append(pend[col][0]); pend[col] = (pend[col][0], pend[col][1] - 1); continue
            if ci < len(parsed):
                body, rs = parsed[ci]; ci += 1
                full.append(body)
                if rs > 1: pend[col] = (body, rs - 1)
            else: full.append('')
        rows.append(full)
    return headers, rows


def col(headers, row, *keys):
    for i, h in enumerate(headers):
        if h and any(h.lower().startswith(k) for k in keys): return row[i]
    return ''


def parse_time(v):
    m = re.search(r'\{\{[Dd]uration\|([^}|]+)', v or '')
    t = m.group(1) if m else ''
    if (x := re.match(r'\s*(\d+)\s*(?:mins?|m)\b', t)): return int(x.group(1)), None
    if (x := re.match(r'\s*(\d+)\s*Hours?', t, re.I)): return int(x.group(1)) * 60, f'wiki states {t.strip()}; converted hours*60'
    if (x := re.match(r'\s*(\d+)\s*(?:days?|nights?)', t, re.I)):
        return int(x.group(1)) * 1440, f'wiki states "{clean(v)}"; time_minutes = days*1440 (approximate: finishes at a fixed morning time)'
    return None, None


def parse_formula(v):
    v = (v or '').replace('&times;', '×')
    if (m := re.search(r'\{\{(?:Price|Qualityprice\|[^|}]+)\|(\d[\d,]*)', v)) and '×' not in v:
        return m.group(1).replace(',', '')
    m = re.match(r'\s*([\d.]+)\s*×[^+(]*?Price\s*(?:\+\s*(?:\{\{Price\|)?(\d+))?', v)
    if m: return f'price*{m.group(1)}' + (f'+{m.group(2)}' if m.group(2) else '')
    return None


def machines(R):
    for mname in MACHINES:
        pg = page(mname)
        if not pg: print('machine page not cached:', mname); continue
        mid = slug(mname)
        wt = pg['wikitext']
        R['machine'].append({'id': mid, 'name_en': mname, 'name_th': None, 'image_id': f'img_{mid}' if mid in ITEMS else None, 'notes': None})
        R['entity_source'].append(src('machine', mid, pg))
        tbl = wt[wt.find('{|'):wt.find('|}', wt.find('{|')) + 2]
        headers, rows = table_rows(tbl)
        if mname == 'Bee House':
            # Honey: no input item; flavour depends on nearby flower
            t, tn = parse_time(rows[0][4])
            notes = 'no input item; ' + (tn or '') + '; base price by nearby flower: ' + '; '.join(
                f'{clean(r[-2])} {clean(r[-1])}' for r in rows)
            add_rule(R, pg, mid, None, None, 1, 'honey', 1, t, None, notes); continue
        for row in rows:
            outcell = col(headers, row, 'name')
            out_name = (names_in(outcell) or [(None, 1)])[0][0] or clean(re.sub(r'\[\[[^\]|]*\|([^\]]*)\]\]', r'\1', outcell))
            out_name = re.sub(r'\s*\(\d+\)$', '', clean(outcell))
            out_id = slug(out_name)
            ing = col(headers, row, 'ingredient')
            t, tn = parse_time(col(headers, row, 'processing'))
            sp = col(headers, row, 'sell')
            f = parse_formula(sp)
            notes = [n for n in [tn] if n]
            if re.search(r'\(\d+\)\s*$', clean(outcell) or ''): notes.append(f'wiki name cell reads "{clean(outcell)}" (meaning of the number not stated; output_qty left 1)')
            ing_pos = re.sub(r'\((?:other than|except)[^)]*\)', '', ing)   # drop exclusions like '(other than Mushrooms)'
            cats = [c for p, c in CAT_LINKS if re.search(p, ing_pos)]
            items = names_in(ing)
            if not items and not cats:   # e.g. "5 [[Grape]]s"
                m = re.match(r'\s*(\d+)?\s*\[\[([^\]|]+)', ing)
                if m: items = [(m.group(2), int(m.group(1) or 1))]
            qty_m = re.match(r'\s*(\d+) of', ing)
            if cats:
                q = int(qty_m.group(1)) if qty_m else 1
                extra = [n for n, _ in items if n != 'Coal']
                cn = notes + [f'wiki ingredient: {clean(ing)}']
                if any(n == 'Coal' for n, _ in items): cn.append('also requires 1 Coal')
                for c in cats:
                    add_rule(R, pg, mid, None, c, q, out_id, 1, t, f, '; '.join(cn))
            else:
                for n, q in items:
                    add_rule(R, pg, mid, slug(n), None, q, out_id, 1, t, f, '; '.join(notes) or None)


def add_rule(R, pg, mid, in_id, in_cat, q, out_id, oq, t, f, notes):
    ctx = f'processing_rule {mid}'
    if in_id and not known(in_id, ctx + ' input'): return
    if out_id and not known(out_id, ctx + ' output'): return
    rid = len(R['processing_rule']) + 1
    R['processing_rule'].append({'id': rid, 'machine_id': mid, 'input_item_id': in_id, 'input_category': in_cat, 'input_qty': q,
                                 'output_item_id': out_id, 'output_qty': oq, 'time_minutes': t, 'price_formula': f, 'notes': notes or None})
    R['entity_source'].append(src('processing_rule', str(rid), pg))


def recipes(R):
    for pg in all_pages():
        wt = pg['wikitext']; box = infobox_type(wt)
        if box not in ('Infobox', 'Infobox cooking'): continue
        ib = infobox(wt)
        if not ib.get('ingredients') or not (ib.get('recipe') or ib.get('craftingstation')): continue
        name = clean(ib.get('eng') or ib.get('name')) or pg['title']
        rid = slug(name)
        if any(r['id'] == rid for r in R['recipe']): continue
        crafted = bool(ib.get('craftingstation')) or 'Crafting' in (ib.get('source') or '') or box == 'Infobox'
        kind = 'crafting' if crafted else 'cooking'
        out = rid if rid in ITEMS else None
        if not out: SKIPPED.append(f'recipe {rid}: output item unknown (recipe kept, output_item_id NULL)')
        pm = re.match(r'\s*(\d+)\s', clean(ib.get('produces')) or '')
        R['recipe'].append({'id': rid, 'kind': kind, 'output_item_id': out, 'output_qty': int(pm.group(1)) if pm else 1,
                            'unlock': clean(ib.get('recipe'))})
        R['entity_source'].append(src('recipe', rid, pg))
        for n, q in names_in(ib['ingredients']):
            iid = slug(n)
            if not known(iid, f'recipe_ingredient {rid}'): continue
            R['recipe_ingredient'].append({'recipe_id': rid, 'item_id': iid, 'qty': q})
            R['entity_source'].append(src('recipe_ingredient', f'{rid}|{iid}', pg))


def size_of(v, ctx):
    """'''7x4''' / 7x4 / 7×4 -> (7, 4) as written on the wiki (width x height in tiles); fails loudly if absent."""
    m = re.search(r'(\d+)\s*[x×]\s*(\d+)', v or '')
    if not m: sys.exit(f'{ctx}: cannot parse size from {v!r}')
    return int(m.group(1)), int(m.group(2))


def upgrades_from(pg):
    """Multi-column building infobox (Barn/Coop/Shed pages): '''Name''' header cells + the 'Upgrades From' row.
    Returns {building name: name it upgrades from or None}."""
    wt = pg['wikitext']
    i = wt.find('Upgrades From')
    if i < 0: return {}
    top = wt[:wt.find('|-', wt.find('|-') + 1)]          # first row: the column titles
    names = re.findall(r"'''([^']+)'''", top)
    row = wt[i:wt.find('\n|-', i)].split('\n')[1:]
    vals = [clean(re.sub(r'^\|(?:[^|\[{]*\|)?', '', l)) for l in row if l.startswith('|')]
    if len(vals) != len(names): sys.exit(f'{pg["title"]}: Upgrades From has {len(vals)} cells for {len(names)} columns')
    return {n: (None if v in (None, 'N/A') else v) for n, v in zip(names, vals)}


def add_building(R, pg, bid, builder, name, cost, days, mats, size=(None, None), upfrom=None):
    if any(b['id'] == bid for b in R['building']): return
    R['building'].append({'id': bid, 'builder': builder, 'name_en': name, 'name_th': None, 'cost_gold': cost, 'build_days': days,
                          'max_count': None, 'image_id': f'img_building_{bid}' if f'img_building_{bid}' in ICONS else None, 'content_pack': 'vanilla',
                          'size_w': size[0], 'size_h': size[1], 'upgrade_from': upfrom})
    R['entity_source'].append(src('building', bid, pg))
    for n, q in mats:
        iid = slug(n)
        if not known(iid, f'building_material {bid}'): continue
        R['building_material'].append({'building_id': bid, 'item_id': iid, 'qty': q})
        R['entity_source'].append(src('building_material', f'{bid}|{iid}', pg))


def buildings(R):
    pg = page("Carpenter's Shop"); wt = pg['wikitext']
    s = wt.find('==Farm Buildings'); s = wt.find('{|', s)
    headers, rows = table_rows(wt[s:wt.find('\n|}', s) + 3])
    for row in rows:
        name = clean(col(headers, row, 'name'))
        cost = col(headers, row, 'cost')
        ct = clean(col(headers, row, 'construction')) or ''
        days = 0 if ct.lower() == 'instant' else (first_int(ct) if re.search(r'\d+\s*days?', ct) else None)
        pm = re.search(r'\{\{Price\|([\d,]+)', cost)
        size = size_of(col(headers, row, 'size'), f'Carpenter\'s Shop {name}')
        # upgrade chain from the building's own page (the Name cell links to it, e.g. [[Barn|Big Barn]])
        lk = re.search(r'\[\[([^\]|#]+)', col(headers, row, 'name'))
        own = page(lk.group(1)) if lk else None
        up = upgrades_from(own).get(name) if own else None
        add_building(R, pg, slug(name), 'Robin', name, int(pm.group(1).replace(',', '')) if pm else None, days, names_in(cost),
                     size, slug(up) if up else None)
    # Wizard buildings: Infobox building pages whose intro says it is bought from the Wizard.
    # build_days: the Wizard's Tower page states these buildings "require no build time" -> 0.
    wtp = page("Wizard's Tower")
    wiz_days = 0 if wtp and re.search(r'require no build time', wtp['wikitext']) else None
    if wiz_days is None: sys.exit("Wizard's Tower: build-time sentence not found")
    for pg in all_pages():
        wt = pg['wikitext']
        if infobox_type(wt) != 'Infobox building': continue
        intro = wt[:3000]
        if not re.search(r'purchasable from the \[\[Wizard\]\]', intro): continue
        ib = infobox(wt); name = clean(ib.get('name')) or pg['title']
        pm = re.search(r'\{\{Price\|([\d,]+)', ib.get('cost') or '')
        add_building(R, pg, slug(name), 'Wizard', name, int(pm.group(1).replace(',', '')) if pm else None, wiz_days,
                     names_in(ib.get('materials')), size_of(ib.get('size'), pg['title']))


def tools(R):
    pg = page('Blacksmith'); wt = pg['wikitext']
    s = wt.find('==Upgrade Tools'); e = wt.find('\n==', s + 5)
    for tbl in re.findall(r'\{\|.*?\n\|\}', wt[s:e], re.S):
        headers, rows = table_rows(tbl)
        for row in rows:
            name = clean(col(headers, row, 'name')); level = name.split()[0]
            imgs = re.findall(r'File:(?:Copper|Steel|Gold|Iridium) ([\w ]+?)\.png', col(headers, row, 'image'))
            tl = ['Trash Can'] if 'Trash Can' in name else imgs
            bar = names_in(col(headers, row, 'ingredient'))
            gold = first_int(clean(col(headers, row, 'cost')))
            for tool in tl:
                bid = slug(bar[0][0]) if bar else None
                if bid and not known(bid, f'tool_upgrade {tool} {level}'): bid = None
                R['tool_upgrade'].append({'tool': tool, 'level': level, 'gold': gold, 'bar_item_id': bid, 'bar_qty': bar[0][1] if bar else None})
                R['entity_source'].append(src('tool_upgrade', f'{tool}|{level}', pg))


def main():
    R = {k: [] for k in ['machine', 'processing_rule', 'recipe', 'recipe_ingredient', 'building', 'building_material', 'tool_upgrade', 'entity_source']}
    machines(R); recipes(R); buildings(R); tools(R)
    write_fragments('crafting', R)
    print(f'\nskipped (unknown item): {len(SKIPPED)}')
    for s in SKIPPED: print('  ', s)


if __name__ == '__main__':
    main()
