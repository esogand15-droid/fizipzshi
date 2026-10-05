# -*- coding: utf-8 -*-
"""HumsYar — «جزوه جامع فیزیک پزشکی» PDF renderer.

Renders the locked chapter JSONs (lock/chNN.json) into a single A4 PDF with the
HumsYar visual language (WeasyPrint, RTL, embedded Vazirmatn).

usage:  python3 render/render.py [out.pdf]
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
FONT_DIR = ROOT / "fonts"
LOCK = ROOT / "lock"
CSS_FILE = BASE / "style.css"
BOOK = "فیزیک پزشکی"
BRAND = "HumsYar"

FA = "۰۱۲۳۴۵۶۷۸۹"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def esc(s) -> str:
    return html.escape(str(s), quote=False)


def fa_digits(s: str) -> str:
    return str(s).translate(str.maketrans("0123456789", FA))


def LTR_DIGITS(text: str) -> str:
    """Persian digits outside [[...]] islands; islands go through `island()`.

    Routing islands through the same helper the body text uses keeps the digit
    style identical everywhere (captions, «منبع:» lines and bold runs included),
    so a quantity never appears as ``0.25 mm`` on one line and «۰.۲۵ میلی‌متر» on
    the next.
    """
    parts = re.split(r"(\[\[.*?\]\])", str(text))
    out = []
    for i, p in enumerate(parts):
        if i % 2 == 1:  # LTR island
            out.append(island(p[2:-2]))
        else:
            out.append(fa_digits(esc(p)))
    return "".join(out)


FA_CHARS = re.compile(r"[\u0600-\u06FF]")
_LATIN_TOK = re.compile(r"[A-Za-z0-9]")


def _island_chunks(inner: str) -> list[tuple[str, str]]:
    """Split island content into (kind, text) pieces: 'fa' | 'num' | 'ltr' | 'neu'."""
    out: list[tuple[str, str]] = []
    for tok in re.findall(r"\S+\s*|\s+", inner):
        if FA_CHARS.search(tok):
            kind = "fa"
        elif re.search(r"[\^_\\]", tok) or re.search(r"[A-Za-z]", tok):
            kind = "ltr"           # Latin word or math token: keep in an LTR span
        elif _LATIN_TOK.search(tok):
            kind = "num"           # bare number: Persian digits, RTL flow
        else:
            kind = "neu"
        if out and (kind == "neu" or out[-1][0] == kind):
            out[-1] = (out[-1][0], out[-1][1] + tok)
        else:
            out.append((kind, tok))
    return out


# A plain number (optionally grouped/decimal) and a bare unit symbol.
_NUMBER = r"[0-9]+(?:[.,\u066B][0-9]+)*"
# «۱۱×۱۱»، «۱.۷۰ / ۰.۰۰۰۴»، «۰.۲۴/۳»: an expression built only from digits and
# arithmetic separators — no Latin letter, so nothing of it is an identifier.
_NUM_EXPR = re.compile(r"^[0-9\s.,\u066B/×÷−–—+%:]+$")
# «0.25 mm»، «1.022 MeV»، «1540 m/s»: one number, one space, one unit symbol.
_NUM_UNIT = re.compile(rf"^({_NUMBER})\s+([A-Za-z\u00b5\u03bc\u03a9\u00b0]"
                       r"[A-Za-z\u00b5\u03bc\u03a9\u00b00-9/\u00b7]{0,8})$")


def quantity(inner: str) -> str | None:
    """Render «عدد» / «عدد + یکا» with Persian digits, as one unbreakable run.

    The book writes every number of the running text in Persian digits — that is
    what a mixed island such as ``[[2.5 سانتی‌متر]]`` already produced. A Latin-only
    island used to escape that rule and printed ``2.5`` next to «۲.۵» in the very
    same sentence (``11×11`` beside «۱۷×۱۷», ``100 mrad`` beside «۲.۵ سانتی‌متر»).
    Pure quantities now follow the same rule; formulas, element/isotope symbols
    and anything holding a Latin identifier (``A = 87``, ``U-238 → Th-234``,
    ``100 × R``) are left untouched as LTR math.
    """
    t = str(inner).strip()
    if not t or not re.search(r"[0-9]", t):
        return None
    if _NUM_EXPR.match(t):
        return '<span class="qty">' + fa_digits(esc(t)) + "</span>"
    m = _NUM_UNIT.match(t)
    if m:
        return ('<span class="qty">' + fa_digits(esc(m.group(1))) + "\u00a0"
                + '<span dir="ltr">' + esc(m.group(2)) + "</span></span>")
    return None


def island(inner: str) -> str:
    """[[...]] island → bidi-correct HTML.

    Latin-only islands stay a single LTR span, so unit strings such as ``mSv/h``
    or formulas such as ``A = 87`` never split. When an island mixes Persian words
    with numbers or Latin units (``5 سانتی‌متر``, ``2 تا 5 مگاهرتز``), the pieces are
    emitted in logical order inside the surrounding RTL flow — wrapping the whole
    island in ``dir="ltr"`` used to render the number *before* its unit word when
    read right-to-left (``سانتی‌متر 5``). A Latin-only island that is just a number
    (with or without a unit symbol) is handled by `quantity()` so the digit style
    stays the same across the whole book.
    """
    chunks = _island_chunks(inner)
    if not any(k == "fa" for k, _ in chunks):
        q = quantity(inner)
        if q is not None:
            return q
        return '<span dir="ltr">' + mathml_like(inner) + "</span>"
    out = []
    for idx, (kind, tok) in enumerate(chunks):
        nxt = chunks[idx + 1][0] if idx + 1 < len(chunks) else None
        if kind in ("fa", "num"):
            piece = fa_digits(esc(tok))
            if kind == "num" and nxt in ("fa", "ltr"):
                # «۵ سانتی‌متر» / «۸ mSv/h»: a number must never be left at the end
                # of a line with its unit pushed to the next one.
                piece = re.sub(r"[ \t]+$", "\u00a0", piece)
            out.append(piece)
        elif kind == "ltr":
            out.append('<span dir="ltr">' + mathml_like(tok) + "</span>")
        else:
            out.append(esc(tok))
    return "".join(out)


def inline(text: str) -> str:
    """Mini markup: **bold**, [[ltr]] islands, Persian digits elsewhere."""
    chunks = re.split(r"(\[\[.*?\]\]|\*\*.*?\*\*)", str(text))
    out = []
    for c in chunks:
        if c.startswith("[[") and c.endswith("]]"):
            out.append(island(c[2:-2]))
        elif c.startswith("**") and c.endswith("**"):
            out.append("<b>" + LTR_DIGITS(c[2:-2]) + "</b>")
        else:
            out.append(LTR_DIGITS(c))
    return "".join(out)


def frac(num: str, den: str) -> str:
    """num/den arrive already rendered (see mathml_like)."""
    return (f'<span class="frac"><span class="fn"><span>{num}</span></span>'
            f'<span class="fd"><span>{den}</span></span></span>')


SYMS = {
    "rightarrow": "\u27f6", "to": "\u2192", "leftarrow": "\u2190", "leftrightarrow": "\u2194",
    "times": "\u00d7", "cdot": "\u00b7", "propto": "\u221d", "approx": "\u2248", "neq": "\u2260",
    "leq": "\u2264", "geq": "\u2265", "pm": "\u00b1", "mp": "\u2213", "infty": "\u221e",
    "circ": "\u00b0", "degree": "\u00b0", "sim": "\u223c", "sum": "\u03a3", "partial": "\u2202",
    "int": "\u222b", "sqrt": "\u221a", "alpha": "\u03b1", "beta": "\u03b2", "gamma": "\u03b3",
    "lambda": "\u03bb", "mu": "\u03bc", "nu": "\u03bd", "omega": "\u03c9", "pi": "\u03c0",
    "sigma": "\u03c3", "theta": "\u03b8", "Delta": "\u0394", "rho": "\u03c1", "phi": "\u03c6",
    "tau": "\u03c4", "eta": "\u03b7", "kappa": "\u03ba", "psi": "\u03c8", "zeta": "\u03b6",
    "epsilon": "\u03b5", "chi": "\u03c7", "Omega": "\u03a9", "Sigma": "\u03a3", "Phi": "\u03a6",
    "quad": " ", "qquad": "  ", "space": " ", "langle": "\u27e8", "rangle": "\u27e9",
}

# spacing commands: backslash followed by one of these characters
SPACE_CMDS = {" ": " ", ",": " ", ";": " ", ":": " ", "!": ""}


def _group(s: str, i: int) -> tuple[str, int]:
    """Read a balanced {...} group that starts at s[i]; returns (inner, next index)."""
    depth, j = 0, i
    while j < len(s):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    return s[i + 1:], len(s)


def mathml_like(tex: str, _depth: int = 0) -> str:
    """Small formula renderer: \\frac{}{}, ^{}, _{}, \\bar{}, greek/symbol shortcuts.

    Groups are parsed with a real brace matcher and sub-parts are rendered
    recursively, so nested cases such as \\frac{1}{T_{eff}} no longer leak raw LaTeX
    into the PDF (the previous flat regexes silently failed on them).
    """
    s = str(tex)
    out: list[str] = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch == "\\" and i + 1 < n and s[i + 1] in SPACE_CMDS:
            out.append(SPACE_CMDS[s[i + 1]])
            i += 2
            continue
        if ch == "\\":
            m = re.match(r"\\([A-Za-z]+)", s[i:])
            if m:
                cmd = m.group(1)
                i += 1 + len(cmd)
                nxt = s[i] if i < n else ""
                if cmd in ("frac", "dfrac", "tfrac") and nxt == "{":
                    a, i = _group(s, i)
                    b = ""
                    if i < n and s[i] == "{":
                        b, i = _group(s, i)
                    out.append(frac(mathml_like(a, _depth + 1), mathml_like(b, _depth + 1)))
                elif cmd in ("bar", "hat", "vec", "dot", "tilde") and nxt == "{":
                    g, i = _group(s, i)
                    out.append(f'<span class="acc">{mathml_like(g, _depth + 1)}</span>')
                elif cmd in ("text", "mathrm", "mathit", "operatorname") and nxt == "{":
                    g, i = _group(s, i)
                    out.append(esc(g))
                elif cmd == "sqrt":
                    if nxt == "{":
                        g, i = _group(s, i)
                    else:
                        g = s[i] if i < n else ""
                        i += 1
                    out.append("\u221a(" + mathml_like(g, _depth + 1) + ")")
                elif cmd in SYMS:
                    out.append(SYMS[cmd])
                elif cmd in ("left", "right", "big", "Big", "bigg", "Bigg", "bigl", "bigr",
                             "Bigl", "Bigr", "displaystyle", "textstyle", "nolimits", "limits"):
                    pass                     # sizing/delimiter hints: drop, keep the bracket
                else:
                    out.append(cmd)          # unknown command: keep it readable
                continue
            i += 1
            continue
        if s.startswith("{}", i):
            i += 2                            # empty group that carries the scripts
            continue
        if ch in "^_":
            i += 1
            if i < n and s[i] == "{":
                g, i = _group(s, i)
            else:
                # `c^2`, `10^-10`, `10^-4`, `2m_ec^2`, `e^-`: take the sign+number
                # run when there is one, else a single letter — the old one-char
                # rule turned `10^-4` into `10^{-}4`.
                m = re.match(r"-?\d+(?:[.,]\d+)?|[A-Za-z]|[+\-]", s[i:])
                g = m.group(0) if m else ""
                i += len(g)
            tag = "sup" if ch == "^" else "sub"
            out.append(f"<{tag}>{mathml_like(g, _depth + 1)}</{tag}>")
            continue
        out.append(esc(ch) if ch in "<>&" else ch)
        i += 1
    return "".join(out)


def icon_svg(kind: str, size: int = 76, stroke: str = "#5eead4", sw: float = 3) -> str:
    c = (f'fill="none" stroke="{stroke}" stroke-width="{sw}" '
         f'stroke-linecap="round" stroke-linejoin="round"')
    P = {
        "radiation": f'<circle cx="36" cy="36" r="6" {c}/>'
                     f'<path d="M36 30 L36 12 M31 39 L15 48 M41 39 L57 48" {c}/>'
                     f'<circle cx="36" cy="36" r="26" {c} stroke-dasharray="3 5"/>',
        "atom": f'<circle cx="36" cy="36" r="5" {c}/>'
                f'<ellipse cx="36" cy="36" rx="26" ry="11" {c}/>'
                f'<ellipse cx="36" cy="36" rx="26" ry="11" transform="rotate(60 36 36)" {c}/>'
                f'<ellipse cx="36" cy="36" rx="26" ry="11" transform="rotate(120 36 36)" {c}/>',
        "tube": f'<rect x="12" y="28" width="48" height="18" rx="6" {c}/>'
                f'<path d="M60 37 h8 M12 37 h-6 M24 28 v-8 M48 28 v-8" {c}/>'
                f'<path d="M30 37 l6 -4 v8 z" {c}/>',
        "skull": f'<path d="M22 50 v-12 a14 14 0 0 1 28 0 v12 z" {c}/>'
                 f'<circle cx="30" cy="34" r="3.5" {c}/><circle cx="42" cy="34" r="3.5" {c}/>'
                 f'<path d="M32 52 v6 M40 52 v6" {c}/>',
        "wave": f'<path d="M8 36 q7 -16 14 0 t14 0 t14 0 t14 0" {c}/>'
                f'<path d="M8 48 h56" {c} stroke-dasharray="4 5"/>',
        "magnet": f'<path d="M20 52 a16 16 0 0 1 32 0" {c}/><path d="M20 52 v-12 M52 52 v-12" {c}/>'
                  f'<path d="M14 52 h12 M46 52 h12" {c}/><path d="M28 22 h16 M28 28 h16" {c}/>',
        "shield": f'<path d="M36 10 L58 20 v18 c0 14 -10 22 -22 26 c-12 -4 -22 -12 -22 -26 V20 Z" {c}/>'
                  f'<path d="M28 36 l6 6 l12 -14" {c}/>',
        "dose": f'<rect x="14" y="22" width="44" height="30" rx="5" {c}/>'
                f'<path d="M24 38 h8 M44 38 h8 M36 30 v16" {c}/>',
        "chart": f'<path d="M12 56 h52 M12 56 V14" {c}/>'
                 f'<path d="M20 48 q10 -22 20 -14 q8 6 20 -18" {c}/>',
    }
    body = P.get(kind, P["radiation"])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 72 72">{body}</svg>')


# --------------------------------------------------------------------------- #
# block renderers
# --------------------------------------------------------------------------- #
def src_line(src: str | None) -> str:
    if not src:
        return ""
    return f'<div class="src">منبع: {LTR_DIGITS(src)}</div>'


def blk_h3(b: dict) -> str:
    return (f'<div class="subhead3"><span class="st3">{inline(b.get("text",""))}</span></div>'
            + src_line(b.get("src")))


def blk_h2(b: dict) -> str:
    flag = ""
    kind = b.get("flag")
    if kind == "exam":
        flag = '<span class="flag badge-exam">در امتحان می‌آید</span>'
    elif kind == "nonexam":
        flag = '<span class="flag badge-nonexam">خارج از حذفیات امتحان — مطالعه تکمیلی</span>'
    anchor = ""
    if b.get("anchor"):
        anchor = f'<a id="{esc(b["anchor"])}"></a>'
        idx = ANCHOR_MARK.get(b["anchor"])
        if idx is not None:
            anchor += f'<span class="marker">JZG{idx:02d}MARK</span>'""
    return (f'{anchor}<div class="subhead"><span class="sd"></span>'
            f'<span class="st">{inline(b.get("text",""))}</span>{flag}<span class="sl"></span></div>')


def blk_p(b: dict) -> str:
    return f'<p class="tx">{inline(b.get("text",""))}</p>' + src_line(b.get("src"))


def blk_bullets(b: dict) -> str:
    items = "".join(f"<li>{inline(i)}</li>" for i in b.get("items", []))
    return f'<ul class="bl">{items}</ul>' + src_line(b.get("src"))


def blk_table(b: dict) -> str:
    head = b.get("head") or []
    rows = b.get("rows") or []
    th = "".join(f"<th>{inline(h)}</th>" for h in head)
    trs = []
    for r in rows:
        tds = "".join(f"<td>{inline(c)}</td>" for c in r)
        trs.append(f"<tr>{tds}</tr>")
    cap = f'<div class="cap">{inline(b["caption"])}</div>' if b.get("caption") else ""
    # Long tables may run over a page boundary (the header row repeats); short
    # ones are kept whole. Forcing every table to stay on one page is what left
    # half-empty pages behind — the table jumped over, the text stayed put.
    cls = "ftable long" if len(rows) >= 5 else "ftable"
    return (f'<div class="{cls}"><table class="dt"><thead><tr>{th}</tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table>{cap}</div>' + src_line(b.get("src")))


def blk_formula(b: dict) -> str:
    fx = mathml_like(b.get("tex", ""))
    legend = b.get("legend") or []
    leg = "".join(f"<div>{inline(x)}</div>" for x in legend)
    name = f'<div class="fleg"><b>{inline(b["name"])}</b></div>' if b.get("name") else ""
    return (f'<div class="fbox"><div class="fx">{fx}</div>{name}'
            f'<div class="fleg">{leg}</div></div>' + src_line(b.get("src")))


# A4 (210mm) minus the @page side margins (11mm each) minus .chbody padding (2mm
# each) minus the .card img padding (3mm each) — the usable picture width.
COL_MM = 210.0 - 2 * 11.0 - 2 * 2.0 - 2 * 3.0
# Printed height cap for a single figure. Without it a portrait scan at width 86%
# can be ~180mm tall; together with its caption it eats a whole page and leaves the
# previous page a fifth empty, which is the "fragmented layout" complaint.
FIG_MAX_MM = 112.0


def _fig_width(path: str, want: str) -> str:
    """Shrink a figure's width so its printed height stays under `FIG_MAX_MM`."""
    if not want.endswith("%"):
        return want
    try:
        from PIL import Image  # optional: only used to read the aspect ratio
        with Image.open(path) as im:
            px_w, px_h = im.size
    except Exception:
        return want
    if px_w <= 0 or px_h <= 0:
        return want
    pct = float(want[:-1])
    if COL_MM * pct / 100.0 * px_h / px_w <= FIG_MAX_MM:
        return want
    capped = FIG_MAX_MM * px_w / px_h / COL_MM * 100.0
    return f"{max(40.0, min(pct, capped)):.1f}%"


