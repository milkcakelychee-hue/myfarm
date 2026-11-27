#!/usr/bin/env python3
"""Download item images (status 'pending') from the official wiki into images/items/<image_id>.png.
The file URL is computed the MediaWiki way (md5 of the file name -> /images/a/ab/Name.png), so no API calls.
Writes data/image.images.json (file_path, width, height, full sha1, status='downloaded').
build_db.py keeps the FIRST row per id and loads image.images.json before every other image fragment,
so downloaded rows win over the pending ones. Stops on the first 403 (wiki rate limit).
Usage: IMG_DELAY=1 python3 scripts/download_images.py"""
import glob, hashlib, json, os, struct, subprocess, sys, time, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'images', 'items')
UA = 'StardewCompanionPersonalDB/0.1 (personal, non-commercial; personal use)'
DELAY = float(os.environ.get('IMG_DELAY', '1.0'))


IMAGE_BASE = {'wiki_official': 'https://stardewvalleywiki.com/mediawiki/images',
              'wiki_sve': 'https://stardewvalleyexpanded.wiki.gg/images'}


def file_url(file_page_url, source_id='wiki_official'):
    name = urllib.parse.unquote(file_page_url.split('File:', 1)[1]).replace(' ', '_')
    if source_id == 'wiki_sve':          # wiki.gg serves flat /images/<Name> (hashed path 301s to it)
        return f'{IMAGE_BASE[source_id]}/{urllib.parse.quote(name)}'
    h = hashlib.md5(name.encode('utf-8')).hexdigest()
    return f'{IMAGE_BASE[source_id]}/{h[0]}/{h[:2]}/{urllib.parse.quote(name)}'


def png_size(b):
    return struct.unpack('>II', b[16:24]) if b[:8] == b'\x89PNG\r\n\x1a\n' else (None, None)


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'data', 'image.*.json'))):
        if p.endswith('image.images.json'): continue
        rows += json.load(open(p, encoding='utf-8'))
    done_p = os.path.join(ROOT, 'data', 'image.images.json')
    done = {r['id']: r for r in json.load(open(done_p, encoding='utf-8')) if r.get('width') and os.path.exists(os.path.join(ROOT, r['file_path']))} if os.path.exists(done_p) else {}
    failed = []

    def save():
        with open(done_p, 'w', encoding='utf-8') as f:
            f.write('[\n' + ',\n'.join(' ' + json.dumps(r, ensure_ascii=False) for r in done.values()) + '\n]\n')

    def record(r, dest):
        b = open(dest, 'rb').read(); w, h = png_size(b)
        done[r['id']] = {**r, 'file_path': f'images/items/{r["id"]}.png', 'width': w, 'height': h,
                         'sha1': hashlib.sha1(b).hexdigest(), 'status': 'downloaded'}
        print('ok', r['id'], w, h)

    for r in rows:
        if r['id'] in done or not r.get('source_url'): continue
        dest = os.path.join(OUT, r['id'] + '.png')
        if os.path.exists(dest) and open(dest, 'rb').read(8) == b'\x89PNG\r\n\x1a\n':
            record(r, dest); save(); continue          # already on disk from an interrupted run
        url = file_url(r['source_url'], r.get('source_id') or 'wiki_official')
        res = subprocess.run(['curl', '-sSL', '--fail', '-A', UA, '--max-time', '60', '-o', dest, url], capture_output=True)
        time.sleep(DELAY)
        if res.returncode != 0:
            failed.append((r['id'], res.stderr.decode().strip()[:80]))
            if os.path.exists(dest): os.remove(dest)
            if '403' in res.stderr.decode(): print('403 from wiki - stopping to back off'); break
            continue
        if open(dest, 'rb').read(8) != b'\x89PNG\r\n\x1a\n':
            failed.append((r['id'], 'not a PNG')); os.remove(dest); continue
        record(r, dest); save()
    save()
    print(f'downloaded {len(done)} total; failed this run: {len(failed)}')
    for i, e in failed[:30]: print('  FAIL', i, e)


if __name__ == '__main__':
    main()
