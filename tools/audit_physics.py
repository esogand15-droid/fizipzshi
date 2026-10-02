#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Targeted numerical/content checks for the ultrasound and nuclear-physics edits.

Run: .venv/bin/python tools/audit_physics.py
This complements audit.py; it does not replace visual PDF review.
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_module(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relpath)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {relpath}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fail(msg: str) -> None:
    raise AssertionError(msg)


def main() -> int:
    sono = load_module("ch07_sono", "content/ch07_sono.py")
    nuclear = load_module("ch04_nuclear", "content/ch04_nuclear.py")
    protection = load_module("ch06_protection", "content/ch06_protection.py")
    video = load_module("video_extra", "content/video_extra.py")

    blocks = sono.BLOCKS
    text = "\n".join(str(b) for b in blocks)
    if r"R = \\left(\\frac{Z_2 - Z_1}{Z_2 + Z_1}\\right)^2" not in text:
        fail("ultrasound energy-reflectance equation missing or malformed")
    if not any(b.get("type") == "formula" and b.get("tex") == "T = 1 - R" for b in blocks):
        fail("transmission must be defined as the fractional complement T = 1 - R")
    if "نه درصدها" not in text or "100% − درصدِ بازتاب" not in text:
        fail("fraction-versus-percent distinction is missing")
    if "ویژگی ذاتی موج" not in text or "شدت" not in text or "توان منبع" not in text:
        fail("intrinsic wave properties and intensity dependence are not clearly distinguished")

    def reflectance(z1: float, z2: float) -> float:
        return ((z2 - z1) / (z2 + z1)) ** 2

    muscle_r = reflectance(1.70, 0.0004)
    fat_kidney_r = reflectance(1.38, 1.62)
    if not math.isclose(muscle_r * 100, 99.906, rel_tol=0.0, abs_tol=0.01):
        fail(f"muscle/air reflectance calculation unexpected: {muscle_r * 100:.4f}%")
    if not math.isclose(fat_kidney_r * 100, 0.64, rel_tol=0.0, abs_tol=1e-9):
        fail(f"fat/kidney reflectance calculation unexpected: {fat_kidney_r * 100:.4f}%")
    expected_figs = {
        "images/fig/fig07_transmission_reflection.jpg",
        "images/fig/fig07_reflection_muscle_air.jpg",
    }
    if not expected_figs.issubset({b.get("file") for b in blocks if b.get("type") == "figure"}):
        fail("one or more source diagrams are not placed in the ultrasound chapter")
    layer_table = next((b for b in blocks if b.get("type") == "table"
                        and "جزء / اصطلاح استاندارد" in b.get("head", [])), None)
    if layer_table is None:
        fail("transducer layer terminology table is missing")
    layer_text = " ".join(str(cell) for row in layer_table["rows"] for cell in row)
    for term in ("Matching Layer", "Coupling Gel", "Backing", "Damping Layer",
                 "لایهٔ پشتی", "بلوک پشتی", "لایهٔ پشتیبان"):
        if term not in layer_text:
            fail(f"transducer layer distinction/synonym missing: {term}")
    extra_text = " ".join(str(x) for entries in video.VIDEO_BLOCKS.get(7, [])
                        for block in entries.get("blocks", []) for x in block.values())
    if "نمی‌توان نتیجه گرفت سونوگرافی ریه کاربرد تشخیصی ندارد" not in extra_text:
        fail("lung-ultrasound clinical caveat is missing from the video/source reconciliation")
    if "10.1002/jum.16088" not in extra_text:
        fail("external clinical reference for lung ultrasound is missing")

    nuclear_text = "\n".join(str(b) for b in nuclear.BLOCKS)
    if "2 m_e c^2" not in nuclear_text:
        fail("positron threshold formula should display 2 m_e c^2")
    gamma = next((b for b in nuclear.BLOCKS if b.get("type") == "formula"
                  and "87m" in b.get("tex", "")), None)
    if not gamma or "_{38}" not in gamma.get("tex", "") or "rightarrow" not in gamma.get("tex", ""):
        fail("gamma isotope notation should show Sr-87m (Z=38) → Sr-87")
    renderer = load_module("renderer", "render/render.py")
    gamma_html = renderer.mathml_like(gamma["tex"])
    if "<sup>87m</sup>" not in gamma_html or "<sub>38</sub>" not in gamma_html or "γ" not in gamma_html:
        fail("gamma isotope formula does not render with the expected superscripts/subscripts")
    reflection = next(b for b in blocks if b.get("type") == "formula"
                      and b.get("name", "").startswith("کسر انرژی بازتاب"))
    reflection_html = renderer.mathml_like(reflection["tex"])
    if "<sup>2</sup>" not in reflection_html or "frac" not in reflection_html:
        fail("reflection formula is not rendered as a squared fraction")
    if "<sub>e</sub>" not in renderer.inline("[[2 m_e c^2]]"):
        fail("electron-mass subscript in the 2 m_e c^2 formula is not rendered")

    protection_text = "\n".join(str(b) for b in protection.BLOCKS)
    if "آشعه" in protection_text:
        fail("OCR typo آشعه remains in the protection chapter")
    fig_place = load_module("fig_place", "content/fig_place.py")
    for redundant in ("images/fig/slide06_afzalipour_p104_0.jpg",
                      "images/fig/slide06_afzalipour_p105_0.jpg"):
        if redundant not in fig_place.FIG_DROP:
            fail(f"redundant protection image has not been removed: {redundant}")
    apron_path = "images/fig/fig06_lead_apron.jpg"
    if any(b.get("type") == "figure" and b.get("file") == apron_path
           for b in protection.BLOCKS):
        fail("orphaned apron image remains in the protection chapter")
    attach_figures = load_module("attach_figures", "tools/attach_figures.py")
    if any(fig.get("file") == apron_path
           for _anchor, figures in attach_figures.PLAN.get(6, []) for fig in figures):
        fail("figure helper would reinsert the redundant apron image")

    print("فیزیک سونوگرافی: R/T، درصدها، اعداد مثال‌ها، شکل‌ها و جدول لایه‌ها ✓")
    print(f"محاسبه‌ها: عضله/هوا R={muscle_r*100:.3f}%؛ چربی/کلیه R={fat_kidney_r*100:.2f}% ✓")
    print("فصل هسته‌ای: 2 m_e c^2 و نمادگذاری Sr-87m → Sr-87 ✓")
    print("حفاظت: املای اشعه و حذف شکل تکراری ✓")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"خطا: {exc}", file=sys.stderr)
        raise SystemExit(1)
