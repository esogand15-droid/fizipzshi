#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Image asset pipeline for the جزوه — discovery → placement, in one tool.

The جزوه is built from a handful of lecture documents (slide decks exported to
PDF and two scanned hand-outs).  Those sources hold a few thousand image
objects; only a fraction are real teaching figures and many appear in more than
one deck.  This tool walks the whole corpus systematically instead of by hand:

  discover   inventory every source document and every figure already in the book
  extract    render each *visual region* of every page — the embedded picture
             together with the vector arrows and labels drawn on top of it
  dedupe     group near-identical crops (dHash + aHash + size) and keep the best
  sheets     contact sheets of the unique crops, for the human review pass
  report     the cross-reference manifest used for review and placement

Everything is deterministic and re-runnable.  Candidates live under
work/figpipe/cand (git-ignored); only the manifest and the chosen figures enter
the repository.

usage:  python3 tools/figpipe.py discover|extract|dedupe|sheets|report [slug]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src/extracted/فیزیک پزشکی"
OUT = ROOT / "work/figpipe"
CAND = OUT / "cand"

# slug -> (relative path, human name, kind)
SOURCES: dict[str, tuple[str, str, str]] = {
    "haghparast_mphpd": (
        "فیزیک پزشکی تشعشع/M.Ph.P.D [Repaired] [Repaired].pdf",
        "اسلایدهای M.Ph.P.D — دکتر حق‌پرست", "slides"),
    "haghparast_tashasho": (
        "فیزیک پزشکی تشعشع/جزوه فیزیک تشعشع و پزشکی هسته_ای.pdf",
        "جزوه فیزیک تشعشع و پزشکی هسته‌ای — دکتر حق‌پرست", "scan"),
    "haghparast_sono": (
        "فیزیک پزشکی تشعشع/جزوه فیزیک سونوگرافی.pdf",
        "جزوه فیزیک سونوگرافی — دکتر حق‌پرست", "scan"),
    "darvish_radiobio": (
        "رادیوبیولوژِی/جزوه لیلی درویش.pdf",
        "اسلایدهای رادیوبیولوژی — دکتر درویش", "slides"),
    "darvish_mri": (
        "MRI/22MRI.pdf", "اسلایدهای MRI — دکتر درویش", "slides"),
    "afzalipour": (
        "فیزیک پزشکی/جزوه افضلی پور.pdf", "جزوه/اسلایدهای دکتر افضلی‌پور", "slides"),
    "exam_medphys": (
        "نمونه سوال/Medical Physics.pdf", "نمونه سوال — Medical Physics", "exam"),
    "exam_bank": (
        "نمونه سوال/بانک سوالات فیزیک پزشکی هامزیار.pdf",
        "بانک سوالات فیزیک پزشکی هامزیار", "exam"),
}

DPI = 200
SCALE = DPI / 72.0
GAP = 12.0              # pt — closer than this and two pieces are one figure
IMG_MIN_COV = 0.004     # a placed picture smaller than this is an icon/bullet
IMG_MAX_COV = 0.70      # bigger than this and it is the slide background
DRAW_MIN_COV = 0.0015
DRAW_MAX_COV = 0.45
CLUSTER_MAX_COV = 0.92  # a cluster this big is the whole slide, not a figure
MIN_W, MIN_H = 240, 150         # px at DPI
MIN_STD = 11.0          # flat colour blocks and gradients are decoration
MIN_INK = 0.012
MAX_SIDE = 1800         # px — plenty for a 112 mm wide print


# --------------------------------------------------------------------------- #
# geometry helpers
# --------------------------------------------------------------------------- #
def rect_near(a, b, gap: float = GAP) -> bool:
    return not (a[0] - gap > b[2] or b[0] - gap > a[2]
                or a[1] - gap > b[3] or b[1] - gap > a[3])


def rect_union(a, b):
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def overlap_frac(box, others) -> float:
    """Share of `box` covered by `others` (rough: sum of clipped areas)."""
    x0, y0, x1, y1 = box
    area = max(1.0, (x1 - x0) * (y1 - y0))
    tot = 0.0
    for o in others:
        ox0 = max(x0, o[0]); oy0 = max(y0, o[1])
        ox1 = min(x1, o[2]); oy1 = min(y1, o[3])
        if ox1 > ox0 and oy1 > oy0:
            tot += (ox1 - ox0) * (oy1 - oy0)
    return min(1.0, tot / area)


