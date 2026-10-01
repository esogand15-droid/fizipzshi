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
    """Persian digits outside [[...]] LTR islands; ASCII kept inside islands."""
    parts = re.split(r"(\[\[.*?\]\])", str(text))
    out = []
    for i, p in enumerate(parts):
        if i % 2 == 1:  # LTR island
            out.append("<span dir=\"ltr\">" + esc(p[2:-2]) + "</span>")
        else:
            out.append(fa_digits(esc(p)))
    return "".join(out)


def inline(text: str) -> str:
    """Mini markup: **bold**, [[ltr]] islands, Persian digits elsewhere."""
    chunks = re.split(r"(\[\[.*?\]\]|\*\*.*?\*\*)", str(text))
    out = []
    for c in chunks:
        if c.startswith("[[") and c.endswith("]]"):
            out.append('<span dir="ltr">' + esc(c[2:-2]) + "</span>")
        elif c.startswith("**") and c.endswith("**"):
            out.append("<b>" + LTR_DIGITS(c[2:-2]) + "</b>")
        else:
            out.append(LTR_DIGITS(c))
    return "".join(out)


def frac(num: str, den: str) -> str:
    return (f'<span class="frac"><span class="fn"><span>{esc(num)}</span></span>'
            f'<span class="fd"><span>{esc(den)}</span></span></span>')


def mathml_like(tex: str) -> str:
    """Very small formula renderer: \\frac{}{}, ^{}, _{}, greek shortcuts."""
    s = str(tex)
    greek = {"alpha": "α", "beta": "β", "gamma": "γ", "lambda": "λ", "mu": "μ",
             "nu": "ν", "omega": "ω", "pi": "π", "sigma": "σ", "theta": "θ",
             "Delta": "Δ", "rho": "ρ", "phi": "φ", "tau": "τ"}
    for k, v in greek.items():
        s = s.replace("\\" + k, v)

    def repl_frac(m):
        return frac(m.group(1), m.group(2))

    prev = None
    while prev != s:
        prev = s
        s = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", repl_frac, s)
    s = re.sub(r"\^\{([^{}]*)\}", r"<sup>\1</sup>", s)
    s = re.sub(r"_\{([^{}]*)\}", r"<sub>\1</sub>", s)
    s = re.sub(r"\^(\w)", r"<sup>\1</sup>", s)
    s = re.sub(r"_(\w)", r"<sub>\1</sub>", s)
    return s


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
    return (f'<div class="ftable"><table class="dt"><thead><tr>{th}</tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table>{cap}</div>' + src_line(b.get("src")))


def blk_formula(b: dict) -> str:
    fx = mathml_like(b.get("tex", ""))
    legend = b.get("legend") or []
    leg = "".join(f"<div>{inline(x)}</div>" for x in legend)
    name = f'<div class="fleg"><b>{inline(b["name"])}</b></div>' if b.get("name") else ""
    return (f'<div class="fbox"><div class="fx">{fx}</div>{name}'
            f'<div class="fleg">{leg}</div></div>' + src_line(b.get("src")))


def blk_figure(b: dict) -> str:
    f = b.get("file", "")
    path = f if os.path.isabs(f) else str(ROOT / f)
    if not Path(path).exists():
        return f'<div class="fnote">شکل در دسترس نیست: {esc(f)}</div>'
    cap = inline(b.get("caption", ""))
    cs = f'<span class="csrc">{LTR_DIGITS(b.get("src",""))}</span>' if b.get("src") else ""
    w = b.get("width") or "86%"
    return (f'<div class="card"><img src="{path}" style="width:{w}"/>'
            f'<div class="cap">{cap}{cs}</div></div>')


def blk_key(b: dict) -> str:
    return f'<div class="key"><b>نکته کلیدی: </b>{inline(b.get("text",""))}</div>'


def blk_examtip(b: dict) -> str:
    return f'<div class="examtip"><b>نکته امتحانی: </b>{inline(b.get("text",""))}</div>'


def blk_conflict(b: dict) -> str:
    return f'<div class="conflict"><b>⚠ اختلاف منابع: </b>{inline(b.get("text",""))}</div>'


def blk_note(b: dict) -> str:
    return f'<div class="fnote">{inline(b.get("text",""))}</div>'


def blk_review(b: dict) -> str:
    items = "".join(f"<li>{inline(i)}</li>" for i in b.get("items", []))
    return f'<div class="review"><h3>مرور سریع</h3><ul>{items}</ul></div>'


RENDER = {
    "h2": blk_h2, "h3": blk_h3, "p": blk_p, "bullets": blk_bullets, "table": blk_table,
    "formula": blk_formula, "figure": blk_figure, "key": blk_key,
    "examtip": blk_examtip, "conflict": blk_conflict, "note": blk_note,
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


def end_html(n_pages: str, n_fig: str, n_videos: str, hours: str) -> str:
    return f"""
<div class="endpage">
  <div class="wordmark"><div class="wm1">{BRAND}</div><div class="wm2">H U M S &nbsp; Y A R</div></div>
  <div class="rule"></div>
  <div class="t1">پایان جزوه فیزیک پزشکی</div>
  <div class="t2">این جزوه از تلفیق جزوه‌های درسی، پاورپوینت‌های اسلاید و ویدیوهای تدریس سه استاد
  (دکتر افضلی‌پور، دکتر لیلی درویش و دکتر حق‌پرست) تهیه شده است.<br/>
  {fa_digits(n_pages)} صفحه · {fa_digits(n_fig)} شکل · {fa_digits(n_videos)} ویدیو
  ({fa_digits(hours)} ساعت تدریس)</div>
  <div class="t3">همه مطالب با ذکر منبع (جزوه/اسلاید/ویدیو) آورده شده‌اند؛ هیچ مطلبی خارج از منابع درس افزوده نشده است.<br/>
  برای مرور نهایی: جعبه‌های «نکته کلیدی»، بخش‌های «مرور سریع» و صفحه راهنمای دکتر درویش را ببینید.</div>
</div>"""


def build_html(page_map: dict | None = None, total_pages: str = "—") -> str:
    chapters = load_chapters()
    guide_rows = json.loads((LOCK / "guide.json").read_text(encoding="utf-8")) \
        if (LOCK / "guide.json").exists() else []
    ANCHOR_MARK.clear()
    for gi, r in enumerate(guide_rows):
        for a in r.get("anchors", []):
            ANCHOR_MARK[a] = gi
    n = len(chapters)
    n_fig = sum(1 for ch in chapters for b in ch["blocks"] if b.get("type") == "figure")

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
    parts.append(end_html(total_pages, n_fig, "۱۹", "۷"))
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


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "HumsYar_MedPhysics_Jozve.pdf"
    chapters = load_chapters()
    guide_rows = json.loads((LOCK / "guide.json").read_text(encoding="utf-8")) if (LOCK / "guide.json").exists() else []

    from weasyprint import HTML

    # pass 1: placeholder page numbers (also used to measure the final page count)
    html1 = build_html()
    (BASE / "pass1.html").write_text(html1, encoding="utf-8")
    tmp = BASE / "pass1.pdf"
    HTML(string=html1, base_url=str(BASE)).write_pdf(str(tmp))
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
