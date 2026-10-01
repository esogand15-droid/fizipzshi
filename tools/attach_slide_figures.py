#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Attach the remaining slide figures to the chapters, automatically.

The curated batches (work/figpicks.json + earlier picks) already put ~68 figures in
the book. This tool takes every other candidate produced by
tools/extract_slide_figures.py (images/slide/INDEX.json), skips the (source, page)
combinations that are already in the book, routes each survivor to a chapter
(work/figure_routing.tsv first, keyword scoring as fallback) and writes
content/figures_slide.py — an *overlay* consumed by tools/build_lock.py, so the
hand-written chapter modules stay untouched.

usage: attach_slide_figures.py [--min-cov 0.10] [--dry]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SLIDE_IDX = ROOT / "images" / "slide" / "INDEX.json"
ROUTING = ROOT / "work" / "figure_routing.tsv"
OUT = ROOT / "content" / "figures_slide.py"
CONTENT = ROOT / "content"
LOCK = ROOT / "lock"

FA = "۰۱۲۳۴۵۶۷۸۹"

RULES = {
    1: ["تعریف تشعشع", "یونیزان", "غیر یونیزان", "آلفا", "بتا", "رونتگن", "طبقه", "طیف الکترومغناطیس"],
    2: ["اشعه ایکس", "x-ray", "لامپ", "لوله", "آند", "کاتد", "ترمزی", "bremsstrahlung",
        "مشخصه", "characteristic", "طیف", "spectrum", "فیلامان", "تنگستن", "kvp", "anode"],
    3: ["رادیوگرافی", "رادیوگراف", "فلوروسکوپی", "fluoroscopy", "سی تی", "tomography",
        "ماموگرافی", "mammography", "گرید", "کنتراست", "آنژیو", "gantry", "آشکارساز", "باریوم"],
    4: ["رادیواکتیو", "واپاشی", "decay", "نیمه عمر", "پزشکی هسته", "پرتوزا", "پوزیترون",
        "positron", "pet", "تکنسیوم", "tc-99", "tc-99m", "mo-99", "اکتیویته", "activity",
        "گاما", "رادیودارو", "کوری", "بکرل", "generator", "ژنراتور", "milking", "annihilation",
        "radionuclide", "رادیونوکلید", "half-life", "half life"],
    5: ["دوز", "dose", "واحد", "gray", "rem", "سیورت", "راد", "بکرل", "کوری", "دزیمتر", "اسپوژر", "رونتگن"],
    6: ["حفاظت", "protection", "پرتوکار", "shielding", "سرب", "alara", "دز حد", "گوناد", "lead"],
    7: ["سونوگرافی", "اولتراسوند", "ultrasound", "پیزوالکتریک", "piezoelectric", "probe", "پروب",
        "داپلر", "doppler", "امپدانس", "impedance", "echo", "ترانسدیوسر", "transducer", "موج صوتی",
        "a-mode", "b-mode", "m-mode", "a mode", "b mode", "display", "scan", "crt", "frame",
        "pulse", "پالس", "مبدل", "بافت نرم"],
    8: ["رادیوبیولوژی", "radiobiology", "اثرات زیستی", "کروموزوم", "chromosome", "dna",
        "سلول", "cell", "survival", "بقا", "let", "rbe", "اپوپتوز", "تصادفی", "قطعی", "سندروم"],
    9: ["mri", "ام آر آی", "امارای", "مغناطیس", "magnetic", "تشدید", "resonance", "t1", "t2",
        "پروتون", "proton", "relaxation", "tr ", "te ", "اسپین", "spin", "rf", "گرادیان"],
}

SLUG_FA = {
    "afzalipour": "اسلایدهای دکتر افضلی‌پور",
    "haghparast_mphpd": "اسلایدهای M.Ph.P.D — دکتر حق‌پرست",
    "haghparast_sono": "اسلایدهای سونوگرافی — دکتر حق‌پرست",
    "haghparast_tashasho": "اسلایدهای فیزیک تشعشع — دکتر حق‌پرست",
    "darvish_radiobio": "اسلایدهای رادیوبیولوژی — دکتر درویش",
    "darvish_mri": "اسلایدهای MRI — دکتر درویش",
    "afzalipour_ppt": "پاورپوینت‌های دکتر افضلی‌پور",
}

