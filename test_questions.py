#!/usr/bin/env python3
"""
Batch Question Tester — รัน 50 คำถามลูกค้าพร้อมกัน แสดงผลแบบ Rich
"""
from __future__ import annotations

import csv
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv
from google import genai
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

load_dotenv()

# ─── 50 คำถามจริงที่ลูกค้าโทรเข้ามา ────────────────────────────────────────

QUESTIONS: List[Tuple[str, str]] = [
    # ── หุ้นเพิ่มทุน QDC (RO) ────────────────────────────────────────────
    ("RO",  "QDC จองซื้อราคาเท่าไหร่"),
    ("RO",  "หุ้น QDC ราคาจองเท่าไหร่คะ"),
    ("RO",  "QDC จองได้ถึงวันไหน"),
    ("RO",  "วันแรกที่เปิดรับจอง QDC คือวันอะไร"),
    ("RO",  "จองหุ้น QDC กี่วัน"),
    ("RO",  "อัตราส่วนการจองซื้อ QDC เป็นยังไง"),
    ("RO",  "จองหุ้น QDC เกินสิทธิได้ไหม"),
    ("RO",  "QDC-W3 ได้มาได้ยังไง"),
    ("RO",  "จ่ายเงินค่าจอง QDC โอนผ่านแอปได้ไหม"),
    ("RO",  "Bill Payment QDC ใช้ service code อะไร"),
    ("RO",  "จ่ายเงินจอง QDC ด้วยเช็คส่งได้ถึงวันไหน"),
    ("RO",  "ชำระเงินจอง QDC ด้วย QR Code ได้ไหม"),
    ("RO",  "จองหุ้น QDC ออนไลน์ได้ที่ไหน"),
    ("RO",  "จองหุ้น QDC ผ่าน E-RO ทำยังไง"),
    ("RO",  "สาขาที่รับจองหุ้น QDC อยู่ที่ไหน"),
    ("RO",  "จองหุ้น QDC ส่งเอกสารทางไปรษณีย์ได้ไหม"),
    ("RO",  "ติดต่อสอบถามเรื่อง QDC กับใครได้บ้าง"),
    ("RO",  "เบอร์โทรสอบถามเรื่องจอง QDC"),
    ("RO",  "จองหุ้น QDC ชำระเงินทางไหนบ้าง"),
    ("RO",  "ชื่อบัญชีสำหรับโอนเงินจอง QDC คืออะไร"),

    # ── หุ้น IPO UNIX ──────────────────────────────────────────────────
    ("IPO", "IPO UNIX ราคาเท่าไหร่"),
    ("IPO", "หุ้น UNIX จองได้วันไหนถึงวันไหน"),
    ("IPO", "UNIX จองขั้นต่ำกี่หุ้น"),
    ("IPO", "ซื้อหุ้น UNIX ได้กี่หุ้นต่อครั้ง"),
    ("IPO", "UNIX จะเข้าตลาดวันไหน"),
    ("IPO", "หุ้น UNIX listing วันที่เท่าไหร่"),
    ("IPO", "จ่ายเงินจอง UNIX ด้วย ATS ได้ไหม"),
    ("IPO", "ชำระเงินจอง UNIX หักหลักประกันได้ไหม"),
    ("IPO", "จองหุ้น UNIX ทางโทรศัพท์ได้ไหม"),
    ("IPO", "ขั้นตอนจอง IPO UNIX ในระบบทำยังไง"),
    ("IPO", "UNIX จองได้กี่วันทำการ"),
    ("IPO", "สอบถามเรื่อง IPO UNIX ติดต่อใคร"),

    # ── Tender Offer NDR ──────────────────────────────────────────────
    ("TO",  "Tender Offer NDR ราคารับซื้อเท่าไหร่"),
    ("TO",  "ราคาสุทธิที่จะได้รับจาก Tender NDR เท่าไหร่"),
    ("TO",  "NDR Tender Offer เปิดรับตั้งแต่วันไหน"),
    ("TO",  "วันสุดท้ายของ Tender Offer NDR คือวันที่เท่าไหร่"),
    ("TO",  "Tender NDR รับซื้อกี่วัน"),
    ("TO",  "ยกเลิกแสดงเจตนาขาย NDR ได้ถึงวันไหน"),
    ("TO",  "ถ้าจะยกเลิก Tender NDR มีค่าธรรมเนียมไหม"),
    ("TO",  "ค่าธรรมเนียมยกเลิก Tender NDR เท่าไหร่"),
    ("TO",  "NDR จะได้รับเงินวันไหน"),
    ("TO",  "วันชำระราคา Tender NDR คือวันอะไร"),
    ("TO",  "รับเงินจาก Tender NDR ทางไหนได้บ้าง"),
    ("TO",  "โอนเงิน Tender NDR เข้าบัญชีได้ไหม ค่าธรรมเนียมเท่าไหร่"),
    ("TO",  "ค่าธรรมเนียมออกเช็ค Tender NDR เท่าไหร่"),
    ("TO",  "แสดงเจตนาขาย NDR ออนไลน์ได้ไหม"),
    ("TO",  "ตอบรับ Tender NDR ผ่านเว็บไซต์ได้ไหม"),
    ("TO",  "เอกสารที่ต้องเตรียมสำหรับ Tender Offer NDR มีอะไรบ้าง"),
    ("TO",  "ยื่น Tender NDR ผ่าน Broker ต้องมีหนังสือมอบอำนาจไหม"),
    ("TO",  "ผู้ทำ Tender Offer NDR คือใคร"),
    ("TO",  "ติดต่อเรื่อง Tender NDR ได้ที่ไหน"),

    # ── FAQ ทั่วไป ────────────────────────────────────────────────────────
    ("GEN", "ที่อยู่บริษัทหลักทรัพย์ ทรีนีตี้อยู่ที่ไหน"),
    ("GEN", "อีเมลติดต่อทรีนีตี้คืออะไร"),
    ("GEN", "ส่งเอกสารไปรษณีย์ได้ไหม"),
    ("GEN", "จะโอนสายเจ้าหน้าที่ต้องกดอะไร"),
    ("GEN", "หุ้นจะเข้าพอร์ตเมื่อไหร่"),
    ("GEN", "วันเริ่มซื้อขายหุ้นในตลาดกำหนดจากอะไร"),

    # ── Rephrasing / พูดใหม่ (stress test phrasing variation) ──────────────
    ("RO",  "ราคา QDC เท่าไร"),                           # ตัด "จองซื้อ" ออก
    ("RO",  "QDC ซื้อได้กี่บาท"),                         # คำต่างออกไป
    ("RO",  "ควอนตัม ดี ซี ราคาหุ้นเท่าไหร่"),            # ใช้ชื่อเต็ม ไม่มีสัญลักษณ์
    ("RO",  "QDC เช็คสั่งจ่ายชื่ออะไร"),                  # คำถามสั้น
    ("RO",  "ทำ E-RO ต้องเตรียมอะไรบ้าง"),                # อีกแบบของ online RO
    ("RO",  "จองหุ้นเพิ่มทุน QDC ผ่านมือถือได้ไหม"),      # mobile phrasing
    ("RO",  "QDC warrant ได้กี่หน่วย"),                   # warrant ใช้คำอื่น
    ("RO",  "ธนาคารไหนรับ Bill Payment QDC"),             # ถามธนาคารแทน service code
    ("IPO", "UNIX ราคา IPO"),                             # กลับลำดับคำ
    ("IPO", "ยูนิคพลาสติก จองราคาเท่าไหร่"),              # ชื่อเต็ม ไม่มีสัญลักษณ์
    ("IPO", "หุ้น UNIX ซื้อขั้นต่ำกี่บาท"),               # ถามเป็นบาท ไม่ใช่หุ้น
    ("IPO", "UNIX เพิ่มได้ครั้งละกี่หุ้น"),               # lot size ต่างคำ
    ("IPO", "UNIX เข้าตลาดหลักทรัพย์วันที่เท่าไหร่"),     # ใช้คำเต็ม
    ("IPO", "จองหุ้น IPO UNIX หักเงินจากบัญชีได้ไหม"),    # ATS ใช้คำอื่น
    ("TO",  "NDR tender ราคาต่อหุ้น"),                    # ย่อคำถาม
    ("TO",  "เอ็น ดี รับเบอร์ ราคา tender"),              # อ่านออกเสียง ไม่ใช้สัญลักษณ์
    ("TO",  "ขายหุ้น NDR ได้ถึงเมื่อไหร่"),               # อีก phrasing
    ("TO",  "NDR ยกเลิกขายหุ้นได้กี่วัน"),               # ถามจำนวนวัน
    ("TO",  "จะรับเช็คจาก NDR ต้องทำอะไร"),              # process แทนวัน
    ("TO",  "ค่าธรรมเนียมรับโอนเงิน tender NDR"),         # อีกคำ transfer fee
    ("TO",  "NDR ตอบรับ tender ส่งเอกสารอะไร"),           # documents

    # ── Cross-product (ถามข้ามหุ้น — ทดสอบ disambiguation) ──────────────
    ("MIX", "ราคาจองซื้อของหุ้นทั้งหมดคือเท่าไหร่"),      # ถามหลายหุ้นพร้อมกัน
    ("MIX", "มีหุ้นอะไรให้จองบ้างตอนนี้"),                # broad query
    ("MIX", "วันจองซื้อของแต่ละหุ้นเป็นอย่างไร"),         # ถาม date ทุกตัว
    ("MIX", "ชำระเงินจองหุ้นผ่าน QR Code ได้ทุกตัวไหม"),  # ถาม feature ข้ามหุ้น
    ("MIX", "หุ้นไหนชำระด้วย ATS ได้บ้าง"),               # ถาม filter

    # ── Edge case — นอกข้อมูล (ควรตอบว่าไม่พบ) ──────────────────────────
    ("OOS", "ราคาหุ้น PTT วันนี้"),                        # หุ้นอื่นในตลาด
    ("OOS", "กองทุน RMF แนะนำตัวไหนดี"),                  # นอก scope
    ("OOS", "เปิดบัญชีหุ้นใหม่ต้องทำอะไรบ้าง"),          # onboarding ไม่ใช่ subscription
    ("OOS", "ดอกเบี้ยเงินกู้มาร์จิ้นเท่าไหร่"),            # margin loan
    ("OOS", "หุ้น BTC ซื้อที่ไหน"),                       # crypto

    # ── Typo / ภาษาพูด / ไม่เป็นทางการ ──────────────────────────────────
    ("RO",  "qdc ราคาจองเท่าไหร่ครับ"),                   # lowercase
    ("RO",  "QDC จองซื้อยังไงครับพี่"),                   # informal
    ("RO",  "จองคิวดีซีออนไลน์"),                         # เขียนทับศัพท์
    ("TO",  "เอ็นดีอาร์ tender ราคาเท่าไหร่"),            # อ่านสัญลักษณ์ออกเสียง
    ("TO",  "ขาย NDR ได้เงินวันไหนครับ"),                 # informal + วันชำระ

    # ── คำถามยาว / multi-intent ──────────────────────────────────────────
    ("RO",  "ถ้าผมอยากจอง QDC ผ่านออนไลน์และจ่ายผ่าน QR Code ต้องทำยังไงบ้าง"),
    ("TO",  "สมมติผมถือหุ้น NDR อยู่ อยากขายผ่าน Tender ต้องเตรียมเอกสารอะไรและส่งที่ไหน"),
    ("IPO", "UNIX จองขั้นต่ำ 1000 หุ้น แล้วถ้าอยากจองเพิ่มต้องเพิ่มทีละเท่าไหร่"),
    ("GEN", "บริษัทอยู่แถวไหน ใกล้ BTS ไหม และอีเมลติดต่อคืออะไร"),

    # ── คำถามสั้นมาก / keyword เดียว ────────────────────────────────────
    ("RO",  "QDC ราคา"),
    ("RO",  "วันจอง QDC"),
    ("IPO", "UNIX ราคา"),
    ("IPO", "UNIX วันเข้าตลาด"),
    ("TO",  "NDR ราคา"),
    ("TO",  "NDR วันสุดท้าย"),
    ("GEN", "อีเมลทรีนีตี้"),
    ("GEN", "ที่อยู่ทรีนีตี้"),
]

