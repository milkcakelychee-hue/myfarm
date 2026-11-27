#!/usr/bin/env python3
"""download wikitext for MediaWiki sources into cache/ and skip unchanged pages.
Run on a machine with normal internet access (e.g. Claude Code on the user's computer), NOT through a chat tool.
  python3 scripts/fetch_wiki.py wiki_official --category Crops
  python3 scripts/fetch_wiki.py wiki_official --titles Pumpkin Barn
  python3 scripts/fetch_wiki.py wiki_sve --category Characters
Cache layout: cache/<source_id>/<safe_title>.json = {title, revid, timestamp, wikitext, accessed_at}
Be polite: 1 request/second, custom User-Agent, batches of <=50 titles."""
import argparse, json, os, re, time, datetime
import urllib.parse, subprocess
API = {'wiki_official': 'https://stardewvalleywiki.com/mediawiki/api.php',
       'wiki_sve': 'https://stardewvalleyexpanded.wiki.gg/api.php',
       'wiki_fandom': 'https://stardewvalley.fandom.com/api.php'}
UA = {'User-Agent': 'StardewCompanionPersonalDB/0.1 (personal, non-commercial; personal use)'}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def call(src, **p):
    p.update(format='json', formatversion=2)
    time.sleep(float(os.environ.get("WIKI_DELAY", "2.0")))                                  # polite: the wiki starts returning 403 at ~1 req/s sustained
    # transport = system curl (python urllib is refused by the wiki's Cloudflare front; curl gets a normal 200)
    url = API[src] + '?' + urllib.parse.urlencode(p)
    for attempt in range(3):                       # retry transient network errors with back-off
        out = subprocess.run(['curl', '-sS', '--fail', '-A', UA['User-Agent'], '--max-time', '90', url], capture_output=True)
        if out.returncode == 0: return json.loads(out.stdout)
        if b'403' in out.stderr: break             # firewall rejects this exact URL: retrying won't help
        time.sleep(10 * (attempt + 1))
    raise RuntimeError(f'curl failed {out.returncode}: {out.stderr.decode()[:200]}')

def category_titles(src, cat):
    out, cont = [], {}
    while True:
        j = call(src, action='query', list='categorymembers', cmtitle=f'Category:{cat}', cmlimit=500, cmtype='page', **cont)
        out += [m['title'] for m in j['query']['categorymembers']]
        if 'continue' not in j: return out
        cont = j['continue']

def all_titles(src):
    out, cont = [], {}
    while True:
        j = call(src, action='query', list='allpages', apnamespace=0, apfilterredir='nonredirects', aplimit=500, **cont)
        out += [m['title'] for m in j['query']['allpages']]
        if 'continue' not in j: return out
        cont = j['continue']

def safe(t): return re.sub(r'[^\w.-]+', '_', t)

def fetch(src, titles, missing_only=False):
    d = os.path.join(ROOT, 'cache', src); os.makedirs(d, exist_ok=True)
    if missing_only: titles = [t for t in titles if not os.path.exists(os.path.join(d, safe(t) + '.json'))]
    print(len(titles), 'titles to fetch')
    blocked = []
    B = int(os.environ.get("WIKI_BATCH", "20"))         # the wiki firewall rejects some multi-title URLs: use 1 if you see 403
    for i in range(0, len(titles), B):
        batch = titles[i:i+B]
        try:
            j = call(src, action='query', prop='revisions', rvprop='ids|timestamp|content', rvslots='main', titles='|'.join(batch), redirects=1)
        except RuntimeError as e:
            print('BLOCKED', ' | '.join(batch), '-', str(e)[:60]); blocked.extend(batch); continue
        for p in j['query']['pages']:
            if p.get('missing') or 'revisions' not in p: print('missing', p['title']); continue
            rev = p['revisions'][0]; f = os.path.join(d, safe(p['title']) + '.json')
            if os.path.exists(f) and json.load(open(f, encoding='utf-8')).get('revid') == rev['revid']: continue   # unchanged
            json.dump({'title': p['title'], 'revid': rev['revid'], 'timestamp': rev['timestamp'], 'wikitext': rev['slots']['main']['content'],
                       'accessed_at': datetime.date.today().isoformat()}, open(f, 'w', encoding='utf-8'), ensure_ascii=False)
            print('saved', p['title'])
    if blocked:
        json.dump(blocked, open(os.path.join(d, '..', f'blocked_{src}.json'), 'w'), ensure_ascii=False, indent=0)
        print(len(blocked), 'titles blocked by the wiki firewall -> cache/blocked_' + src + '.json')

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('source', choices=API); ap.add_argument('--category'); ap.add_argument('--titles', nargs='*'); ap.add_argument('--all', action='store_true'); ap.add_argument('--missing-only', action='store_true')
    a = ap.parse_args(); t = (all_titles(a.source) if a.all else []) + (category_titles(a.source, a.category) if a.category else []) + (a.titles or [])
    fetch(a.source, t, a.missing_only)
