#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the locked chapter JSON files (lock/chNN.json) from content/*.py modules.

The renderer only ever reads lock/ — content modules are the authoring layer.
"""
from __future__ import annotations

import importlib.util
import json
import re
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
            icon="atom", module="ch04_nuclear"),
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


def load_video_extra():
    path = CONTENT / "video_extra.py"
    if not path.exists():
        return {}
    spec = importlib.util.spec_from_file_location("video_extra", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    blocks = dict(getattr(mod, "VIDEO_BLOCKS", {}) or {})
    # نکته‌های تکمیلی پوشش (غیر ویدیویی) با همان ساختار لنگر
    for no, entries in (getattr(mod, "COVER_EXTRA", {}) or {}).items():
        blocks.setdefault(no, [])
        blocks[no] = list(blocks[no]) + list(entries)
    return blocks


def apply_video_extra(no: int, blocks: list[dict], extra: dict) -> list[dict]:
    """Insert each video block right after the block its `after` text matches."""
    entries = extra.get(no) or []
    if not entries:
        return blocks
    out = list(blocks)
    for ent in entries:
        for blk in ent.get("blocks", []):
            if any(b.get("src") == blk.get("src") and b.get("type") == blk.get("type")
                   for b in out):
                continue                      # idempotent
            needle = (ent.get("after") or "").strip()
            pos = None
            for i, b in enumerate(out):
                hay = json.dumps(b, ensure_ascii=False)
                if needle and needle in hay:
                    pos = i
                    break
            entry = {k: v for k, v in blk.items()}
            if pos is None:
                # no anchor matched: keep it in the body, just before «مرور سریع»
                idx = next((i for i, b in enumerate(out) if b.get("type") == "quickreview"),
                           len(out))
                out.insert(idx, entry)
            else:
                # skip over any figures attached to the anchored block so the added
                # text stays next to the section it belongs to (not after its picture)
                j = pos + 1
                while j < len(out) and out[j].get("type") == "figure":
                    j += 1
                out.insert(j, entry)
    return out


def load_fig_place():
    """content/fig_place.py — جای‌گذاری دستی شکل‌های باقی‌مانده اسلایدها."""
    path = CONTENT / "fig_place.py"
    if not path.exists():
        return {}, {}
    spec = importlib.util.spec_from_file_location("fig_place", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    after = getattr(mod, "FIG_AFTER", {}) or {}
    move = getattr(mod, "FIG_MOVE", {}) or {}
    drop = getattr(mod, "FIG_DROP", []) or []
    caption = getattr(mod, "FIG_CAPTION", {}) or {}
    video_after = getattr(mod, "VIDEO_AFTER", {}) or {}
    after = {str(k): (int(v[0]), str(v[1])) for k, v in after.items()}
    video_after = {int(k): {str(a): str(b) for a, b in v.items()}
                   for k, v in video_after.items()}
    return (after, {str(k): int(v) for k, v in move.items()},
            {str(x) for x in drop}, {str(k): str(v) for k, v in caption.items()},
            video_after)


def load_overlay():
    """content/figures_slide.py — auto-generated figures inserted after a matching block."""
    path = CONTENT / "figures_slide.py"
    if not path.exists():
        return {}
    spec = importlib.util.spec_from_file_location("figures_slide", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "SLIDE_FIGURES", {})


LEXICON = {
    # english slide term -> words that appear in this book (figures are usually
    # labelled in english while the chapters are persian)
    "bremsstrahlung": ["ترمزی", "برمشترالونگ"], "characteristic": ["مشخصه", "اختصاصی"],
    "anode": ["آند", "هدف"], "cathode": ["کاتد"], "filament": ["فیلامان", "رشته"],
    "tube": ["لامپ", "لوله"], "spectrum": ["طیف"], "filtration": ["فیلتر", "صافش"],
    "collimator": ["کولیماتور", "کولیماسیون"], "grid": ["گرید", "ضدپراکندگی"],
    "detector": ["آشکارساز", "دتکتور"], "screen": ["صفحه", "فلورسنت"],
    "fluoroscopy": ["فلوروسکوپی"], "radiography": ["رادیوگرافی"], "tomography": ["توموگرافی"],
    "hounsfield": ["هانسفیلد"], "mammography": ["ماموگرافی"], "angiography": ["آنژیوگرافی"],
    "contrast": ["کنتراست", "حاجب"], "barium": ["باریوم"], "iodine": ["ید"],
    "decay": ["واپاشی", "استحاله"], "half-life": ["نیمه‌عمر"], "activity": ["اکتیویته"],
    "generator": ["ژنراتور"], "annihilation": ["فنا", "محو"],
    "positron": ["پوزیترون"], "nuclide": ["نوکلید"], "gamma": ["گاما"],
    "dosimetry": ["دزیمتری"], "dosimeter": ["دزیمتر"], "dose": ["دوز"],
    "gray": ["گری"], "sievert": ["سیورت"], "becquerel": ["بکرل"], "curie": ["کوری"],
    "shielding": ["حفاظ", "حفاظت"], "apron": ["روپوش"], "gonad": ["گوناد"],
    "occupational": ["شغلی", "پرتوکار"], "pregnancy": ["باردار", "بارداری"],
    "ultrasound": ["اولتراسوند", "سونوگرافی", "فراصوت"], "sonography": ["سونوگرافی"],
    "piezoelectric": ["پیزوالکتریک"], "transducer": ["ترانسدیوسر", "پروب"],
    "impedance": ["امپدانس"], "reflection": ["بازتاب", "بازتابش"], "doppler": ["داپلر"],
    "mode": ["حالت", "مود"], "frequency": ["فرکانس", "بسامد"], "wavelength": ["طول موج"],
    "radiobiology": ["رادیوبیولوژی"], "chromosome": ["کروموزوم"], "chromatid": ["کروماتید"],
    "dna": ["دی‌ان‌ای", "دنا"], "cell": ["سلول"], "survival": ["بقا", "زنده‌مانی"],
    "apoptosis": ["اپوپتوز"], "necrosis": ["نکروز"], "stochastic": ["تصادفی", "احتمالی"],
    "deterministic": ["قطعی", "غیراحتمالی"], "syndrome": ["سندروم", "نشانگان"],
    "radical": ["رادیکال"], "hydrolysis": ["هیدرولیز"], "water": ["آب"],
    "mutation": ["جهش"], "aberration": ["ناهنجاری"], "dicentric": ["دی‌سنتریک"],
    "ring": ["حلقه"], "mitosis": ["میتوز"], "cycle": ["چرخه"],
    "relaxation": ["آسایش"], "spin": ["اسپین"], "precession": ["تقدیمی"],
    "gradient": ["گرادیان"], "magnetic": ["مغناطیس"], "resonance": ["تشدید"],
    "proton": ["پروتون"], "density": ["چگالی", "دنسیتی"], "weighted": ["وزن‌دار"],
    "hemorrhage": ["خون‌ریزی"], "tissue": ["بافت"], "signal": ["سیگنال"],
    "sensitivity": ["حساسیت"], "protection": ["حفاظت"], "alara": ["آلارا", "alara"],
    "exposure": ["اکسپوژر", "تابش‌گیری"], "patient": ["بیمار"], "staff": ["کارکنان", "پرسنل"],
}


def _expand(tokens: set[str]) -> set[str]:
    """add the persian words this book uses for english slide terms."""
    extra: set[str] = set()
    for t in tokens:
        for w in LEXICON.get(t, []):
            extra.add(w)
    return tokens | extra


def _tokens(text: str) -> set[str]:
    """significant words of a page text or a block (Persian/latin, 4+ chars)."""
    text = re.sub(r"\[\[|\]\]", "", text).lower()
    return {w for w in re.findall(r"[\w\u0600-\u06ff]{4,}", text)}


def apply_overlay(no: int, blocks: list[dict], overlay: dict,
                  fig_after: dict | None = None, fig_caption: dict | None = None) -> list[dict]:
    """Insert each overlay figure right after the block its source page talks about.

    The figure carries the *source page text* in `match`; the best block is the one
    sharing the most significant words with it (2+ words, and at least 6% of the
    page's vocabulary, so a single accidental word never wins).
    """
    figs = overlay.get(no) or []
    if not figs:
        return blocks
    out = list(blocks)
    fig_after = fig_after or {}
    for fig in figs:
        if any(b.get("file") == fig.get("file") for b in out):
            continue                       # idempotent
        needle = (fig.pop("match", "") or "").strip()
        cap_fix = (fig_caption or {}).get(str(fig.get("file")))
        if cap_fix:
            fig["caption"] = cap_fix
        manual = fig_after.get(str(fig.get("file")))
        if manual and manual[0] == no:
            idx = None
            for i, b in enumerate(out):
                if b.get("type") == "figure" or b.get("file"):
                    continue
                if manual[1] in json.dumps(b, ensure_ascii=False):
                    idx = i
                    break
            if idx is not None:
                entry = {k: v for k, v in fig.items()}
                entry.setdefault("type", "figure")
                j = idx + 1
                while j < len(out) and out[j].get("type") == "figure":
                    j += 1                 # گروه شکل‌های آن بخش را به هم نزن
                out.insert(j, entry)
                continue
        want = _expand(_tokens(needle))
        best, best_sc = None, 0.0
        if want:
            need = max(2, int(0.05 * len(want)))
            for i, b in enumerate(out):
                if b.get("type") in ("figure", "quickreview", "h2") or b.get("file"):
                    continue
                have = _expand(_tokens(json.dumps({k: v for k, v in b.items() if k != "type"},
                                                  ensure_ascii=False)))
                sc = len(want & have)
                if sc >= need and sc > best_sc:
                    best, best_sc = i, sc
        entry = {k: v for k, v in fig.items()}
        entry.setdefault("type", "figure")
        if best is not None:
            out.insert(best + 1, entry)
        else:
            # nothing matched: keep it in the chapter's source-figure appendix when the
            # module has one, else just before «مرور سریع»
            idx = None
            for i, b in enumerate(out):
                if b.get("type") == "h2" and "شکل‌های منبع" in (b.get("text") or ""):
                    idx = i + 1
            if idx is None:
                idx = next((i for i, b in enumerate(out) if b.get("type") == "quickreview"),
                           len(out))
            out.insert(idx, entry)
    return out

def _ahash(path: str, size: int = 16) -> str:
    """average hash of an image (lazy PIL import; empty string when unavailable)."""
    try:
        from PIL import Image
    except Exception:                      # pragma: no cover - pillow is present locally
        sys.stderr.write("warning: pillow missing — duplicate-figure check skipped\n")
        return ""
    try:
        im = Image.open(path).convert("L").resize((size, size))
        px = list(im.getdata())
    except Exception:
        return ""
    avg = sum(px) / len(px)
    return "".join("1" if v > avg else "0" for v in px)


def dedupe_figures(blocks: list[dict], threshold: int = 10) -> tuple[list[dict], int]:
    """Drop auto slide crops whose picture already exists as a curated figure.

    The curated ``figNN_*`` images come from the same slide decks; when a slide crop
    and a curated figure are the same picture (average-hash distance <= threshold),
    the slide crop is redundant and is removed.  Only ``slide*`` files are dropped,
    never curated ones, and only against figures of the *same chapter*.
    """
    import os as _os
    idx = [i for i, b in enumerate(blocks) if b.get("type") == "figure"]
    hashes = {i: _ahash(blocks[i].get("file", "")) for i in idx}
    drop = set()
    for i in idx:
        h = hashes.get(i) or ""
        name = _os.path.basename(blocks[i].get("file", ""))
        if not h or not name.startswith("slide"):
            continue
        for j in idx:
            if j == i or j in drop or not hashes.get(j):
                continue
            other = _os.path.basename(blocks[j].get("file", ""))
            if other.startswith("slide"):
                continue                   # slide-vs-slide was deduped when cropping
            d = sum(1 for x, y in zip(h, hashes[j]) if x != y)
            if d <= threshold:
                drop.add(i)
                break
    if not drop:
        return blocks, 0
    return [b for k, b in enumerate(blocks) if k not in drop], len(drop)

def figures_after_text(blocks: list[dict]) -> tuple[list[dict], int]:
    """شکل‌ها نباید بلافاصله بعد از سرفصل بیایند.

    دانشجو اول باید متن بخش را بخواند و بعد شکل را ببیند؛ اگر شکل بلافاصله بعد
    از یک سرفصل افتاده باشد، به بعد از نخستین بلوک توضیحی همان بخش منتقل می‌شود.
    بخش «شکل‌های منبع» از این قاعده مستثناست (گالری شکل است و ترتیب ندارد).
    """
    out = list(blocks)
    moved = 0
    i = 0
    while i < len(out):
        if out[i].get("type") != "figure":
            i += 1
            continue
        # سر سرفصلِ بخش؟
        j = i - 1
        while j >= 0 and out[j].get("type") == "figure":
            j -= 1
        if j < 0 or out[j].get("type") not in ("h2", "h3"):
            i += 1
            continue
        if "شکل‌های منبع" in (out[j].get("text") or ""):
            i += 1
            continue
        # طول ران شکل‌ها
        k = i
        while k < len(out) and out[k].get("type") == "figure":
            k += 1
        run = out[i:k]
        rest = out[k:]
        # نخستین بلوک توضیحی پس از شکل‌ها
        t = 0
        while t < len(rest) and rest[t].get("type") in ("h2", "h3", "figure"):
            t += 1
        if t >= len(rest):
            i = k
            continue
        out = out[:i] + rest[:t + 1] + run + rest[t + 1:]
        moved += len(run)
        i += t + len(run) + 1
    return out, moved


def normalise_captions(blocks: list[dict]) -> int:
    """شماره‌های شکل که از خودِ منبع آمده‌اند را روشن کن.

    شرح‌هایی مثل «شکل ۵ — ...» در واقع شماره شکل در کتاب/اسلاید منبع‌اند؛ چون
    جزوه شکل‌های خودش را شماره نمی‌زند، این عدد وهم‌انگیز است. آن‌ها را به
    «شکل منبع ۵ — ...» تبدیل می‌کنیم تا مرجع‌بودنشان روشن بماند.
    """
    n = 0
    for b in blocks:
        if b.get("type") != "figure":
            continue
        cap = b.get("caption") or ""
        m = re.match(r"^\s*شکل\s*([۰-۹0-9]+)\s*[—–-]\s*", cap)
        if m:
            b["caption"] = "شکل منبع " + m.group(1) + " — " + cap[m.end():]
            n += 1
    return n


def relocate_figures(no: int, blocks: list[dict], fig_after: dict) -> tuple[list[dict], int]:
    """شکل‌هایی که در فایل محتوا جای نامناسبی دارند را کنار بلوک مرجعشان می‌برد.

    هر ورودی FIG_AFTER: file -> (chapter, anchor). اگر شکل در آن فصل باشد ولی
    بی‌واسطه بعد از بلوک حاوی لنگر نباشد، برداشته و آنجا درج می‌شود (پس از
    هر شکل‌های همان گروه تا ترتیب شکل‌ها به‌هم نریزد).
    """
    moves = {f: a for f, a in (fig_after or {}).items() if a and a[0] == no}
    if not moves:
        return blocks, 0
    out = list(blocks)
    moved = 0
    for fname, (_ch, anchor) in sorted(moves.items()):
        cur = next((i for i, b in enumerate(out)
                    if b.get("type") == "figure" and str(b.get("file")) == fname), None)
        if cur is None:
            continue
        tgt = None
        for i, b in enumerate(out):
            if b.get("type") == "figure":
                continue
            if anchor in json.dumps(b, ensure_ascii=False):
                tgt = i
                break
        if tgt is None:
            continue
        # already sitting in the figure run just after the anchor?
        j = tgt + 1
        run = []
        while j < len(out) and out[j].get("type") == "figure":
            run.append(j)
            j += 1
        if cur in run:
            continue
        entry = out.pop(cur)
        if cur < tgt:
            tgt -= 1
        j = tgt + 1
        while j < len(out) and out[j].get("type") == "figure":
            j += 1
        out.insert(j, entry)
        moved += 1
    return out, moved


def relocate_video(no: int, blocks: list[dict], video_after: dict) -> tuple[list[dict], int]:
    """بلوک ویدیویی را از ته فصل به کنار بلوک مرجعش می‌برد.

    کلید هر ورودی بخشی از ``src`` بلوک ویدیویی است و مقدار، متنی از بلوک مقصد.
    """
    moves = (video_after or {}).get(no) or {}
    if not moves:
        return blocks, 0
    out = list(blocks)
    moved = 0
    for key, anchor_txt in moves.items():
        cur = next((i for i, b in enumerate(out) if key in (b.get("src") or "")), None)
        if cur is None:
            continue
        tgt = None
        for i, b in enumerate(out):
            if i == cur or b.get("type") == "figure":
                continue
            if anchor_txt in json.dumps(b, ensure_ascii=False):
                tgt = i
                break
        if tgt is None:
            continue
        if cur == tgt + 1:                      # همین حالا کنار لنگر است
            continue
        j = tgt + 1
        run = []
        while j < len(out) and out[j].get("type") == "figure":
            run.append(j)
            j += 1
        if cur in run:                          # در گروه شکل‌های همان بلوک است
            continue
        entry = out.pop(cur)
        if cur < tgt:
            tgt -= 1
        j = tgt + 1
        while j < len(out) and out[j].get("type") == "figure":
            j += 1
        out.insert(j, entry)
        moved += 1
    return out, moved


def quickreview_last(blocks: list[dict]) -> tuple[list[dict], int]:
    """«مرور سریع» را به انتهای محتوای فصل (قبل از گالری شکل‌های منبع) می‌برد."""
    out = list(blocks)
    idx = next((i for i, b in enumerate(out) if b.get("type") == "quickreview"), None)
    if idx is None:
        return out, 0
    target = next((i for i, b in enumerate(out)
                   if b.get("type") == "h2" and "شکل‌های منبع" in (b.get("text") or "")), len(out))
    if idx + 1 >= target:
        return out, 0
    entry = out.pop(idx)
    if idx < target:
        target -= 1
    out.insert(target, entry)
    return out, 1


def drop_empty_sections(blocks: list[dict]) -> tuple[list[dict], int]:
    """سرفصل‌هایی که پس از انتقال شکل‌ها خالی مانده‌اند را حذف می‌کند."""
    out = list(blocks)
    heads = [i for i, b in enumerate(out) if b.get("type") == "h2"]
    removed = 0
    for k in range(len(heads) - 1, -1, -1):
        i = heads[k]
        j = heads[k + 1] if k + 1 < len(heads) else len(out)
        if not any(b.get("type") not in ("h2", "h3") for b in out[i + 1:j]):
            del out[i]
            removed += 1
    return out, removed


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
    overlay = load_overlay()
    fig_after, fig_move, fig_drop, fig_caption, video_after = load_fig_place()
    if fig_move:
        lookup = {}
        for ch_no, entries in overlay.items():
            for entry in entries:
                lookup[str(entry.get("file"))] = ch_no
        for fname, target in fig_move.items():
            src = lookup.get(fname)
            if src is None or src == target:
                continue
            entry = next((e for e in overlay.get(src, []) if str(e.get("file")) == fname), None)
            if entry is None:
                continue
            overlay[src].remove(entry)
            overlay.setdefault(target, []).append(entry)
    if fig_drop:
        # شکل‌هایی که عیناً جای دیگری چاپ شده‌اند یا اسلاید عنوان/فهرست‌اند
        for ch_no in list(overlay):
            overlay[ch_no] = [e for e in overlay[ch_no]
                              if str(e.get("file")) not in fig_drop]
    video_extra = load_video_extra()
    for no, meta in CHAPTERS.items():
        if only and no not in only:
            continue
        mod = load_module(meta["module"])
        if mod is None:
            print(f"ch{no:02d}: module missing ({meta['module']})")
            continue
        blocks = apply_overlay(no, list(mod.BLOCKS), overlay, fig_after, fig_caption)
        if fig_drop:
            blocks = [b for b in blocks if str(b.get("file")) not in fig_drop]
            for b in blocks:
                if b.get("type") == "figure":
                    fix = fig_caption.get(str(b.get("file")))
                    if fix:
                        b["caption"] = fix
        blocks = apply_video_extra(no, blocks, video_extra)
        blocks, vid_moved = relocate_video(no, blocks, video_after)
        blocks, qr_moved = quickreview_last(blocks)
        normalise_captions(blocks)
        blocks, relocated = relocate_figures(no, blocks, fig_after)
        blocks, detached = figures_after_text(blocks)
        blocks, dropped_figs = dedupe_figures(blocks)
        blocks, empty_sections = drop_empty_sections(blocks)
        ch = {"no": no, "session": meta["session"], "title": meta["title"],
              "prof": meta["prof"], "icon": meta["icon"], "blocks": blocks}
        if meta.get("exam_flag"):
            ch["exam_flag"] = meta["exam_flag"]
        (LOCK / f"ch{no:02d}.json").write_text(
            json.dumps(ch, ensure_ascii=False, indent=1), encoding="utf-8")
        src = sum(1 for b in ch["blocks"] if b.get("src"))
        figs = sum(1 for b in ch["blocks"] if b.get("type") == "figure")
        notes = []
        if relocated:
            notes.append(f"{relocated} شکل جابه‌جا")
        if vid_moved:
            notes.append(f"{vid_moved} بلوک ویدیویی جابه‌جا")
        if qr_moved:
            notes.append("مرور سریع به پایان")
        if detached:
            notes.append(f"{detached} شکل پس از متن")
        if dropped_figs:
            notes.append(f"{dropped_figs} تکراری حذف شد")
        if empty_sections:
            notes.append(f"{empty_sections} سرفصل خالی حذف شد")
        extra = (", " + "، ".join(notes)) if notes else ""
        print(f"ch{no:02d}: {len(ch['blocks'])} blocks, {figs} figures, {src} with src{extra}")
        built += 1
    print("built", built)
    return 0


if __name__ == "__main__":
    sys.exit(main())
