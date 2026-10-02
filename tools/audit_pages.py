#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""پوشش صفحه‌به‌صفحه منابع: کدام صفحه از جزوه‌های منبع در جزوه جامع بازتاب ندارد؟

برای هر صفحه از هر جزوه (بلوک‌های «===== page N =====») واژه‌های محتوایی
استخراج می‌شود و میزان هم‌پوشانی با کل جزوه جامع سنجیده می‌شود. صفحه‌هایی که
هم‌پوشانی کم دارند صف بررسی انسانی می‌شوند (برخی فقط تصویر یا فهرست‌اند).

usage:  python3 tools/audit_pages.py [--min-words 25] [--thresh 0.18] [--out FILE]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FA_STOP = set("""
و در به از که با این را برای است هست نیست می های ها یک دو سه آن او ما شما آنها
شود شده باشد بودند دارد داریم دارند کرد کردن کند هم نیز بر تا بی هر همه اگر
اما یا چه چیزی وقتی زمان طور صورت مورد نظر بین روی زیر بالا پایین داخل خارج
هنگام همچنین بنابراین مثلا مانند بسیار خیلی کم زیاد بزرگ کوچک اول دوم سوم
چهارم پنجم ششم هفتم هشتم نهم دهم باید نباید توان نمی گفته داده استفاده عنوان
دلیل علت استاد درس جلسه صفحه اسلاید جزوه ویدیو فایل بخش فصل شکل جدول
این آن‌ها یکی دیگر باید شود کنید کنیم دهیم بدهیم بگیریم بگوییم است.
""".split())

PAGE = re.compile(r"=====\s*page\s*(\d+)\s*=====", re.I)
LATIN = re.compile(r"[A-Za-z][A-Za-z0-9\-]{2,}")
FAW = re.compile(r"[\u0600-\u06ff]{4,}")
NUM = re.compile(r"[\d\u06f0-\u06f9][\d\u06f0-\u06f9.]{2,}")


def digits(s: str) -> str:
    return s.translate({ord(f): ord(e) for f, e in zip("۰۱۲۳۴۵۶۷۸۹", "0123456789")})


def norm(s: str) -> str:
    s = re.sub(r"\[\[|\]\]", " ", s or "")
    return s.replace("\u200c", " ").replace("ي", "ی").replace("ك", "ک")


def terms(text: str) -> set[str]:
    out = set()
    for w in LATIN.findall(text):
        out.add("la:" + w.lower())
    for w in NUM.findall(digits(text)):
        out.add("num:" + w)
    for w in FAW.findall(text):
        w = w.replace("\u200c", " ").strip()
        if w and w not in FA_STOP:
            out.add("fa:" + w)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-words", type=int, default=25)
    ap.add_argument("--thresh", type=float, default=0.18)
    ap.add_argument("--out", default=str(ROOT / "work" / "review" / "page_coverage.md"))
    args = ap.parse_args()

    jz_parts = []
    for f in sorted((ROOT / "lock").glob("ch*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        for b in d["blocks"]:
            parts = [b.get("text") or "", b.get("caption") or ""]
            parts += [str(x) for x in (b.get("items") or [])]
            parts += [str(x) for x in (b.get("head") or [])]
            for r in b.get("rows") or []:
                parts += [str(x) for x in r]
            for lg in b.get("legend") or []:
                parts += [str(x) for x in lg]
            jz_parts.append(norm(" ".join(parts)))
    jz = terms(" ".join(jz_parts))

    lines = ["# پوشش صفحه‌به‌صفحه منابع", "",
             f"آستانه هم‌پوشانی: {args.thresh:.0%} · حداقل واژه صفحه: {args.min_words}", ""]
    total = low = 0
    worst = []
    for src in sorted((ROOT / "work" / "ocr").iterdir()):
        f = src / "all.md"
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        marks = [(m.start(), int(m.group(1))) for m in PAGE.finditer(text)]
        lines.append(f"## {src.name}")
        for i, (pos, pno) in enumerate(marks):
            end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
            body = norm(text[pos:end])
            t = terms(body)
            if len(t) < args.min_words:
                continue
            total += 1
            hit = len(t & jz)
            cov = hit / len(t)
            if cov < args.thresh:
                low += 1
                sample = " ".join(re.findall(r"[\u0600-\u06ff]{4,}|[A-Za-z]{4,}", body))[:160]
                worst.append((cov, src.name, pno, len(t), sample))
                lines.append(f"- ص {pno} · پوشش {cov:.0%} ({hit}/{len(t)}) — {sample[:110]}")
        lines.append("")
    lines.insert(4, f"**صفحه‌های بررسی‌شده: {total} · با پوشش کم: {low}**\n")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"صفحه‌های بررسی‌شده: {total} · با پوشش کم (<{args.thresh:.0%}): {low}")
    print(f"گزارش: {out}")
    print("\nکم‌پوشش‌ترین صفحه‌ها:")
    for cov, name, pno, n, sample in sorted(worst)[:25]:
        print(f"  {cov:5.0%} {name:22s} ص{pno:<4d} {sample[:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