# --- page-fill state (see fit_figures() in main) ----------------------------- #
# FIG_SEQ counts the figures of one build_html() pass so every figure gets a
# stable id; FIG_SCALE holds the shrink factor the fitting pass decided for it.
FIG_SEQ = 0
FIG_SCALE: dict[int, float] = {}


def blk_figure(b: dict) -> str:
    global FIG_SEQ
    f = b.get("file", "")
    path = f if os.path.isabs(f) else str(ROOT / f)
    if not Path(path).exists():
        return f'<div class="fnote">شکل در دسترس نیست: {esc(f)}</div>'
    fid = FIG_SEQ
    FIG_SEQ += 1
    cap = inline(b.get("caption", ""))
    cs = f'<span class="csrc">{LTR_DIGITS(b.get("src",""))}</span>' if b.get("src") else ""
    w = _fig_width(path, b.get("width") or "86%")
    scale = FIG_SCALE.get(fid, 1.0)
    if scale < 1.0 and w.endswith("%"):
        w = f"{max(26.0, float(w[:-1]) * scale):.1f}%"
    return (f'<div class="card"><span class="marker">JZF{fid:03d}MARK</span>'
            f'<img src="{path}" style="width:{w}"/>'
            f'<div class="cap">{cap}{cs}</div></div>')


