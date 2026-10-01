#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Route extracted slide figures to book chapters using the OCR text of their page.

Writes work/figure_routing.tsv: one row per figure with the routed chapter and a
short text snippet, so a human (or the agent) can curate the final selection.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OCR = ROOT / "work" / "ocr"
IDX = ROOT / "images" / "slide" / "INDEX.json"
OUT = ROOT / "work" / "figure_routing.tsv"

# chapter -> keyword weights (Persian + latin)
RULES = {
    1: ["تعریف تشعشع", "یونیزان", "غیر یونیزان", "غیریونیزان", "آلفا", "بتا", "رونتگن", "طبقه"],
    2: ["اشعه ایکس", "x-ray", "لامپ", "لوله", "آند", "کاتد", "ترمزی", "bremsstrahlung",
        "مشخصه", "characteristic", "طیف", "spectrum", "تولید پرتو", "فیلامان", "تنگستن", "kvp"],
    3: ["رادیوگرافی", "رادیوگراف", "فلوروسکوپی", "fluoroscopy", "سی تی", "ct ", "tomography",
        "ماموگرافی", "mammography", "گرید", "کنتراست", "تصویر", "آنژیو", "gantry", "آشکارساز"],
    4: ["رادیواکتیو", "واپاشی", "decay", "نیمه عمر", "پزشکی هسته", "پرتوزا", "پوزیترون",
        "positron", "pet", "تکنسیوم", "tc-99", "mo-99", "اکتیویته", "گاما", "رادیودارو"],
    5: ["دوز", "dose", "واحد", "gray", "rem", "سیورت", "راد", "بکرل", "کوری", "دزیمتر"],
    6: ["حفاظت", "protection", "پرتوکار", "shielding", "سرب", "alara", "دز حد", "گوناد"],
    7: ["سونوگرافی", "اولتراسوند", "اولترا ساوند", "ultrasound", "پیزوالکتریک", "probe", "پروب",
        "داپلر", "doppler", "امپدانس", "frequency", "wave", "موج", "echo"],
    8: ["رادیوبیولوژی", "radiobiology", "اثرات زیستی", "کروموزوم", "chromosome", "dna",
        "سلول", "cell", "survival", "بقا", "let", "rbe", "اپوپتوز", "تصادفی", "قطعی",
        "استوکستیک", "stochastic", "سندروم", "syndrome"],
    9: ["mri", "ام آر آی", "امارای", "مغناطیس", "magnetic", "تشدید", "resonance", "t1", "t2",
        "پروتون", "proton", "contrast", "relaxation", "tr ", "te ", "اسپین", "spin"],
}
PAGES: dict[str, dict[int, str]] = {}


def load_pages(slug: str) -> dict[int, str]:
    if slug in PAGES:
        return PAGES[slug]
    p = OCR / slug / "all.md"
    pages: dict[int, str] = {}
    if p.exists():
        cur = 0
        buf: list[str] = []
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            m = re.match(r"=====\s*page\s+(\d+)\s*=====", line.strip())
            if m:
                if cur:
                    pages[cur] = "\n".join(buf)
                cur = int(m.group(1))
                buf = []
            else:
                buf.append(line)
        if cur:
            pages[cur] = "\n".join(buf)
    PAGES[slug] = pages
    return pages


def route(text: str) -> tuple[int, int]:
    low = text.lower()
    best, best_n = 0, 0
    for ch, kws in RULES.items():
        n = sum(low.count(k.lower()) for k in kws)
        if n > best_n:
            best, best_n = ch, n
    return best, best_n


def main() -> int:
    idx = json.loads(IDX.read_text(encoding="utf-8"))
    rows = ["slug\tpage\tcov\tchapter\tscore\tfile\tsnippet"]
    for r in idx:
        pages = load_pages(r["slug"])
        text = pages.get(r["page"], "") or r.get("heading", "")
        ch, score = route(text)
        snip = " ".join(text.split())[:110].replace("\t", " ")
        rows.append(f"{r['slug']}\t{r['page']}\t{r['cov']}\t{ch}\t{score}\t{r['file']}\t{snip}")
    OUT.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("wrote", OUT, len(rows) - 1, "figures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
