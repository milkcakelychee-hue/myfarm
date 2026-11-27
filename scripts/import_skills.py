#!/usr/bin/env python3
"""Skills importer: profession table (level 5/10 per skill), crop-quality / fertilizer / quality-price constants,
and Pierre's fertilizer prices. Every number is parsed from the cached wiki text (never typed by hand).
Output: data/{profession,game_constant,shop_price,entity_source}.skills.json
Usage: python3 scripts/import_skills.py"""
import html, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from wikitext import page, src, clean, slug, write_fragments

SKILLS = ['Farming', 'Fishing', 'Foraging', 'Mining', 'Combat']
# profession -> bonus_kind for professions whose effect is a plain multiplier the app applies (value comes from the text)
BONUS = {'Rancher': 'animal_product_price', 'Tiller': 'crop_price', 'Artisan': 'artisan_price',
         'Agriculturist': 'growth_speed', 'Fisher': 'fish_price', 'Angler': 'fish_price',
         'Blacksmith': 'metal_bar_price', 'Gemologist': 'gem_price', 'Tapper': 'syrup_price'}


def die(msg): sys.exit('import_skills: ' + msg)


def need(m, what):
    if not m: die(f'could not find {what} on the wiki page - check the page text')
    return m


def get(title):
    pg = page(title)
    if not pg: die(f'page {title!r} not in cache')
    return pg


def prof_cells(block):
    """Table cells that hold a profession: "'''Name'''" then effect text up to the next cell."""
    out = []
    for m in re.finditer(r"\n\|[^\n]*?'''([^'\n]+)'''[ \t]*\n(.*?)(?=\n\||\n!|\Z)", block, re.S):
        desc = html.unescape(clean(re.sub(r'^\s*:\s*', '', m.group(2), flags=re.M).replace('\n', ' ')) or '')
        desc = re.sub(r',? see details here\)', ')', desc)
        out.append((m.group(1).strip(), desc))
    return out


def bonus(name, desc):
    kind = BONUS.get(name)
    m = re.search(r'worth (\d+)% more', desc or '')
    if m and not kind: die(f'{name}: "+N% worth" profession without a bonus_kind mapping - add one to BONUS')
    if not kind: return None, None
    if kind == 'growth_speed':
        m = need(re.search(r'grow (\d+)% faster', desc), name + ' growth %')
        return kind, int(m.group(1)) / 100
    need(m, f'{name} "worth N% more"')
    return kind, round(1 + int(m.group(1)) / 100, 4)


def professions(R):
    for skill in SKILLS:
        pg = get(skill + ' Skill'); wt = pg['wikitext']
        i5, i10 = wt.find('Level 5'), wt.find('Level 10')
        if i5 < 0 or i10 < 0: die(f'{skill} Skill: Level 5 / Level 10 headers not found')
        lv5, lv10 = prof_cells(wt[i5:i10]), prof_cells(wt[i10:])
        names5 = [n for n, _ in lv5]
        parents = [h for h in re.findall(r"class=\"skillsubheader\"\s*\|\s*''([^':]+):''", wt[i10:]) if h in names5]
        if len(lv5) != 2 or len(lv10) != 4 or parents != names5:
            die(f'{skill} Skill: expected 2+4 professions with parent headers, got {lv5} {lv10} {parents}')
        rows = [(n, d, 5, None) for n, d in lv5] + [(n, d, 10, slug(parents[k % 2])) for k, (n, d) in enumerate(lv10)]
        for n, d, lvl, parent in rows:
            kind, v = bonus(n, d)
            pid = slug(n)
            R['profession'].append({'id': pid, 'skill': skill, 'level': lvl, 'parent_id': parent, 'name_en': n,
                                    'name_th': None, 'description_en': d, 'bonus_kind': kind, 'bonus_value': v})
            R['entity_source'].append(src('profession', pid, pg))