def blk_key(b: dict) -> str:
    return f'<div class="key"><b>نکته کلیدی: </b>{inline(b.get("text",""))}</div>'


def blk_examtip(b: dict) -> str:
    return f'<div class="examtip"><b>نکته امتحانی: </b>{inline(b.get("text",""))}</div>'




def blk_note(b: dict) -> str:
    return f'<div class="fnote">{inline(b.get("text",""))}</div>'


def blk_review(b: dict) -> str:
    items = "".join(f"<li>{inline(i)}</li>" for i in b.get("items", []))
    return f'<div class="review"><h3>مرور سریع</h3><ul>{items}</ul></div>'


RENDER = {
    "h2": blk_h2, "h3": blk_h3, "p": blk_p, "bullets": blk_bullets, "table": blk_table,
    "formula": blk_formula, "figure": blk_figure, "key": blk_key,
    "examtip": blk_examtip, "note": blk_note,
    "quickreview": blk_review,
}


ANCHOR_MARK: dict[str, int] = {}


def render_blocks(blocks: list[dict]) -> str:
    out = []
    for b in blocks:
        fn = RENDER.get(b.get("type", ""))
        if fn is None:
            print("!! unknown block type:", b.get("type"))
            continue
        out.append(fn(b))
    return "".join(out)


