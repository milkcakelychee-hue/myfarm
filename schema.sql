-- Stardew companion DB schema (v3). Source of truth = data/*.json ; this SQLite file is rebuilt from them by scripts/build_db.py
PRAGMA foreign_keys = ON;

CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);

CREATE TABLE source (
  id TEXT PRIMARY KEY,               -- wiki_official | wiki_th | wiki_fandom | wiki_sve | game_files
  name TEXT NOT NULL, base_url TEXT NOT NULL,
  role TEXT NOT NULL,                -- primary | secondary | thai_text | mod_content | ground_truth
  license TEXT, notes TEXT
);

CREATE TABLE image (
  id TEXT PRIMARY KEY,
  file_path TEXT,                    -- relative, e.g. images/items/pumpkin.png (NULL until downloaded)
  origin TEXT NOT NULL CHECK (origin IN ('wiki','game','self')),
  source_id TEXT REFERENCES source(id),
  source_url TEXT, width INTEGER, height INTEGER, sha1 TEXT,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','downloaded','replaced_by_game')),
  notes TEXT
);

CREATE TABLE item (
  id TEXT PRIMARY KEY,               -- slug of English name, e.g. pumpkin
  name_en TEXT NOT NULL,
  name_th TEXT,
  name_th_status TEXT NOT NULL DEFAULT 'none' CHECK (name_th_status IN ('none','placeholder','fan','self')),
  category TEXT,
  sell_price INTEGER,                -- base (normal quality), gold
  edibility INTEGER,
  description_en TEXT, description_th TEXT,
  image_id TEXT REFERENCES image(id),
  content_pack TEXT NOT NULL DEFAULT 'vanilla' CHECK (content_pack IN ('vanilla','sve')),
  is_approx INTEGER NOT NULL DEFAULT 0   -- 1 = value is approximate (UI shows "approx" badge)
);

CREATE TABLE crop (
  item_id TEXT PRIMARY KEY REFERENCES item(id),   -- the harvested item
  seed_item_id TEXT REFERENCES item(id),
  growth_days INTEGER NOT NULL,                    -- days from planting to first harvest
  regrow_days INTEGER,                             -- NULL = single harvest
  xp INTEGER,
  min_harvest INTEGER NOT NULL DEFAULT 1, max_harvest INTEGER NOT NULL DEFAULT 1,
  stage_days TEXT,                                 -- JSON array, days per stage
  notes TEXT
);
CREATE TABLE crop_season (
  crop_id TEXT NOT NULL REFERENCES crop(item_id),
  season TEXT NOT NULL CHECK (season IN ('Spring','Summer','Fall','Winter')),
  PRIMARY KEY (crop_id, season)
);

CREATE TABLE shop_price (
  item_id TEXT NOT NULL REFERENCES item(id),
  shop TEXT NOT NULL, price INTEGER NOT NULL, currency TEXT NOT NULL DEFAULT 'g',
  condition TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (item_id, shop, condition)
);

CREATE TABLE fish (
  item_id TEXT PRIMARY KEY REFERENCES item(id),
  locations TEXT, seasons TEXT, weather TEXT,      -- JSON arrays / text
  time_start INTEGER, time_end INTEGER,            -- 24h clock, e.g. 600..2600
  difficulty INTEGER, behavior TEXT
);

CREATE TABLE machine (
  id TEXT PRIMARY KEY, name_en TEXT NOT NULL, name_th TEXT, image_id TEXT REFERENCES image(id), notes TEXT
);
CREATE TABLE processing_rule (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  machine_id TEXT NOT NULL REFERENCES machine(id),
  input_item_id TEXT REFERENCES item(id), input_category TEXT,   -- one of the two
  input_qty INTEGER NOT NULL DEFAULT 1,
  output_item_id TEXT REFERENCES item(id), output_qty INTEGER NOT NULL DEFAULT 1,
  time_minutes INTEGER,
  price_formula TEXT,                              -- e.g. "price*2" / "price*3.0+50" (documented in SCHEMA.md)
  notes TEXT
);

CREATE TABLE recipe (
  id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK (kind IN ('cooking','crafting')),
  output_item_id TEXT REFERENCES item(id), output_qty INTEGER NOT NULL DEFAULT 1, unlock TEXT
);
CREATE TABLE recipe_ingredient (
  recipe_id TEXT NOT NULL REFERENCES recipe(id), item_id TEXT NOT NULL REFERENCES item(id),
  qty INTEGER NOT NULL, PRIMARY KEY (recipe_id, item_id)
);

CREATE TABLE bundle (
  id TEXT PRIMARY KEY, room TEXT NOT NULL, name_en TEXT NOT NULL, reward_text TEXT, required_count INTEGER
);
CREATE TABLE bundle_item (
  bundle_id TEXT NOT NULL REFERENCES bundle(id), item_id TEXT NOT NULL REFERENCES item(id),
  qty INTEGER NOT NULL DEFAULT 1, min_quality TEXT NOT NULL DEFAULT 'normal',
  PRIMARY KEY (bundle_id, item_id, min_quality)
);

CREATE TABLE npc (
  id TEXT PRIMARY KEY, name_en TEXT NOT NULL, name_th TEXT,
  birthday_season TEXT CHECK (birthday_season IN ('Spring','Summer','Fall','Winter')), birthday_day INTEGER,
  marriageable INTEGER NOT NULL DEFAULT 0, image_id TEXT REFERENCES image(id),
  content_pack TEXT NOT NULL DEFAULT 'vanilla' CHECK (content_pack IN ('vanilla','sve')),
  home TEXT                                        -- where they live (villager infobox 'address', cleaned)
);
CREATE TABLE npc_schedule (                        -- regular + rain day schedules (scripts/import_schedules.py)
  npc_id TEXT NOT NULL REFERENCES npc(id),
  season TEXT CHECK (season IN ('Spring','Summer','Fall','Winter')),   -- NULL = all seasons
  day_kind TEXT NOT NULL CHECK (day_kind IN ('normal','rain','other')),
  time INTEGER NOT NULL,                           -- game time: 900 = 9:00 AM, 2530 = 1:30 AM next day
  location TEXT, note TEXT,
  location_th TEXT, note_th TEXT,                  -- v7: Thai from data/npc_schedule_th.json
  PRIMARY KEY (npc_id, season, day_kind, time)
);
CREATE TABLE gift_taste (
  npc_id TEXT NOT NULL REFERENCES npc(id), item_id TEXT NOT NULL REFERENCES item(id),
  taste TEXT NOT NULL CHECK (taste IN ('love','like','neutral','dislike','hate')),
  PRIMARY KEY (npc_id, item_id)
);
CREATE TABLE calendar_event (
  id TEXT PRIMARY KEY,
  season TEXT NOT NULL CHECK (season IN ('Spring','Summer','Fall','Winter')),
  day_start INTEGER NOT NULL, day_end INTEGER,
  kind TEXT NOT NULL CHECK (kind IN ('festival','birthday','event','other')),
  name_en TEXT NOT NULL, npc_id TEXT REFERENCES npc(id), notes TEXT
);

CREATE TABLE building (
  id TEXT PRIMARY KEY, builder TEXT NOT NULL,      -- Robin | Wizard | other
  name_en TEXT NOT NULL, name_th TEXT, cost_gold INTEGER, build_days INTEGER, max_count INTEGER,
  image_id TEXT REFERENCES image(id), content_pack TEXT NOT NULL DEFAULT 'vanilla' CHECK (content_pack IN ('vanilla','sve')),
  size_w INTEGER, size_h INTEGER,                 -- footprint in tiles as the wiki writes it (Barn 7x4)
  upgrade_from TEXT REFERENCES building(id)        -- big_barn -> barn; NULL = not an upgrade
);
CREATE TABLE building_material (
  building_id TEXT NOT NULL REFERENCES building(id), item_id TEXT NOT NULL REFERENCES item(id),
  qty INTEGER NOT NULL, PRIMARY KEY (building_id, item_id)
);
CREATE TABLE tool_upgrade (
  tool TEXT NOT NULL, level TEXT NOT NULL, gold INTEGER NOT NULL,
  bar_item_id TEXT REFERENCES item(id), bar_qty INTEGER, PRIMARY KEY (tool, level)
);

-- Special Orders (town board), from the wiki Quests page. Targets: one row per thing to deliver/catch/slay.
CREATE TABLE special_order (
  id TEXT PRIMARY KEY, name_en TEXT NOT NULL, name_th TEXT,
  requester_npc_id TEXT REFERENCES npc(id),
  board TEXT NOT NULL DEFAULT 'town' CHECK (board IN ('town','qi')),
  prerequisite_en TEXT, days INTEGER, repeatable INTEGER NOT NULL DEFAULT 0,
  objective_en TEXT,                                 -- requirement text as written on the wiki
  content_pack TEXT NOT NULL DEFAULT 'vanilla' CHECK (content_pack IN ('vanilla','sve')),
  sort INTEGER
);
CREATE TABLE special_order_target (
  order_id TEXT NOT NULL REFERENCES special_order(id), seq INTEGER NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('item','monster','category')),
  item_id TEXT REFERENCES item(id), monster_id TEXT REFERENCES monster(id),
  label_en TEXT NOT NULL, qty INTEGER,
  one_of INTEGER NOT NULL DEFAULT 0,                 -- 1 = choose one of the rows with one_of=1 (per season if season set)
  season TEXT CHECK (season IN ('Spring','Summer','Fall','Winter')),
  PRIMARY KEY (order_id, seq)
);


-- provenance: every fact-bearing row should have at least one entity_source row
CREATE TABLE entity_source (
  entity_type TEXT NOT NULL,                       -- table name, e.g. item / crop / npc
  entity_id TEXT NOT NULL,
  source_id TEXT NOT NULL REFERENCES source(id),
  page_title TEXT NOT NULL, url TEXT,
  revision_ts TEXT,                                -- page revision timestamp (for change detection)
  revision_id INTEGER,
  accessed_at TEXT NOT NULL,
  confidence TEXT NOT NULL DEFAULT 'medium' CHECK (confidence IN ('high','medium','low')),
  verified INTEGER NOT NULL DEFAULT 0,             -- 1 = cross-checked (second source or game files)
  PRIMARY KEY (entity_type, entity_id, source_id, page_title)
);

-- hand edits (e.g. Thai names) that updates must never overwrite
CREATE TABLE user_override (
  entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, field TEXT NOT NULL, value TEXT, updated_at TEXT,
  PRIMARY KEY (entity_type, entity_id, field)
);

CREATE TABLE changelog (id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, round TEXT, summary TEXT NOT NULL);

-- v3 additions (full-database round): seasons for non-crop items, animals, monsters, item origins
CREATE TABLE item_season (
  item_id TEXT NOT NULL REFERENCES item(id),
  season TEXT NOT NULL CHECK (season IN ('Spring','Summer','Fall','Winter')),
  PRIMARY KEY (item_id, season)
);
CREATE TABLE item_location (                       -- where a forage / mineral / fish can be found (free text from the wiki)
  item_id TEXT NOT NULL REFERENCES item(id), location TEXT NOT NULL, PRIMARY KEY (item_id, location)
);
CREATE TABLE animal (
  id TEXT PRIMARY KEY, name_en TEXT NOT NULL, name_th TEXT,
  building TEXT NOT NULL CHECK (building IN ('Coop','Barn','Other')),
  building_level INTEGER,                            -- 1 = base, 2 = Big, 3 = Deluxe (minimum level that can house it)
  price INTEGER,                                     -- purchase price at Marnie's (NULL = not sold)
  produce_item_id TEXT REFERENCES item(id), deluxe_item_id TEXT REFERENCES item(id),
  produce_days INTEGER, mature_days INTEGER,
  image_id TEXT REFERENCES image(id), notes TEXT
);
CREATE TABLE monster (
  id TEXT PRIMARY KEY, name_en TEXT NOT NULL, name_th TEXT,
  hp INTEGER, damage INTEGER, defense INTEGER, speed INTEGER, xp INTEGER,
  locations TEXT,                                    -- JSON array of location names
  drops TEXT,                                        -- JSON array of {item, chance} as written on the wiki
  image_id TEXT REFERENCES image(id)
);

-- v4: single game numbers the app calculates with (sprinkler reach, housing capacity, greenhouse plots).
-- One row per number, each with provenance in entity_source (entity_type='game_constant').
CREATE TABLE game_constant (
  key TEXT PRIMARY KEY, value INTEGER NOT NULL, unit TEXT, note TEXT
);

-- v5: skill professions (level 5 / 10). bonus_kind/bonus_value only for plain multipliers the app applies
-- (price professions: multiplier e.g. 1.1; growth_speed: fraction faster e.g. 0.1). Provenance in entity_source.
CREATE TABLE profession (
  id TEXT PRIMARY KEY,
  skill TEXT NOT NULL CHECK (skill IN ('Farming','Fishing','Foraging','Mining','Combat')),
  level INTEGER NOT NULL CHECK (level IN (5,10)),
  parent_id TEXT REFERENCES profession(id),
  name_en TEXT NOT NULL, name_th TEXT, description_en TEXT,
  bonus_kind TEXT, bonus_value REAL
);

-- SVE locations page (scripts/import_locations.py); category = heading on the wiki Locations page, kept in English
CREATE TABLE location (
  id TEXT PRIMARY KEY, name_en TEXT NOT NULL, name_th TEXT, category TEXT NOT NULL, sort INTEGER,
  image_id TEXT REFERENCES image(id), description_en TEXT,
  content_pack TEXT NOT NULL DEFAULT 'sve' CHECK (content_pack IN ('vanilla','sve'))
);
-- other spellings of a location (e.g. in fish.locations) -> location.id
CREATE TABLE location_alias (alias TEXT PRIMARY KEY, location_id TEXT REFERENCES location(id));