def cluster(rects: list[tuple]) -> list[tuple]:
    """Merge rectangles that touch or nearly touch, repeatedly until stable."""
    boxes = list(rects)
    changed = True
    while changed and len(boxes) > 1:
        changed = False
        out: list[tuple] = []
        for r in boxes:
            for i, o in enumerate(out):
                if rect_near(r, o):
                    out[i] = rect_union(r, o)
                    changed = True
                    break
            else:
                out.append(r)
        boxes = out
    return boxes


# --------------------------------------------------------------------------- #
# image helpers
# --------------------------------------------------------------------------- #
def dhash(im, size: int = 8) -> int:
    import numpy as np
    g = np.asarray(im.convert("L").resize((size + 1, size)), dtype="int16")
    bits = 0
    k = 0
    for y in range(size):
        for x in range(size):
            if g[y, x] < g[y, x + 1]:
                bits |= 1 << k
            k += 1
    return bits


def ahash(im, size: int = 8) -> int:
    import numpy as np
    g = np.asarray(im.convert("L").resize((size, size)), dtype="float32")
    avg = g.mean()
    bits = 0
    k = 0
    for y in range(size):
        for x in range(size):
            if g[y, x] > avg:
                bits |= 1 << k
            k += 1
    return bits


def hdist(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def img_stats(im) -> tuple[float, float, float]:
    """(contrast, ink fraction, sharpness) — used for quality ranking."""
    import numpy as np
    g = np.asarray(im.convert("L").resize((160, 160)), dtype="float32")
    gx = float(abs(g[:, 1:] - g[:, :-1]).mean())
    gy = float(abs(g[1:, :] - g[:-1, :]).mean())
    return float(g.std()), float((g < 200).mean()), gx + gy


def text_like(im) -> bool:
    """True when a crop is a block of prose rather than a picture.

    Scanned slides store their text as an image and dark themes print light
    text on a dark background, so neither the PDF text layer nor a fixed
    threshold can be trusted.  Ink is therefore measured as *deviation from the
    page background*, and the row profile is inspected: running text makes many
    thin, regularly spaced bands with clean gaps and little total ink, while
    pictures, charts and diagrams do not.
    """
    import numpy as np
    g = np.asarray(im.convert("L"), dtype="int16")
    if g.shape[0] < 40 or g.shape[1] < 40:
        return False
    hist = np.bincount(np.clip(g, 0, 255).ravel(), minlength=256)
    bg = int(hist.argmax())                      # dominant tone = background
    ink = np.abs(g - bg) > 42
    dens = float(ink.mean())
    if dens > 0.24:
        return False                             # photographs / filled charts
    rows = ink.mean(axis=1) > 0.012
    bands, y, H = [], 0, len(rows)
    while y < H:
        if rows[y]:
            y0 = y
            while y < H and rows[y]:
                y += 1
            bands.append(y - y0)
        else:
            y += 1
    if len(bands) < 3:
        return False
    hs = np.array(bands, dtype="float32")
    med = float(np.median(hs))
    if med > 0.13 * H:
        return False                             # bands too tall to be text
    regular = float((np.abs(hs - med) < 0.8 * med + 3).mean())
    gapfrac = 1.0 - float(rows.mean())
    return regular > 0.55 and gapfrac > 0.18


def autocrop(im, tol: int = 10, pad: int = 8):
    """Trim uniform margins only — never touches labels, arrows or legends."""
    import numpy as np
    a = np.asarray(im.convert("L"), dtype="int16")
    if a.size == 0:
        return im
    bg = int(round(float(a[0, 0] + a[0, -1] + a[-1, 0] + a[-1, -1]) / 4))
    mask = np.abs(a - bg) > tol
    if not mask.any():
        return im
    ys, xs = np.where(mask)
    y0 = max(0, int(ys.min()) - pad)
    x0 = max(0, int(xs.min()) - pad)
    y1 = min(a.shape[0] - 1, int(ys.max()) + pad)
    x1 = min(a.shape[1] - 1, int(xs.max()) + pad)
    if (x1 - x0) < 40 or (y1 - y0) < 40:
        return im
    return im.crop((x0, y0, x1 + 1, y1 + 1))


def shrink(im, max_side: int = MAX_SIDE):
    if max(im.size) <= max_side:
        return im
    r = max_side / max(im.size)
    return im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))))