# --------------------------------------------------------------------------- #
# document assembly
# --------------------------------------------------------------------------- #
def load_chapters() -> list[dict]:
    chs = []
    for p in sorted(LOCK.glob("ch*.json")):
        chs.append(json.loads(p.read_text(encoding="utf-8")))
    return sorted(chs, key=lambda c: c["no"])


def css() -> str:
    return CSS_FILE.read_text(encoding="utf-8").replace("__FONTS__", str(FONT_DIR))


def cover_html(total_pages: str, n_ch: int, n_fig: int) -> str:
    return f"""
<div class="cover">
  <div class="wordmark">
    <div class="wm1">{BRAND}</div>
    <div class="wm2">H U M S &nbsp; Y A R</div>
    <div class="wm3">آموزش پزشکی</div>
  </div>
  <div class="rule"></div>
  <div class="kicker">جزوه جامع امتحانی</div>
  <h1>جزوه جامع فیزیک پزشکی</h1>
  <div class="subtitle">تلفیق جزوه‌ها، پاورپوینت‌ها و ویدیوهای اساتید</div>
  <div class="ref">دکتر افضلی‌پور &nbsp;·&nbsp; دکتر لیلی درویش &nbsp;·&nbsp; دکتر حق‌پرست</div>
  <table class="stats"><tr>
    <td class="stat"><span class="num">{fa_digits(total_pages)}</span><span class="lbl">صفحه</span></td>
    <td class="stat"><span class="num">{fa_digits(n_ch)}</span><span class="lbl">فصل / جلسه</span></td>
    <td class="stat"><span class="num">{fa_digits(n_fig)}</span><span class="lbl">شکل</span></td>
  </tr></table>
  <div class="foot">جزوه‌ای برای مرور دو روزه پیش از امتحان — همه مطالب با ذکر منبع، مطابق جزوه، اسلاید و ویدیوی همان جلسه</div>
</div>"""


