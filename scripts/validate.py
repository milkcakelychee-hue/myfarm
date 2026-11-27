#!/usr/bin/env python3
"""Sanity checks on stardew.sqlite. Exit 1 on errors; warnings are informational."""
import os, sqlite3, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
con = sqlite3.connect(os.path.join(ROOT, 'stardew.sqlite')); con.execute('PRAGMA foreign_keys=ON')
errors, warns = [], []
fk = con.execute('PRAGMA foreign_key_check').fetchall()
if fk: errors.append(f'foreign key violations: {fk[:5]}')
q = lambda s: con.execute(s).fetchall()
for r in q("SELECT item_id FROM crop WHERE growth_days<=0 OR growth_days>28"): errors.append(f'crop growth_days out of range: {r[0]}')
for r in q("SELECT id FROM item WHERE sell_price<0"): errors.append(f'negative sell_price: {r[0]}')
for r in q("SELECT item_id FROM crop WHERE item_id NOT IN (SELECT crop_id FROM crop_season)"): errors.append(f'crop without season: {r[0]}')
for r in q("SELECT birthday_day FROM npc WHERE birthday_day NOT BETWEEN 1 AND 28"): errors.append('npc birthday out of 1..28')
for t, pk in [('item','id'),('crop','item_id'),('npc','id'),('building','id'),('image','id')]:
    for r in q(f"SELECT {pk} FROM {t} WHERE {pk} NOT IN (SELECT entity_id FROM entity_source WHERE entity_type='{t}')"):
        warns.append(f'no provenance: {t}/{r[0]}')
n = q("SELECT count(*) FROM image WHERE status='pending'")[0][0]
if n: warns.append(f'{n} image(s) still pending download')
n = q("SELECT count(*) FROM item WHERE name_th IS NULL")[0][0]
if n: warns.append(f'{n} item(s) without Thai name')
for w in warns: print('WARN ', w)
for e in errors: print('ERROR', e)
print('OK' if not errors else 'FAILED'); sys.exit(1 if errors else 0)
