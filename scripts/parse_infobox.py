#!/usr/bin/env python3
"""DRAFT helper - turn the {{Infobox ...}} template in cached wikitext into a dict.
Verified by hand on the Pumpkin page (fields: eng, seed, growth, season, xp, sellprice, edibility, color).
Usage: python3 scripts/parse_infobox.py cache/wiki_official/Pumpkin.json"""
import json, re, sys
def infobox(wikitext):
    m = re.search(r'\{\{Infobox[ \w]*\n(.*?)\n\}\}', wikitext, re.S)
    if not m: return {}
    out = {}
    for line in m.group(1).splitlines():
        k = re.match(r'\|\s*([\w-]+)\s*=\s*(.*)', line)
        if k: out[k.group(1)] = k.group(2).strip()
    return out
if __name__ == '__main__':
    print(json.dumps(infobox(json.load(open(sys.argv[1], encoding='utf-8'))['wikitext']), ensure_ascii=False, indent=1))