def toc_html(chapters: list[dict], pages: dict[int, tuple[int, int]]) -> str:
    rows = []
    for ch in chapters:
        pg = pages.get(ch["no"])
        rng = f"صفحه {fa_digits(pg[0])} تا {fa_digits(pg[1])}" if pg else ""
        badge = ""
        if ch.get("exam_flag") == "exam":
            badge = '<span class="badge-exam">امتحانی — دکتر درویش</span>'
        elif ch.get("exam_flag") == "nonexam":
            badge = '<span class="badge-nonexam">مطالب دکتر درویش خارج از حذفیات امتحان</span>'
        rows.append(f"""<div class="row">
      <span class="nbadge">{fa_digits(ch['no'])}</span>
      <span class="ttl">{inline(ch['title'])} {badge}<small>{inline(ch.get('prof',''))}</small></span>
      <span class="rng">{rng}</span></div>""")
    return f'<div class="toc"><h2>فهرست مباحث</h2><div class="tline"></div>{"".join(rows)}</div>'


def guide_html(rows: list[dict]) -> str:
    ths = "".join(f"<th>{inline(h)}</th>" for h in
                  ["مبحث امتحانی", "فصل / جلسه", "صفحه‌های همین PDF", "منبع اصلی (فایل، اسلاید/صفحه، زمان ویدیو)"])
    trs = []
    for r in rows:
        pg = r.get("pages")
        if pg and pg[0] != pg[1]:
            label = f'صفحه {fa_digits(pg[0])} تا {fa_digits(pg[1])}'
        elif pg:
            label = f'صفحه {fa_digits(pg[0])}'
        else:
            label = '—'
        pgcell = (f'<a href="#{esc(r["anchors"][0])}"><span class="pgpill">{label}</span></a>')
        trs.append(f"<tr><td>{inline(r['topic'])}</td><td>{inline(r['where'])}</td>"
                   f"<td>{pgcell}</td><td>{inline(r['source'])}</td></tr>")
    return f"""<div class="guide">
  <h2>راهنمای مطالعه: دکتر درویش</h2>
  <div class="lead">استاد اعلام کرده‌اند فقط مباحث زیر در امتحان می‌آید؛ بقیه مطالب ایشان در این جزوه
  به‌صورت کامل آمده است ولی در امتحان نیست. در سرتیتر بخش‌های امتحانی، نشان
  «در امتحان می‌آید» و در بخش‌های دیگر مطالب ایشان نشان خاکستری «خارج از حذفیات امتحان — برای مطالعه تکمیلی»
  درج شده است.</div>
  <table class="gt"><thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table>

  <div class="key" style="margin-top:7mm"><b>ترتیب پیشنهادی مرور دو روزه: </b>
  ابتدا سه مبحث امتحانی بالا را از فصل‌های ۸ و ۹ بخوانید، سپس «مرور سریع» پایان هر فصل و در آخر
  جدول‌های جمع‌بندی و فرمول‌های کلیدی را دوره کنید.</div>
</div>"""


