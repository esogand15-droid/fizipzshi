#!/usr/bin/env python3
"""Build a complete inventory of a source-material tree.

The جزوه is assembled from a pile of lecture material (PowerPoint decks,
scanned PDFs, hand-written notes, screen recordings). Before a single figure is
touched we need to know *exactly* what material exists, so that nothing is
silently skipped — a file is never ignored just because its name looks odd.

usage:  python3 tools/src_inventory.py <root> [out.json]

For every file it records path/size/kind; for PowerPoint decks the slide count
and the embedded media; for PDFs the page count, embedded image count and
whether the page carries a text layer.
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

SLIDE_EXT = {".pptx", ".ppt", ".pptm", ".odp", ".key"}
DOC_EXT = {".pdf", ".docx", ".doc", ".odt", ".rtf"}
TEXT_EXT = {".md", ".txt", ".srt", ".vtt", ".csv", ".json"}
IMG_EXT = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp", ".emf", ".wmf"}
AV_EXT = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mp3", ".wav", ".m4a", ".aac", ".ogg"}


def kind_of(ext: str) -> str:
    if ext in SLIDE_EXT:
        return "slides"
    if ext in DOC_EXT:
        return "document"
    if ext in TEXT_EXT:
        return "text"
    if ext in IMG_EXT:
        return "image"
    if ext in AV_EXT:
        return "video/audio"
    return "other"


def probe_pptx(p: Path) -> dict:
    """Slide + media census straight from the OOXML package (no pptx lib needed)."""
    info: dict = {"slides": 0, "media": 0, "media_bytes": 0, "media_ext": {}, "notes": 0}
    try:
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                if re.fullmatch(r"ppt/slides/slide\d+\.xml", n):
                    info["slides"] += 1
                elif re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", n):
                    info["notes"] += 1
                elif n.startswith("ppt/media/"):
                    ext = Path(n).suffix.lower()
                    if ext in AV_EXT:
                        continue
                    info["media"] += 1
                    info["media_bytes"] += z.getinfo(n).file_size
                    info["media_ext"][ext] = info["media_ext"].get(ext, 0) + 1
    except Exception as exc:  # pragma: no cover - diagnostics only
        info["error"] = f"{type(exc).__name__}: {exc}"
    return info


def probe_pdf(p: Path) -> dict:
    info: dict = {"pages": 0, "images": 0, "text_chars": 0, "pages_without_text": 0}
    try:
        import pymupdf  # type: ignore

        with pymupdf.open(p) as doc:
            info["pages"] = doc.page_count
            seen: set = set()
            for page in doc:
                txt = page.get_text("text")
                info["text_chars"] += len(txt.strip())
                if len(txt.strip()) < 20:
                    info["pages_without_text"] += 1
                for img in page.get_images(full=True):
                    seen.add(img[0])
            info["images"] = len(seen)
    except Exception as exc:  # pragma: no cover
        info["error"] = f"{type(exc).__name__}: {exc}"
    return info


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve()
    out = Path(argv[2]) if len(argv) > 2 else Path("work/sources/inventory.json")
    out.parent.mkdir(parents=True, exist_ok=True)

    records = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        rec = {
            "path": str(p.relative_to(root)),
            "name": p.name,
            "ext": ext,
            "bytes": p.stat().st_size,
            "kind": kind_of(ext),
        }
        if ext == ".pptx" or ext == ".pptm":
            rec["pptx"] = probe_pptx(p)
        elif ext == ".pdf":
            rec["pdf"] = probe_pdf(p)
        records.append(rec)

    totals: dict = {}
    for r in records:
        t = totals.setdefault(r["kind"], {"files": 0, "bytes": 0})
        t["files"] += 1
        t["bytes"] += r["bytes"]

    out.write_text(json.dumps({"root": str(root), "totals": totals, "files": records},
                              ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"inventory: {len(records)} files -> {out}")
    for k, v in sorted(totals.items()):
        print(f"  {k:12s} {v['files']:4d} files  {v['bytes']/1e6:9.1f} MB")
    for r in records:
        if r["kind"] in ("slides", "document"):
            extra = r.get("pptx") or r.get("pdf") or {}
            bits = " ".join(f"{k}={v}" for k, v in extra.items() if k != "media_ext")
            print(f"  · {r['path']}  ({r['bytes']/1e6:.1f} MB) {bits}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
