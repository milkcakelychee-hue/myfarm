# วิธีอัปเดตฐานข้อมูล

หลักการ: **JSON คือแหล่งความจริง**, SQLite สร้างใหม่ได้ทุกเมื่อ, สิ่งที่แก้เองอยู่ใน `user_override` และไม่ถูกทับ

## ขั้นตอนอัปเดตข้อมูลจากเว็บ
1. ดูว่าหน้าไหนเปลี่ยน: เทียบ `revision_id` ใน `entity_source` กับ revision ปัจจุบันจาก API (`prop=revisions&rvprop=ids|timestamp`) หรือใช้ `list=recentchanges` สำหรับ MediaWiki
2. ดึงเฉพาะหน้าที่เปลี่ยนด้วย `scripts/fetch_wiki.py` (ข้ามหน้าที่ revid เดิมอยู่แล้ว)
3. แปลงเป็นแถวใหม่ (`parse_infobox.py` หรือตัวแปลงของหมวดนั้น) แล้วแก้ `data/<table>.json` ด้วยการ **upsert ตามคีย์หลัก** ไม่ลบแถวที่ไม่ได้มาจากหน้าที่เปลี่ยน
4. อัปเดต `entity_source` (revision, accessed_at) และตั้ง `verified=false` สำหรับค่าที่เปลี่ยน
5. เพิ่มบรรทัดใน `data/changelog.json` (วันที่, รอบ, สรุป — รวมค่าที่เปลี่ยนจริง)
6. `python3 scripts/build_db.py && python3 scripts/validate.py` ต้องผ่านก่อนส่งต่อ

## การแก้เอง (เช่นชื่อไทย)
เพิ่มใน `data/user_override.json`:
```json
[{"entity_type":"item","entity_id":"pumpkin","field":"name_th","value":"(ชื่อที่คุณเลือก)","updated_at":"2026-11-12"},
 {"entity_type":"item","entity_id":"pumpkin","field":"name_th_status","value":"self","updated_at":"2026-11-12"}]
```
`build_db.py` ใช้ค่านี้ทับเสมอหลังโหลดข้อมูล และเตือนถ้าไม่พบเป้าหมาย

## เมื่อเกมอัปเดต / ได้ไฟล์เกม
- เปลี่ยน `game_version_target` ใน `meta` และดึงหน้าที่เปลี่ยนใหม่
- เมื่อได้ไฟล์เกม: นำเข้าตัวเลขเป็นแหล่ง `game_files`, เทียบกับค่าจากวิกิ, ถ้าตรงตั้ง `verified=1`, ถ้าขัดกันให้บันทึกใน `changelog` และถามผู้ใช้ก่อนเลือกค่า
- แทนรูป: ตั้ง `image.status='replaced_by_game'` และ `origin='game'`

## ส่งต่อให้ Claude Code
ส่งทั้งโฟลเดอร์ `stardew-db/` (ไม่ต้องส่ง `cache/` ถ้าใหญ่) แล้วให้เริ่มจาก `README.md`
