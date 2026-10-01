#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the locked chapter JSON files (lock/chNN.json) from content/*.py modules.

The renderer only ever reads lock/ — content modules are the authoring layer.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
LOCK = ROOT / "lock"

CHAPTERS = {
    1: dict(session="فصل ۱", title="مبانی فیزیک پزشکی و طبقه‌بندی پرتوها", prof="دکتر رضا افضلی‌پور",
            icon="radiation", module="ch01_basics"),
    2: dict(session="فصل ۲", title="تولید پرتو ایکس و ساختمان لامپ", prof="دکتر رضا افضلی‌پور",
            icon="tube", module="ch02_xray"),
    3: dict(session="فصل ۳", title="تشکیل تصویر رادیوگرافی، فلوروسکوپی و سی‌تی‌اسکن",
            prof="دکتر رضا افضلی‌پور", icon="chart", module="ch03_imaging"),
    4: dict(session="فصل ۴", title="رادیواکتیویته، واپاشی‌ها و پزشکی هسته‌ای", prof="دکتر حق‌پرست",
            icon="atom", module="ch04_radioactivity"),
    5: dict(session="فصل ۵", title="واحدهای سنجش پرتو و دزیمتری", prof="دکتر حق‌پرست",
            icon="dose", module="ch05_dosimetry"),
    6: dict(session="فصل ۶", title="حفاظت در برابر پرتو", prof="دکتر حق‌پرست",
            icon="shield", module="ch06_protection"),
    7: dict(session="فصل ۷", title="فیزیک سونوگرافی و اولتراسوند", prof="دکتر حق‌پرست",
            icon="wave", module="ch07_sono"),
    8: dict(session="فصل ۸", title="رادیوبیولوژی و اثرات زیستی پرتوها", prof="دکتر لیلی درویش",
            icon="skull", module="ch08_radiobio", exam_flag="exam"),
    9: dict(session="فصل ۹", title="تصویربرداری تشدید مغناطیسی (MRI)", prof="دکتر لیلی درویش",
            icon="magnet", module="ch09_mri", exam_flag="exam"),
}


def load_module(name: str):
    path = CONTENT / f"{name}.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    only = [int(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else None
    LOCK.mkdir(exist_ok=True)
    built = 0
    for no, meta in CHAPTERS.items():
        if only and no not in only:
            continue
        mod = load_module(meta["module"])
        if mod is None:
            print(f"ch{no:02d}: module missing ({meta['module']})")
            continue
        ch = {"no": no, "session": meta["session"], "title": meta["title"],
              "prof": meta["prof"], "icon": meta["icon"], "blocks": mod.BLOCKS}
        if meta.get("exam_flag"):
            ch["exam_flag"] = meta["exam_flag"]
        (LOCK / f"ch{no:02d}.json").write_text(
            json.dumps(ch, ensure_ascii=False, indent=1), encoding="utf-8")
        src = sum(1 for b in ch["blocks"] if b.get("src"))
        figs = sum(1 for b in ch["blocks"] if b.get("type") == "figure")
        print(f"ch{no:02d}: {len(ch['blocks'])} blocks, {figs} figures, {src} with src")
        built += 1
    print("built", built)
    return 0


if __name__ == "__main__":
    sys.exit(main())
