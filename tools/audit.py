#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بازبینی صفر تا صد جزوه: ساختار، بهداشت متن، جای شکل‌ها و حرف استادها، پوشش منابع، و PDF.

اجرا:  python3 tools/audit.py [--pdf FILE] [--out FILE]
خروجی: گزارش فارسی روی صفحه + render/audit_report.txt
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "lock"
CONTENT = ROOT / "content"

FA2EN = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
ARABIC = re.compile(r"[\u0600-\u06ff]")
PRESENTATION = re.compile(r"[\uFB50-\uFDFF\uFE70-\uFEFF]")
TATWEEL = re.compile(r"\u0640")
ARABIC_LETTERS = re.compile(r"[\u064A\u0643\u0649]")     # ي ك ى (عربی، نه فارسی)
REPLACEMENT = re.compile(r"[\uFFFD]")

STOP = set("""
و در به از که با این را برای است هست نیست می های ها یک دو سه آن او ما شما آنها شود شده باشد
بودند دارد داریم دارند کرد کردن کند هم نیز بر تا بی هر همه اگر اما یا چه چیزی وقتی زمان طور
صورت مورد نظر بین روی زیر بالا پایین داخل خارج هنگام همچنین بنابراین مثلا مانند بسیار خیلی کم
زیاد بزرگ کوچک اول دوم سوم چهارم پنجم ششم هفتم هشتم نهم دهم باید نباید توان نمی گفته داده
استفاده عنوان دلیل علت استاد درس جلسه صفحه اسلاید جزوه ویدیو فایل بخش فصل شکل جدول این
آن‌ها یکی دیگر کنید کنیم دهیم بدهیم بگیریم بگوییم شده‌اند شده‌است نخست زیر
""".split())

ISSUES: list[tuple[str, str, str]] = []
LINES: list[str] = []


def line(s: str = "") -> None:
    LINES.append(s)


def issue(sev: str, area: str, msg: str) -> None:
    ISSUES.append((sev, area, msg))


def load_lock() -> dict:
    out = {}
    for f in sorted(LOCK.glob("ch*.json")):
        out[int(f.stem[2:])] = json.loads(f.read_text(encoding="utf-8"))
    return out


def btext(b: dict) -> str:
    parts = [b.get("text") or "", b.get("caption") or "", b.get("name") or "", b.get("tex") or ""]
    parts += b.get("items") or []
    parts += b.get("head") or []
    parts += b.get("legend") or []
    for row in b.get("rows") or []:
        parts += [str(c) for c in row]
    return " ".join(p for p in parts if p)


def toks(s: str) -> set[str]:
    s = re.sub(r"\[\[|\]\]", "", s).lower()
    return {w for w in re.findall(r"[\w\u0600-\u06ff]{4,}", s) if w not in STOP}


# --------------------------------------------------------------------- ساختار
def check_structure(chs: dict) -> None:
    line("## ۱) ساختار و ترتیب فصل‌ها")
    for no, ch in sorted(chs.items()):
        blocks = ch["blocks"]
        heads = [b["text"] for b in blocks if b.get("type") == "h2"]
        nums = []
        for t in heads:
            m = re.match(r"^([۰-۹]+)\.", t)
            nums.append(int(m.group(1).translate(FA2EN)) if m else None)
        if nums != list(range(1, len(nums) + 1)):
            issue("خطا", "ساختار", f"فصل {no}: شماره بخش‌ها پیوسته نیست → {nums}")
        seen, dup = set(), []
        for t in heads:
            if t in seen:
                dup.append(t)
            seen.add(t)
        if dup:
            issue("خطا", "ساختار", f"فصل {no}: تیتر تکراری → {dup}")
        # ترتیب بلوک‌ها: «مرور سریع» باید آخرین بلوک محتوایی باشد
        idx = [i for i, b in enumerate(blocks) if b.get("type") == "quickreview"]
        if len(idx) != 1:
            issue("هشدار", "ساختار", f"فصل {no}: {len(idx)} بلوک «مرور سریع» (انتظار: ۱)")
        elif idx[0] != len(blocks) - 1:
            tail = [b.get("type") for b in blocks[idx[0] + 1:]]
            issue("خطا", "ساختار", f"فصل {no}: بعد از «مرور سریع» هنوز {len(tail)} بلوک است → {tail[:6]}")
        # هر شکل باید بین دو تیتر، بعد از متن همان بخش باشد (نه بلافاصله بعد از تیتر)
        for i, b in enumerate(blocks):
            if b.get("type") != "figure":
                continue
            j = i - 1
            while j >= 0 and blocks[j].get("type") == "figure":
                j -= 1
            if j < 0 or blocks[j].get("type") in ("h2", "h3"):
                issue("هشدار", "ساختار", f"فصل {no}[{i}]: شکل بلافاصله بعد از تیتر آمده "
                                        f"({os.path.basename(b.get('file', ''))})")
        figs = sum(1 for b in blocks if b.get("type") == "figure")
        line(f"- فصل {no} — {ch['title']}: {len(blocks)} بلوک، {len(heads)} بخش، {figs} شکل، "
             f"{sum(1 for b in blocks if b.get('type') == 'table')} جدول")
    line()


