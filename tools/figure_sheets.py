#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build labelled contact sheets of every figure embedded in the source PDFs.

The workflow runs tools/extract_figures.py first (images/raw/<slug>/pNNN_n.ext +
images/INDEX.json), then this script tiles the images into a handful of sheets so a
human (or the agent) can pick the useful ones by their printed index number.

Sheets land in work/figsheets/sheet_<n>.png together with a JSON manifest that maps
every printed index to its raw file, page and heading.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "work" / "figsheets"
CELL = 320          # cell size in the sheet
COLS, ROWS = 5, 4   # 20 per sheet
LABEL_H = 26


def main() -> int:
    index = json.loads((ROOT / "images" / "INDEX.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    per_sheet = COLS * ROWS
    n_sheets = math.ceil(len(index) / per_sheet)
    manifest = []
    for s in range(n_sheets):
        chunk = index[s * per_sheet:(s + 1) * per_sheet]
        sheet = Image.new("RGB", (COLS * CELL, ROWS * (CELL + LABEL_H)), "white")
        dr = ImageDraw.Draw(sheet)
        for j, item in enumerate(chunk):
            r, c = divmod(j, COLS)
            x, y = c * CELL, r * (CELL + LABEL_H)
            try:
                im = Image.open(ROOT / item["file"]).convert("RGB")
                im.thumbnail((CELL - 8, CELL - 8))
                sheet.paste(im, (x + (CELL - im.width) // 2, y + (CELL - im.height) // 2))
            except Exception as exc:  # pragma: no cover - diagnostics only
                dr.text((x + 6, y + 20), f"!! {exc}"[:40], fill="red")
            idx = s * per_sheet + j
            dr.rectangle([x, y + CELL, x + CELL, y + CELL + LABEL_H], fill="#eef2ff")
            dr.text((x + 6, y + CELL + 6),
                    f"#{idx} {item['slug'][:9]} p{item['page']} {item['w']}x{item['h']}", fill="#111")
            manifest.append({"idx": idx, **item})
        sheet.save(OUT / f"sheet_{s:02d}.png", optimize=True)
        print("sheet", s, len(chunk))
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print("sheets:", n_sheets, "images:", len(index))
    return 0


if __name__ == "__main__":
    sys.exit(main())
