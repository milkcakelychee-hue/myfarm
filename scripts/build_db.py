#!/usr/bin/env python3
"""Rebuild stardew.sqlite from schema.sql + data/*.json (JSON is the source of truth).
Usage: python3 scripts/build_db.py            (run from the stardew-db folder)
Rows in data/<table>.json are lists of objects whose keys are column names.
Lists/objects are stored as JSON text; true/false become 1/0.
data/user_override.json is applied LAST so hand edits survive every rebuild."""
import json, os, sqlite3, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORDER = ['meta','source','image','item','item_season','item_location','crop','crop_season','shop_price','fish','machine',
         'processing_rule','recipe','recipe_ingredient','bundle','bundle_item','npc','gift_taste','calendar_event','building',
         'building_material','tool_upgrade','animal','monster','game_constant','profession','npc_schedule','location','location_alias','entity_source','changelog']
PK = {'game_constant':'key','profession':'id','item':'id','crop':'item_id','npc':'id','building':'id','machine':'id','recipe':'id','bundle':'id','image':'id','fish':'item_id','location':'id'}

def val(v):
    if isinstance(v, bool): return int(v)
    if isinstance(v, (list, dict)): return json.dumps(v, ensure_ascii=False)
    return v

def main():
    db_path = os.path.join(ROOT, 'stardew.sqlite')
    if os.path.exists(db_path): os.remove(db_path)
    con = sqlite3.connect(db_path)
    con.executescript(open(os.path.join(ROOT, 'schema.sql'), encoding='utf-8').read())
    # data/<table>.json first, then fragments data/<table>.<importer>.json (one per importer script).
    # A duplicate primary key keeps the FIRST row and prints a warning (core importer wins).
    import glob, sqlite3 as _s
    for t in ORDER:
        files = [os.path.join(ROOT, 'data', t + '.json')] + sorted(glob.glob(os.path.join(ROOT, 'data', t + '.*.json')))
        # downloaded image rows (image.images.json, written by download_images.py) must win over every pending fragment
        files.sort(key=lambda p: not p.endswith('image.images.json'))
        cols_ok = {r[1] for r in con.execute(f'PRAGMA table_info({t})')}
        n = dup = 0
        for p in files:
            if not os.path.exists(p): continue
            for r in json.load(open(p, encoding='utf-8')):
                bad = set(r) - cols_ok
                if bad: sys.exit(f'{os.path.basename(p)}: unknown column(s) {sorted(bad)}')
                ks = list(r)
                try:
                    con.execute(f'INSERT INTO {t} ({",".join(ks)}) VALUES ({",".join("?"*len(ks))})', [val(r[k]) for k in ks]); n += 1
                except _s.IntegrityError as e:
                    if 'UNIQUE' not in str(e) and 'PRIMARY' not in str(e): raise
                    dup += 1
        if n or dup: print(f'{t:20s} {n} rows' + (f'  ({dup} duplicate keys skipped)' if dup else ''))
    # owner exclusions (data/exclude.json): drop matching rows and every row that references an excluded item
    ep = os.path.join(ROOT, 'data', 'exclude.json')
    if os.path.exists(ep):
        ex = json.load(open(ep, encoding='utf-8'))
        for t, where in ex.get('delete_where', {}).items():
            print(f'exclude {t:14s} {con.execute(f"DELETE FROM {t} WHERE {where}").rowcount} rows')
        ids = [r[0] for pat in ex.get('item_name_like', []) for r in con.execute('SELECT id FROM item WHERE name_en LIKE ?', (pat,))]
        if ids:
            q = ','.join('?' * len(ids))
            con.execute('PRAGMA foreign_keys=OFF')       # delete children and parents together; validate.py re-checks FKs
            con.execute(f'DELETE FROM crop_season WHERE crop_id IN ({q})', ids)
            for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
                for fk in con.execute(f'PRAGMA foreign_key_list({t})').fetchall():
                    if fk[2] == 'item' and t != 'item':
                        con.execute(f'DELETE FROM {t} WHERE {fk[3]} IN ({q})', ids)
            con.execute(f"DELETE FROM entity_source WHERE entity_type='item' AND entity_id IN ({q})", ids)
            con.execute(f'DELETE FROM item WHERE id IN ({q})', ids)
            con.execute(f"DELETE FROM image WHERE id IN ({','.join('?' * len(ids))}) AND id NOT IN (SELECT image_id FROM item WHERE image_id IS NOT NULL)", [f'img_{i}' for i in ids])
            con.execute('PRAGMA foreign_keys=ON')
            print(f'exclude item           {len(ids)} rows ({", ".join(ids[:8])}{"…" if len(ids) > 8 else ""})')
    op = os.path.join(ROOT, 'data', 'user_override.json')
    n = 0
    for o in (json.load(open(op, encoding='utf-8')) if os.path.exists(op) else []):
        t, pk = o['entity_type'], PK.get(o['entity_type'])
        if not pk: sys.exit(f'override: unsupported table {t}')
        con.execute('INSERT OR REPLACE INTO user_override VALUES (?,?,?,?,?)', (t, o['entity_id'], o['field'], o.get('value'), o.get('updated_at')))
        cur = con.execute(f'UPDATE {t} SET {o["field"]}=? WHERE {pk}=?', (o.get('value'), o['entity_id']))
        if cur.rowcount == 0: print(f'WARN override target not found: {t}/{o["entity_id"]}')
        n += 1
    print(f'user_override        {n} applied')
    con.commit(); con.close(); print('built', db_path)
main()
