#!/usr/bin/env python3
"""Special Orders (town board) from https://stardewvalleywiki.com/Quests, section "List of Special Orders".
Page revision 195566 (2026-11-19T23:11:33Z), read 2026-11-27 in a browser (the site blocks scripted fetches),
so the rows below are transcribed from that table. Writes data/{special_order,special_order_target,entity_source}.special_orders.json.
Target item names are resolved to item.id through the current stardew.sqlite; names that are categories
(e.g. "River Fish") keep item_id = null and only a label.
Usage: python3 scripts/import_special_orders.py && python3 scripts/build_db.py"""
import json, os, re, sqlite3
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REV, REV_TS, ACCESSED = 195566, '2026-11-19T23:11:33Z', '2026-11-27'

# name, requester npc id, prerequisite (as written), days, repeatable, objective (as written)
# targets: (label, qty, one_of, season, kind)   kind = item | monster | category
O = [
 ("Island Ingredients", "caroline", "Ginger Island unlocked", 28, True,
  "Harvest, then ship 100 of one of the following: Taro Root, Ginger, Pineapple. Crops must be harvested while quest is active. Ginger dropped by Tiger Slimes counts toward the total.",
  [("Taro Root",100,1,None,"item"),("Ginger",100,1,None,"item"),("Pineapple",100,1,None,"item")]),
 ("Cave Patrol", "clint", "None", 7, True,
  "Slay 50 of one of the following: Bats, Dust Sprites, Skeletons, Grubs",
  [("bats",50,1,None,"monster"),("dust_sprite",50,1,None,"monster"),("skeleton",50,1,None,"monster"),("grub",50,1,None,"monster")]),
 ("Aquatic Overpopulation", "demetrius", "None", 7, True,
  "Catch 10 of one of the following (depending on the season): Spring: Flounder, Halibut, Largemouth Bass, Sardine, Sunfish; Summer: Dorado, Rainbow Trout, Red Mullet, Tilapia, Tuna; Fall: Albacore, Midnight Carp, Salmon, Tiger Trout; Winter: Lingcod, Perch, Squid",
  [(f,10,1,s,"item") for s,fs in [("Spring",["Flounder","Halibut","Largemouth Bass","Sardine","Sunfish"]),("Summer",["Dorado","Rainbow Trout","Red Mullet","Tilapia","Tuna"]),("Fall",["Albacore","Midnight Carp","Salmon","Tiger Trout"]),("Winter",["Lingcod","Perch","Squid"])] for f in fs]),
 ("Biome Balance", "demetrius", "None", 7, True,
  "Catch 20 of one of the following: River Fish, Ocean Fish, Lake Fish",
  [("River Fish",20,1,None,"category"),("Ocean Fish",20,1,None,"category"),("Lake Fish",20,1,None,"category")]),
 ("Rock Rejuvenation", "emily", "Have access to the Sewing Machine in Emily's House", 7, False,
  "Deliver to Emily all of the following: Ruby (1), Topaz (1), Emerald (1), Jade (1), Amethyst (1). Can be collected before accepting the special order",
  [(g,1,0,None,"item") for g in ["Ruby","Topaz","Emerald","Jade","Amethyst"]]),
 ("Gifts for George", "evelyn", "Spring", 28, False,
  "Collect, then place onto Evelyn's stove: Leek (12). Items must be collected while quest is active. Leeks grown and harvested from Spring Seeds count toward this quest.",
  [("Leek",12,0,None,"item")]),
 ("Fragments of the past", "gunther", "None", 7, False,
  "Collect 100 of any combination of bone items, then dump in the box in the Museum. Items must be collected while quest is active.",
  [("Bone items (any combination)",100,0,None,"category")]),
 ("Gus' Famous Omelet", "gus", "None", 14, True,
  "Collect, then place into the fridge of the Stardrop Saloon: 24 Eggs gathered from the ground or from an Auto-Grabber, or purchased, after the quest begins. Eggs can be from any animal (e.g., chicken, duck, dinosaur). Chicken eggs can be of any size and color.",
  [("Eggs (any animal)",24,0,None,"category")]),
 ("Crop Order", "lewis", "Not Winter", 28, True,
  "Harvest, then ship 100 of one of the following (depending on the season): Spring: Cauliflower, Garlic, Green Bean, Potato; Summer: Blueberry, Hot Pepper, Melon, Radish, Tomato, Wheat; Fall: Amaranth, Artichoke, Bok Choy, Cranberries, Eggplant, Grape, Pumpkin, Yam. Crops must be harvested while quest is active.",
  [(c,100,1,s,"item") for s,cs in [("Spring",["Cauliflower","Garlic","Green Bean","Potato"]),("Summer",["Blueberry","Hot Pepper","Melon","Radish","Tomato","Wheat"]),("Fall",["Amaranth","Artichoke","Bok Choy","Cranberries","Eggplant","Grape","Pumpkin","Yam"])] for c in cs]),
 ("Community Cleanup", "linus", "None", 7, False,
  "Gather, then dump in the bin at the train platform: 20 trash items (except Joja Cola and Rotten Plant). Gathering counter works with Crab Pots, Garbage Cans, and trash caught by Fishing.",
  [("Trash items (except Joja Cola and Rotten Plant)",20,0,None,"category")]),
 ("The Strong Stuff", "pam", "Spring", 14, False,
  "Collect, then place in Pam's kitchen: 12 Potato Juice. Juice must be collected from Keg while quest is active.",
  [("Potato Juice",12,0,None,"category")]),
 ("Pierre's Prime Produce", "pierre", "None", 28, False,
  "Harvest, then dump in the bin in Pierre's General Store: 25 Gold-quality Vegetables. Items must be harvested while the quest is active. Iridium quality vegetables do not count. Fiddlehead Fern does not count.",
  [("Gold-quality Vegetables",25,0,None,"category")]),
 ("Robin's Project", "robin", "None", 7, False,
  "Collect: Hardwood (80). Items must be collected while quest is active.",
  [("Hardwood",80,0,None,"item")]),
 ("Robin's Resource Rush", "robin", "None", 7, True,
  "Collect 1000 of: Wood or Stone. Can be purchased from Robin's shop. Wood obtained from a Wood Chipper counts.",
  [("Wood",1000,1,None,"item"),("Stone",1000,1,None,"item")]),
 ("Juicy Bugs Wanted!", "willy", "None", 7, False,
  "Collect, then dump in the bin next to the fish shop: Bug Meat (100). Items must be collected while quest is active.",
  [("Bug Meat",100,0,None,"item")]),
 ("Tropical Fish", "willy", "Ginger Island unlocked, Island Resort built", 7, False,
  "Stingray (5), Blue Discus (5), Lionfish (5)",
  [(f,5,0,None,"item") for f in ["Stingray","Blue Discus","Lionfish"]]),
 ("A Curious Substance", "wizard", "None", 7, False, "Ectoplasm (1)", [("Ectoplasm",1,0,None,"item")]),
 ("Prismatic Jelly", "wizard", "None", 7, False, "Prismatic Jelly (1)", [("Prismatic Jelly",1,0,None,"item")]),
]

