#!/usr/bin/env python3
"""Core importer: one `item` row (+ image + provenance + seasons) for every wiki page that describes an item.
Other importers (crops, fish, npc, ...) reference these item ids by slug of the English name.
Output: data/{item,image,item_season,entity_source}.items.json
Usage: python3 scripts/import_items.py"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from wikitext import all_pages, infobox, infobox_type, clean, first_int, seasons_in, categories, slug, src, write_fragments, WIKI

ITEM_BOXES = {'Infobox', 'Infobox fish', 'Infobox mineral', 'Infobox artifact', 'Infobox seed', 'Infobox cooking'}

# wiki category -> app category (first match wins; order matters)
CATEGORY_MAP = [
    ('Fish', lambda c, t: t == 'Infobox fish' or any(x.endswith(' fish') or x == 'Legendary fish' for x in c)),
    ('Seed', lambda c, t: t == 'Infobox seed' or 'Seeds' in c or 'Saplings' in c or any(x.endswith(' seeds') for x in c)),
    ('Cooking', lambda c, t: t == 'Infobox cooking' or 'Cooking' in c),
    ('Artisan Goods', lambda c, t: 'Artisan Goods' in c),
    ('Animal Product', lambda c, t: 'Animal Products' in c),
    ('Flower', lambda c, t: 'Flowers' in c),
    ('Fruit', lambda c, t: 'Fruits' in c or 'Fruit' in c or any(x.endswith(' fruit') for x in c)),
    ('Vegetable', lambda c, t: 'Vegetables' in c),
    ('Forage', lambda c, t: any(x.endswith(' Forage') or x in ('Foraging', 'Mushrooms') for x in c)),
    ('Gem', lambda c, t: 'Gems' in c),
    ('Mineral', lambda c, t: t == 'Infobox mineral' or any('Minerals' in x for x in c)),
    ('Artifact', lambda c, t: t == 'Infobox artifact' or 'Artifacts' in c),
    ('Monster Loot', lambda c, t: 'Monster Loot' in c),
    ('Resource', lambda c, t: 'Resources' in c),
    ('Fertilizer', lambda c, t: 'Fertilizer' in c),
    ('Bait & Tackle', lambda c, t: 'Bait' in c or 'Fishing Tackle' in c),
    ('Machine', lambda c, t: 'Artisan Equipment' in c or 'Machines' in c),
    ('Crafting', lambda c, t: 'Craftable items' in c),
    ('Book', lambda c, t: 'Books' in c),
    ('Trash', lambda c, t: 'Trash' in c),
]


def app_category(cats, box, ib, wt=''):
    intro = wt[:2000]
    if ib.get('growth') and ib.get('seed'):           # crop page: the intro links its crop group
        for k, v in (('Flowers', 'Flower'), ('Fruits', 'Fruit'), ('Vegetables', 'Vegetable')):
            if f'[[{k}|' in intro or f'[[{k}]]' in intro: return v
    for name, test in CATEGORY_MAP:
        if test(cats, box): return name
    if ib.get('crafttime') or ib.get('produces'): return 'Machine'
    return 'Other'


def sell(ib):
    v = ib.get('sellprice') or ib.get('price')
    if not v or re.search(r'cannot be sold|can\'t be sold|n/a', v, re.I): return None
    return first_int(clean(v))


# Items that have no page of their own: they live inside a table on another page.
# Price depends on the input (formula) or isn't a single number, so sell_price stays NULL.
EXTRA = [('Jelly', 'Jellies and Pickles', 'Artisan Goods'), ('Pickles', 'Jellies and Pickles', 'Artisan Goods'),
         ('Sturgeon Roe', 'Roe', 'Animal Product'), ('Large Brown Egg', 'Egg', 'Animal Product')]


def main():
    R = {'item': [], 'image': [], 'item_season': [], 'entity_source': []}
    seen = set()
    for pg in all_pages():
        wt = pg['wikitext']; box = infobox_type(wt)
        if box not in ITEM_BOXES: continue
        ib = infobox(wt)
        name = clean(ib.get('eng') or ib.get('name')) or pg['title']
        iid = slug(name)
        if iid in seen: continue
        seen.add(iid)
        cats = categories(wt)
        file = (clean(ib.get('image')) or (name + '.png')).replace(' ', '_')
        R['image'].append({'id': f'img_{iid}', 'file_path': None, 'origin': 'wiki', 'source_id': 'wiki_official',
                           'source_url': WIKI + 'File:' + file, 'status': 'pending'})
        R['item'].append({'id': iid, 'name_en': name, 'name_th': None, 'name_th_status': 'none',
                          'category': app_category(cats, box, ib, wt), 'sell_price': sell(ib),
                          'edibility': first_int(clean(ib.get('edibility'))) if ib.get('edibility') else None,
                          'description_en': clean(ib.get('description')) if ib.get('description') and '{{Description' not in ib.get('description', '') else None,
                          'image_id': f'img_{iid}', 'content_pack': 'vanilla', 'is_approx': 0})
        R['item_season'] += [{'item_id': iid, 'season': s} for s in seasons_in(ib.get('season'))]
        R['entity_source'] += [src('item', iid, pg), src('image', f'img_{iid}', pg)]
    from wikitext import page
    for name, title, cat in EXTRA:
        iid = slug(name); pg = page(title)
        if iid in seen or not pg or name not in pg['wikitext']: continue
        seen.add(iid)
        R['item'].append({'id': iid, 'name_en': name, 'name_th': None, 'name_th_status': 'none', 'category': cat,
                          'sell_price': None, 'edibility': None, 'description_en': None, 'image_id': f'img_{iid}',
                          'content_pack': 'vanilla', 'is_approx': 0})
        R['image'].append({'id': f'img_{iid}', 'file_path': None, 'origin': 'wiki', 'source_id': 'wiki_official',
                           'source_url': WIKI + 'File:' + name.replace(' ', '_') + '.png', 'status': 'pending'})
        R['entity_source'] += [src('item', iid, pg, 'low'), src('image', f'img_{iid}', pg, 'low')]
    write_fragments('items', R)


if __name__ == '__main__':
    main()
