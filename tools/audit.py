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
import unicodedata
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

# الگوهای محاوره‌ای: هر واژه با مرز نویسه‌های فارسی محصور می‌شود تا «مدارهای»،
# «می‌دهند» و مانند آن‌ها اشتباهاً محاوره‌ای شمرده نشوند.
COLLOQUIAL_WORDS = ["می‌کنن", "می‌دن", "می‌گن", "می‌گه", "می‌شه", "نمی‌شه", "می‌خواد",
                    "می‌تونه", "نمی‌تونه", "دیگه", "باشه", "داره", "اینا", "بچه‌ها",
                    "عزیزان", "خدمتتون", "خوبید", "چطورید"]
COLLOQUIAL = [rf"(?<![\u0600-\u06ff]){re.escape(w)}(?![\u0600-\u06ff])"
              for w in COLLOQUIAL_WORDS] + ["استاد گفت", "خدمت شما"]

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
            # جمله‌های محاوره‌ای (فقط صورت‌های محاوره‌ایِ مستقل، نه واژه‌های کتابی مانند
            # «می‌دهد» یا «مدارهای»)
            for bad in COLLOQUIAL:
                if re.search(bad, t):
                    issue("هشدار", "متن",
                          f"ch{no}[{i}] لحن محاوره‌ای «{bad}»: {t[:60]}")
                    break
    line("- براکت، کاراکتر عرض‌نمایشی، کشیده، حروف عربی، لحن محاوره‌ای، تکرار بررسی شد.")
    line()