# --------------------------------------------------------------------- بلوک‌ها
def check_blocks(chs: dict) -> None:
    line("## ۲) بلوک‌ها: خالی‌بودن، منبع و فایل شکل‌ها")
    for no, ch in sorted(chs.items()):
        for i, b in enumerate(ch["blocks"]):
            t = b.get("type")
            if t == "bullets" and not (b.get("items") or []):
                issue("خطا", "بلوک", f"ch{no}[{i}] bullets بدون آیتم")
            elif t != "figure" and not btext(b).strip():
                issue("خطا", "بلوک", f"ch{no}[{i}] {t} خالی")
            if t == "figure":
                fp = ROOT / (b.get("file") or "")
                if not fp.exists():
                    issue("خطا", "شکل", f"ch{no}[{i}] فایل شکل نیست: {b.get('file')}")
                if not (b.get("caption") or "").strip():
                    issue("خطا", "شکل", f"ch{no}[{i}] شکل بدون شرح: {b.get('file')}")
            if t in ("p", "key", "bullets", "examtip", "quickreview", "table", "formula") \
                    and not (b.get("src") or "").strip():
                issue("هشدار", "منبع", f"ch{no}[{i}] {t} بدون منبع: {btext(b)[:45]}")
    line("- همه بلوک‌ها بررسی شد (خالی/بدون شرح شکل/بدون منبع).")
    line()


# --------------------------------------------------------------------- بهداشت متن
def check_text(chs: dict) -> None:
    line("## ۳) بهداشت متن (نشانه‌های OCR/ASR)")
    for no, ch in sorted(chs.items()):
        for i, b in enumerate(ch["blocks"]):
            t = btext(b)
            if not t:
                continue
            if t.count("[[") != t.count("]]"):
                issue("خطا", "متن", f"ch{no}[{i}] براکت نامتوازن: {t[:60]}")
            if PRESENTATION.search(t):
                issue("خطا", "متن", f"ch{no}[{i}] کاراکتر عرض‌نمایشی عربی: {t[:60]}")
            if TATWEEL.search(t):
                issue("خطا", "متن", f"ch{no}[{i}] کشیده (ـ): {t[:60]}")
            if REPLACEMENT.search(t):
                issue("خطا", "متن", f"ch{no}[{i}] کاراکتر جایگزین U+FFFD: {t[:60]}")
            if ARABIC_LETTERS.search(t):
                issue("هشدار", "متن", f"ch{no}[{i}] حرف عربی (ي/ك/ى): {t[:60]}")
            if "  " in t:
                issue("هشدار", "متن", f"ch{no}[{i}] فاصله دوتایی: {t[:60]}")
            if not ARABIC.search(t) and len(t) > 25:
                issue("هشدار", "متن", f"ch{no}[{i}] بلوک بدون متن فارسی: {t[:70]}")
            if re.search(r"(.)\1{5,}", t):
                issue("هشدار", "متن", f"ch{no}[{i}] تکرار حرف: {t[:60]}")
            # جمله‌های محاوره‌ای و نشانی‌های رونویسی خام
            for bad in ("می‌کنن", "می‌ده", "دیگه", "باشه", "بچه‌ها", "عزیزان", "خدمتتون", "خدمت شما",
                        "استاد گفت", "میشه", "داره", "اینا"):
                if bad in t:
                    issue("هشدار", "متن", f"ch{no}[{i}] لحن محاوره‌ای «{bad}»: {t[:60]}")
                    break
    line("- براکت، کاراکتر عرض‌نمایشی، کشیده، حروف عربی، لحن محاوره‌ای، تکرار بررسی شد.")
    line()