def section_cover(ch: dict, i: int, n: int, pages: tuple[int, int] | None) -> str:
    n_blocks = len(ch["blocks"])
    n_fig = sum(1 for b in ch["blocks"] if b.get("type") == "figure")
    n_tab = sum(1 for b in ch["blocks"] if b.get("type") == "table")
    # pages[0] is the section-cover page itself; content starts on the next page
    # (same convention as the TOC and the Darvish study guide).
    if pages and pages[1] > pages[0]:
        rng = f"صفحه‌های {fa_digits(pages[0] + 1)} تا {fa_digits(pages[1])}"
    elif pages:
        rng = f"صفحه {fa_digits(pages[0])}"
    else:
        rng = ""
    return f"""
<div class="seccover"><div class="seccover-inner">
  <span class="marker">JZC{ch['no']:02d}MARK</span>
  <span class="pill">فصل {fa_digits(i)} از {fa_digits(n)}</span>
  <table class="icnt"><tr><td class="icn">{icon_svg(ch.get('icon','radiation'))}</td></tr></table>
  <div class="sess">{inline(ch.get('session', ''))}</div>
  <h2>{inline(ch['title'])}</h2>
  <div class="prof">{inline(ch.get('prof',''))}</div>
  <div class="range">{rng}</div>
  <table class="meta"><tr>
    <td class="mbox"><span class="n">{fa_digits(n_blocks)}</span><span class="l">بخش</span></td>
    <td class="mbox"><span class="n">{fa_digits(n_fig)}</span><span class="l">شکل</span></td>
    <td class="mbox"><span class="n">{fa_digits(n_tab)}</span><span class="l">جدول</span></td>
  </tr></table>
</div></div>"""


def media_stats() -> dict:
    """Video count and teaching hours, read from the relay manifest when present."""
    mf = ROOT / "work" / "relay" / "video_manifest.tsv"
    n, mins = 0, 0.0
    if mf.exists():
        for line in mf.read_text(encoding="utf-8").splitlines():
            f = line.split("\t")
            if len(f) >= 3:
                n += 1
                try:
                    mins += float(f[2]) / 60.0
                except ValueError:
                    pass
    return {"n": n or 19, "hours": round(mins / 60.0) if mins else 7}


def end_html(n_pages: str, n_fig: str, n_tab: str, n_blocks: str,
             n_videos: str, hours: str) -> str:
    return f"""
<div class="endpage">
  <div class="wordmark"><div class="wm1">{BRAND}</div><div class="wm2">H U M S &nbsp; Y A R</div></div>
  <div class="rule"></div>
  <div class="t1">پایان جزوه فیزیک پزشکی</div>
  <div class="t2">این جزوه از تلفیق جزوه‌های درسی، پاورپوینت‌های اسلاید و ویدیوهای تدریس سه استاد
  (دکتر افضلی‌پور، دکتر لیلی درویش و دکتر حق‌پرست) تهیه شده است.<br/>
  {fa_digits(n_pages)} صفحه · {fa_digits(n_blocks)} بخش · {fa_digits(n_fig)} شکل ·
  {fa_digits(n_tab)} جدول · {fa_digits(n_videos)} ویدیو ({fa_digits(hours)} ساعت تدریس)</div>
  <div class="t3">همه مطالب با ذکر منبع (جزوه/اسلاید/ویدیو) آورده شده‌اند؛ هیچ مطلبی خارج از منابع درس افزوده نشده است.<br/>
  برای مرور نهایی: جعبه‌های «نکته کلیدی»، بخش‌های «مرور سریع» و صفحه راهنمای دکتر درویش را ببینید.</div>
</div>"""


