# My Farm — ส่งต่องาน (27 พ.ย. 2026)

## สถานะตอนนี้
- **แอป:** PWA คู่มือ Stardew Valley (+SVE) สำหรับ iPhone ของ Blue
- **เว็บจริง:** https://milkcakelychee-hue.github.io/my-farm/
- **Repo:** github.com/milkcakelychee-hue/my-farm (public) เก็บเฉพาะโฟลเดอร์ `app/`
- **Commit ล่าสุด:** d92f105 deploy แล้ว
- **ดีไซน์เดิม:** artifact https://claude.ai/artifact/4Z4aQVW3m3YcGcWCbKwaVw (บอร์ดอยู่ที่ `project/<Name>.dc.html`) → **Blue จะรีดีไซน์ใหม่ทั้งหมด** ใช้ของเดิมเป็นแค่ข้อมูลอ้างอิงว่ามีหน้าอะไร ไม่ต้องยึดหน้าตา

| ขั้น | เรื่อง | สถานะ |
|---|---|---|
| 0 | โครงแอป, ระบบดีไซน์, PWA | เสร็จ |
| 1 | ข้อมูล (SQLite ในแอป) | อนุมัติ |
| 2 | My Farm | อนุมัติ |
| 3 | Skills + คำนวณ | อนุมัติ |
| 4 | Wiki (พืช ปลา อาคาร NPC ค้นหา แผนที่ SVE ป้าย SVE) | ทำเสร็จ รออนุมัติ |
| 5 | วันนี้ + เซฟ + วันที่ + To-do | ยังไม่เริ่ม ต้องถามหน้า B 04 และ 10 ก่อน |
| 6 | เพิ่มเติม / เซฟ / สำรองข้อมูล | ยังไม่เริ่ม |
| 7 | หมวด Wiki ที่เหลือ (หน้า C) | ยังไม่เริ่ม |
| 8 | เก็บงาน | ยังไม่เริ่ม |

## ไฟล์สำคัญ
- **สเปก:** `stardew-app-SPEC.md` (รายละเอียดฟีเจอร์และหน้า)
- **แผนฐานข้อมูล:** `stardew-db-PLAN.md`
- **ฐานข้อมูล:** `stardew-db/` (schema_version 8, มีคอลัมน์ `content_pack` = 'sve' หรือ 'vanilla' ในตาราง item, npc, building)
  - backup อยู่ที่ repo public github.com/milkcakelychee-hue/myfarm (แก้แล้ว commit + push ด้วย)
  - `npm run sync-db` (ใน app) คัดลอก DB เข้า `app/public/data/stardew.sqlite` และย่อรูป
- **แอป** `app/` ใช้ Vite 6 + Preact + TypeScript + vite-plugin-pwa (prompt mode + `src/update.ts` อัปเดตเอง)
  - route แบบ hash `#/<tab>/<sub>`, 5 แท็บ: วันนี้ · Wiki · My Farm · คำนวณ · เพิ่มเติม
  - เก็บข้อมูลผู้เล่นด้วย idb-keyval, อ่าน DB ด้วย sql.js
  - `src/ui.tsx` คอมโพเนนต์กลาง · `src/index.css` token สี/ฟอนต์
  - `src/myfarm.tsx`, `src/calculate.tsx`, `src/wiki.tsx` หน้าจอแต่ละแท็บ
  - `src/data/` : `gamedb.ts` (เปิด DB), `wikidata.ts` / `farmdata.ts` / `calc.ts` (query), `save.ts` `useSave.ts` `backup.ts` (เซฟผู้เล่น), `icons.ts` (รูป)
  - `src/stage1.tsx` หน้าทดสอบเก่า ลบได้
- **ภาพเทียบเดิม:** `screenshots/`, `compare/`

> ถ้ารีดีไซน์ ส่วนที่ควรเก็บไว้ใช้ต่อคือ `src/data/*` (query + เซฟ), DB, ระบบ PWA/deploy ส่วนหน้าจอ (`*.tsx`, `ui.tsx`, `index.css`) เขียนใหม่ได้

## Deploy
- push ขึ้น `main` แล้ว GitHub Actions จะ build และขึ้น Pages เอง (Claude ทำเองได้ ไม่ต้องถาม)
- ถ้า deploy ล้มด้วยข้อความ "No artifacts" ให้รัน `gh run rerun <id>`
- GitHub Pages cache ประมาณ 10 นาที
- ดูก่อน deploy: `npm run build` แล้ว `npx vite preview --port 4173` เปิด http://localhost:4173/#/... (base `./` ไม่ต้องมี /my-farm/)