# --------------------------------------------------------------------- ویدیو
VIDEO_FILES = {8: {4, 5, 6}, 9: {1, 2, 3}, 7: {7, 8, 9, 10},
               4: {11, 12, 13, 14, 15, 16}, 5: {11, 12, 13, 14, 15, 16},
               6: {11, 12, 13, 14, 15, 16}, 1: {17, 18, 19}, 2: {17, 18, 19}, 3: {17, 18, 19}}


def check_video(chs: dict) -> None:
    line("## ۴) بلوک‌های ویدیویی: قالب، زمان و تناسب فصل")
    pat = re.compile(r"فایل ([۰-۹0-9]+)")
    counts = collections.Counter()
    for no, ch in sorted(chs.items()):
        for i, b in enumerate(ch["blocks"]):
            src = b.get("src") or ""
            if "منبع: ویدیو" not in src:
                continue
            if not src.startswith("منبع: ویدیو —"):
                issue("هشدار", "ویدیو", f"ch{no}[{i}] قالب منبع: {src[:60]}")
            m = pat.search(src)
            if not m:
                issue("خطا", "ویدیو", f"ch{no}[{i}] بدون شماره فایل: {src[:60]}")
                continue
            num = int(m.group(1).translate(FA2EN))
            counts[num] += 1
            if not re.search(r"[۰-۹0-9]{1,2}:[۰-۹0-9]{2}", src):
                issue("هشدار", "ویدیو", f"ch{no}[{i}] بدون زمان MM:SS: {src[:60]}")
            if no in VIDEO_FILES and num not in VIDEO_FILES[no]:
                issue("خطا", "ویدیو", f"ch{no}[{i}] ویدیو {num} به این فصل نمی‌خورد: {src[:50]}")
    missing = [n for n in range(1, 20) if not counts[n]]
    if missing:
        issue("خطا", "ویدیو", f"ویدیوهای بدون هیچ ارجاع: {missing}")
    line(f"- {sum(counts.values())} بلوک ویدیویی از ۱۹ ویدیو؛ بدون ارجاع: {missing or 'ندارد'}")
    line()


# --------------------------------------------------------------------- جای‌گذاری
def _idf(secs, blocks):
    df = collections.Counter()
    for s in secs:
        for w in toks(" ".join(btext(b) for b in blocks[s[0]:s[2]])):
            df[w] += 1
    n = max(1, len(secs))
    return lambda w: math.log(1 + n / (1 + df.get(w, 0)))


def check_placement(chs: dict) -> None:
    line("## ۵) جای شکل‌ها و بلوک‌های ویدیویی نسبت به متن بخش")
    for no, ch in sorted(chs.items()):
        blocks = ch["blocks"]
        secs = []
        for i, b in enumerate(blocks):
            if b.get("type") == "h2":
                secs.append([i, b["text"]])
        for k, s in enumerate(secs):
            s.append(secs[k + 1][0] if k + 1 < len(secs) else len(blocks))
        if not secs:
            continue
        idf = _idf(secs, blocks)
        bad = 0
        for i, b in enumerate(blocks):
            isfig = b.get("type") == "figure"
            isvid = "منبع: ویدیو" in (b.get("src") or "")
            if not (isfig or isvid):
                continue
            tk = toks(b.get("caption") or btext(b))
            if not tk:
                continue
            win = set()
            for d in range(1, 5):
                for j in (i - d, i + d):
                    if 0 <= j < len(blocks) and blocks[j].get("type") != "figure":
                        win |= toks(btext(blocks[j]))
            local = sum(idf(w) for w in tk & win)
            best, bj = 0.0, None
            for j in range(len(blocks)):
                if abs(j - i) <= 3:
                    continue
                w2 = set()
                for d in range(0, 3):
                    if j + d < len(blocks) and blocks[j + d].get("type") != "figure":
                        w2 |= toks(btext(blocks[j + d]))
                sc = sum(idf(w) for w in tk & w2)
                if sc > best:
                    best, bj = sc, j
            if best > local * 1.5 and best > 2.0 and bj is not None:
                bad += 1
                ci = next((s for s in secs if s[0] <= i < s[2]), None)
                bi = next((s for s in secs if s[0] <= bj < s[2]), None)
                issue("بررسی", "جای‌گذاری",
                      f"ch{no}[{i}] {'شکل' if isfig else 'ویدیو'} در «{ci[1][:30] if ci else '—'}» "
                      f"ولی متن مشابه در «{bi[1][:30] if bi else '—'}» است: {(b.get('caption') or btext(b))[:45]}")
        line(f"- فصل {no}: {bad} مورد نیازمند بررسی دستی")
    line()


