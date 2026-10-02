#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بازبینی جامع جزوه: ساختار، ترتیب، جای شکل‌ها، جای حرف استادها و پوشش منابع.

این ابزار «قفل» فصل‌ها (lock/chNN.json) و PDF نهایی را می‌خواند و یک گزارش
مشکل‌محور تولید می‌کند؛ هیچ چیزی را تغییر نمی‌دهد.

usage:  python3 tools/audit_jozve.py [--pdf FILE] [--out FILE]
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "lock"
CONTENT = ROOT / "content"

FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
EN_DIGITS = "0123456789"
NUM_RE = re.compile(r"[۰-۹]+")


def fa2en(s: str) -> str:
    return s.translate({ord(f): ord(e) for f, e in zip(FA_DIGITS, EN_DIGITS)})


def norm(s: str) -> str:
    s = re.sub(r"\[\[|\]\]", "", s or "")
    s = s.replace("\u200c", " ").replace("ي", "ی").replace("ك", "ک")
    return re.sub(r"\s+", " ", s).strip()


def tokens(s: str) -> set[str]:
    s = norm(s).lower()
    return {w for w in re.findall(r"[\w\u0600-\u06ff]{4,}", s)}


def load_chapters() -> list[dict]:
    out = []
    for f in sorted(LOCK.glob("ch*.json")):
        out.append(json.loads(f.read_text(encoding="utf-8")))
    return out


def block_text(b: dict) -> str:
    parts = [b.get("text") or "", b.get("caption") or "", b.get("name") or ""]
    parts += [str(x) for x in (b.get("items") or [])]
    parts += [str(x) for x in (b.get("head") or [])]
    for row in b.get("rows") or []:
        parts += [str(x) for x in row]
    for lg in b.get("legend") or []:
        parts += [str(x) for x in lg]
    return " ".join(p for p in parts if p)


# --------------------------------------------------------------------------- #
# 1. ساختار و ترتیب
# --------------------------------------------------------------------------- #
def check_structure(chapters: list[dict], issues: list[str]) -> None:
    for ch in chapters:
        no = ch["no"]
        h2s = [b for b in ch["blocks"] if b.get("type") == "h2"]
        if not h2s:
            issues.append(f"ch{no:02d}: هیچ سرفصل h2 ندارد")
            continue
        nums = []
        for b in h2s:
            m = re.match(r"\s*([۰-۹]+)\s*[.٫]", norm(b["text"]))
            nums.append(int(fa2en(m.group(1))) if m else None)
        real = [n for n in nums if n is not None]
        if real != list(range(1, len(real) + 1)):
            issues.append(f"ch{no:02d}: شماره‌گذاری h2 پیوسته نیست → {nums}")
        # بلوک قبل از اولین h2 (به‌جز جلد/فهرست فصل)
        first = ch["blocks"].index(h2s[0])
        if first > 0:
            pre = [b.get("type") for b in ch["blocks"][:first]]
            issues.append(f"ch{no:02d}: {first} بلوک پیش از نخستین سرفصل ({pre})")
        # سرفصل‌های تکراری
        seen = collections.Counter(norm(b["text"]) for b in h2s)
        for t, c in seen.items():
            if c > 1:
                issues.append(f"ch{no:02d}: سرفصل تکراری «{t[:40]}» ×{c}")


# --------------------------------------------------------------------------- #
# 2. جای شکل‌ها
# --------------------------------------------------------------------------- #
def check_figures(chapters: list[dict], issues: list[str], info: list[str]) -> list[dict]:
    rows = []
    for ch in chapters:
        no = ch["no"]
        cur_h2, cur_text = "", ""
        for i, b in enumerate(ch["blocks"]):
            if b.get("type") == "h2":
                cur_h2, cur_text = b.get("text", ""), ""
            elif b.get("type") != "figure":
                cur_text += " " + block_text(b)
            if b.get("type") != "figure":
                continue
            file = b.get("file", "")
            rows.append(dict(ch=no, idx=i, file=file, section=cur_h2,
                             caption=b.get("caption", ""), src=b.get("src", ""),
                             section_text=cur_text[-1500:]))
            if not file:
                issues.append(f"ch{no:02d} fig@{i}: بلوک شکل بدون فایل")
                continue
            if not (ROOT / file).exists():
                issues.append(f"ch{no:02d} fig@{i}: فایل موجود نیست → {file}")
            if not (b.get("caption") or "").strip():
                issues.append(f"ch{no:02d} fig@{i}: بدون شرح (caption) → {os.path.basename(file)}")
            if not (b.get("src") or "").strip():
                issues.append(f"ch{no:02d} fig@{i}: بدون منبع → {os.path.basename(file)}")
            # هم‌پوشانی واژگانی شرح/منبع شکل با متن بخش
            sec_tok = tokens(cur_text)
            cap_tok = tokens((b.get("caption") or "") + " " + (b.get("src") or ""))
            if sec_tok and cap_tok:
                inter = len(sec_tok & cap_tok)
                if inter == 0 and "شکل‌های منبع" not in cur_h2:
                    issues.append(f"ch{no:02d} fig@{i} [{cur_h2[:28]}] هیچ واژه مشترکی با متن بخش ندارد "
                                  f"→ {os.path.basename(file)}")
    return rows


