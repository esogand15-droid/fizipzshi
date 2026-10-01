#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the transcription matrix (one row per (video, part)) for GitHub Actions."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

MANIFEST = Path("work/relay/video_manifest.json")
PART_MIN = 80.0  # split videos longer than this into parts


def main() -> int:
    selector = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
    if not selector or selector == "all":
        want = Path("work/relay/want.txt")
        if want.exists():
            selector = want.read_text(encoding="utf-8").strip() or "all"
    rows = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if selector and selector != "all":
        want = {s.strip() for s in selector.split(",") if s.strip()}
        rows = [r for r in rows if r["slug"] in want]

    include = []
    for r in rows:
        dur_min = r["duration"] / 60.0
        if dur_min <= PART_MIN:
            include.append({"slug": r["slug"], "name": r["name"], "part": 0,
                            "offset": 0, "limit": 0,
                            "mins": round(dur_min, 1)})
        else:
            nparts = int(dur_min // PART_MIN) + (1 if dur_min % PART_MIN else 0)
            for p in range(nparts):
                include.append({"slug": r["slug"], "name": r["name"], "part": p,
                                "offset": round(p * PART_MIN, 1), "limit": PART_MIN,
                                "mins": round(dur_min, 1)})

    matrix = {"include": include}
    out = os.environ.get("GITHUB_OUTPUT")
    text = json.dumps(matrix, ensure_ascii=False)
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"matrix={text}\n")
            fh.write(f"count={len(include)}\n")
    print(text)
    print(f"entries: {len(include)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