def build_html(page_map: dict | None = None, total_pages: str = "—") -> str:
    global FIG_SEQ
    FIG_SEQ = 0
    chapters = load_chapters()
    guide_rows = json.loads((LOCK / "guide.json").read_text(encoding="utf-8")) \
        if (LOCK / "guide.json").exists() else []
    ANCHOR_MARK.clear()
    for gi, r in enumerate(guide_rows):
        for a in r.get("anchors", []):
            ANCHOR_MARK[a] = gi
    n = len(chapters)
    n_fig = sum(1 for ch in chapters for b in ch["blocks"] if b.get("type") == "figure")
    n_tab = sum(1 for ch in chapters for b in ch["blocks"] if b.get("type") == "table")
    n_blocks = sum(len(ch["blocks"]) for ch in chapters)
    media = media_stats()

    toc_pages: dict[int, tuple[int, int]] = {}
    sec_pages: dict[int, tuple[int, int]] = {}
    if page_map:
        for ch in chapters:
            blk = page_map.get(f"ch{ch['no']}")
            if blk:
                sec_pages[ch["no"]] = (blk["start"], blk["end"])
                body_start = blk["start"] + 1  # section cover page
                toc_pages[ch["no"]] = (body_start, blk["end"])

    if page_map:
        for gi, r in enumerate(guide_rows):
            r["pages"] = page_map.get(f"guide:{gi}")

    parts = [cover_html(total_pages, n, n_fig)]
    parts.append(toc_html(chapters, toc_pages))
    parts.append(guide_html(guide_rows))
    for i, ch in enumerate(chapters, 1):
        parts.append(section_cover(ch, i, n, sec_pages.get(ch["no"])))
        parts.append('<div class="chbody">' + render_blocks(ch["blocks"]) + "</div>")
    parts.append(end_html(total_pages, n_fig, n_tab, n_blocks,
                          media["n"], media["hours"]))
    doc = ("<html dir=\"rtl\"><head><meta charset=\"utf-8\"><title>جزوه جامع فیزیک پزشکی — HumsYar</title>"
           f"<style>{css()}</style></head><body>" + "".join(parts) + "</body></html>")
    return doc


# --------------------------------------------------------------------------- #
# page scan (two-pass page numbers)
# --------------------------------------------------------------------------- #
CH_MARK = re.compile(r"JZC(\d\d)MARK")
GUIDE_MARK = re.compile(r"JZG(\d\d)MARK")


def scan_pages(pdf_path: Path, chapters: list[dict], guide_rows: list[dict]) -> dict:
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(pdf_path))
    page_txt = []
    for i in range(len(doc)):
        tp = doc[i].get_textpage()
        page_txt.append(tp.get_text_range() or "")
    total = len(doc)

    def find(needles: list[str], start: int = 1) -> int | None:
        for p in range(start - 1, len(page_txt)):
            t = page_txt[p]
            for nd in needles:
                if nd and nd in t:
                    return p + 1
        return None

    out: dict = {}
    ch_start: dict[int, int] = {}
    for pno, t in enumerate(page_txt, 1):
        for m in CH_MARK.finditer(t):
            ch_start.setdefault(int(m.group(1)), pno)
    guide_pages: dict[int, int] = {}
    for pno, t in enumerate(page_txt, 1):
        for m in GUIDE_MARK.finditer(t):
            guide_pages.setdefault(int(m.group(1)), pno)

    for ch in chapters:
        start = ch_start.get(ch["no"])
        if start is None:
            start = find([re.sub(r"\[\[|\]\]|\*\*", "", ch["title"])[:28]])
        if start is None:
            continue
        nxt = ch_start.get(ch["no"] + 1)
        out[f"ch{ch['no']}"] = {"start": start, "end": (nxt - 1) if nxt else total}

    for gi, r in enumerate(guide_rows):
        pages = []
        if gi in guide_pages:
            pages.append(guide_pages[gi])
        for a in r.get("anchors", []):
            needles = r.get("needles_by_anchor", {}).get(a) or r.get("needles", [])
            got = find(needles)
            if got:
                pages.append(got)
        if pages:
            out[f"guide:{gi}"] = (min(pages), max(pages))
    return out


FIG_MARK = re.compile(r"JZF(\d\d\d)MARK")
# a page whose content stops this far above the footer is "half empty"
GAP_LIMIT = 0.20