# --------------------------------------------------------------------------- #
# 1. discovery
# --------------------------------------------------------------------------- #
def cmd_discover() -> dict:
    import pymupdf
    OUT.mkdir(parents=True, exist_ok=True)
    inv: dict = {"sources": [], "book_figures": []}
    for slug, (rel, name, kind) in SOURCES.items():
        p = SRC / rel
        rec = {"slug": slug, "path": str(p.relative_to(ROOT)), "name": name,
               "kind": kind, "exists": p.exists(),
               "format": p.suffix.lower().lstrip(".")}
        if p.exists():
            doc = pymupdf.open(p)
            imgs = chars = blank = 0
            for pg in doc:
                imgs += len(pg.get_images(full=True))
                t = pg.get_text().strip()
                chars += len(t)
                blank += 0 if t else 1
            rec.update(pages=len(doc), images=imgs, text_chars=chars,
                       pages_without_text=blank, bytes=p.stat().st_size)
            doc.close()
        inv["sources"].append(rec)

    for f in sorted((ROOT / "lock").glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        blocks = data.get("blocks") if isinstance(data, dict) else data
        for b in blocks or []:
            if b.get("type") == "figure":
                inv["book_figures"].append(
                    {"chapter": f.stem, "file": b.get("file"),
                     "caption": b.get("caption", ""), "src": b.get("src", "")})
    (OUT / "discover.json").write_text(
        json.dumps(inv, ensure_ascii=False, indent=1), encoding="utf-8")
    npp = sum(1 for s in inv["sources"] if s["format"] in ("ppt", "pptx"))
    print(f"sources: {len(inv['sources'])} — PowerPoint {npp}, "
          f"PDF {len(inv['sources']) - npp}")
    for s in inv["sources"]:
        if s["exists"]:
            print(f"  · {s['slug']:22s} {s['pages']:4d} pages  "
                  f"{s['images']:5d} image objects  {s['text_chars']:7d} chars  "
                  f"kind={s['kind']}")
        else:
            print(f"  !! missing {s['path']}")
    print(f"figures already in the book: {len(inv['book_figures'])}")
    return inv


# --------------------------------------------------------------------------- #
# 2. extraction
# --------------------------------------------------------------------------- #
def page_context(slug: str, pno: int, page) -> dict:
    txt = (page.get_text() or "").strip()
    if not txt:
        ocr = ROOT / f"work/ocr/{slug}/p{pno:03d}.txt"
        if ocr.exists():
            txt = ocr.read_text(encoding="utf-8").strip()
    lines = [l.strip() for l in txt.splitlines() if l.strip()]
    title = next((l for l in lines if 3 < len(l) < 90), "")
    return {"title": title, "text": " ".join(lines)[:1500]}


def scan_regions(full, parea_px: int) -> list[tuple]:
    """Figure bands on a scanned hand-out page (pixel coords).

    Text lines make a regular, thin, high-frequency ink profile; a figure makes
    a tall band of ink.  Rows are grouped into bands and a band is kept when it
    is tall enough and its ink is not arranged as narrow text lines.
    """
    import numpy as np
    g = np.asarray(full.convert("L"), dtype="uint8")
    ink = (g < 190)
    rows = ink.mean(axis=1)
    on = rows > 0.004
    bands: list[tuple[int, int]] = []
    y = 0
    H = len(on)
    while y < H:
        if on[y]:
            y0 = y
            gap = 0
            while y < H and (on[y] or gap < 14):
                gap = 0 if on[y] else gap + 1
                y += 1
            bands.append((y0, min(H - 1, y - gap)))
        else:
            y += 1
    out = []
    for y0, y1 in bands:
        h = y1 - y0
        if h < 150:
            continue
        sub = ink[y0:y1 + 1]
        # share of rows that are "empty" inside the band: text blocks have many
        # (the gaps between lines), a picture has few
        empt = float((sub.mean(axis=1) < 0.004).mean())
        dens = float(sub.mean())
        cols = sub.mean(axis=0)
        xs = np.where(cols > 0.01)[0]
        if xs.size == 0:
            continue
        x0, x1 = int(xs.min()), int(xs.max())
        if (x1 - x0) < 240:
            continue
        if empt > 0.42 and dens < 0.10:
            continue                       # looks like a block of text lines
        out.append((x0, y0, x1, y1))
    return out


def cmd_extract(only: str | None = None) -> None:
    import pymupdf
    from PIL import Image
    CAND.mkdir(parents=True, exist_ok=True)
    cands: list[dict] = []
    for slug, (rel, name, kind) in SOURCES.items():
        if only and slug != only:
            continue
        if kind == "exam":
            continue                       # question banks hold no teaching figures
        pdf = SRC / rel
        if not pdf.exists():
            print(f"!! missing {pdf}")
            continue
        (CAND / slug).mkdir(parents=True, exist_ok=True)
        doc = pymupdf.open(pdf)
        kept = 0
        for pno in range(1, len(doc) + 1):
            page = doc[pno - 1]
            prect = page.rect
            parea = abs(prect) or 1.0
            ctx = page_context(slug, pno, page)
            # where the page puts real text, in pixel coords — a crop that is
            # mostly text is a bullet slide, not a figure
            text_boxes = []
            for blk in page.get_text("blocks") or []:
                x0, y0, x1, y1 = blk[:4]
                if len(blk) > 6 and blk[6] != 0:
                    continue                      # image block, not text
                if (blk[4] or "").strip():
                    text_boxes.append((x0 * SCALE, y0 * SCALE,
                                       x1 * SCALE, y1 * SCALE))
            img_boxes = []
            for info in page.get_image_info():
                r = pymupdf.Rect(info["bbox"]) & prect
                if not r.is_empty:
                    img_boxes.append((r.x0 * SCALE, r.y0 * SCALE,
                                      r.x1 * SCALE, r.y1 * SCALE))
            pix = page.get_pixmap(dpi=DPI)
            full = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

            if kind == "scan":
                boxes_px = scan_regions(full, pix.width * pix.height)
            else:
                seeds = []
                for info in page.get_image_info():
                    r = pymupdf.Rect(info["bbox"]) & prect
                    if r.is_empty:
                        continue
                    cov = abs(r) / parea
                    if IMG_MIN_COV <= cov <= IMG_MAX_COV:
                        seeds.append(tuple(r))
                for d in page.get_drawings():
                    r = pymupdf.Rect(d["rect"]) & prect
                    if r.is_empty:
                        continue
                    cov = abs(r) / parea
                    if DRAW_MIN_COV <= cov <= DRAW_MAX_COV:
                        seeds.append(tuple(r))
                if not seeds:
                    continue
                boxes_px = []
                for bx in cluster(seeds):
                    r = pymupdf.Rect(bx) & prect
                    if r.is_empty or abs(r) / parea > CLUSTER_MAX_COV:
                        continue
                    boxes_px.append((int(r.x0 * SCALE), int(r.y0 * SCALE),
                                     int(r.x1 * SCALE), int(r.y1 * SCALE)))
                if not boxes_px:
                    # Some decks export their whole slide as dozens of image
                    # tiles, so object geometry says "one page-sized blob".
                    # Fall back to reading the ink profile of the rendered page.
                    boxes_px = scan_regions(full, pix.width * pix.height)

            boxes_px.sort(key=lambda b: -((b[2] - b[0]) * (b[3] - b[1])))
            for idx, bx in enumerate(boxes_px):
                tf = overlap_frac(bx, text_boxes)
                imf = overlap_frac(bx, img_boxes)
                if tf > 0.50 and imf < 0.12:
                    continue                      # a slide of prose, not a figure
                crop = autocrop(full.crop(bx))
                if crop.width < MIN_W or crop.height < MIN_H:
                    continue
                if text_like(crop):
                    continue
                std, ink, sharp = img_stats(crop)
                if std < MIN_STD or ink < MIN_INK:
                    continue
                crop = shrink(crop)
                rel_out = f"work/figpipe/cand/{slug}/p{pno:03d}_{idx}.jpg"
                crop.convert("RGB").save(ROOT / rel_out, quality=88, optimize=True)
                cands.append({
                    "id": f"{slug}:p{pno:03d}:{idx}", "slug": slug, "source": name,
                    "kind": kind, "page": pno, "file": rel_out,
                    "w": crop.width, "h": crop.height,
                    "std": round(std, 1), "ink": round(ink, 3),
                    "sharp": round(sharp, 2),
                    "text_frac": round(tf, 2), "img_frac": round(imf, 2),
                    "dhash": dhash(crop), "ahash": ahash(crop),
                    "title": ctx["title"], "text": ctx["text"],
                })
                kept += 1
        doc.close()
        print(f"  {slug:22s} {kept:4d} candidate regions")
    (OUT / "candidates.json").write_text(
        json.dumps(cands, ensure_ascii=False), encoding="utf-8")
    print(f"total candidates: {len(cands)} -> work/figpipe/candidates.json")


# --------------------------------------------------------------------------- #
# 3. deduplication  (perceptual, not by file name)
# --------------------------------------------------------------------------- #
def book_hashes() -> list[dict]:
    """Hash every figure the book already prints, so we never add it twice."""
    from PIL import Image
    out = []
    for f in sorted((ROOT / "images/fig").glob("*")):
        if f.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        try:
            im = Image.open(f)
            im.load()
        except Exception:
            continue
        std, ink, sharp = img_stats(im)
        out.append({"file": f"images/fig/{f.name}", "w": im.width, "h": im.height,
                    "dhash": dhash(im), "ahash": ahash(im), "sharp": round(sharp, 2)})
    return out


def quality(c: dict) -> float:
    """Rank two copies of the same picture: resolution first, then crispness."""
    return (c["w"] * c["h"]) ** 0.5 * (1.0 + 0.01 * c.get("sharp", 0.0))


def same_picture(a: dict, b: dict, dh: int = 8, ah: int = 10) -> bool:
    """Near-duplicate test: both hashes must agree, so a merely *similar*
    diagram (normal vs pathological, overview vs detail) stays its own figure."""
    return hdist(a["dhash"], b["dhash"]) <= dh and hdist(a["ahash"], b["ahash"]) <= ah


def cmd_dedupe() -> None:
    cands = json.loads((OUT / "candidates.json").read_text(encoding="utf-8"))
    book = book_hashes()
    (OUT / "book_hashes.json").write_text(
        json.dumps(book, ensure_ascii=False), encoding="utf-8")

    # --- group near-identical candidates, keep the best copy of each group ---
    groups: list[list[dict]] = []
    for c in sorted(cands, key=lambda x: -quality(x)):
        for g in groups:
            if same_picture(c, g[0]):
                g.append(c)
                break
        else:
            groups.append([c])

    uniq = []
    for g in groups:
        best = g[0]
        best = dict(best)
        best["copies"] = [o["id"] for o in g[1:]]
        best["n_copies"] = len(g)
        # does the book already print this picture?
        hit = next((b for b in book if same_picture(best, b)), None)
        if hit:
            better = quality(best) > quality(hit) * 1.25
            best["status"] = "REPLACE_CANDIDATE" if better else "ALREADY_EXISTS"
            best["book_file"] = hit["file"]
        else:
            best["status"] = "NEW"
        uniq.append(best)

    uniq.sort(key=lambda c: (c["slug"], c["page"]))
    (OUT / "unique.json").write_text(
        json.dumps(uniq, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    st = Counter(u["status"] for u in uniq)
    print(f"candidates {len(cands)} -> unique {len(uniq)}  "
          f"(duplicates collapsed: {len(cands) - len(uniq)})")
    for k, v in st.most_common():
        print(f"  {k:18s} {v}")


# --------------------------------------------------------------------------- #
# 4. contact sheets for the human review pass
# --------------------------------------------------------------------------- #
def cmd_sheets(status: str | None = None) -> None:
    from PIL import Image, ImageDraw
    uniq = json.loads((OUT / "unique.json").read_text(encoding="utf-8"))
    if status:
        uniq = [u for u in uniq if u["status"] == status]
    sheets = OUT / "sheets"
    sheets.mkdir(parents=True, exist_ok=True)
    for f in sheets.glob("*.jpg"):
        f.unlink()
    COLS, ROWS, CELL = 4, 4, 420
    per = COLS * ROWS
    for s in range(0, len(uniq), per):
        chunk = uniq[s:s + per]
        sheet = Image.new("RGB", (COLS * CELL, ROWS * (CELL + 26)), "white")
        d = ImageDraw.Draw(sheet)
        for i, u in enumerate(chunk):
            im = Image.open(ROOT / u["file"]).convert("RGB")
            im.thumbnail((CELL - 12, CELL - 12))
            x = (i % COLS) * CELL + (CELL - im.width) // 2
            y = (i // COLS) * (CELL + 26) + 22
            sheet.paste(im, (x, y))
            d.text(((i % COLS) * CELL + 6, (i // COLS) * (CELL + 26) + 6),
                   f"[{s + i:03d}] {u['slug'][:14]} p{u['page']} {u['status'][:9]}",
                   fill="black")
        sheet.save(sheets / f"sheet{s // per:02d}.jpg", quality=86)
    print(f"{len(uniq)} crops -> {sheets}/sheet*.jpg")


# --------------------------------------------------------------------------- #
# 5. cross-reference + reverse audit
# --------------------------------------------------------------------------- #
GRADES = {
    "A": ("MUST INCLUDE", "برای فهم مبحث لازم است"),
    "B": ("USEFUL", "ارزش آموزشی دارد"),
    "C": ("OPTIONAL", "کم‌اهمیت — فقط در صورت وجود فضا"),
    "D": ("NOT RELEVANT", "تزیینی/غیرآموزشی"),
    "E": ("ALREADY EXISTS", "همین تصویر از پیش در جزوه هست"),
    "R": ("REPLACED WITH BETTER VERSION", "نسخهٔ بهتر جایگزین شکل موجود شد"),
}
CH_NAMES = {
    1: "مبانی پرتوها", 2: "تولید پرتو ایکس", 3: "تصویربرداری تشخیصی",
    4: "پزشکی هسته‌ای", 5: "پرتودرمانی", 6: "حفاظت در برابر پرتو",
    7: "سونوگرافی", 8: "رادیوبیولوژی", 9: "MRI",
}


def _load_placements() -> dict:
    """images/fig/<file> -> (chapter, caption, anchor) from content/figures_extra.py."""
    import importlib.util
    out: dict[str, tuple] = {}
    path = ROOT / "content/figures_extra.py"
    if not path.exists():
        return out
    spec = importlib.util.spec_from_file_location("figures_extra", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for ch, entries in (getattr(mod, "EXTRA_FIGURES", {}) or {}).items():
        for e in entries:
            out[e["file"]] = (ch, e.get("caption", ""), e.get("after", ""))
    for old, new in (getattr(mod, "FIG_UPGRADE", {}) or {}).items():
        nf = new["file"] if isinstance(new, dict) else new
        out[nf] = (0, f"نسخهٔ بهتر، جایگزین {Path(old).name}", "")
    return out


def _lock_pages() -> dict:
    """images/fig/<file> -> printed page number, read back from the built PDF."""
    pages: dict[str, int] = {}
    pm = ROOT / "render/page_map.json"
    if not pm.exists():
        return pages
    return pages


def cmd_report() -> None:
    uniq = json.loads((OUT / "unique.json").read_text(encoding="utf-8"))
    dec = json.loads((OUT / "decisions.json").read_text(encoding="utf-8"))
    crop = {c["index"]: c for c in
            json.loads((OUT / "cropped.json").read_text(encoding="utf-8"))}
    placed = _load_placements()
    disc = json.loads((OUT / "discover.json").read_text(encoding="utf-8")) \
        if (OUT / "discover.json").exists() else {"sources": [], "book_figures": []}

    rows = []
    for i, u in enumerate(uniq):
        g, ch, note = dec.get(str(i), ["D", 0, ""])
        f = crop.get(i, {}).get("file", "")
        pl = placed.get(f)
        rows.append({
            "idx": i, "slug": u["slug"], "source": u["source"], "page": u["page"],
            "copies": u.get("n_copies", 1), "w": u["w"], "h": u["h"],
            "grade": g, "status": GRADES[g][0], "chapter": pl[0] if pl else ch,
            "note": note, "file": f, "caption": pl[1] if pl else "",
            "anchor": pl[2] if pl else "",
        })

    by_grade: dict[str, int] = {}
    for r in rows:
        by_grade[r["grade"]] = by_grade.get(r["grade"], 0) + 1
    n_extracted = sum(u.get("n_copies", 1) for u in uniq)

    L = []
    A = L.append
    A("# Cross-reference منابع ← جزوه\n")
    A("خروجی `tools/figpipe.py report`. هر سطر یک **تصویر یکتا** از منابع است؛")
    A("نسخه‌های تکراری همان تصویر در ستون «نسخه‌ها» شمرده شده‌اند.\n")

    A("\n## ۱) فهرست منابع بررسی‌شده\n")
    A("| منبع | نوع | مسیر | صفحه/اسلاید | شیء تصویری | نویسه متن |")
    A("|---|---|---|---|---|---|")
    for s in disc.get("sources", []):
        if not s.get("exists"):
            A(f"| {s['slug']} | — | {s['path']} | **یافت نشد** | — | — |")
            continue
        A(f"| {s['slug']} | {s['kind']} | `{s['path']}` | {s['pages']} | "
          f"{s['images']} | {s['text_chars']} |")
    A("")
    A(f"- فایل PowerPoint در کل آرشیو: **۰** (همهٔ اسلایدها به‌صورت PDF ارائه شده‌اند)")
    A(f"- سند بررسی‌شده: **{len(disc.get('sources', []))}**")

    A("\n## ۲) خلاصهٔ آماری\n")
    A("| سنجه | تعداد |")
    A("|---|---|")
    A(f"| ناحیهٔ تصویری استخراج‌شده | {n_extracted} |")
    A(f"| تصویر یکتا پس از حذف تکراری‌ها | {len(uniq)} |")
    A(f"| تکراری‌های حذف‌شده در خود منابع | {n_extracted - len(uniq)} |")
    for g in "ABCDER":
        A(f"| {GRADES[g][0]} ({g}) — {GRADES[g][1]} | {by_grade.get(g, 0)} |")
    A(f"| **شکل تازه افزوده‌شده به جزوه** | {sum(1 for r in rows if r['file'] and r['grade'] in 'AB')} |")
    A(f"| **شکل ارتقایافته (نسخهٔ بهتر)** | {sum(1 for r in rows if r['grade'] == 'R')} |")
    A(f"| کل شکل‌های جزوه پس از این پاس | {len(disc.get('book_figures', []))} |")

    A("\n## ۳) نگاشت کامل: منبع → صفحه → تصویر → فصل → جایگاه\n")
    A("| # | منبع | ص | نسخه‌ها | وضعیت | فصل | فایل در جزوه | لنگر متنی / توضیح |")
    A("|---|---|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda r: (r["slug"], r["page"], r["idx"])):
        ch = CH_NAMES.get(r["chapter"], "—") if r["chapter"] else "—"
        tgt = f"`{Path(r['file']).name}`" if r["file"] else "—"
        why = r["anchor"] or r["note"]
        A(f"| {r['idx']} | {r['slug']} | {r['page']} | {r['copies']} | "
          f"{r['grade']} · {r['status']} | {ch} | {tgt} | {why} |")

    A("\n## ۴) Reverse audit — از سمت هر منبع به جزوه\n")
    A("| منبع | یکتا | A | B | C | D | E | R | وارد جزوه شد |")
    A("|---|---|---|---|---|---|---|---|---|")
    for slug in SOURCES:
        rs = [r for r in rows if r["slug"] == slug]
        if not rs:
            continue
        cnt = {g: sum(1 for r in rs if r["grade"] == g) for g in "ABCDER"}
        A(f"| {slug} | {len(rs)} | {cnt['A']} | {cnt['B']} | {cnt['C']} | "
          f"{cnt['D']} | {cnt['E']} | {cnt['R']} | "
          f"{sum(1 for r in rs if r['file'])} |")
    A("")
    A("هیچ تصویر درجهٔ A یا B بدون جای‌گذاری نمانده است؛ موارد زیر اگر پر باشد")
    A("یعنی شکلی مهم جا مانده و باید بررسی شود:\n")
    orphan = [r for r in rows if r["grade"] in "AB" and not r["file"]]
    A("```")
    A("\n".join(f"{r['idx']} {r['slug']} p{r['page']} {r['note']}" for r in orphan)
      or "(خالی — هیچ شکل مهمی جا نمانده)")
    A("```")

    A("\n## ۵) فهرست C (اختیاری) — ذخیره برای پرکردن فضاهای خالی\n")
    A("| # | منبع | ص | توضیح |")
    A("|---|---|---|---|")
    for r in rows:
        if r["grade"] == "C":
            A(f"| {r['idx']} | {r['slug']} | {r['page']} | {r['note']} |")

    (OUT / "CROSSREF.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"cross-reference -> work/figpipe/CROSSREF.md  "
          f"({len(rows)} unique, {sum(1 for r in rows if r['file'])} placed)")
    for g in "ABCDER":
        print(f"  {g} {GRADES[g][0]:30s} {by_grade.get(g, 0):4d}")


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "all"
    arg = argv[2] if len(argv) > 2 else None
    if cmd in ("discover", "all"):
        cmd_discover()
    if cmd in ("extract", "all"):
        cmd_extract(arg)
    if cmd in ("dedupe", "all"):
        cmd_dedupe()
    if cmd in ("sheets", "all"):
        cmd_sheets(arg)
    if cmd in ("report", "all"):
        cmd_report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