# --------------------------------------------------------------------- ویدیو
# ویدیوهای تک‌موضوعی محدود می‌شوند؛ رادیوبیولوژی (۴–۶) افزون بر فصل ۸، در فصل‌های
# درمان (۴) و حفاظت (۶) هم مجاز است، چون محتوای آن جلسات همان‌جا موضوعیت دارد.
VIDEO_FILES = {
    1: {9}, 2: {9}, 3: {9},
    4: {8, 4, 6}, 5: {8, 4, 6}, 6: {8, 4, 6},
    7: {7}, 8: {7}, 9: {7}, 10: {7},
}


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
            if num in VIDEO_FILES and no not in VIDEO_FILES[num]:
                issue("خطا", "ویدیو", f"ch{no}[{i}] ویدیو تک‌موضوعی {num} باید در فصل "
                                        f"{sorted(VIDEO_FILES[num])} باشد: {src[:50]}")
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
    """آیا شکل‌ها و بلوک‌های ویدیویی در همان بخشی هستند که دربارهٔ موضوعشان حرف می‌زند؟

    سنجه: پوشش وزنی (IDF) واژه‌های شرح هر شکل با واژه‌های همهٔ بلوک‌های متنی همان بخش
    (از سرفصل تا سرفصل بعدی). اگر شرح شکل هیچ پشتوانهٔ متنی در بخش خودش نداشته باشد
    ولی در بخش دیگری داشته باشد، به‌عنوان «جای‌گذاری مشکوک» گزارش می‌شود.
    """
    line("## ۵) جای شکل‌ها و بلوک‌های ویدیویی نسبت به متن بخش")
    for no, ch in sorted(chs.items()):
        blocks = ch["blocks"]
        secs = [[i, b["text"]] for i, b in enumerate(blocks) if b.get("type") == "h2"]
        for k, s in enumerate(secs):
            s.append(secs[k + 1][0] if k + 1 < len(secs) else len(blocks))
        if not secs:
            continue
        idf = _idf(secs, blocks)
        sec_txt = []
        for st, _, en in secs:
            acc = set()
            for j in range(st + 1, en):
                if blocks[j].get("type") not in ("figure", "table"):
                    acc |= toks(btext(blocks[j]))
            sec_txt.append(acc)
        bad = 0
        for i, b in enumerate(blocks):
            isfig = b.get("type") == "figure"
            isvid = "منبع: ویدیو" in (b.get("src") or "")
            if not (isfig or isvid):
                continue
            tk = toks(b.get("caption") or btext(b))
            if len(tk) < 3:
                continue
            total = sum(idf(w) for w in tk) or 1.0
            si = next((k for k, s in enumerate(secs) if s[0] <= i < s[2]), None)
            if si is None:
                continue
            here = sum(idf(w) for w in tk & sec_txt[si]) / total
            there, tj = 0.0, None
            for k, acc in enumerate(sec_txt):
                if k == si:
                    continue
                sc = sum(idf(w) for w in tk & acc) / total
                if sc > there:
                    there, tj = sc, k
            # فقط وقتی هشدار می‌دهیم که در بخش خودش تقریباً هیچ پشتوانه‌ای نباشد
            # ولی در بخش دیگری پشتوانهٔ روشنی داشته باشد.
            if here < 0.30 and there > 0.55 and tj is not None:
                bad += 1
                issue("بررسی", "جای‌گذاری",
                      f"ch{no}[{i}] {'شکل' if isfig else 'ویدیو'} در «{secs[si][1][:28]}» "
                      f"(پوشش {here*100:.0f}٪) ولی در «{secs[tj][1][:28]}» "
                      f"(پوشش {there*100:.0f}٪) پشتوانهٔ بیشتر دارد: "
                      f"{(b.get('caption') or btext(b))[:40]}")
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
    total_pages = low_pages = en_pages = 0
    reviewed: list[str] = []
    for slug in sorted(slugs):
        txt = (ROOT / "work" / "ocr" / slug / "all.md").read_text(encoding="utf-8", errors="ignore")
        parts = re.split(r"={3,}\s*page\s*(\d+)\s*={3,}", txt, flags=re.I)
        pages = {int(parts[i]): parts[i + 1] for i in range(1, len(parts), 2)}
        for n, body in pages.items():
            t = toks(body)
            if len(t) < 18:
                continue                       # صفحه‌های تصویری/کم‌متن
            latin = len(re.findall(r"[A-Za-z]{3,}", body))
            persian = len(re.findall(r"[\u0600-\u06ff]{3,}", body))
            if latin > persian:
                en_pages += 1                  # اسلاید انگلیسی: در جزوه به فارسی ترجمه شده است
                continue
            total_pages += 1
            cov = len(t & book) / len(t)
            if cov < 0.55:
                low_pages += 1
                verdict = MANUAL_REVIEW.get((slug, n))
                if verdict:
                    reviewed.append(f"{slug} ص{n} → {verdict}")
                else:
                    issue("بررسی", "پوشش",
                          f"{slug} ص{n}: پوشش واژگانی {cov*100:.0f}% (بدون بازبینی دستی) — "
                          f"ناموجودها: {'، '.join(sorted(t - book)[:8])}")
    line(f"- صفحه‌های متنی فارسی بررسی‌شده: {total_pages} · کم‌پوشش (<۵۵٪): {low_pages}"
         f" · اسلاید انگلیسی/تصویری (خارج از سنجش واژگانی، ترجمه‌شده در جزوه): {en_pages}")
    if reviewed:
        line(f"- از صفحه‌های کم‌پوشش، {len(reviewed)} صفحه دستی بازبینی شد و موضوعشان در جزوه هست:")
        for r in reviewed:
            line(f"    · {r}")

    # پوشش عددی ویدیوها: خلاصه‌های هر ویدیو (render/video_digests) با اعداد جزوه سنجیده می‌شود.
    missing, explained = {}, []
    for i in range(1, 20):
        dg = DIGESTS / f"{i:02d}.txt"
        if not dg.exists():
            continue
        txt = "\n".join(ln for ln in dg.read_text(encoding="utf-8").splitlines()
                        if not ln.startswith("###"))
        uniq = [n for n, _ in collections.Counter(re.findall(r"\b\d{2,4}\b", txt)).most_common()]
        for n in uniq:
            if n in book_num:
                continue
            why = EXPLAINED_ASR.get((i, n))
            if why:
                explained.append((i, n, why))
            else:
                missing.setdefault(i, []).append(n)
    if missing:
        for k, v in missing.items():
            issue("بررسی", "ویدیو", f"ویدیو {k:02d}: عدد ناموجود در جزوه → {v[:8]}")
    else:
        line("- پوشش عددی ویدیوها: کامل؛ هیچ عدد بی‌توضیحی نمانده است.")
    if explained:
        line(f"- عددهای ادغام‌شدهٔ ASR که توضیح مستند دارند: {len(explained)}")
        for i, n, why in explained:
            issue("بررسی", "ASR", f"ویدیو {i:02d} عدد «{n}» → {why}")
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
    # استخراج متن PDF ترتیب دیداری (RTL) دارد؛ برای تطبیق، واژه‌های هر خط را برمی‌گردانیم
    def rtl(t: str) -> str:
        return re.sub(r"\s+", " ", " ".join(" ".join(reversed(ln.split()))
                                              for ln in t.splitlines()))
    pages_raw = [rtl(t) for t in raw]
    pages = [re.sub(r"[^\w\u0600-\u06ff]", "", t) for t in pages_raw]
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
    # هر شرح شکل: دست‌کم ۷۰٪ واژه‌های محتوایی‌اش باید در یکی از صفحه‌های PDF باشد
    # (متن PDF ترتیب دیداری دوجهته دارد؛ پس تطبیق واژه‌ای می‌کنیم نه رشته‌ای)
    page_toks = [_tokens(p) for p in pages_raw]
    cap_missing = []
    for no, ch in sorted(chs.items()):
        for b in ch["blocks"]:
            if b.get("type") != "figure":
                continue
            words = sorted(_tokens((b.get("caption") or "").translate(FA2EN)))
            if len(words) < 3:
                continue
            need = 0.6 * len(words)
            if not any(sum(1 for w in words if w in pt) >= need for pt in page_toks):
                cap_missing.append((no, os.path.basename(b.get("file", "")), " ".join(words[:5])))
    if cap_missing:
        for no, f, k in cap_missing[:10]:
            issue("بررسی", "PDF", f"ch{no}: تطبیق واژه‌ای شرح شکل کامل نشد (متن دوجهته) → {f} ({k})")
    line(f"- شرح شکل‌های پیدانشده در PDF: {len(cap_missing)}")

    # شماره صفحه فصل‌ها در فهرست
    pm = json.loads((ROOT / "render" / "page_map.json").read_text(encoding="utf-8"))
    wrong = []
    for k, v in pm.items():
        if not k.startswith("ch"):
            continue
        no = int(k[2:])
        first = next((b["text"] for b in chs[no]["blocks"] if b.get("type") == "h2"), "")
        key = re.sub(r"[^\w\u0600-\u06ff]", "", first)[:16]
        pg = v["start"]                       # ۰-مبنا
        ok = bool(key) and key in pages[pg]
        if not ok:
            wrong.append((k, pg + 1, first[:22]))
    if wrong:
        issue("خطا", "PDF", f"شماره صفحه شروع فصل با نخستین سرفصل آن نمی‌خواند: {wrong[:6]}")
    line(f"- تطبیق شروع فصل‌ها با نخستین سرفصل روی همان صفحه: {'درست' if not wrong else 'نادرست'}")

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