ACCENT = {"ی", "ا", "و", "د", "ر", "ن", "م", "ت", "ه", "ب", "س", "ک", "g", "kg"}

# source PDF for each slug: used to read the real page text (headings alone are short)
PDFS = {
    "afzalipour": "src/extracted/فیزیک پزشکی/فیزیک پزشکی/جلسه دوم افضلی پور.pdf",
    "haghparast_mphpd": "src/extracted/فیزیک پزشکی/فیزیک پزشکی تشعشع/M.Ph.P.D [Repaired] [Repaired].pdf",
    "haghparast_sono": "src/extracted/فیزیک پزشکی/فیزیک پزشکی تشعشع/جزوه فیزیک سونوگرافی.pdf",
    "haghparast_tashasho": "src/extracted/فیزیک پزشکی/فیزیک پزشکی تشعشع/جزوه فیزیک تشعشع و پزشکی هسته_ای.pdf",
    "darvish_radiobio": "src/extracted/فیزیک پزشکی/رادیوبیولوژِی/جزوه لیلی درویش.pdf",
    "darvish_mri": "src/extracted/فیزیک پزشکی/MRI/22MRI.pdf",
}


def page_texts() -> dict[tuple[str, int], str]:
    """full text of every page that contributed a slide figure."""
    try:
        import pymupdf
    except ImportError:                     # pragma: no cover
        return {}
    out: dict[tuple[str, int], str] = {}
    cache: dict[str, "pymupdf.Document"] = {}
    for e in json.loads(SLIDE_IDX.read_text(encoding="utf-8")):
        key = (e["slug"], int(e["page"]))
        if key in out:
            continue
        path = ROOT / PDFS.get(e["slug"], "")
        if not path.exists():
            out[key] = e.get("heading") or ""
            continue
        doc = cache.get(e["slug"]) or cache.setdefault(e["slug"], pymupdf.open(path))
        if int(e["page"]) - 1 < len(doc):
            out[key] = doc[int(e["page"]) - 1].get_text("text")
        else:
            out[key] = ""
    return out


def fa_digits(x) -> str:
    return "".join(FA[int(c)] if c.isdigit() else c for c in str(x))


def strip_marks(s: str) -> str:
    s = re.sub(r"\[\[|\]\]", "", s)
    s = re.sub(r"\*\*", "", s)
    return s


def used_pairs() -> set[tuple[str, int]]:
    """(slug, page) combos that already have a figure in the book."""
    pairs: set[tuple[str, int]] = set()
    # curated raw picks carry slug+page explicitly
    fp = ROOT / "work" / "figpicks.json"
    if fp.exists():
        for e in json.loads(fp.read_text(encoding="utf-8")):
            if e.get("slug") and e.get("page"):
                pairs.add((e["slug"], int(e["page"])))
    # everything else only has a human-readable source label: map it back to a slug
    name2slug = {
        "افضلی‌پور": "afzalipour",
        "M.Ph.P.D": "haghparast_mphpd",
        "سونوگرافی": "haghparast_sono",
        "فیزیک تشعشع": "haghparast_tashasho",
        "رادیوبیولوژی": "darvish_radiobio",
        "MRI": "darvish_mri",
    }
    page_re = re.compile(r"ص\s*([۰-۹0-9]+)")
    for f in list(CONTENT.glob("*.py")) + list(LOCK.glob("ch*.json")):
        txt = f.read_text(encoding="utf-8")
        for m in re.finditer(r'"src":\s*"([^"]+)"', txt):
            src = m.group(1)
            for label, slug in name2slug.items():
                if label in src:
                    pm = page_re.search(src)
                    if pm:
                        page = pm.group(1).translate(str.maketrans(FA, "0123456789"))
                        pairs.add((slug, int(page)))
                    break
    return pairs


