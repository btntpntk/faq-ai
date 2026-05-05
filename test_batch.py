#!/usr/bin/env python3
"""
Batch tester for doc_qa.py.

Pulls QUESTIONS from test_questions.py, sends each through doc_qa.ask(),
saves TTS audio to voice_output/<no>_<slug>.wav, and writes a results CSV.

Usage:
    python test_batch.py                  # run all questions
    python test_batch.py --refresh        # force re-upload docs first
    python test_batch.py --tag IPO        # filter by tag (RO/IPO/TO/GEN/MIX/OOS)
"""

import csv
import sys
import time
from datetime import datetime
from pathlib import Path

from test_questions import QUESTIONS
from doc_qa import _get_client, load_docs, ask
from tts import speak_thai_text_to_file

VOICE_DIR = Path(__file__).parent / "voice_output"
RESULTS_DIR = Path(__file__).parent

RATE_LIMIT_DELAY = 0.5  # seconds between Gemini calls


def safe_filename(text: str, max_len: int = 40) -> str:
    keep = []
    for ch in text:
        if ch.isalnum() or ch in " _-":
            keep.append(ch)
    slug = "".join(keep).strip().replace(" ", "_")
    return slug[:max_len]


def run_batch(questions: list[tuple[str, str]], force_refresh: bool = False):
    VOICE_DIR.mkdir(exist_ok=True)

    client = _get_client()
    uploaded = load_docs(client, force_refresh=force_refresh)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_path = RESULTS_DIR / f"test_results_{timestamp}.csv"

    results = []
    total = len(questions)

    for i, (tag, question) in enumerate(questions, start=1):
        if i > 1:
            time.sleep(RATE_LIMIT_DELAY)

        print(f"[{i:>3}/{total}] [{tag}] {question[:60]}")

        t0 = time.time()
        actual_answer = ask(client, uploaded, question, [])
        elapsed_ms = int((time.time() - t0) * 1000)

        print(f"          → {actual_answer[:80]}  ({elapsed_ms}ms)")

        slug = safe_filename(question)
        voice_filename = f"{i:03d}_{slug}.wav"
        voice_path = VOICE_DIR / voice_filename

        try:
            speak_thai_text_to_file(actual_answer, str(voice_path))
            print(f"          Voice: {voice_filename}")
        except Exception as e:
            print(f"          TTS error: {e}")
            voice_filename = f"ERROR: {e}"

        results.append({
            "no": i,
            "tag": tag,
            "question": question,
            "actual_answer": actual_answer,
            "latency_ms": elapsed_ms,
            "voice_file": voice_filename,
        })

    with open(results_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["no", "tag", "question", "actual_answer", "latency_ms", "voice_file"],
        )
        writer.writeheader()
        writer.writerows(results)

    print(f"\nDone. {total} questions processed.")
    print(f"Results CSV : {results_path}")
    print(f"Voice files : {VOICE_DIR}/")


def main():
    force_refresh = "--refresh" in sys.argv

    tag_filter = None
    if "--tag" in sys.argv:
        idx = sys.argv.index("--tag")
        if idx + 1 < len(sys.argv):
            tag_filter = sys.argv[idx + 1].upper()

    questions = QUESTIONS
    if tag_filter:
        questions = [(t, q) for t, q in QUESTIONS if t == tag_filter]
        if not questions:
            print(f"No questions found for tag '{tag_filter}'.")
            sys.exit(1)
        print(f"Filtered to {len(questions)} questions with tag '{tag_filter}'\n")

    run_batch(questions, force_refresh=force_refresh)


if __name__ == "__main__":
    main()
