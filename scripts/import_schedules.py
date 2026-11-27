#!/usr/bin/env python3
"""Schedules importer: npc_schedule from the ==Schedule== section of each Infobox villager page.
Output: data/{npc_schedule,entity_source}.schedules.json
Usage: python3 scripts/import_schedules.py

Scope: the 'Regular Schedule' table (day_kind 'normal') and the 'Rain' / 'Rain (Option 1)' table (day_kind 'rain')
per season. Season comes from {{ScheduleHeader|<Season>}}; pages without season headers give season NULL (all seasons).
Everything else (dated days, weekdays, festivals, green rain, Rain (Option 2+), {{ScheduleHeader|Marriage}} and after)
is skipped. When a section has ===level-3=== sub-headings (e.g. Leo: Fewer than 6 Hearts / 6+ Hearts) only the LAST
sub-heading is used and its title is put in note. If both a conditional ('Regular Schedule (Beach Bridge Repaired)')
and a plain label exist, the plain one wins. time is game time ('All day' -> 600 with a note; 900 = 9:00 AM, 2400 = midnight, 2530 = 1:30 AM).
Any time cell that cannot be parsed stops the run.
location_th / note_th come from data/npc_schedule_th.json (owner's Thai glossary, English string -> Thai); missing strings are warned."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from wikitext import SEASONS, all_pages, infobox_type, clean, slug, src, write_fragments

TIME = re.compile(r'^\s*(\d{1,2}):(\d{2})\s*([AP])\.?M\.?\s*$', re.I)
TH = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'data', 'npc_schedule_th.json'), encoding='utf-8'))
EXACT = {'normal': ['Regular Schedule'], 'rain': ['Rain', 'Rain (Option 1)']}


def game_time(cell, ctx):
    if re.match(r'\s*All day\s*$', clean(cell) or '', re.I): return 600, 'wiki time "All day" (stored as 600)'
    m = TIME.match(clean(cell) or '')
    if not m: sys.exit(f'{ctx}: cannot parse time cell {cell!r}')
    h, mi, ap = int(m.group(1)), int(m.group(2)), m.group(3).upper()
    h = (0 if h == 12 else h) + (12 if ap == 'P' else 0)
    t = h * 100 + mi
    return (t + 2400 if t < 600 else t), None


def kind_of(label):
    if re.match(r'Regular Schedule\b', label): return 'normal'
    if label == 'Rain' or re.match(r'Rain \(Option 1\)$', label) or re.match(r'Rain \((?!Option)', label): return 'rain'
    return None


def tables(sec):
    """Yield (season, label, cells) for every schedule table in the section, in order."""
    season = None
    pos = 0
    events = sorted([(m.start(), 'H', m.group(1)) for m in re.finditer(r'\{\{ScheduleHeader\|([^}|]+)\}\}', sec)] +
                    [(m.start(), 'T', m) for m in re.finditer(r'\{\|.*?\n\|\}', sec, re.S)], key=lambda e: e[0])
    for p, kind, v in events:
        if kind == 'H':
            season = v.strip()
            if season == 'Marriage': return
            if season not in SEASONS: sys.exit(f'unknown ScheduleHeader {season!r}')
            continue
        tbl = v.group(0)
        hm = re.search(r'^!\s*colspan="?2"?\s*\|(.*)$', tbl, re.M)
        if hm: label = hm.group(1)
        else:
            before = sec[pos:p].rstrip().split('\n')[-1]
            lm = re.match(r"^'''(.*)'''\s*$", before)
            label = lm.group(1) if lm else None
        pos = v.end()
        if not label: continue
        cells = []
        for line in tbl.split('\n')[1:]:
            if line.startswith(('|-', '|}', '!', '{|')): continue
            if line.startswith('|'):
                cells += [re.sub(r'^[\w-]+="[^"]*"(?:\s+[\w-]+="[^"]*")*\s*\|(?!\|)', '', c.strip()).strip() for c in line[1:].split('||')]
            elif cells and line.strip(): cells[-1] += ' ' + line.strip()
        yield season, clean(label), cells


def main():
    R = {'npc_schedule': [], 'entity_source': []}
    covered, none = [], []
    missing = set()
    for pg in all_pages():
        wt = pg['wikitext']
        if infobox_type(wt) != 'Infobox villager': continue
        nid = slug(pg['title'])
        i = wt.find('==Schedule==')
        if i < 0: none.append(pg['title']); continue
        e = re.search(r'\n==[^=]', wt[i + 12:])
        sec = wt[i:i + 12 + e.start()] if e else wt[i:]
        subs = list(re.finditer(r'^===\s*([^=\n]+?)\s*===\s*$', sec, re.M))
        sub_note = None
        if subs: sec, sub_note = sec[subs[-1].end():], clean(subs[-1].group(1))
        pick = {}
        for season, label, cells in tables(sec):
            k = kind_of(label or '')
            if not k: continue
            cur = pick.get((season, k))
            if cur is None or (cur[0] not in EXACT[k] and label in EXACT[k]): pick[(season, k)] = (label, cells)
        n = 0
        for (season, k), (label, cells) in pick.items():
            if len(cells) % 2: sys.exit(f'{pg["title"]} {season} {label}: odd number of cells {cells}')
            for j in range(0, len(cells), 2):
                t, tnote = game_time(cells[j], f'{pg["title"]} {season} {label}')
                note = '; '.join(x for x in [sub_note, label if label not in ('Regular Schedule', 'Rain') else None, tnote] if x) or None
                R['npc_schedule'].append({'npc_id': nid, 'season': season, 'day_kind': k, 'time': t,
                                          'location': clean(cells[j + 1]), 'note': note})
                r = R['npc_schedule'][-1]
                for f in ('location', 'note'):
                    r[f + '_th'] = TH.get(r[f]) if r[f] else None
                    if r[f] and r[f] not in TH: missing.add(r[f])
                R['entity_source'].append(src('npc_schedule', f'{nid}|{season or "all"}|{k}|{t}', pg))
                n += 1
        (covered if n else none).append(pg['title'])
    write_fragments('schedules', R)
    if missing: print(f'WARNING: {len(missing)} schedule strings have no Thai in data/npc_schedule_th.json: ' + ' | '.join(sorted(missing)))
    else: print('Thai translations: all strings covered')
    print(f'npcs with schedule rows: {len(covered)}')
    print(f'villager pages with no parsed regular/rain schedule ({len(none)}): {", ".join(none)}')


if __name__ == '__main__':
    main()