# ─── Main ────────────────────────────────────────────────────────────────────

CSV_COLUMNS = [
    "no", "tag", "question", "found", "fallback",
    "sheet_title", "field", "value",
    "confidence_pct", "rrf_score", "latency_ms",
]


def _save_csv(results: list, path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "no":             r["no"],
                "tag":            r["tag"],
                "question":       r["question"],
                "found":          "YES" if r["found"] else "NO",
                "fallback":       "YES" if r.get("is_fallback") else "NO",
                "sheet_title":    r["sheet"],
                "field":          r["field"],
                "value":          r["value"],
                "confidence_pct": f"{r['confidence']:.1f}",
                "rrf_score":      f"{r['rrf_score']:.6f}",
                "latency_ms":     r["ms"],
            })


def main() -> None:
    from src.db import check_connection, count_documents
    from src.generator import format_results
    from src.indexer import load_all_documents
    from src.retriever import HybridRetriever

    console = Console()

    console.print(Panel(
        "[bold cyan]Batch Question Test[/] — 50 คำถามจริงจากลูกค้า\n"
        "[dim]Hybrid RAG (pgvector + BM25) — Direct Table Lookup[/]",
        border_style="cyan",
        padding=(0, 2),
    ))

    # ── เชื่อมต่อ ─────────────────────────────────────────────────────────
    with console.status("[cyan]เชื่อมต่อ...[/]"):
        if not check_connection():
            console.print("[red]✗ PostgreSQL ไม่สำเร็จ[/]"); return
        n = count_documents()
        if n == 0:
            console.print("[red]✗ ยังไม่ได้ index — รัน python main.py index ก่อน[/]"); return

        api_key = os.environ.get("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        db_docs = load_all_documents()
        retriever = HybridRetriever(client, db_docs)

    console.print(f"[green]✓[/] พร้อม — {n} docs | {len(db_docs)} BM25\n")

    # ── รัน 50 คำถาม ─────────────────────────────────────────────────────
    results = []
    for i, (tag, q) in enumerate(QUESTIONS, 1):
        if i > 1:
            time.sleep(0.5)  # 0.5s between questions to avoid 429
        t0 = time.time()
        retrieved = retriever.retrieve(q, top_k=3)
        rows = format_results(retrieved, question=q, gemini_client=client)
        elapsed = time.time() - t0

        top_value     = rows[0]["value"]       if rows else "— ไม่พบข้อมูล —"
        top_field     = rows[0]["field"]       if rows else ""
        top_sheet     = rows[0]["sheet_title"] if rows else ""
        top_conf      = rows[0]["confidence"]  if rows else 0.0
        top_rrf       = retrieved[0][1]        if retrieved else 0.0
        is_fallback   = rows[0].get("fallback", False) if rows else False
        found = bool(rows) and not is_fallback

        results.append({
            "no":          i,
            "tag":         tag,
            "question":    q,
            "field":       top_field,
            "value":       top_value,
            "sheet":       top_sheet,
            "found":       found,
            "is_fallback": is_fallback,
            "confidence":  top_conf,
            "rrf_score":   top_rrf,
            "ms":          int(elapsed * 1000),
        })

        # แสดง real-time
        if is_fallback:
            status   = "[yellow]○[/]"
            conf_str = f"[yellow]{top_conf:.1f}%[/] [dim](OOS)[/]"
        elif found:
            status   = "[green]✓[/]"
            conf_str = (f"[green]{top_conf:.1f}%[/]" if top_conf >= 75
                        else f"[yellow]{top_conf:.1f}%[/]" if top_conf >= 50
                        else f"[red]{top_conf:.1f}%[/]")
        else:
            status   = "[red]✗[/]"
            conf_str = f"[red]{top_conf:.1f}%[/]"

        console.print(
            f"  {status} [{i:>3}] [dim]{tag:3}[/] [cyan]{q[:36]:36}[/] "
            f"→ [white]{top_value[:38]}[/] {conf_str} [dim]{elapsed*1000:.0f}ms[/]"
        )

    # ── Summary Table ─────────────────────────────────────────────────────
    console.print()
    console.print(Rule("[bold cyan]สรุปผล[/]"))

    found_count = sum(1 for r in results if r["found"])
    avg_ms = sum(r["ms"] for r in results) / len(results)

    summary = Table(box=box.ROUNDED, border_style="cyan", show_lines=False,
                    header_style="bold cyan", expand=True)
    summary.add_column("#",          width=4,  justify="right", style="dim")
    summary.add_column("Tag",        width=4,  style="dim")
    summary.add_column("คำถาม",      min_width=26)
    summary.add_column("หัวข้อที่พบ", min_width=20, style="yellow")
    summary.add_column("คำตอบ",      min_width=28, style="white")
    summary.add_column("Conf",       width=8,  justify="right")
    summary.add_column("RRF",        width=8,  justify="right", style="dim")
    summary.add_column("ms",         width=6,  justify="right", style="dim")

    for r in results:
        conf = r["confidence"]
        if not r["found"]:
            conf_str = "[red]—[/]"
            row_style = "red"
        elif conf >= 75:
            conf_str  = f"[green]{conf:.1f}%[/]"
            row_style = ""
        elif conf >= 50:
            conf_str  = f"[yellow]{conf:.1f}%[/]"
            row_style = ""
        else:
            conf_str  = f"[red]{conf:.1f}%[/]"
            row_style = ""

        summary.add_row(
            str(r["no"]),
            r["tag"],
            r["question"],
            r["field"],
            r["value"][:50] + ("…" if len(r["value"]) > 50 else ""),
            conf_str,
            f"{r['rrf_score']:.4f}",
            str(r["ms"]),
            style=row_style,
        )

    console.print(summary)
    console.print()

    # ── Stats ─────────────────────────────────────────────────────────────
    not_found = [r for r in results if not r["found"]]

    oos_count     = sum(1 for r in results if r.get("is_fallback"))
    found_results = [r for r in results if r["found"]]
    avg_conf  = sum(r["confidence"] for r in found_results) / len(found_results) if found_results else 0
    high_conf = sum(1 for r in found_results if r["confidence"] >= 75)
    mid_conf  = sum(1 for r in found_results if 50 <= r["confidence"] < 75)
    low_conf  = sum(1 for r in found_results if r["confidence"] < 50)
    threshold = os.environ.get("OOS_CONFIDENCE_THRESHOLD", "65.0")

    console.print(Panel(
        f"[bold]พบข้อมูล[/]       : [green]{found_count}[/] / {len(results)} "
        f"([green]{found_count/len(results)*100:.0f}%[/])\n"
        f"[bold]OOS fallback[/]   : [yellow]{oos_count}[/] คำถาม "
        f"[dim](threshold {threshold}%)[/]\n"
        f"[bold]ไม่พบข้อมูล[/]    : [red]{len(not_found)}[/] คำถาม\n"
        f"[bold]Avg Confidence[/] : [cyan]{avg_conf:.1f}%[/]\n"
        f"[bold]สูง ≥75%[/]       : [green]{high_conf}[/]  "
        f"[bold]กลาง 50-74%[/]: [yellow]{mid_conf}[/]  "
        f"[bold]ต่ำ <50%[/]: [red]{low_conf}[/]\n"
        f"[bold]เวลาเฉลี่ย[/]      : {avg_ms:.0f} ms / คำถาม",
        title="[bold cyan]Statistics[/]",
        border_style="green" if (found_count + oos_count) == len(results) else "yellow",
        padding=(0, 2),
    ))

    # ── แยกสถิติตาม tag ───────────────────────────────────────────────────
    from collections import defaultdict
    by_tag: dict = defaultdict(lambda: {"found": 0, "total": 0})
    for r in results:
        by_tag[r["tag"]]["total"] += 1
        if r["found"]:
            by_tag[r["tag"]]["found"] += 1

    tag_table = Table(box=box.SIMPLE, border_style="dim", header_style="bold cyan",
                      title="สถิติแยกตาม Tag")
    tag_table.add_column("Tag",    style="cyan", width=6)
    tag_table.add_column("พบ",     justify="right", style="green")
    tag_table.add_column("ทั้งหมด",justify="right")
    tag_table.add_column("%",      justify="right", style="yellow")
    for tag, s in sorted(by_tag.items()):
        pct = s["found"] / s["total"] * 100
        color = "green" if pct == 100 else "yellow" if pct >= 80 else "red"
        tag_table.add_row(tag, str(s["found"]), str(s["total"]),
                          f"[{color}]{pct:.0f}%[/{color}]")
    console.print(tag_table)

    if not_found:
        console.print("[bold red]คำถามที่ไม่พบข้อมูล:[/]")
        for r in not_found:
            console.print(f"  [red]✗[/] [{r['tag']}] {r['question']}")

    # ── บันทึก CSV ────────────────────────────────────────────────────────
    console.print()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = Path(f"test_results_{ts}.csv")
    _save_csv(results, csv_path)
    console.print(
        f"[bold green]✓[/] บันทึกผลลัพธ์ → [cyan]{csv_path}[/]  "
        f"[dim]({len(results)} rows, UTF-8)[/]"
    )


if __name__ == "__main__":
    main()