def clean_heading(text: str) -> str:
    """a slide page's text is noisy; pick the longest latin/persian phrase as a label."""
    if not text:
        return ""
    lines = [re.sub(r"\s+", " ", l).strip() for l in text.splitlines()]
    lines = [l for l in lines if len(l) >= 4]
    if not lines:
        return ""
    # prefer a line with letters (not just page numbers) and a reasonable length
    good = [l for l in lines if re.search(r"[A-Za-zآ-ی]{4,}", l)]
    pool = good or lines
    return max(pool, key=len)[:95]


def score_chapter(text: str) -> tuple[int, int]:
    low = text.lower()
    best, best_score = 0, 0
    for ch, words in RULES.items():
        sc = sum(1 for w in words if w.lower() in low)
        if sc > best_score:
            best, best_score = ch, sc
    return best, best_score


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-cov", type=float, default=0.10)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    idx = json.loads(SLIDE_IDX.read_text(encoding="utf-8"))
    ptext = page_texts()
    routed: dict[str, int] = {}
    if ROUTING.exists():
        for r in csv.DictReader(ROUTING.open(encoding="utf-8"), delimiter="\t"):
            routed[r["file"]] = int(r["chapter"])

    used = used_pairs()
    plan: dict[int, list[dict]] = {}
    skipped_used = skipped_cov = skipped_noroute = 0

    for e in idx:
        slug, page = e["slug"], int(e["page"])
        if (slug, page) in used:
            skipped_used += 1
            continue
        if float(e.get("cov") or 0) < args.min_cov:
            skipped_cov += 1
            continue
        body = (e.get("heading") or "") + "\n" + ptext.get((slug, page), "")
        e["body"] = body
        ch = routed.get(e["file"], 0)
        if not ch:
            ch, sc = score_chapter(body)
            if not sc:
                skipped_noroute += 1
                continue
        plan.setdefault(ch, []).append(e)

    total = sum(len(v) for v in plan.values())
    print(f"candidates {len(idx)} | already in book {skipped_used} | low-cov {skipped_cov} "
          f"| unrouted {skipped_noroute} | to add {total}")
    print("per chapter:", {k: len(v) for k, v in sorted(plan.items())})

    if args.dry:
        return 0

    from PIL import Image

    FID = ROOT / "images" / "fig"
    files = []
    for ch in sorted(plan):
        files.append(f"    {ch}: [")
        for e in plan[ch]:
            snippet = clean_heading(e.get("body") or e.get("heading") or "")
            label = SLUG_FA.get(e["slug"], e["slug"])
            page = int(e["page"])
            cap = f"شکل — {snippet}" if snippet else f"شکل — از {label}"
            # the slide dir is git-ignored: copy the chosen crop into images/fig (tracked)
            crop = Path(e["file"]).stem.split("_")[-1]
            out = FID / f"slide{ch:02d}_{e['slug']}_p{page:03d}_{crop}.jpg"
            if not out.exists():
                img = Image.open(ROOT / e["file"]).convert("RGB")
                if img.width > 1400:
                    img = img.resize((1400, int(img.height * 1400 / img.width)))
                img.save(out, "JPEG", quality=86, optimize=True)
            files.append("        dict(")
            files.append('            type="figure",')
            files.append(f'            file="images/fig/{out.name}", width="70%",')
            files.append(f'            caption="{cap}",')
            files.append(f'            src="{label} — ص{fa_digits(page)}",')
            files.append(f'            match="{snippet.replace(chr(34), "")}",')
            files.append("        ),")
        files.append("    ],")
    # find the matching anchor block for each figure (best keyword overlap)
    body = ["# -*- coding: utf-8 -*-",
            '"""Auto-generated figure overlay (tools/attach_slide_figures.py).',
            "Attached by tools/build_lock.py after each chapter module is loaded:",
            "each figure is inserted right after the best-matching block text.",
            '"""',
            "",
            "SLIDE_FIGURES: dict[int, list[dict]] = {",
            *files,
            "}",
            ""]
    OUT.write_text("\n".join(body), encoding="utf-8")
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