# --------------------------------------------------------------------------- #
# 3. جای حرف استادها (بلوک‌های ویدیویی)
# --------------------------------------------------------------------------- #
def check_video_blocks(chapters: list[dict], issues: list[str]) -> list[dict]:
    sys.path.insert(0, str(ROOT / "tools"))
    spec_files = {
        "video_extra": CONTENT / "video_extra.py",
    }
    import importlib.util
    out_rows = []
    spec = importlib.util.spec_from_file_location("video_extra", spec_files["video_extra"])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    vblocks = getattr(mod, "VIDEO_BLOCKS", {})
    by_ch = {ch["no"]: ch for ch in chapters}
    # نقشه فایل ویدیو → موضوع (از manifest)
    manifest = {}
    mf = ROOT / "work" / "relay" / "video_manifest.tsv"
    if mf.exists():
        for line in mf.read_text(encoding="utf-8").splitlines()[1:]:
            cols = line.split("\t")
            if len(cols) >= 2:
                manifest[cols[0].strip()] = cols[1].strip()
    for no, entries in sorted(vblocks.items()):
        ch = by_ch.get(no)
        if ch is None:
            issues.append(f"video_extra: فصل {no} وجود ندارد")
            continue
        for ent in entries:
            anchor = (ent.get("after") or "").strip()
            found = [i for i, b in enumerate(ch["blocks"])
                     if anchor and anchor in json.dumps(b, ensure_ascii=False)]
            for blk in ent.get("blocks", []):
                src = blk.get("src") or ""
                m = re.search(r"فایل\s*([۰-۹0-9]+)", src)
                vfile = fa2en(m.group(1)).zfill(2) if m else None
                out_rows.append(dict(ch=no, vfile=vfile, anchor=anchor,
                                     has_anchor=bool(found),
                                     text=block_text(blk)[:80], src=src))
                if not src.startswith("منبع: ویدیو"):
                    issues.append(f"ch{no:02d}: بلوک ویدیویی بدون برچسب «منبع: ویدیو» → {block_text(blk)[:40]}")
                if vfile is None:
                    issues.append(f"ch{no:02d}: بلوک ویدیویی بدون شماره فایل → {block_text(blk)[:40]}")
                if not found:
                    issues.append(f"ch{no:02d}: لنگر ویدیو پیدا نشد → «{anchor[:40]}» برای {block_text(blk)[:40]}")
                if not re.search(r"[۰-۹0-9]{2}:[۰-۹0-9]{2}", src):
                    issues.append(f"ch{no:02d}: بلوک ویدیویی بدون زمان → {block_text(blk)[:40]}")
    return out_rows


# --------------------------------------------------------------------------- #
# 4. متن: نشانه‌های رندرنشده
# --------------------------------------------------------------------------- #
def check_text(chapters: list[dict], issues: list[str]) -> None:
    for ch in chapters:
        no = ch["no"]
        for i, b in enumerate(ch["blocks"]):
            t = block_text(b)
            if "[[" in t or "]]" in t:
                pass  # نشانه‌گذاری داخلی مجاز است؛ در PDF بررسی می‌شود
            if "\\frac" in t or "\\text" in t or "\\bar" in t:
                # فرمول‌ها به‌صورت tex ذخیره می‌شوند و در رندر تبدیل می‌شوند
                if b.get("type") not in ("formula",):
                    issues.append(f"ch{no:02d}@{i}: tex در بلوک غیرفرمول → {t[:50]}")
            if b.get("type") in ("table",) and not b.get("rows"):
                issues.append(f"ch{no:02d}@{i}: جدول بدون سطر")
            if b.get("type") in ("bullets",) and not b.get("items"):
                issues.append(f"ch{no:02d}@{i}: bullets بدون آیتم")
            if b.get("type") in ("p", "key", "examtip") and not (b.get("text") or "").strip():
                issues.append(f"ch{no:02d}@{i}: بلوک {b.get('type')} خالی")