## รีดีไซน์ (เริ่ม 27 พ.ย. 2026) — พักไว้ที่นี่
- ดีไซน์ใหม่: มินิมอล ขาว/ดำ/เทา + ส้มแดง `#E8481C` · เนื้อหา Bai Jamjuree · หัวข้อ Inter + IBM Plex Sans Thai · ป้าย SVE = gradient · การ์ด "แนะนำ" = เขียว `#2E7D32` · ไอคอนเกมมีกรอบ
- แคนวาสดีไซน์: https://claude.ai/artifact/2j28xUmXTDioq1Qd44hEPG (หมวดวันนี้ / Wiki / My Farm บางหน้า)
- โค้ดใหม่ใน `app/src`: `kit.tsx` (ชิ้นส่วนกลาง), `today.tsx`, `addtodo.tsx`, `pickdate.tsx`, `buildpicker.tsx`, `review.tsx`, `pickdonate.tsx`, `picktools.tsx`, `pickgift.tsx`, `board.tsx`, `wikihome.tsx`, `wikilist.tsx`, `wikiitem.tsx`, `wikifish.tsx`
- ขึ้นเว็บแล้ว (commit d1ea65d): หมวดวันนี้ครบ (วันนี้ · เพิ่มงาน 5 เทมเพลต · เลือกวัน · ตรวจรายการงาน) + Wiki หน้ารวม · พืชผลรายการ · รายละเอียดพืช · ปลาแผนที่ · รายละเอียดปลา
- เซฟ schema 5 (เพิ่ม `bundle_done`, `tool_levels` ซึ่งตอนนี้ไม่ได้ใช้)
- ฐานข้อมูล schema 10: เพิ่ม `special_order(_target)`, `npc_romance`, รูปมอนสเตอร์ 57/65
- **ทำต่อ:** Wiki รายการ/รายละเอียดหมวดที่เหลือ (ของป่า แร่ อาหาร เครื่องจักร อาคาร NPC มอนสเตอร์) · ผลค้นหา · My Farm · คำนวณ · เพิ่มเติม · รายการงานที่ "ไม่กำหนดวัน" ยังไม่มีที่แสดง
- **ค้างในฐานข้อมูล:** ลบแถว wiki_style_guide_* · Construction Bundle มี Wood ซ้ำ · ฤดูปลาบางตัวเพี้ยน · วันเกิด/เทศกาล SVE
- กติกาเพิ่ม: ทำทีละหน้า รีวิวจากภาพ 390 ในเครื่อง ไม่ขึ้นเว็บจนกว่า Blue สั่ง · ลบแบบที่ไม่เอาทิ้ง

## กติกาที่ Blue ตั้งไว้
- ตอบเป็นภาษาไทยเสมอ ถามแทนการเดา ห้ามเปลี่ยนจากดีไซน์โดยไม่บอก
- ทำทีละขั้น จบแต่ละขั้นส่งภาพหน้าจอกว้าง 390 เทียบกับดีไซน์ + รายการจุดที่ต่าง แล้วรออนุมัติ
- หน้าที่ยังไม่ชัด ให้ถามเป็นตัวเลือก 2–3 แบบก่อนทำ
- **ห้ามใส่ตัวเลขเกมเอง** ต้องดึงจาก DB ถ้าไม่มีให้แสดง "ยังไม่มีข้อมูล"
- ตัดเส้นทาง Joja ออก รวมเนื้อหา SVE ด้วย และติดป้าย SVE (สีม่วง) ให้ของที่มาจาก SVE

## งานค้าง / ปัญหาที่รู้แล้ว
- ปฏิทิน SVE ยังไม่ครบ: NPC ของ SVE 19 คนไม่มีวันเกิด และยังไม่มีเทศกาล SVE (สัญญาว่าจะเติมก่อนขั้น 5)
- ข้อความสถานที่ของปลาเกมหลักบางตัวเพี้ยน
- ไม่มีรูป Hank, Treyvon, Shipping Bin
- หน้า My Farm และคำนวณยังไม่มีป้าย SVE (มีเฉพาะใน Wiki)
