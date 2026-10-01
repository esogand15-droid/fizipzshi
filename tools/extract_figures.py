#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract embedded images (figures) from the source PDFs.

Output: images/raw/<slug>/pNNN_<n>.<ext> + images/INDEX.json
Filters out tiny/decorative images and near duplicates (perceptual hash).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pymupdf
from PIL import Image

SRC = Path("src/extracted/فیزیک پزشکی")
MAP = {
    "haghparast_mphpd": "فیزیک پزشکی تشعشع/M.Ph.P.D [Repaired] [Repaired].pdf",
    "haghparast_tashasho": "فیزیک پزشکی تشعشع/جزوه فیزیک تشعشع و پزشکی هسته_ای.pdf",
    "haghparast_sono": "فیزیک پزشکی تشعشع/جزوه فیزیک سونوگرافی.pdf",
    "darvish_radiobio": "رادیوبیولوژِی/جزوه لیلی درویش.pdf",
    "darvish_mri": "MRI/22MRI.pdf",
    "afzalipour": "فیزیک پزشکی/جزوه افضلی پور.pdf",
}
MIN_W, MIN_H, MIN_AREA = 90, 70, 12000


def ahash(im: Image.Image, size: int = 8) -> int:
    g = im.convert("L").resize((size, size), Image.Resampling.LANCZOS)
    px = list(g.getdata())
    avg = sum(px) / len(px)
    bits = 0
    for i, v in enumerate(px):
        if v > avg:
            bits |= 1 << i
    return bits


def hdist(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def first_heading(page) -> str:
    txt = page.get_text().strip().splitlines()
    for line in txt:
        line = line.strip()
        if 4 < len(line) < 90:
            return line
    return ""


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    index: list[dict] = []
    if Path("images/INDEX.json").exists():
        index = json.loads(Path("images/INDEX.json").read_text(encoding="utf-8"))

    for slug, rel in MAP.items():
        if only and slug != only:
            continue
        pdf = SRC / rel
        if not pdf.exists():
            print("missing", pdf)
            continue
        outdir = Path("images/raw") / slug
        outdir.mkdir(parents=True, exist_ok=True)
        doc = pymupdf.open(pdf)
        hashes: list[int] = []
        kept = 0
        for pno in range(len(doc)):
            page = doc[pno]
            heading = first_heading(page)
            n = 0
            for info in page.get_images(full=True):
                xref = info[0]
                try:
                    pix = pymupdf.Pixmap(doc, xref)
                    if pix.n - pix.alpha > 3:
                        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                    if pix.width < MIN_W or pix.height < MIN_H or pix.width * pix.height < MIN_AREA:
                        pix = None
                        continue
                    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                except Exception:  # noqa: BLE001
                    continue
                h = ahash(img)
                if any(hdist(h, old) < 6 for old in hashes):
                    continue
                # skip near-uniform (background) images
                ex = img.convert("L").getextrema()
                if ex[1] - ex[0] < 35:
                    continue
                n += 1
                hashes.append(h)
                fname = f"p{pno+1:03d}_{n}.png"
                img.save(outdir / fname, "PNG", optimize=True)
                index.append({
                    "file": f"images/raw/{slug}/{fname}", "slug": slug,
                    "page": pno + 1, "w": img.width, "h": img.height,
                    "heading": heading,
                })
                kept += 1
        doc.close()
        print(f"{slug}: kept {kept} images")

    # de-dup index by file (re-runs)
    seen = {}
    for e in index:
        seen[e["file"]] = e
    index = sorted(seen.values(), key=lambda e: (e["slug"], e["page"], e["file"]))
    Path("images/INDEX.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print("total indexed:", len(index))
    return 0


if __name__ == "__main__":
    sys.exit(main())
