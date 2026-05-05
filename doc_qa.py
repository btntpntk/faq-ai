#!/usr/bin/env python3
"""
Document Q&A — Gemini reads files in source_docs/ and answers questions strictly from them.
Uploaded files are cached in source_docs/.cache.json (valid 47h) so re-runs skip uploading.

Usage:
    python doc_qa.py                  # interactive chat
    python doc_qa.py "your question"  # single question
    python doc_qa.py --refresh        # force re-upload all files
"""

import os
import sys
import time
import json
import hashlib
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from tts import speak_thai_text
from stt import listen_thai

load_dotenv()

DOCS_DIR = Path(__file__).parent / "source_docs"
CACHE_FILE = DOCS_DIR / ".cache.json"
MODEL = "models/gemini-2.5-flash"
CACHE_TTL_SECONDS = 47 * 3600  # Gemini files live 48h; refresh at 47h to be safe

TTS_TAIL_DELAY_SEC = 1.0       # buffer after TTS playback before mic opens
MAX_UPLOAD_WAIT_RETRIES = 30   # × 2s = 60s max wait for file to become ACTIVE

GREETING = "สวัสดีค่ะ บริษัทหลักทรัพย์ทรีนีตี้ จำกัด ยินดีให้บริการ"

SUPPORTED_MIME = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".md": "text/markdown",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}

OFFICE_HOURS = {
    # weekday() 0=Monday … 4=Friday
    "days": range(0, 5),
    "morning": (8, 30, 12, 0),    # 08:30–12:00
    "afternoon": (13, 0, 17, 0),  # 13:00–17:00
}


def is_office_hours() -> bool:
    now = datetime.now()
    if now.weekday() not in OFFICE_HOURS["days"]:
        return False
    h, m = now.hour, now.minute
    sh, sm, eh, em = OFFICE_HOURS["morning"]
    if (h, m) >= (sh, sm) and (h, m) < (eh, em):
        return True
    sh, sm, eh, em = OFFICE_HOURS["afternoon"]
    if (h, m) >= (sh, sm) and (h, m) < (eh, em):
        return True
    return False


def build_system_prompt() -> str:
    if is_office_hours():
        unavailable_msg = "ขณะนี้ระบบกำลังโอนสายไปยังเจ้าหน้าที่ กรุณาถือสายรอสักครู่ ค่ะ"
    else:
        unavailable_msg = "กรุณาติดต่อใหม่อีกครั้งในเวลาทำการ วันจันทร์ ถึง ศุกร์ เวลา 08.30–12.00 น. และ 13.00–17.00 น."

    return f"""You are a Thai phone assistant for Trinity Securities (บริษัทหลักทรัพย์ทรีนีตี้ จำกัด).

The system already greeted the caller at startup. If the user greets you (e.g. สวัสดี, หวัดดี, hello, hi), do NOT repeat the company greeting. Instead respond with:
"มีอะไรให้ช่วยเหลือ สามารถถามคำถามได้เลยค่ะ"

If the user sends a short conversational response that is NOT a question — such as acknowledgments (โอเค, ขอบคุณ, เข้าใจแล้ว, ได้เลย, ครับ, ค่ะ, ใช่, รับทราบ, ok, okay, thanks, i see, alright) or simple affirmations — respond naturally and briefly, then invite further questions. For example:
- "ขอบคุณค่ะ มีอะไรให้ช่วยเหลืออีกไหมคะ"
- "ยินดีค่ะ หากมีคำถามเพิ่มเติมถามได้เลยนะคะ"
Do NOT search the documents for these conversational replies.

For all other questions:
- Answer ONLY based on the content of the provided documents.
- If the user asks for a list of stocks (e.g., มีหุ้นอะไรบ้าง): Summarize the stocks from the documents. If there are many, categorize them or list the top ones (max 5) to keep it concise for a voice call, then ask if they want details on a specific one.
- If the answer is NOT in the documents, say "{unavailable_msg}".
- Respond in Thai. For English acronyms or Stock Tickers, use phonetic Thai (e.g., "CPALL" -> "ซี พี ออล", "PTT" -> "พี ที ที").
- Keep answers concise and friendly.

**CRITICAL RULES FOR AZURE TTS PACING:**
- Generate responses STRICTLY in Thai script only. No English letters (A-Z, a-z).
- No Markdown formatting (No asterisks **, bolding, or hashtags). Output pure plain text.
- For English acronyms or tickers, use phonetic Thai with spaces between letters (e.g., PTT -> พี ที ที, UNIX -> ยู นิกซ์, "CPALL" -> "ซี พี ออล", "PTT" -> "พี ที ที", "NDR" -> "เอ็น ดี อาร์", "Smart" -> "สมาร์ท").
- **Mandatory Pacing Markers:** Azure TTS requires explicit punctuation for pauses. You MUST:
  1. Insert a comma (,) wherever a short breathing pause is needed, such as between list items, after connecting words, or to break up long subjects.
  2. **DO NOT place a period (.) immediately after polite particles like "ค่ะ" or "ครับ".** This causes a TTS glitch. 
  3. Instead of using a period after "ค่ะ" or "ครับ", use a simple space or start a new line (\n) to indicate the end of the sentence. Use periods (.) ONLY at the end of sentences that do not end in "ค่ะ" or "ครับ".
"""


def _get_client():
    from google import genai
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set")
        sys.exit(1)
    return genai.Client(api_key=api_key)


def _file_hash(path: Path) -> str:
    h = hashlib.md5()
    h.update(path.read_bytes())
    return h.hexdigest()


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except json.JSONDecodeError:
            print("Warning: cache file corrupted, starting fresh")
    return {}


