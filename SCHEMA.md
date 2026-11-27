# SCHEMA (v2)

ดูนิยามเต็มใน `schema.sql` นี่คือคำอธิบายแนวคิด

| ตาราง | เก็บอะไร | ใช้คำนวณอะไร |
|---|---|---|
| `item` | ไอเท็มทุกชนิด (id = slug ชื่ออังกฤษ), ราคาขายฐาน, edibility, ชื่ออังกฤษ/ไทย + สถานะชื่อไทย, `is_approx` | กำไร/ราคา |
| `crop` + `crop_season` | วันโต, วันงอกซ้ำ, XP, ฤดูที่ปลูกได้ (หลายฤดูได้) | ปฏิทินปลูก-เก็บ, "ใกล้จบฤดู" |
| `shop_price` | ราคาซื้อ (เมล็ด ฯลฯ) ตามร้านและเงื่อนไข | ต้นทุน/ROI |
| `fish` | สถานที่ ฤดู สภาพอากาศ ช่วงเวลา ความยาก | Wiki ปลา |
| `machine` + `processing_rule` | เครื่องแปรรูป และกฎ input→output, เวลา, สูตรราคา | โหมดคำนวณแปรรูป |
| `recipe` + `recipe_ingredient` | สูตรอาหาร/คราฟต์และวัตถุดิบ | เช็กลิสต์วัตถุดิบ |
| `bundle` + `bundle_item` | Bundle ตามห้อง ของที่ต้องใช้ คุณภาพขั้นต่ำ | เทมเพลตบริจาค |
| `npc`, `gift_taste`, `calendar_event` | วันเกิด ความชอบของขวัญ เทศกาล | ปฏิทิน/เทมเพลตของขวัญ |
| `building` + `building_material` | อาคาร Robin/Wizard, ราคา, วัตถุดิบ | เทมเพลตสร้างสิ่งปลูกสร้าง (หน้า 06–07) |
| `tool_upgrade` | ราคาอัปเกรดเครื่องมือ ระดับ แท่งโลหะ | เทมเพลตอัปเกรด |
| `image` | ไฟล์รูป ที่มา ขนาด hash สถานะ | UI |
| `entity_source` | ที่มา/revision/วันที่เข้าถึง/ความมั่นใจ/ตรวจแล้วหรือยัง ของทุกแถว | ตรวจสอบ+อัปเดต |
| `user_override` | ค่าที่คุณแก้เอง (เช่นชื่อไทย) ใช้ทับเสมอ | กันอัปเดตทับ |
| `changelog`, `meta`, `source` | บันทึกการเปลี่ยนแปลง เวอร์ชัน ข้อมูลแหล่ง | — |

## หมายเหตุสำคัญ
- **วัน/ฤดู:** ฤดูละ 28 วัน, วันที่ 1 เป็นวันจันทร์ ใช้ค่า `Spring|Summer|Fall|Winter`
- **เวลา:** `time_start/time_end` เป็นเวลา 24 ชม. แบบเกม (เช่น 600 = 6:00, 2600 = 2:00 ของวันถัดไป)
- **คอลัมน์ JSON:** เก็บเป็นข้อความ JSON (เช่น `stage_days`, `fish.locations`)
- **`price_formula`:** เก็บเป็นข้อความ เช่น `price*2` ให้ตัวคำนวณในแอปตีความ จะกำหนดไวยากรณ์ตอนทำรอบแปรรูป
- **คุณภาพ:** `normal|silver|gold|iridium` (ราคา/ตัวคูณจะเพิ่มเมื่อถึงรอบที่ต้องใช้)
- **Pilot ปัจจุบัน:** `item` 2 แถว (pumpkin, pumpkin_seeds), `crop` 1, `crop_season` 1, `image` 1

## special_order / special_order_target (schema v9)
- `special_order`: Special Order บนบอร์ดในเมือง 18 รายการ จากหน้า wiki Quests (ชื่อ, `requester_npc_id`, เงื่อนไข, `days`, `repeatable`, `objective_en` ข้อความตามวิกิ)
- `special_order_target`: ของที่ต้องส่ง/จับ/ล่า ต่อภารกิจ `kind` = item | monster | category, `one_of=1` คือเลือกอย่างใดอย่างหนึ่ง (แยกตาม `season` ถ้ามี)
- ยังไม่มี Qi's Special Orders และของ SVE

## npc_romance (schema v10)
- ผู้ที่แต่งงานได้ แยก bachelor / bachelorette · เกมหลักจากหน้า wiki Marriage · SVE ตั้งโดยเจ้าของ (source = owner)