def page_gaps(pdf_path: Path) -> list[float]:
    """Fraction of each page's body height left blank at the bottom.

    Rasterises every page at low resolution and finds the last row that holds
    any ink. The footer band (page number / wordmark) is excluded, and dark
    cover pages come out as 0 because their background is ink.
    """
    import pypdfium2 as pdfium
    from PIL import Image

    gaps = []
    pdf = pdfium.PdfDocument(str(pdf_path))
    for i in range(len(pdf)):
        img = pdf[i].render(scale=0.5).to_pil().convert("L")
        img = img.point(lambda v: 255 if v > 225 else 0)
        body = img.crop((0, 0, img.width, int(img.height * 0.945)))
        col = body.resize((1, body.height), Image.BOX)
        rows = list(col.getdata())
        last = -1
        for y, v in enumerate(rows):
            if v < 254:
                last = y
        gaps.append(1.0 if last < 0 else (len(rows) - 1 - last) / len(rows))
    return gaps


def figure_pages(pdf_path: Path) -> dict[int, int]:
    """figure id → 1-based page it was laid out on."""
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(pdf_path))
    out: dict[int, int] = {}
    for i in range(len(pdf)):
        txt = pdf[i].get_textpage().get_text_bounded()
        for m in FIG_MARK.finditer(txt):
            out.setdefault(int(m.group(1)), i + 1)
    return out


def fit_figures(render_once, rounds: int = 4) -> None:
    """Shrink the figures that leave a big hole at the bottom of their page.

    A figure card cannot be split across pages, so whenever the block after it
    does not fit, the rest of the page stays empty and the جزوه looks torn apart
    (the reader sees one item alone at the bottom and the next two overleaf).
    Each round finds the pages with the largest holes, shrinks the last figure
    sitting on them, and re-renders; a figure that does not actually help is
    restored and frozen so the loop always converges.
    """
    pdf_path = render_once()
    gaps = page_gaps(pdf_path)
    frozen: set[int] = set()
    for _ in range(rounds):
        figs = figure_pages(pdf_path)
        by_page: dict[int, list[int]] = {}
        for fid, pno in figs.items():
            by_page.setdefault(pno, []).append(fid)
        picks = []
        for pno, g in enumerate(gaps, 1):
            if g <= GAP_LIMIT:
                continue
            cands = [f for f in by_page.get(pno, []) if f not in frozen
                     and FIG_SCALE.get(f, 1.0) > 0.62]
            if cands:
                picks.append((max(cands), pno, g))
        if not picks:
            break
        before = {f: FIG_SCALE.get(f, 1.0) for f, _, _ in picks}
        for fid, _, _ in picks:
            FIG_SCALE[fid] = round(before[fid] * 0.85, 3)
        pdf_path = render_once()
        new_gaps = page_gaps(pdf_path)
        improved = False
        for fid, pno, g in picks:
            ng = new_gaps[pno - 1] if pno - 1 < len(new_gaps) else 1.0
            if ng < g - 0.03:
                improved = True
            else:
                FIG_SCALE[fid] = before[fid]
                frozen.add(fid)
        if not improved:
            # every candidate was rolled back -> re-render the restored layout
            pdf_path = render_once()
            new_gaps = page_gaps(pdf_path)
        gaps = new_gaps
    print("page-fill: shrunk figures:",
          {k: v for k, v in sorted(FIG_SCALE.items()) if v < 1.0})


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "HumsYar_MedPhysics_Jozve.pdf"
    chapters = load_chapters()
    guide_rows = json.loads((LOCK / "guide.json").read_text(encoding="utf-8")) if (LOCK / "guide.json").exists() else []

    from weasyprint import HTML

    # pass 1: placeholder page numbers (also used to measure the final page count)
    tmp = BASE / "pass1.pdf"

    def render_pass1() -> Path:
        html1 = build_html()
        (BASE / "pass1.html").write_text(html1, encoding="utf-8")
        HTML(string=html1, base_url=str(BASE)).write_pdf(str(tmp))
        return tmp

    # pass 1b: pull orphaned blocks back by shrinking the figures that leave
    # half-empty pages behind them (keeps sections visually compact)
    fit_figures(render_pass1, rounds=3)
    pm = scan_pages(tmp, chapters, guide_rows)

    # page count changes once real numbers are substituted -> render pass 2 with
    # measured count, rescan, then final pass if it shifted.
    import pypdfium2 as pdfium

    n1 = len(pdfium.PdfDocument(str(tmp)))
    total = fa_digits(n1)
    for _ in range(3):
        html2 = build_html(pm, total)
        (BASE / "pass2.html").write_text(html2, encoding="utf-8")
        HTML(string=html2, base_url=str(BASE)).write_pdf(str(out))
        n2 = len(pdfium.PdfDocument(str(out)))
        pm2 = scan_pages(out, chapters, guide_rows)
        if pm2 == pm and str(n2) == str(n1):
            break
        pm, n1, total = pm2, n2, fa_digits(n2)
    print("rendered", out, "pages:", n2)
    (BASE / "page_map.json").write_text(json.dumps(pm, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