def _save_cache(cache: dict):
    CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False))


def _upload_one(client, path: Path, mime: str):
    """Upload a single file and wait until ACTIVE. Returns file ref or None."""
    print(f"  Uploading: {path.name} ...", end=" ", flush=True)
    with open(path, "rb") as fh:
        response = client.files.upload(
            file=fh,
            config={"mime_type": mime, "display_name": path.name},
        )
    file_ref = response
    for _ in range(MAX_UPLOAD_WAIT_RETRIES):
        if file_ref.state.name == "ACTIVE":
            break
        time.sleep(2)
        file_ref = client.files.get(name=file_ref.name)

    if file_ref.state.name != "ACTIVE":
        print(f"FAILED (state: {file_ref.state.name})")
        return None
    print("OK")
    return file_ref


def load_docs(client, force_refresh: bool = False) -> list:
    """Return list of active Gemini file refs, uploading only what's new/changed/expired."""
    local_files = [
        f for f in sorted(DOCS_DIR.iterdir())
        if not f.is_dir() and not f.name.startswith(".")
        and f.suffix.lower() in SUPPORTED_MIME
    ]

    if not local_files:
        print(f"No files found in {DOCS_DIR}/")
        print("Put your PDF, CSV, TXT, or DOCX files there and re-run.")
        sys.exit(1)

    cache = {} if force_refresh else _load_cache()
    now = time.time()
    result = []
    cache_updated = False

    for f in local_files:
        ext = f.suffix.lower()
        mime = SUPPORTED_MIME[ext]
        fhash = _file_hash(f)
        entry = cache.get(f.name, {})

        if (
            not force_refresh
            and entry.get("hash") == fhash
            and entry.get("uri")
            and (now - entry.get("uploaded_at", 0)) < CACHE_TTL_SECONDS
        ):
            try:
                file_ref = client.files.get(name=entry["gemini_name"])
                if file_ref.state.name == "ACTIVE":
                    print(f"  Cached:    {f.name}")
                    result.append(file_ref)
                    continue
            except Exception:
                pass  # File gone on Gemini side — fall through to re-upload

        file_ref = _upload_one(client, f, mime)
        if file_ref:
            cache[f.name] = {
                "hash": fhash,
                "uri": file_ref.uri,
                "gemini_name": file_ref.name,
                "mime_type": mime,
                "uploaded_at": now,
            }
            cache_updated = True
            result.append(file_ref)

    local_names = {f.name for f in local_files}
    stale = [k for k in cache if k not in local_names]
    if stale:
        for k in stale:
            del cache[k]
        cache_updated = True

    if cache_updated:
        _save_cache(cache)

    if not result:
        print("\nNo files available.")
        sys.exit(1)

    print(f"\nReady: {', '.join(f.display_name for f in result)}\n")
    return result


def ask(client, uploaded_files: list, question: str, chat_history: list) -> str:
    from google.genai import types

    # Include file URIs only in the first turn; subsequent turns use text only
    if not chat_history:
        file_parts = [types.Part.from_uri(file_uri=f.uri, mime_type=f.mime_type) for f in uploaded_files]
        user_parts = file_parts + [types.Part.from_text(text=question)]
    else:
        user_parts = [types.Part.from_text(text=question)]

    chat_history.append(types.Content(role="user", parts=user_parts))

    response = client.models.generate_content(
        model=MODEL,
        contents=chat_history,
        config=types.GenerateContentConfig(
            system_instruction=build_system_prompt(),
            temperature=0.1,
            max_output_tokens=4096,
        ),
    )
    answer = response.text.strip()
    chat_history.append(types.Content(role="model", parts=[types.Part.from_text(text=answer)]))
    return answer


def main():
    force_refresh = "--refresh" in sys.argv
    voice_mode    = "--voice" in sys.argv
    text_mode     = "--text" in sys.argv
    args = [a for a in sys.argv[1:] if a not in ("--refresh", "--voice", "--text")]

    client = _get_client()
    uploaded = load_docs(client, force_refresh=force_refresh)

    if args:
        question = " ".join(args)
        print(f"Q: {question}\n")
        answer = ask(client, uploaded, question, [])
        print(f"A: {answer}\n")
        speak_thai_text(answer)
        return

    if not voice_mode and not text_mode:
        print("\nเลือกโหมดรับคำถาม:")
        print("  1) พิมพ์  (text)")
        print("  2) พูด    (voice)")
        choice = input("เลือก [1/2]: ").strip()
        voice_mode = (choice == "2")

    if voice_mode:
        print("=" * 60)
        print("Document Q&A — พูดคำถามได้เลย (Ctrl+C เพื่อออก)")
        print("=" * 60)
    else:
        print("=" * 60)
        print("Document Q&A — พิมพ์คำถาม (พิมพ์ 'quit' เพื่อออก)")
        print("=" * 60)

    print(f"\nBot: {GREETING}")
    speak_thai_text(GREETING)
    if voice_mode:
        time.sleep(TTS_TAIL_DELAY_SEC)

    chat_history: list = []

    while True:
        try:
            if voice_mode:
                question = listen_thai()
                if not question:
                    continue
                print(f"\nคุณ: {question}")
            else:
                question = input("\nคุณ: ").strip()
                if not question:
                    continue
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if question.strip("? ").lower() in ("quit", "exit", "q", "ออก"):
            print("Bye!")
            break

        answer = ask(client, uploaded, question, chat_history)
        print(f"\nBot: {answer}")
        speak_thai_text(answer)
        if voice_mode:
            time.sleep(TTS_TAIL_DELAY_SEC)


if __name__ == "__main__":
    main()