# --------------------------------------------------------------------- پوشش
def check_coverage(chs: dict) -> None:
    line("## ۶) پوشش منابع OCR و ویدیوها")
    book = set()
    book_num = set()
    for ch in chs.values():
        for b in ch["blocks"]:
            book |= toks(json.dumps(b, ensure_ascii=False))
            book_num |= set(re.findall(r"\d{2,}", json.dumps(b, ensure_ascii=False)
                                       .translate(FA2EN)))
    slugs = [p.name for p in (ROOT / "work" / "ocr").iterdir() if (p / "all.md").exists()]
    total_pages = low_pages = 0
    for slug in sorted(slugs):
        txt = (ROOT / "work" / "ocr" / slug / "all.md").read_text(encoding="utf-8", errors="ignore")
        parts = re.split(r"={3,}\s*page\s*(\d+)\s*={3,}", txt, flags=re.I)
        pages = {int(parts[i]): parts[i + 1] for i in range(1, len(parts), 2)}
        for n, body in pages.items():
            t = toks(body)
            if len(t) < 18:
                continue                       # صفحه‌های تصویری/کم‌متن
            total_pages += 1
            cov = len(t & book) / len(t)
            if cov < 0.55:
                low_pages += 1
                issue("بررسی", "پوشش",
                      f"{slug} ص{n}: پوشش واژگانی {cov*100:.0f}% — "
                      f"ناموجودها: {'، '.join(sorted(t - book)[:8])}")
    line(f"- صفحه‌های متنی بررسی‌شده: {total_pages} · کم‌پوشش (<۵۵٪): {low_pages}")

    # پوشش عددی ویدیوها
    missing = {}
    for i in range(1, 20):
        p = Path(f"/tmp/dg_{i:02d}.txt")
        if not p.exists():
            continue
        txt = p.read_text(encoding="utf-8")
        nums = re.findall(r"\b\d{2,4}\b", txt)
        uniq = [n for n, _ in collections.Counter(nums).most_common()]
        miss = [n for n in uniq if n not in book_num]
        if miss:
            missing[i] = miss
    if missing:
        for k, v in missing.items():
            issue("بررسی", "ویدیو", f"ویدیو {k:02d}: عددهای ناموجود در جزوه → {v[:8]}")
    else:
        line("- پوشش عددی ویدیوها: کامل (هر عدد کلیدی هر ۱۹ ویدیو در جزوه هست).")
    line()


