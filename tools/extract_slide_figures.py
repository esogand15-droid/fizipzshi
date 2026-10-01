#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract *usable* slide figures by rendering the image region of each PDF page.

The raw embedded images in the scanned/exported slide decks are often moiré tiles,
so instead of pulling embedded objects we render the page region occupied by the
real picture at 200 dpi. Near-uniform (decorative) crops are rejected.

Output: images/slide/<slug>/pNNN_<i>.png + images/slide/INDEX.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pymupdf
from PIL import Image

SRC = Path("src/extracted/فیزیک پزشکی")
OUT = Path("images/slide")
MAP = {
    "haghparast_mphpd": "فیزیک پزشکی تشعشع/M.Ph.P.D [Repaired] [Repaired].pdf",
    "haghparast_tashasho": "فیزیک پزشکی تشعشع/جزوه فیزیک تشعشع و پزشکی هسته_ای.pdf",
    "haghparast_sono": "فیزیک پزشکی تشعشع/جزوه فیزیک سونوگرافی.pdf",
    "darvish_radiobio": "رادیوبیولوژِی/جزوه لیلی درویش.pdf",
    "darvish_mri": "MRI/22MRI.pdf",
    "afzalipour": "فیزیک پزشکی/جزوه افضلی پور.pdf",
}
DPI = 200
MIN_COV = 0.10      # image must cover >=10% of the slide
MAX_COV = 0.97      # full-page background images are decorative
MIN_STD = 12.0      # reject near-uniform crops (gradients, coloured boxes)
MIN_W, MIN_H = 260, 160


def std_of(im: Image.Image) -> float:
    g = im.convert("L")
    px = list(g.getdata())
    n = len(px)
    m = sum(px) / n
    return (sum((v - m) ** 2 for v in px) / n) ** 0.5


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    index, total = [], 0
    for slug, rel in MAP.items():
        pdf = SRC / rel
        if not pdf.exists():
            print(f"!! missing {pdf}")
            continue
        (OUT / slug).mkdir(parents=True, exist_ok=True)
        doc = pymupdf.open(pdf)
        seen: set[int] = set()
        n_saved = 0
        for pno in range(1, len(doc) + 1):
            page = doc[pno - 1]
            area = abs(page.rect)
            infos = sorted(page.get_image_info(), key=lambda i: -abs(pymupdf.Rect(i["bbox"])))
            picks = []
            for i in infos:
                r = pymupdf.Rect(i["bbox"]) & page.rect
                if abs(r) < 1:
                    continue
                cov = abs(r) / area
                if cov < MIN_COV or cov > MAX_COV:
                    continue
                picks.append((cov, r))
                if len(picks) >= 2:
                    break
            for k, (cov, r) in enumerate(picks):
                if r.width * DPI / 72 < MIN_W or r.height * DPI / 72 < MIN_H:
                    continue
                pix = page.get_pixmap(clip=r, dpi=DPI)
                im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                if std_of(im) < MIN_STD:
                    continue
                # cheap perceptual dedupe (8x8 average hash)
                g = im.convert("L").resize((8, 8), Image.Resampling.LANCZOS)
                px = list(g.getdata())
                avg = sum(px) / len(px)
                h = 0
                for j, v in enumerate(px):
                    if v > avg:
                        h |= 1 << j
                if h in seen:
                    continue
                seen.add(h)
                f = OUT / slug / f"p{pno:03d}_{k}.png"
                im.save(f, "PNG", optimize=True)
                heading = " / ".join(page.get_text().split("\n")[:2]).strip()[:80]
                index.append({"file": str(f), "slug": slug, "page": pno,
                              "w": im.width, "h": im.height,
                              "cov": round(cov, 3), "heading": heading})
                n_saved += 1
        doc.close()
        print(f"{slug}: {n_saved} figures")
        total += n_saved
    (OUT / "INDEX.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print("total", total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
