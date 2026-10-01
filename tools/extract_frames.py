#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract distinct slide frames from a lecture video (dedup by perceptual hash).

The lecture videos are screen recordings: most frames repeat the same slide.
We sample every N seconds, hash each frame, and keep only frames that differ
meaningfully from the last kept one. Output: frames/<slug>/f_MMSS.jpg + index.json
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

EVERY_SEC = 12          # sample period
HASH_DIST = 10          # min hamming distance (of 64) to count as a new slide
MAX_FRAMES = 220
SCALE_W = 1100


def ahash(img: Image.Image, size: int = 8) -> int:
    g = img.convert("L").resize((size, size), Image.Resampling.LANCZOS)
    px = list(g.getdata())
    avg = sum(px) / len(px)
    bits = 0
    for i, v in enumerate(px):
        if v > avg:
            bits |= 1 << i
    return bits


def dist(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def main() -> int:
    slug = sys.argv[1]
    video = Path(sys.argv[2])
    outdir = Path("frames") / slug
    outdir.mkdir(parents=True, exist_ok=True)
    tmp = Path("work/tmp_frames")
    if tmp.exists():
        for f in tmp.glob("*.jpg"):
            f.unlink()
    tmp.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
         "-vf", f"fps=1/{EVERY_SEC},scale={SCALE_W}:-2", "-q:v", "4", str(tmp / "s_%05d.jpg")],
        check=True)

    idx, kept, last = [], 0, None
    for f in sorted(tmp.glob("s_*.jpg")):
        n = int(f.stem.split("_")[1])
        sec = (n - 1) * EVERY_SEC
        if kept >= MAX_FRAMES:
            break
        if (outdir / f"f_{sec//60:02d}{sec%60:02d}.jpg").exists():
            with Image.open(f) as im:
                last = ahash(im)
            continue
        with Image.open(f) as im:
            h = ahash(im)
            if last is not None and dist(h, last) < HASH_DIST:
                continue
            last = h
            out = outdir / f"f_{sec//60:02d}{sec%60:02d}.jpg"
            im.convert("RGB").save(out, "JPEG", quality=80, optimize=True)
            idx.append({"t": sec, "file": out.name})
            kept += 1

    (outdir / "index.json").write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    for f in tmp.glob("*.jpg"):
        f.unlink()
    print(f"[{slug}] kept {kept} frames")
    return 0


if __name__ == "__main__":
    sys.exit(main())
