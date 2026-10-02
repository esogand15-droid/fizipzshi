#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Condense a raw transcript into the lines that carry teachable content.

Transcription filler ("خب", "یعنی", "بله" ...) is dropped; every surviving line keeps
its {mm:ss} timecode so whatever gets merged into a chapter can cite the video minute.

usage: digest.py <slug> [--min-words 6] [--max-lines 90]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FA = "۰۱۲۳۴۵۶۷۸۹"
FILLER = re.compile(r"^(خب|بله|ببینید|یعنی|درسته|باشه|آره|نه|خوب|اوکی|کاملا|بله‌? ?دیگه)")
# a line is worth keeping when it carries a *fact*: a number, a latin technical
# term, a definition marker or an exam hint. plain narration stays out.
SIGNAL = re.compile(
    r"(امتحان|سوال|نکته|مهم|حفظ|دقت|توجه|مثال|فرمول|رابطه|تعریف|یادتون|اشتباه|"
    r"[0-9۰-۹]|[A-Za-z]{2,}|کیلو|مگا|گیگا|میلی|میکرو|سانتی|درجه|نیمه‌عمر|دوز|واحد|"
    r"انرژی|فرکانس|طول موج|سرعت|ولتاژ|جریان|توان|ضخامت|چگالی|عدد اتمی|جرم|بار|"
    r"سرطان|تومور|بافت|سلول|خون|مغز|استخوان|کبد|کلیه|قلب|ریه|تیروئید|"
    r"سرخ|آبی|سفید|تیره|روشن|کنتراست|چاه|قله|شیب|منحنی|محور)")


def fa_digits(x) -> str:
    return "".join(FA[int(c)] if c.isdigit() else c for c in str(x))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--min-words", type=int, default=6)
    ap.add_argument("--max-lines", type=int, default=90)
    args = ap.parse_args()

    path = ROOT / "work" / "transcripts" / args.slug / "raw.md"
    lines = [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

    kept: list[tuple[str, str]] = []
    for line in lines:
        m = re.match(r"^\[(\d\d:\d\d)\]\s*(.*)$", line)
        tc, text = (m.group(1), m.group(2)) if m else ("", line)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text.split()) < args.min_words or FILLER.match(text):
            continue
        if not SIGNAL.search(text):
            continue
        kept.append((tc, text))

    # merge consecutive timecodes that belong to the same utterance (a sentence split
    # over several segments ends up looking like a list of fragments)
    out, buf = [], None
    for tc, text in kept:
        if buf is None:
            buf = [tc, text]
            continue
        buf[1] += " " + text
        if len(buf[1]) > 190:
            out.append(buf)
            buf = None
    if buf:
        out.append(buf)

    if len(out) > args.max_lines:
        step = len(out) / args.max_lines
        out = [out[int(i * step)] for i in range(args.max_lines)]

    print(f"### {args.slug}  ({len(lines)} lines -> {len(out)} digest lines)")
    for tc, text in out:
        print(f"[{tc}] {text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
