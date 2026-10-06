# -*- coding: utf-8 -*-
"""figcrop — stage 6 of the image asset pipeline: content-aware cropping.

Takes the candidates selected during review (``work/figpipe/selected.json``)
and produces print-ready figures in ``images/fig/``.

What it does, in order:

1. **inner white box** — slide decks very often put the real artwork inside a
   light panel on a coloured slide. When such a panel covers a usable part of
   the tile we crop to it, which removes the title bar, the bullet text and the
   deck's decorative margin in one go.
2. **solid banner strip** — otherwise, drop a full-width band at the top (or the
   bottom) when it is a *solid* colour clearly different from the body of the
   tile: that is the slide's title bar / footer, never the artwork.
3. **ink bounding box** — finally trim the uniform margin that is left, keeping a
   small padding so labels, arrows, axes and scale bars keep breathing room.

Nothing here ever stretches an image: only axis-aligned crops and one
proportional resize at the end.

usage:  python tools/figcrop.py [--dry] [index ...]
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = ROOT / "work" / "figpipe"
OUT = ROOT / "images" / "fig"

PAD = 24               # px of breathing room kept around the detected content
MAX_W = 1500           # final width cap (the page column is ~150 mm)
JPEG_Q = 85
MIN_PANEL = 0.10       # a white panel must cover this fraction of the tile
MIN_SIDE = 160         # never emit something smaller than this
KEEP_INK = 0.975       # a crop must retain this share of the tile's drawn pixels


# ----------------------------------------------------------------- helpers
def _runs(flags: np.ndarray) -> list[tuple[int, int]]:
    """[(start, end_exclusive)] of the True runs of a 1-D boolean array."""
    out, i, n = [], 0, len(flags)
    while i < n:
        if flags[i]:
            j = i
            while j < n and flags[j]:
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def inner_panel(a: np.ndarray) -> tuple[int, int, int, int] | None:
    """Largest light panel inside the tile, as (x0, y0, x1, y1)."""
    h, w, _ = a.shape
    light = (a.min(axis=2) > 205)                     # near-white in every channel
    rows = light.mean(axis=1) > 0.55
    cols = light.mean(axis=0) > 0.55
    rr = [r for r in _runs(rows) if r[1] - r[0] > 0.18 * h]
    cc = [c for c in _runs(cols) if c[1] - c[0] > 0.25 * w]
    if not rr or not cc:
        return None
    y0, y1 = max(rr, key=lambda r: r[1] - r[0])
    x0, x1 = max(cc, key=lambda c: c[1] - c[0])
    if (y1 - y0) * (x1 - x0) < MIN_PANEL * h * w:
        return None
    if y1 - y0 < MIN_SIDE or x1 - x0 < MIN_SIDE:
        return None
    return x0, y0, x1, y1


def strip_banner(a: np.ndarray) -> tuple[int, int]:
    """(top, bottom) rows to drop: solid full-width title bar / footer bands."""
    h, w, _ = a.shape
    # a row is "solid" when its pixels barely vary across the width
    solid = a.std(axis=1).max(axis=1) < 26
    colour = a.mean(axis=1)                            # mean rgb per row
    body = np.median(colour[int(0.35 * h):int(0.65 * h)], axis=0)

    top = 0
    for y in range(min(int(0.30 * h), h - 1)):
        if solid[y] and np.abs(colour[y] - body).max() > 34:
            top = y + 1
        elif y > 4 and not solid[y]:
            break
    bot = h
    for y in range(h - 1, max(int(0.75 * h), 0), -1):
        if solid[y] and np.abs(colour[y] - body).max() > 34:
            bot = y
        elif y < h - 5 and not solid[y]:
            break
    if bot - top < MIN_SIDE:
        return 0, h
    return top, bot


def ink_box(a: np.ndarray) -> tuple[int, int, int, int]:
    """Bounding box of everything that differs from the dominant background."""
    g = a.mean(axis=2)
    hist = np.bincount(g.astype(np.uint8).ravel(), minlength=256)
    bg = float(hist.argmax())
    ink = np.abs(g - bg) > 38
    if ink.sum() < 40:
        return 0, 0, a.shape[1], a.shape[0]
    ys, xs = np.where(ink)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def ink_mask(a: np.ndarray) -> np.ndarray:
    """Pixels that differ from the dominant background colour."""
    g = a.mean(axis=2)
    hist = np.bincount(g.astype(np.uint8).ravel(), minlength=256)
    bg = float(hist.argmax())
    return np.abs(g - bg) > 38


# --- recover artwork the extraction window cut off -------------------------
_BBOX = None


def _bbox_index() -> dict:
    """tile path -> (pdf, page, bbox) from the extraction manifest."""
    global _BBOX
    if _BBOX is None:
        _BBOX = {}
        f = WORK / "candidates.json"
        if f.exists():
            for c in json.loads(f.read_text("utf-8")):
                if c.get("bbox"):
                    _BBOX[c["file"]] = (c["pdf"], c["page"], c["bbox"])
    return _BBOX


def _edge_ink(im) -> bool:
    """True when drawn pixels run into the border — the tile is clipped."""
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    m = ink_mask(a)
    b = 3
    return (m[:b, :].mean() > 0.012 or m[-b:, :].mean() > 0.012
            or m[:, :b].mean() > 0.012 or m[:, -b:].mean() > 0.012)


# A slide whose title sits far above the drawing needs a wider window than the
# default budget allows; these tiles are allowed to grow further because the
# extra area is the figure's own heading, not the slide's body text.
WIDEN_CAP = {
    "work/figpipe/cand/afzalipour/p022_0.jpg": 2.0,
}
DEFAULT_WIDEN_CAP = 1.5


def widen(path: pathlib.Path):
    """Re-render a clipped tile from its PDF with a wider window.

    The extraction window is built from the picture and vector objects of the
    slide, so an axis label or a table column that is pure *text* can fall just
    outside it and come out sliced. When the tile's ink touches its own border
    we go back to the page and grow the window until the cut lands on empty
    space again — labels and legends are never dropped (rule 12/13).
    """
    im = Image.open(path).convert("RGB")
    key = str(path)
    if path.is_absolute():
        try:
            key = str(path.relative_to(ROOT))
        except ValueError:
            pass
    rec = _bbox_index().get(key.replace("\\", "/"))
    if rec is None or not _edge_ink(im):
        return im
    import pymupdf
    pdf, pno, bbox = rec
    doc = pymupdf.open(ROOT / pdf)
    page = doc[pno - 1]
    pr = page.rect
    area0 = im.width * im.height
    cap = WIDEN_CAP.get(key.replace("\\", "/"), DEFAULT_WIDEN_CAP)
    best = im
    for grow in (10, 20, 34, 52):
        r = pymupdf.Rect(bbox[0] - grow, bbox[1] - grow,
                         bbox[2] + grow, bbox[3] + grow) & pr
        pix = page.get_pixmap(dpi=200, clip=r)
        cand = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        if cand.width * cand.height < 0.95 * area0:
            continue            # a bad bbox: never hand back less than we had
        if cand.width * cand.height > cap * area0:
            break               # we would be pulling in the slide's body text
        if not _edge_ink(cand):
            best = cand         # only accept a window that cuts clean air
            break
    doc.close()
    return best

def crop_one(path: pathlib.Path) -> Image.Image:
    """Smallest acceptable crop that still holds (almost) all of the artwork.

    Every candidate crop is checked against the tile's ink mask: a crop that
    would throw away more than ``1 - KEEP_INK`` of the drawn pixels is refused,
    because that is exactly how labels, legends, axes and arrows get cut off.
    """
    im = widen(path)
    a = np.asarray(im).astype(np.float32)
    mask = ink_mask(a)
    total = float(mask.sum()) or 1.0

    def clean_edges(box) -> bool:
        """True when the cut runs through background, not through artwork.

        Keeping 97.5% of the ink is not enough on its own: slicing the first
        letters off an axis label or a table column costs only a few per mille
        of the drawn pixels but ruins the figure. So also require that the crop
        line itself lands on empty space — if ink touches the proposed border,
        something is being cut in half.
        """
        x0, y0, x1, y1 = box
        band = 3
        for sl, full in (
                (mask[y0:y0 + band, x0:x1], y0 > 0),
                (mask[y1 - band:y1, x0:x1], y1 < mask.shape[0]),
                (mask[y0:y1, x0:x0 + band], x0 > 0),
                (mask[y0:y1, x1 - band:x1], x1 < mask.shape[1])):
            if full and sl.size and sl.mean() > 0.012:
                return False
        return True

    def keeps(box) -> bool:
        x0, y0, x1, y1 = box
        if x1 - x0 < MIN_SIDE or y1 - y0 < MIN_SIDE:
            return False
        # a crop that throws away three quarters of the tile is not a crop, it
        # is a different picture — usually a caption strip mistaken for a panel
        if (x1 - x0) * (y1 - y0) < 0.25 * mask.shape[0] * mask.shape[1]:
            return False
        if mask[y0:y1, x0:x1].sum() / total < KEEP_INK:
            return False
        return clean_edges(box)

    # candidates, smallest (most aggressive) first
    cands = []
    panel = inner_panel(a)
    if panel:
        cands.append(panel)
    top, bot = strip_banner(a)
    bx0, by0, bx1, by1 = ink_box(a[top:bot])
    cands.append((bx0, top + by0, bx1, top + by1))
    cands.append((0, 0, im.width, im.height))
    cands.sort(key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))

    x0, y0, x1, y1 = next((b for b in cands if keeps(b)), (0, 0, im.width, im.height))

    x0 = max(0, x0 - PAD)
    y0 = max(0, y0 - PAD)
    x1 = min(im.width, x1 + PAD)
    y1 = min(im.height, y1 + PAD)

    out = im.crop((x0, y0, x1, y1))
    if out.width > MAX_W:                               # proportional, never stretched
        out = out.resize((MAX_W, round(out.height * MAX_W / out.width)), Image.LANCZOS)
    return out


# --- hand-tuned overrides -------------------------------------------------
# Relative (x0, y0, x1, y1) applied *after* the automatic crop, for the handful
# of tiles where the generic rules leave slide chrome behind: a block of body
# text above the artwork, a sliver of the previous slide, or the source book's
# own caption line (we add our own caption, so it would read twice).
MANUAL: dict[int, tuple[float, float, float, float]] = {
    28: (0.00, 0.14, 1.00, 1.00),    # sliver of the previous slide on top
    60: (0.00, 0.47, 1.00, 1.00),    # four lines of body text above the photos
    315: (0.00, 0.00, 1.00, 0.94),   # scanned book caption at the foot
    316: (0.00, 0.00, 1.00, 0.94),
    317: (0.00, 0.00, 1.00, 0.94),
    318: (0.00, 0.00, 1.00, 0.94),
    323: (0.00, 0.00, 1.00, 0.94),
    330: (0.00, 0.00, 1.00, 0.94),
    337: (0.00, 0.00, 1.00, 0.93),
}


def name_for(rec: dict, idx: int) -> str:
    return f"x{idx:03d}_{rec['slug']}_p{rec['page']:03d}.jpg"


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv

    uniq = json.loads((WORK / "unique.json").read_text("utf-8"))
    sel = json.loads((WORK / "selected.json").read_text("utf-8"))
    if args:
        sel = [int(a) for a in args]

    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    for idx in sel:
        rec = uniq[idx]
        src = ROOT / rec["file"]
        if not src.exists():
            print(f"  !! missing {src}")
            continue
        im = crop_one(src)
        if idx in MANUAL:
            fx0, fy0, fx1, fy1 = MANUAL[idx]
            im = im.crop((round(fx0 * im.width), round(fy0 * im.height),
                          round(fx1 * im.width), round(fy1 * im.height)))
        name = name_for(rec, idx)
        if not dry:
            im.save(OUT / name, "JPEG", quality=JPEG_Q, optimize=True)
        made.append((idx, name, im.width, im.height))
        print(f"  [{idx:>3}] {name}  {im.width}x{im.height}")

    (WORK / "cropped.json").write_text(
        json.dumps([{"index": i, "file": f"images/fig/{n}", "w": w, "h": h}
                    for i, n, w, h in made], ensure_ascii=False, indent=1), "utf-8")
    print(f"\n{len(made)} figures cropped into images/fig/")


if __name__ == "__main__":
    main()
