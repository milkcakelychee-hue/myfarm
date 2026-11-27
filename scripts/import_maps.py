#!/usr/bin/env python3
"""Maps importer: image row for the full in-game world map (used by the app's fishing map).
The file is the one the "Player Menu" page captions "The in-game map of Stardew Valley" (File:Map.png).
(File:World Map.png is the wall-hanging furniture / lore map, not the game map.)
Output: data/{image,entity_source}.maps.json ; then run scripts/download_images.py -> images/items/img_map_world.png
No pin coordinates are stored: no cached page carries an imagemap or coordinate data for this file."""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from wikitext import WIKI, page, src, write_fragments


def main():
    pg = page('Player Menu')
    m = re.search(r'\[\[File:([^|\]]+)\|[^\]]*The in-game map of Stardew Valley', pg['wikitext'] if pg else '')
    if not m: sys.exit('Player Menu: in-game map file reference not found')
    fname = m.group(1).strip()
    R = {'image': [{'id': 'img_map_world', 'file_path': None, 'origin': 'wiki', 'source_id': 'wiki_official',
                    'source_url': WIKI + 'File:' + fname.replace(' ', '_'), 'status': 'pending'}],
         'entity_source': [src('image', 'img_map_world', pg)]}
    write_fragments('maps', R)


if __name__ == '__main__':
    main()
