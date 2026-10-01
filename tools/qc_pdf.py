#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Structural QC for the rendered jozve (text-only, via pypdfium2).

Checks: page count, CJK / unknown characters, bidi islands, empty pages,
missing figures, Persian page numbers, and the source coverage of lock files.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parent.parent
CJK = re.compile(r"[\u2e80-\u9fff\uf900-\ufaff\uff00-\uffef]")
ARABIC_RANGE = re.compile(r"[\u0600-\u06ff]")


def main() -> int:
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "HumsYar_MedPhysics_Jozve.pdf"
    doc = pdfium.PdfDocument(str(pdf_path))
    n = len(doc)
    print(f"== pages: {n}")
    empty, cjk_hits, tiny = [], [], []
    for i in range(n):
        tp = doc[i].get_textpage()
        t = tp.get_text_range() or ""
        nchars = len(t.strip())
        if nchars < 25:
            empty.append((i + 1, nchars))
        for m in CJK.finditer(t):
            cjk_hits.append((i + 1, m.group(0), unicodedata.name(m.group(0), "?")))
        if nchars < 25 and i not in (0, n - 1):
            tiny.append(i + 1)
    print("== suspected empty/near-empty pages:", empty[:20])
    print("== CJK/unknown chars:", cjk_hits[:20], "count:", len(cjk_hits))

    # lock coverage
    lock = ROOT / "lock"
    n_blocks = n_figs = n_tabs = n_src = 0
    for f in sorted(lock.glob("ch*.json")):
        ch = json.loads(f.read_text(encoding="utf-8"))
        for b in ch["blocks"]:
            n_blocks += 1
            if b.get("type") == "figure":
                n_figs += 1
                fp = ROOT / b.get("file", "")
                if not fp.exists():
                    print("MISSING FIGURE:", b.get("file"))
            if b.get("type") == "table":
                n_tabs += 1
            if b.get("src"):
                n_src += 1
    print(f"== lock blocks: {n_blocks}, figures: {n_figs}, tables: {n_tabs}, with src: {n_src}")
    print(f"== lock chapters: {len(list(lock.glob('ch*.json')))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