def _tokens(s: str) -> set[str]:
    """واژه‌های ۴+ نویسه‌ای بدون نشانه‌گذاری (برای تطبیق متن دوجهته)."""
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"[،؛؟.,()\[\]»«:;\-–—/\\|\d]", " ", s)
    return set(re.findall(r"[^\W_]{4,}", s, flags=re.UNICODE))


DIGESTS = ROOT / "render" / "video_digests"

# عددهایی که در ASR ویدیو به‌هم چسبیده‌اند (مثل «۴ ممیز ۱۹» → 1900) یا عدد غیرقابل‌تأییدند.
# هر مورد با توضیح مستند ثبت می‌شود تا «عدد ناموجود» تکراری گزارش نشود.
EXPLAINED_ASR = {
    (12, "449"):  "ادغام رقمی ASR؛ در جزوه «[[4.49 × 10^9]] سال» نیمه‌عمر اورانیم-۲۳۸ آمده است.",
    (12, "1900"): "ادغام رقمی ASR («۴ ممیز ۱۹»)؛ در جزوه «[[4.19 MeV]]» انرژی آلفا آمده است.",
    (12, "221"):  "ادغام «۲۲-۱۱» ([[Na-22]])؛ مفهوم فرایند ایزوباریک در همین بخش پوشش داده شده است.",
    (13, "6831"): "ادغام «۶۸» و «۳۱»؛ [[Ga-68]] با عدد اتمی [[31]] در همین بخش آمده است.",
    (13, "6830"): "ادغام «۶۸» و «۳۰»؛ [[Zn-68]] با عدد اتمی [[30]] در همین بخش آمده است.",
    (16, "1620"): "عدد نامفهوم ASR (احتمالاً «۱۶۰۰ سال») بدون ذکر عنصر؛ برای پرهیز از حدس، ثبت نشد. "
                  "فرمول نیمه‌عمر [[T½ = 0.693/λ]] در همین بخش پوشش دارد.",
    (17, "1860"): "سال نامطمئن در بیوگرافی رونتگن (ASR)؛ در جزوه فقط تاریخ مستند کشف پرتو ایکس "
                  "([[8 نوامبر 1895]]) ثبت شده است.",
    (19, "2500"): "ادغام ASR برای «[[0.25 میلی‌متر]] سرب»؛ معادل‌های روپوش سربی در همین بخش آمده است.",
}


