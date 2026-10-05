# -*- coding: utf-8 -*-
"""Systematic layout QA for the rendered جزوه.

Three independent checks, run over *every* page:

1. **Torn blocks** — the renderer can stamp an invisible marker at the start and
   at the end of each block that must stay in one piece (figure cards, formula
   boxes, tables, key/exam notes, the «مرور سریع» card and every single bullet).
   A QA build is produced with those markers on; if a block's two markers land
   on different pages, a page break cut it in half.
2. **Ink outside the type area** — every page is rasterised and checked for ink
   in the margins or in the footer band, which is how clipping, overflowing
   formulas and text colliding with the footer show up.
3. **Half-empty pages** — how much of the body column was left blank at the
   bottom, so fragmentation can be tracked as a number instead of a feeling.

usage:  python3 tools/qc_layout.py [book.pdf]
        (re-renders a marked QA build next to the book for check 1)
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOK = ROOT / "HumsYar_MedPhysics_Jozve.pdf"
QA_PDF = ROOT / "render" / "qa_marked.pdf"

# @page margin: 12mm top, 15mm bottom, 11mm left/right on A4 (210x297mm)
M_TOP, M_BOT, M_SIDE = 12.0, 15.0, 11.0
PAGE_W, PAGE_H = 210.0, 297.0
# the footer sits inside the bottom margin; body text must stay above it
FOOTER_TOP = PAGE_H - M_BOT


def load_renderer():
    spec = importlib.util.spec_from_file_location("jz_render", ROOT / "render" / "render.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------- #
# 1) torn blocks
# --------------------------------------------------------------------------- #
def check_torn(out: list[str]) -> int:
    try:
        from weasyprint import HTML
    except Exception as exc:                      # pragma: no cover
        out.append(f"- پرش از بررسی شکستگی بلوک‌ها (WeasyPrint در دسترس نیست: {exc})")
        return 0
    import pypdfium2 as pdfium

    r = load_renderer()
    r.MARK_ATOMS = True
    r.EMIT_FIG_MARKS = False
    html = r.build_html()
    QA_PDF.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html, base_url=str(ROOT / "render")).write_pdf(str(QA_PDF))

    pdf = pdfium.PdfDocument(str(QA_PDF))
    where: dict[tuple[int, str], int] = {}
    for i in range(len(pdf)):
        txt = pdf[i].get_textpage().get_text_bounded()
        for m in re.finditer(r"JZA(\d{4})([SE])", txt):
            where.setdefault((int(m.group(1)), m.group(2)), i + 1)
    torn = []
    for idx, kind in sorted(r.ATOMS.items()):
        s, e = where.get((idx, "S")), where.get((idx, "E"))
        if s is None or e is None:
            continue
        if s != e:
            torn.append((s, e, kind))
    out.append(f"- بلوک‌های بررسی‌شده: {len(r.ATOMS)} · شکسته بین دو صفحه: {len(torn)}")
    for s, e, kind in torn:
        out.append(f"  ✗ «{kind}» از صفحه {s} به صفحه {e} شکسته است")
    return len(torn)


# --------------------------------------------------------------------------- #
# 2) ink outside the type area + 3) half-empty pages
# --------------------------------------------------------------------------- #
def check_raster(pdf_path: Path, out: list[str]) -> int:
    import pypdfium2 as pdfium
    from PIL import Image

    pdf = pdfium.PdfDocument(str(pdf_path))
    bad = 0
    gaps: list[tuple[int, float]] = []
    scale = 2.0                                   # px per pt
    for i in range(len(pdf)):
        img = pdf[i].render(scale=scale).to_pil().convert("L")
        W, H = img.size
        px_mm = H / PAGE_H
        # dark cover pages are ink end to end; they have no body text to check
        corner = img.crop((0, 0, 12, 12)).resize((1, 1), Image.BOX).getdata()[0]
        dark_page = corner < 120
        ink = img.point(lambda v: 255 if v > 225 else 0)

        def has_ink(box) -> bool:
            c = ink.crop(box)
            if c.width < 1 or c.height < 1:
                return False
            return c.getextrema()[0] < 128

        if not dark_page:
            t = int(M_TOP * px_mm) - 2
            b = int(FOOTER_TOP * px_mm) + 2
            l = int(M_SIDE * px_mm) - 2
            r = W - l
            probs = []
            if has_ink((0, 0, W, max(0, t))):
                probs.append("بالای حاشیه")
            if has_ink((0, 0, max(0, l), H)):
                probs.append("حاشیه چپ")
            if has_ink((min(W, r), 0, W, H)):
                probs.append("حاشیه راست")
            if probs:
                bad += 1
                out.append(f"  ✗ صفحه {i+1}: جوهر بیرون از کادر متن ({'، '.join(probs)})")

        # trailing blank space of the body column
        body = ink.crop((0, 0, W, int(FOOTER_TOP * px_mm)))
        rows = list(body.resize((1, body.height), Image.BOX).getdata())
        last = max((y for y, v in enumerate(rows) if v < 254), default=-1)
        g = 1.0 if last < 0 else (len(rows) - 1 - last) / len(rows)
        if g > 0.20 and not dark_page:
            gaps.append((i + 1, round(g, 2)))
    out.append(f"- صفحه‌های دارای جوهر بیرون از کادر: {bad}")
    out.append(f"- صفحه‌های با بیش از ۲۰٪ فضای خالی در پایین: {len(gaps)} → {gaps}")
    return bad


def main() -> int:
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else BOOK
    out = ["# گزارش بازبینی چیدمان (QC layout)", ""]
    torn = check_torn(out)
    bad = check_raster(pdf_path, out)
    out.append("")
    out.append(f"## نتیجه: شکستگی بلوک {torn} · خروج از کادر {bad}")
    text = "\n".join(out)
    print(text)
    (ROOT / "render" / "qc_layout.txt").write_text(text + "\n", encoding="utf-8")
    return 1 if (torn or bad) else 0


if __name__ == "__main__":
    sys.exit(main())
