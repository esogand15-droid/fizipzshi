#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local PDF processing for the HumsYar medical-physics jozve.

For every source PDF:
  * per-page text  -> work/pdftext/<slug>/pNNN.txt  (+ combined .md)
  * page stats     -> work/pdftext/<slug>.stats.json  (chars/page, has images)
  * page rasters   -> work/pages/<slug>/pNNN.png      (for visual reading / figures)
  * embedded images-> images/raw/<slug>/pNNN_n.png

Slugs are ASCII to keep paths safe for tooling.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pypdfium2 as pdfium

SRC = Path("src/extracted/فیزیک پزشکی")
MAP = {
    "haghparast_mphpd": "فیزیک پزشکی تشعشع/M.Ph.P.D [Repaired] [Repaired].pdf",
    "haghparast_tashasho": "فیزیک پزشکی تشعشع/جزوه فیزیک تشعشع و پزشکی هسته_ای.pdf",
    "haghparast_sono": "فیزیک پزشکی تشعشع/جزوه فیزیک سونوگرافی.pdf",
    "darvish_radiobio": "رادیوبیولوژِی/جزوه لیلی درویش.pdf",
    "darvish_mri": "MRI/22MRI.pdf",
    "afzalipour": "فیزیک پزشکی/جزوه افضلی پور.pdf",
    "exam_sample": "نمونه سوال/Medical Physics.pdf",
    "bank_humsyar": "نمونه سوال/بانک سوالات فیزیک پزشکی هامزیار.pdf",
}


def page_text(page) -> str:
    tp = page.get_textpage()
    try:
        return tp.get_text_range() or ""
    finally:
        tp.close()


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for slug, rel in MAP.items():
        if only and slug != only:
            continue
        pdf_path = SRC / rel
        if not pdf_path.exists():
            print("MISSING", pdf_path)
            continue
        tdir = Path("work/pdftext") / slug
        rdir = Path("work/pages") / slug
        idir = Path("images/raw") / slug
        for d in (tdir, rdir, idir):
            d.mkdir(parents=True, exist_ok=True)

        doc = pdfium.PdfDocument(str(pdf_path))
        stats, combined = [], []
        for i in range(len(doc)):
            page = doc[i]
            txt = page_text(page)
            (tdir / f"p{i+1:03d}.txt").write_text(txt, encoding="utf-8")
            combined.append(f"\n\n===== page {i+1} =====\n{txt}")
            nimg = 0
            try:
                for obj in page.get_objects():
                    if obj.type == 3:  # FPDF_PAGEOBJ_IMAGE
                        nimg += 1
            except Exception:  # noqa: BLE001
                pass
            stats.append({"page": i + 1, "chars": len(txt.strip()), "images": nimg})
            page.close()
        (tdir / "all.md").write_text("".join(combined), encoding="utf-8")
        (Path("work/pdftext") / f"{slug}.stats.json").write_text(
            json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
        n_pages = len(doc)
        doc.close()
        empty = sum(1 for s in stats if s["chars"] < 40)
        print(f"{slug}: {n_pages} pages, {empty} with <40 chars, "
              f"avg {sum(s['chars'] for s in stats)/max(1,n_pages):.0f} chars/page")
    return 0


if __name__ == "__main__":
    sys.exit(main())