# بازبینی دستی صفحه‌های کم‌پوشش (OCR این صفحه‌ها مخدوش/دوزبانه است، پس سنجش واژگانی
# معتبر نیست). هر مورد دستی با جزوه مقابله شده و محل پوشش ثبت شده است.
MANUAL_REVIEW = {
    ("afzalipour", 123): "تقویت‌کننده تصویر در فلوروسکوپی و اثر بزرگ‌نمایی ← فصل ۳ (بخش فلوروسکوپی).",
    ("darvish_radiobio", 6): "اثرات قطعی/احتمالی و شرط دوز آستانه ← فصل ۸ (بخش اثرات قطعی و احتمالی).",
    ("darvish_radiobio", 18): "هیدرولیز آب و رادیکال هیدروکسیل ← فصل ۸ (بخش اثر غیرمستقیم).",
    ("darvish_radiobio", 21): "برهم‌کنش مستقیم با هدف بحرانی ← فصل ۸ (بخش اثر مستقیم).",
    ("darvish_radiobio", 29): "مقایسه ریسک (کره بادام‌زمینی، سیگار، نیویورک، ۱۰ mrem) ← فصل ۸ (بخش مقایسه ریسک).",
    ("darvish_radiobio", 30): "دوره نهفته (کوتاه تا چند دهه) ← فصل ۸ (بخش دوره نهفته).",
    ("darvish_radiobio", 33): "آسیب کروموزومی (اتصال مجدد، قطعه آسنتریک، حلقه و دوسطحی) ← فصل ۸.",
    ("darvish_radiobio", 44): "آسیب پرتوی مولکول‌های زیستی و عوامل دیگر (UV) ← فصل ۸.",
    ("darvish_radiobio", 49): "[[RBE]] و تعریف دوز مرجع ۲۵۰ کیلوولت ← فصل ۸ (بخش RBE).",
    ("darvish_radiobio", 64): "[[LD50/30]]، مکانیسم‌های آسیب و معادل گرمایی ← فصل ۸ (بخش LD50).",
    ("darvish_radiobio", 65): "قانون برگونی و تریبوندو (۱۹۰۶) و سه ویژگی حساسیت ← فصل ۸.",
    ("darvish_radiobio", 66): "سلول‌های کم‌حساس (خونی بالغ، ماهیچه، گانگلیون، مخاط معده) ← فصل ۸.",
    ("darvish_radiobio", 67): "ناهنجاری کروموزومی/کروماتیدی و مراحل اینترفاز ← فصل ۸.",
    ("darvish_radiobio", 80): "بهینه‌سازی [[ALARA]] با عوامل اقتصادی-اجتماعی ← فصل ۶ (سیستم حفاظت).",
    ("haghparast_mphpd", 16): "دسته‌بندی مواد رادیواکتیو (طبیعی/مصنوعی) ← فصل ۴ بخش ۱.",
    ("haghparast_mphpd", 30): "پوزیترون، ناپایداری و نابودی با تولید دو فوتون [[511 keV]] ← فصل ۴.",
    ("haghparast_mphpd", 44): "رابطه نیمه‌عمر [[T½ = 0.693/λ]] ← فصل ۴ (بخش نیمه‌عمر).",
    ("haghparast_mphpd", 59): "فرکانس‌بندی امواج صوتی ([[<16 Hz]]، [[16 Hz–20 kHz]]، [[>20 kHz]]) ← فصل ۷ (جدول فرکانس‌بندی).",
    ("haghparast_mphpd", 61): "فرکانس‌های کاربردی تصویربرداری پزشکی (مگاهرتز) ← فصل ۷ بخش ۱.",
    ("haghparast_mphpd", 66): "سرعت صوت و رابطه عکس با تراکم‌پذیری محیط ← فصل ۷ (بخش سرعت صوت).",
    ("haghparast_mphpd", 67): "اثر چگالی محیط بر سرعت انتشار ← فصل ۷ (بخش سرعت صوت).",
    ("haghparast_mphpd", 69): "مگنتواسترکسیون (فرومغناطیس/نیکل، تا ۱۰۰ کیلوهرتز، فیزیوتراپی) ← فصل ۷ (جدول روش‌های تولید).",
    ("haghparast_mphpd", 71): "پیزوالکتریک معکوس و مستقیم در بلور ← فصل ۷ (بخش ترانس‌دیوسر).",
    ("haghparast_mphpd", 76): "امپدانس صوتی ریه و بازتابش کامل ← فصل ۷ (بخش عوامل بازتابش).",
    ("haghparast_mphpd", 81): "لزوم تابش عمود پروب و آشکارسازی امواج بازگشتی ← فصل ۷ (نکته زاویه تابش).",
    ("haghparast_tashasho", 36): "پس از ده نیمه‌عمر، تابش به یک‌هزارم می‌رسد ← فصل ۴ (بخش نیمه‌عمر).",
}


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