# --------------------------------------------------------------------------- #
# 5. تکراری‌ها
# --------------------------------------------------------------------------- #
def check_duplicates(chapters: list[dict], issues: list[str]) -> None:
    for ch in chapters:
        no = ch["no"]
        seen = {}
        for i, b in enumerate(ch["blocks"]):
            if b.get("type") in ("h2", "figure"):
                continue
            t = norm(block_text(b))
            if len(t) < 60:
                continue
            key = t[:300]
            if key in seen:
                issues.append(f"ch{no:02d}@{i}: متن تکراری با بلوک {seen[key]}")
            else:
                seen[key] = i
        # شکل‌های تکراری بر اساس هش تصویر
        files = [b.get("file") for b in ch["blocks"] if b.get("type") == "figure" and b.get("file")]
        try:
            from PIL import Image
        except Exception:
            continue
        h = {}
        for f in files:
            p = ROOT / f
            if not p.exists():
                continue
            im = Image.open(p).convert("L").resize((16, 16))
            px = list(im.get_flattened_data())
            avg = sum(px) / len(px)
            h[f] = "".join("1" if v > avg else "0" for v in px)
        for i, a in enumerate(files):
            for b in files[i + 1:]:
                if a in h and b in h:
                    d = sum(1 for x, y in zip(h[a], h[b]) if x != y)
                    if d <= 10:
                        issues.append(f"ch{no:02d}: شکل تکراری {os.path.basename(a)} ≈ {os.path.basename(b)} (d={d})")


# --------------------------------------------------------------------------- #
# 6. PDF نهایی
# --------------------------------------------------------------------------- #
def check_pdf(path: Path, issues: list[str], info: list[str]) -> None:
    try:
        import pypdfium2 as pdfium
    except Exception:
        issues.append("PDF: pypdfium2 نصب نیست؛ بررسی PDF انجام نشد")
        return
    if not path.exists():
        issues.append(f"PDF: فایل پیدا نشد → {path}")
        return
    doc = pdfium.PdfDocument(str(path))
    n = len(doc)
    info.append(f"PDF: {n} صفحه، {path.stat().st_size/1e6:.2f} مگابایت")
    empty, leaks, tiny = [], [], []
    for i in range(n):
        t = doc[i].get_textpage().get_text_range() or ""
        s = t.strip()
        if len(s) < 25:
            empty.append(i + 1)
        for pat in ("[[", "]]", "\\frac", "\\text{", "\\bar{", "\\sqrt", "None"):
            if pat in t:
                leaks.append((i + 1, pat))
        if len(s) < 25 and 0 < i < n - 1:
            tiny.append(i + 1)
    if empty:
        issues.append(f"PDF: صفحه‌های خالی/نزدیک‌خالی → {empty[:15]}")
    if leaks:
        issues.append(f"PDF: نشانه‌های رندرنشده → {leaks[:15]} (تعداد {len(leaks)})")
    # تصاویر
    n_img = 0
    pages_with_img = 0
    for i in range(n):
        try:
            c = sum(1 for _ in doc[i].get_objects(filter=(4, 5)))  # image XObjects
        except Exception:
            c = 0
        n_img += c
        pages_with_img += 1 if c else 0
    info.append(f"PDF: {n_img} تصویر جاسازی‌شده در {pages_with_img} صفحه")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default=str(ROOT / "HumsYar_MedPhysics_Jozve.pdf"))
    ap.add_argument("--out", default=str(ROOT / "work" / "review" / "audit_report.md"))
    args = ap.parse_args()

    chapters = load_chapters()
    issues: list[str] = []
    info: list[str] = []

    check_structure(chapters, issues)
    figs = check_figures(chapters, issues, info)
    vids = check_video_blocks(chapters, issues)
    check_text(chapters, issues)
    check_duplicates(chapters, issues)
    check_pdf(Path(args.pdf), issues, info)

    info.insert(0, f"فصل‌ها: {len(chapters)} · بلوک: {sum(len(c['blocks']) for c in chapters)} · "
                   f"شکل: {len(figs)} · بلوک ویدیویی: {len(vids)}")
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# گزارش بازبینی خودکار جزوه", ""]
    lines += ["## خلاصه"] + [f"- {x}" for x in info] + [""]
    lines += [f"## یافته‌ها ({len(issues)} مورد)", ""]
    lines += [f"{i+1}. {x}" for i, x in enumerate(issues)] or ["— موردی یافت نشد —"]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(info))
    print(f"\nissues: {len(issues)}")
    for x in issues[:60]:
        print("  -", x)
    if len(issues) > 60:
        print(f"  ... و {len(issues)-60} مورد دیگر (فایل: {out})")
    print(f"\nنوشته شد: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
