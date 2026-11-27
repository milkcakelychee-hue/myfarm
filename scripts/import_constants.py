#!/usr/bin/env python3
"""Game constants the app calculates with, read from the wiki text (never typed by hand).
Output: data/{game_constant,entity_source}.constants.json
Usage: python3 scripts/import_constants.py"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from wikitext import page, src, write_fragments


def need(m, what):
    if not m: sys.exit(f'import_constants: could not find {what} on the wiki page - check the page text')
    return m


def main():
    R = {'game_constant': [], 'entity_source': []}
    def add(key, value, unit, note, pg):
        R['game_constant'].append({'key': key, 'value': int(value), 'unit': unit, 'note': note})
        R['entity_source'].append(src('game_constant', key, pg))

    # sprinklers: "waters 4 tiles" / "waters the 8 adjacent tiles"
    for title, key in [('Sprinkler', 'sprinkler_tiles'), ('Quality Sprinkler', 'quality_sprinkler_tiles'),
                       ('Iridium Sprinkler', 'iridium_sprinkler_tiles')]:
        pg = page(title)
        m = need(re.search(r'waters (?:the )?(\d+) (?:adjacent )?tiles', pg['wikitext']), title + ' tiles')
        add(key, m.group(1), 'tiles', f'{title}: tiles watered', pg)

    # pressure nozzle: "*[[Iridium Sprinkler]]: 7x7" -> 7*7-1 (the sprinkler's own tile)
    pg = page('Pressure Nozzle')
    for name, key in [('Sprinkler', 'sprinkler_nozzle_tiles'), ('Quality Sprinkler', 'quality_sprinkler_nozzle_tiles'),
                      ('Iridium Sprinkler', 'iridium_sprinkler_nozzle_tiles')]:
        m = need(re.search(r'\*\[\[' + name + r'\]\]:\s*(\d+)x(\d+)', pg['wikitext']), 'nozzle ' + name)
        add(key, int(m.group(1)) * int(m.group(2)) - 1, 'tiles', f'{name} + Pressure Nozzle: {m.group(1)}x{m.group(2)} area minus the sprinkler tile', pg)

    # housing capacity: infobox row "Capacity" followed by 3 cells (base, big, deluxe)
    for title in ['Coop', 'Barn']:
        pg = page(title)
        m = need(re.search(r'\|Capacity\s*\n\|[^\n|]*\|(\d+)\s*\n\|[^\n|]*\|(\d+)\s*\n\|(\d+)', pg['wikitext']), title + ' capacity')
        for lvl, v in zip(['', 'big_', 'deluxe_'], m.groups()):
            add(f'{lvl}{title.lower()}_capacity', v, 'animals', f'{(lvl.rstrip("_").title() + " " if lvl else "")}{title}: animals housed', pg)

    # greenhouse soil: "...N crop spaces are occupied ... leaving room for M plants" -> N+M
    pg = page('Greenhouse')
    m = need(re.search(r'(\d+) crop spaces are occupied by sprinklers[^.]*?\.\s*Leaves room for (\d+) plants', pg['wikitext'], re.I)
             or re.search(r'(\d+) crop spaces are occupied[^|]*?room for (\d+) plants', pg['wikitext'], re.I), 'greenhouse plots')
    add('greenhouse_plots', int(m.group(1)) + int(m.group(2)), 'tiles', 'Greenhouse soil tiles (occupied by sprinklers + left for plants)', pg)
    write_fragments('constants', R)


if __name__ == '__main__':
    main()