def slug(s): return re.sub(r'[^a-z0-9]+', '_', s.lower().replace("'", '')).strip('_')

def main():
    con = sqlite3.connect(os.path.join(ROOT, 'stardew.sqlite'))
    by_name = {n.lower(): i for i, n in con.execute('SELECT id, name_en FROM item')}
    mons = {i for (i,) in con.execute('SELECT id FROM monster')}
    orders, targets, src, missing = [], [], [], []
    for sort, (name, npc, pre, days, rep, obj, tg) in enumerate(O, 1):
        oid = 'so_' + slug(name)
        orders.append({'id': oid, 'name_en': name, 'requester_npc_id': npc, 'board': 'town', 'prerequisite_en': pre,
                       'days': days, 'repeatable': rep, 'objective_en': obj, 'content_pack': 'vanilla', 'sort': sort})
        for seq, (label, qty, one_of, season, kind) in enumerate(tg, 1):
            row = {'order_id': oid, 'seq': seq, 'kind': kind, 'label_en': label, 'qty': qty, 'one_of': bool(one_of), 'season': season,
                   'item_id': None, 'monster_id': None}
            if kind == 'item':
                row['item_id'] = by_name.get(label.lower())
                if not row['item_id']: row['kind'] = 'category'; missing.append(label)
            elif kind == 'monster':
                row['monster_id'] = label if label in mons else None
                if not row['monster_id']: missing.append(label)
            targets.append(row)
        src.append({'entity_type': 'special_order', 'entity_id': oid, 'source_id': 'wiki_official', 'page_title': 'Quests',
                    'url': 'https://stardewvalleywiki.com/Quests#List_of_Special_Orders', 'revision_ts': REV_TS, 'revision_id': REV,
                    'accessed_at': ACCESSED, 'confidence': 'medium', 'verified': False})
    for t, rows in [('special_order', orders), ('special_order_target', targets), ('entity_source', src)]:
        json.dump(rows, open(os.path.join(ROOT, 'data', f'{t}.special_orders.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(orders)} orders, {len(targets)} targets; unresolved items/monsters (kept as label only): {missing or "none"}')
main()