# --------------------------------------------------------------------- PDF
def check_pdf(chs: dict, pdf: Path) -> None:
    if not pdf.exists():
        issue("خطا", "PDF", f"فایل PDF نیست: {pdf}")
        return
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(pdf))
    n = len(doc)
    raw = [(doc[i].get_textpage().get_text_range() or "") for i in range(n)]
    pages = [re.sub(r"\s+", "", t) for t in raw]
    line(f"## ۷) تطبیق با PDF رندرشده ({n} صفحه)")

    # صفحه‌های خالی
    empties = [i + 1 for i, t in enumerate(pages) if len(t) < 25 and i not in (0, n - 1)]
    if empties:
        issue("هشدار", "PDF", f"صفحه‌های کم‌متن: {empties[:10]}")
    line(f"- صفحه‌های خالی/کم‌متن: {len(empties)}")

    # کاراکترهای ناخواسته
    bad = [i + 1 for i, t in enumerate(pages) if PRESENTATION.search(t) or "\ufffd" in t]
    if bad:
        issue("خطا", "PDF", f"صفحه‌های دارای کاراکتر ناخواسته: {bad[:10]}")
    line(f"- صفحه‌های دارای کاراکتر عرض‌نمایشی/جایگزین: {len(bad)}")

    # هر شرح شکل باید در PDF باشد
    cap_missing = []
    for no, ch in sorted(chs.items()):
        for b in ch["blocks"]:
            if b.get("type") != "figure":
                continue
            cap = re.sub(r"\s+|‌", "", (b.get("caption") or ""))
            key = cap[:26]
            if key and not any(key in p for p in pages):
                cap_missing.append((no, os.path.basename(b.get("file", "")), key[:30]))
    if cap_missing:
        for no, f, k in cap_missing[:10]:
            issue("خطا", "PDF", f"ch{no}: شرح شکل در PDF نیست → {f} ({k})")
    line(f"- شرح شکل‌های پیدانشده در PDF: {len(cap_missing)}")

    # شماره صفحه فصل‌ها در فهرست
    pm = json.loads((ROOT / "render" / "page_map.json").read_text(encoding="utf-8"))
    wrong = []
    for k, v in pm.items():
        if not k.startswith("ch"):
            continue
        no = int(k[2:])
        title = re.sub(r"\s+|‌", "", chs[no]["title"])[:18]
        window = "".join(pages[max(0, v["start"] - 1):v["start"] + 2])
        if title not in window:
            wrong.append((k, v["start"] + 1))
    if wrong:
        issue("خطا", "PDF", f"شماره صفحه فهرست با تیتر فصل نمی‌خواند: {wrong[:6]}")
    line(f"- تطبیق تیتر فصل‌ها با شماره صفحه فهرست: {'درست' if not wrong else 'نادرست'}")

    # راهنمای مطالعه دکتر درویش
    guide = [k for k in pm if k.startswith("guide:")]
    line(f"- ردیف‌های راهنمای مطالعه با شماره صفحه: {len(guide)}")

    # سرریز افقی
    over = []
    for i in range(n):
        w = doc[i].get_width()
        try:
            boxes = doc[i].get_textpage().get_rectboxes()
        except Exception:
            boxes = []
        for r in boxes:
            if r.left < -1 or r.right > w + 1:
                over.append(i + 1)
                break
    if over:
        issue("هشدار", "PDF", f"سرریز افقی در صفحه‌های: {over[:10]}")
    line(f"- صفحه‌های دارای سرریز افقی: {len(over)}")
    line()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default=str(ROOT / "HumsYar_MedPhysics_Jozve.pdf"))
    ap.add_argument("--out", default=str(ROOT / "render" / "audit_report.txt"))
    args = ap.parse_args()

    chs = load_lock()
    line("# گزارش بازبینی صفر تا صد جزوه فیزیک پزشکی")
    line()
    check_structure(chs)
    check_blocks(chs)
    check_text(chs)
    check_video(chs)
    check_placement(chs)
    check_coverage(chs)
    check_pdf(chs, Path(args.pdf))

    n_err = sum(1 for s, _, _ in ISSUES if s == "خطا")
    n_warn = sum(1 for s, _, _ in ISSUES if s == "هشدار")
    n_chk = sum(1 for s, _, _ in ISSUES if s == "بررسی")
    line("## جمع‌بندی")
    line(f"- خطا: {n_err} · هشدار: {n_warn} · نیازمند بررسی دستی: {n_chk}")
    if ISSUES:
        line()
        line("### فهرست موارد")
        for sev, area, msg in ISSUES:
            line(f"- [{sev}] {area}: {msg}")
    Path(args.out).write_text("\n".join(LINES) + "\n", encoding="utf-8")
    print("\n".join(LINES[:120]))
    print(f"...\n(گزارش کامل: {args.out})")
    return 1 if n_err else 0


if __name__ == "__main__":
    raise SystemExit(main())
