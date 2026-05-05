# Trinity FAQ — ระบบโทรศัพท์อัตโนมัติ

ระบบผู้ช่วยโทรศัพท์ภาษาไทยสำหรับบริษัทหลักทรัพย์ทรีนีตี้ จำกัด
ผู้โทรสามารถถามคำถามด้วยการพูดหรือพิมพ์ — ระบบตอบจากเอกสารฐานความรู้ผ่าน Gemini แล้วอ่านคำตอบออกเสียงด้วย Azure TTS

---

## สถาปัตยกรรม

```
[ผู้โทร พูด/พิมพ์]
       ↓
    STT (Azure)          ← แปลงเสียงเป็นข้อความ (โหมดพูดเท่านั้น)
       ↓
  Gemini 2.5 Flash       ← ค้นหาคำตอบจากเอกสารใน source_docs/
       ↓
    TTS (Azure)          ← แปลงคำตอบเป็นเสียงพูด (PremwadeeNeural)
       ↓
  [เสียงตอบกลับ]
```

```
source_docs/          ← วางเอกสารฐานความรู้ที่นี่
    ├── *.pdf / *.csv / *.docx / ...
    └── .cache.json   ← cache Gemini File API (อัตโนมัติ อย่าลบ)

voice_output/         ← ไฟล์เสียง WAV จาก batch test (สร้างอัตโนมัติ)
test_results_*.csv    ← ผลลัพธ์ batch test (สร้างอัตโนมัติ)
```

---

## ไฟล์หลัก

| ไฟล์ | หน้าที่ |
|---|---|
| `doc_qa.py` | ระบบหลัก — อัปโหลดเอกสาร, จัดการ cache, ถาม Gemini, วนลูปรับคำถาม |
| `tts.py` | แปลงข้อความ → เสียงพูดภาษาไทย (เล่นลำโพง หรือบันทึกไฟล์ WAV) |
| `stt.py` | แปลงเสียงจากไมโครโฟน → ข้อความภาษาไทย |
| `test_questions.py` | รายการคำถามทดสอบ 100+ ข้อ แบ่งตาม tag (RO, IPO, TO, GEN, MIX, OOS) |
| `test_batch.py` | รัน batch test — ถามทุกคำถาม, บันทึกเสียง WAV, ส่งออก CSV |

---

## ความต้องการของระบบ

### API Keys

| บริการ | ตัวแปร Environment |
|---|---|
| Google Gemini | `GEMINI_API_KEY` |
| Azure Speech | `AZURE_SPEECH_KEY` |
| Azure Speech | `AZURE_SERVICE_REGION` (เช่น `southeastasia`) |

สร้างไฟล์ `.env`:

```
GEMINI_API_KEY=your_gemini_key_here
AZURE_SPEECH_KEY=your_azure_speech_key_here
AZURE_SERVICE_REGION=southeastasia
```

### ติดตั้ง Dependencies

```bash
pip install -r requirements.txt
```

---

## การใช้งาน

### รันระบบหลัก

**เลือกโหมดเมื่อเริ่ม (แนะนำ)**
```bash
python doc_qa.py
```
ระบบจะถามให้เลือก:
```
เลือกโหมดรับคำถาม:
  1) พิมพ์  (text)
  2) พูด    (voice)
เลือก [1/2]:
```

**กำหนดโหมดล่วงหน้า**
```bash
python doc_qa.py --text     # โหมดพิมพ์
python doc_qa.py --voice    # โหมดพูด
```

**ถามคำถามเดียว (single-shot)**
```bash
python doc_qa.py "ราคา IPO UNIX เท่าไหร่"
```

**บังคับ re-upload เอกสารใหม่ทั้งหมด**
```bash
python doc_qa.py --refresh
```

### Batch Test

รันคำถามทั้งหมดใน `test_questions.py` ผ่านระบบจริง บันทึกเสียง WAV และส่งออก CSV:

```bash
python test_batch.py                    # รันทุกคำถาม (~100 ข้อ)
python test_batch.py --tag IPO          # กรองเฉพาะ tag ที่ต้องการ
python test_batch.py --refresh          # re-upload เอกสารก่อนรัน
```

**Tags ที่ใช้ใน test_questions.py:**

| Tag | หมวดหมู่ |
|---|---|
| `RO` | หุ้นเพิ่มทุน QDC |
| `IPO` | หุ้น IPO UNIX |
| `TO` | Tender Offer NDR |
| `GEN` | FAQ ทั่วไป |
| `MIX` | คำถามข้ามผลิตภัณฑ์ |
| `OOS` | คำถามนอกขอบเขต (ควรตอบว่าไม่พบ) |

**ผลลัพธ์:**
- `test_results_YYYYMMDD_HHMMSS.csv` — columns: `no, tag, question, actual_answer, latency_ms, voice_file`
- `voice_output/001_<slug>.wav`, `002_<slug>.wav`, ... — ไฟล์เสียงคำตอบแต่ละข้อ

---

## เอกสารฐานความรู้

วางไฟล์ใน `source_docs/` — ระบบรองรับ:

| นามสกุล | ประเภท |
|---|---|
| `.pdf` | PDF |
| `.csv` | CSV |
| `.txt` | Text |
| `.md` | Markdown |
| `.docx` | Word |
| `.xlsx` | Excel |
| `.png` / `.jpg` / `.jpeg` | รูปภาพ |

---

## ระบบ Cache

ไฟล์ที่อัปโหลดไปยัง Gemini File API จะถูก cache URI ไว้ใน `source_docs/.cache.json`

| สถานการณ์ | พฤติกรรม |
|---|---|
| รันซ้ำโดยไม่แก้ไฟล์ | ใช้ cache — ข้ามขั้นตอน upload |
| แก้ไขเนื้อหาในไฟล์ | ตรวจพบ hash เปลี่ยน → re-upload อัตโนมัติ |
| เพิ่มไฟล์ใหม่ | upload เฉพาะไฟล์ใหม่ |
| ลบไฟล์ออก | ลบ cache entry อัตโนมัติ |
| ผ่านไป 47 ชั่วโมง | re-upload อัตโนมัติ (Gemini เก็บไฟล์ได้ 48h) |
| ใช้ `--refresh` | re-upload ทุกไฟล์ใหม่ทั้งหมด |

---

## นโยบายการตอบคำถาม

- ตอบจากเนื้อหาในเอกสารเท่านั้น
- ถ้าไม่พบข้อมูล → โอนสายให้เจ้าหน้าที่ (ในเวลาทำการ) หรือแจ้งให้โทรกลับ (นอกเวลา)
- เวลาทำการ: วันจันทร์–ศุกร์ 08:30–12:00 น. และ 13:00–17:00 น.
- ตอบเป็นภาษาไทยเสมอ — ตัวย่อภาษาอังกฤษใช้การอ่านออกเสียงภาษาไทย (เช่น PTT → พี ที ที)
- ทุกคำตอบถูกอ่านออกเสียงด้วย Azure TTS (PremwadeeNeural, customer-service style)

---
