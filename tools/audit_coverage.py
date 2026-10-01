#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بازبینی پوشش منابع: چه نکته‌ای از جزوه‌ها و ویدیوها در جزوه جامع جا افتاده است؟

روش: واژه‌های محتوایی هر منبع (اصطلاحات لاتین، اعداد و واژه‌های فارسی ۴+ حرفی)
استخراج می‌شود و اگر واژه‌ای در منبع تکرار قابل‌توجه داشته باشد ولی در کل جزوه
نیاید، به‌عنوان «احتمال جاافتادگی» گزارش می‌شود. این ابزار داوری نمی‌کند؛ فقط
کار را برای بررسی انسانی غربال می‌کند.

usage:  python3 tools/audit_coverage.py [--min-count 4] [--out FILE]
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FA_STOP = set("""
و در به از که با این را برای است هست نیست می های ها یک دو سه آن او ما شما آنها
شود شده می‌شود می‌کند می‌دهد می‌گیرد باشد بودند دارد داریم دارند کرد کردن کند
هم نیز بر تا بی هر همه اگر اما یا چه چیزی وقتی زمان طور صورت مورد نظر بین
روی زیر بالا پایین داخل خارج هنگام هنگام همچنین بنابراین مثلا مانند
بسیار خیلی کم زیاد بزرگ کوچک اول دوم سوم چهارم پنجم ششم هفتم هشتم نهم دهم
باید نباید توان نمی باید کرد گرفته گفته داده استفاده عنوان دلیل علت
استاد درس جلسه صفحه اسلاید جزوه ویدیو فایل بخش فصل شکل جدول
""".split())

LATIN = re.compile(r"[A-Za-z][A-Za-z0-9\-]{1,}")
NUM = re.compile(r"[\d\u06f0-\u06f9][\d\u06f0-\u06f9.,]*")
FAW = re.compile(r"[\u0600-\u06ff]{4,}")


def source_terms(text: str) -> collections.Counter:
    c: collections.Counter = collections.Counter()
    for w in LATIN.findall(text):
        c["la:" + w.lower()] += 1
    for w in NUM.findall(text):
        w = w.strip(".,")
        if len(w) >= 2:
            c["num:" + w] += 1
    for w in FAW.findall(text):
        w = w.replace("\u200c", " ").strip()
        if w and w not in FA_STOP:
            c["fa:" + w] += 1
    return c


def digits(s: str) -> str:
    """همه ارقام را لاتین کن تا «۱.۰۲۲» و «1.022» یکی شمرده شوند."""
    return s.translate({ord(f): ord(e) for f, e in zip("۰۱۲۳۴۵۶۷۸۹", "0123456789")})


def norm(s: str) -> str:
    s = re.sub(r"\[\[|\]\]", " ", s or "")
    s = s.replace("\u200c", " ").replace("ي", "ی").replace("ك", "ک")
    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-count", type=int, default=4)
    ap.add_argument("--out", default=str(ROOT / "work" / "review" / "coverage_report.md"))
    args = ap.parse_args()

    jozve = []
    for f in sorted((ROOT / "lock").glob("ch*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        for b in d["blocks"]:
            parts = [b.get("text") or "", b.get("caption") or "", b.get("name") or ""]
            parts += [str(x) for x in (b.get("items") or [])]
            parts += [str(x) for x in (b.get("head") or [])]
            for r in b.get("rows") or []:
                parts += [str(x) for x in r]
            for lg in b.get("legend") or []:
                parts += [str(x) for x in lg]
            parts.append(b.get("src") or "")
            jozve.append(" ".join(parts))
    jz = norm(" ".join(jozve))
    jz_l = jz.lower()
    jz_num = set(digits(x) for x in NUM.findall(jz))
    jz_fa = set(w.replace("\u200c", " ") for w in FAW.findall(jz))
    jz_fa |= set(digits(w) for w in jz_fa)
    jz_la = set(w.lower() for w in LATIN.findall(jz))

    sources = []
    for d in sorted((ROOT / "work" / "ocr").iterdir()):
        if d.is_dir() and (d / "all.md").exists():
            sources.append(("جزوه: " + d.name, (d / "all.md").read_text(encoding="utf-8", errors="ignore")))
    tdir = ROOT / "work" / "transcripts"
    if tdir.exists():
        for d in sorted(tdir.iterdir()):
            f = d / "raw.md"
            if f.exists():
                sources.append(("ویدیو: " + d.name, f.read_text(encoding="utf-8", errors="ignore")))

    lines = ["# بازبینی پوشش منابع (احتمال جاافتادگی)", ""]
    summary = []
    all_missing = collections.Counter()
    for name, text in sources:
        terms = source_terms(norm(text))
        missing = []
        for t, c in terms.items():
            if c < args.min_count:
                continue
            kind, val = t.split(":", 1)
            if kind == "la":
                hit = val in jz_la
            elif kind == "num":
                hit = digits(val) in jz_num
            else:
                hit = val in jz_fa
            if not hit:
                missing.append((c, t))
        missing.sort(reverse=True)
        summary.append((name, len(terms), len(missing)))
        for c, t in missing[:40]:
            all_missing[t] += 1
        lines.append(f"## {name}")
        lines.append(f"- واژه‌های متمایز: {len(terms)} · ناموجود در جزوه (≥{args.min_count} تکرار): {len(missing)}")
        for c, t in missing[:25]:
            lines.append(f"    - ×{c} `{t}`")
        lines.append("")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"{'منبع':42s} {'واژه':>7s} {'ناموجود':>8s}")
    for name, n, m in summary:
        print(f"{name:42s} {n:7d} {m:8d}")
    print(f"\nگزارش: {out}")
    print("\nپرتکرارترین واژه‌های ناموجود در چند منبع:")
    for t, c in all_missing.most_common(20):
        print(f"   ×{c} منابع  {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