def constants(R):
    def add(key, value, unit, note, pg):
        R['game_constant'].append({'key': key, 'value': int(round(value)), 'unit': unit, 'note': note})
        R['entity_source'].append(src('game_constant', key, pg))
    pg = get('Farming'); wt = pg['wikitext']
    i = wt.find('===Crop Quality Frequency'); f = wt[i:]
    if i < 0: die('Farming: Crop Quality Frequency section not found')
    m = need(re.search(r'<code>([\d.]+) \* \(farming level / (\d+)\) \+ ([\d.]+) \* \(fertilizer level\) \* \(\(farming level \+ (\d+)\) / (\d+)\) \+ ([\d.]+)</code>', f), 'gold formula')
    a, lvdiv, b, lvadd, div2, base = m.groups()
    note = 'Crop gold chance = lvl_coef*(level/lvl_div) + fert_coef*fert*((level+fert_lvl_add)/fert_div) + base'
    add('quality_gold_level_coef_x1000', float(a) * 1000, 'x1000', note + ': lvl_coef', pg)
    add('quality_gold_level_div', int(lvdiv), None, note + ': lvl_div', pg)
    add('quality_gold_fert_coef_x1000', float(b) * 1000, 'x1000', note + ': fert_coef', pg)
    add('quality_gold_fert_level_add', int(lvadd), None, note + ': fert_lvl_add', pg)
    add('quality_gold_fert_div', int(div2), None, note + ': fert_div', pg)
    add('quality_gold_base_x1000', float(base) * 1000, 'x1000', note + ': base', pg)
    m = need(re.search(r'<code>(\d+) \* chance for gold quality</code> \(capped at (\d+)%\)', f), 'silver formula')
    add('quality_silver_gold_mult', int(m.group(1)), None, 'Crop silver chance = this * gold chance (checked only if gold fails)', pg)
    add('quality_silver_cap_x1000', int(m.group(2)) * 10, 'x1000', 'Cap on crop silver chance (fraction x1000)', pg)
    m = need(re.search(r'<code>chance for gold quality / (\d+)</code>', f), 'iridium formula')
    add('quality_iridium_gold_div', int(m.group(1)), None, 'Crop iridium chance = gold chance / this; only with Deluxe (or better) fertilizer, which also makes silver the minimum quality', pg)
    m = need(re.search(r'0 for normal soil, (\d) for \[\[Basic Fertilizer\]\], (\d) for \[\[Quality Fertilizer\]\], and (\d) for \[\[Deluxe Fertilizer\]\]', f), 'fertilizer levels')
    for n, v in zip(['basic', 'quality', 'deluxe'], m.groups()):
        add(f'fertilizer_level_{n}', int(v), 'level', f'{n.title()} Fertilizer level used in the crop quality formula (normal soil = 0)', pg)
    m = need(re.search(r'iridium products are worth ([\d.]+)× base price, gold products are worth ([\d.]+)× base price, and silver products are worth ([\d.]+)× base price', wt), 'quality price multipliers')
    for q, v in zip(['iridium', 'gold', 'silver'], m.groups()):
        add(f'quality_price_{q}_x1000', float(v) * 1000, 'x1000', f'Sell price multiplier for {q} quality (stated on Farming page for animal products; same multipliers used for crops)', pg)


def friendship(R):
    pg = get('Friendship'); wt = pg['wikitext']
    def add(key, value, unit, note):
        R['game_constant'].append({'key': key, 'value': value, 'unit': unit, 'note': note})
        R['entity_source'].append(src('game_constant', key, pg))
    m = need(re.search(r'Each heart is (\d+) friendship points', wt), 'points per heart')
    add('friendship_points_per_heart', int(m.group(1)), 'points', 'Friendship points per heart')
    m = need(re.search(r'birthday \(×(\d+)\)', wt), 'birthday multiplier')
    add('gift_birthday_mult', int(m.group(1)), 'x', 'Gift friendship points are multiplied by this on the villager birthday')
    for t in ['Love', 'Like', 'Neutral', 'Dislike', 'Hate']:
        m = need(re.search(r'^\|\s*' + t + r'\s*\n\|\s*([+-−]?\d+)', wt, re.M), f'{t} gift points')
        add(f'gift_points_{t.lower()}', int(m.group(1).replace('−', '-')), 'points', f'Friendship points for a {t.lower()}d gift on a normal day (no Friendship 101)')


def shop(R):
    for title, cond_re in [('Basic Fertilizer', None), ('Quality Fertilizer', r'beginning in Year (\d+)')]:
        pg = get(title); wt = pg['wikitext']
        m = need(re.search(r"\{\{Price\|(\d+)\}\} (?:from \[\[Pierre's General Store\]\]|starting)|purchased from \[\[Pierre's General Store\]\] for \{\{Price\|(\d+)\}\}", wt), title + " Pierre's price")
        price = int(m.group(1) or m.group(2))
        cond = ''
        if cond_re: cond = f'Year {need(re.search(cond_re, wt), title + " year").group(1)}+'
        iid = slug(title)
        R['shop_price'].append({'item_id': iid, 'shop': "Pierre's General Store", 'price': price, 'currency': 'g', 'condition': cond})
        R['entity_source'].append(src('shop_price', iid, pg))
    if "Pierre" in (re.search(r'\|source\s*=([^\n]*)', get('Deluxe Fertilizer')['wikitext']) or [''])[0]:
        die('Deluxe Fertilizer now lists Pierre as a source - add it to shop()')


def main():
    R = {'profession': [], 'game_constant': [], 'shop_price': [], 'entity_source': []}
    professions(R); constants(R); friendship(R); shop(R)
    write_fragments('skills', R)


if __name__ == '__main__':
    main()
