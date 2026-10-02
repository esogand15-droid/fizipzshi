#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Attach curated slide figures to the chapter content modules.

Every entry names a chapter module, an anchor substring that must match exactly one
block of that module, and the figure(s) to insert right after that block. The tool
rewrites content/*.py in place (idempotent: a figure already present is skipped), so
`tools/build_lock.py` afterwards picks the figures up into lock/.

usage: attach_figures.py [chapter_no ...]
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"

PLAN: dict[int, list[tuple[str, list[dict]]]] = {
    1: [
        ("موجب یونیزه شدن اتم می‌شوند", [dict(
            file="images/fig/fig01_em_spectrum.jpg", width="88%",
            caption="شکل — طیف الکترومغناطیس و جایگاه پرتوهای یونیزان: اشعه ایکس و گاما در ناحیه پرانرژی طیف‌اند و پرتوهای غیر یونیزان (فرابنفش، نور مرئی، مادون‌قرمز، میکروویو و رادیوفرکوئنسی) در ناحیه کم‌انرژی قرار دارند.",
            src="اسلایدهای دکتر افضلی‌پور — ص۲۰ «طیف الکترومغناطیس»")]),
        ("پرتوهای یونیزان با عبور از محیط، ذرات باردار منفی و مثبت تولید می‌کنند", [dict(
            file="images/fig/fig01_energy_spectrum.jpg", width="86%",
            caption="شکل — نمای طیف انرژی از امواج رادیویی تا پرتوهای گاما همراه با طول موج هر ناحیه ([[THE ENERGY SPECTRUM]]).",
            src="اسلایدهای M.Ph.P.D — ص۵")]),
    ],
    2: [
        ("به‌طور کلی پرتو [[X]] در اثر دو فرایند تولید می‌شود", [dict(
            file="images/fig/fig02_xray_production.jpg", width="62%",
            caption="شکل — دو مکانیسم تولید پرتو ایکس: پدیده ترمزی ([[Bremsstrahlung]]) و پدیده مشخصه ([[Characteristic]]).",
            src="اسلایدهای M.Ph.P.D — ص۹")]),
        ("الکترونی که از لایه [[K]] بیرون رانده می‌شود", [dict(
            file="images/fig/fig02_characteristic.jpg", width="66%",
            caption="شکل — اشعه ایکس مشخصه: با خروج الکترون لایه [[K]]، الکترون لایه بالاتر جای خالی را پر می‌کند و فوتون ایکس با انرژی برابر اختلاف انرژی دو لایه گسیل می‌شود.",
            src="اسلایدهای دکتر افضلی‌پور — ص۳۴ «پدیده تابش اختصاصی»")]),
        ("درون لامپ، الکترون‌ها از رشته تنگستنی گداخته تولید می‌شوند", [dict(
            file="images/fig/fig02_xray_penetration.jpg", width="58%",
            caption="شکل — شمای کلی تصویربرداری با پرتو ایکس: مولد پرتو ایکس (یا چشمه رادیواکتیو) پرتو را می‌تاباند و پرتو پس از نفوذ در جسم به گیرنده تصویر می‌رسد.",
            src="اسلایدهای دکتر افضلی‌پور — ص۱۹ «تولید پرتو ایکس»")]),
    ],
    3: [
        ("این روش در مواردی به‌کار می‌رود که بافت‌های مورد رادیوگرافی", [dict(
            file="images/fig/fig03_chest_xray.jpg", width="70%",
            caption="شکل — نمونه رادیوگرافی ساده قفسه سینه: تصویر از تفاوت تضعیف پرتو در بافت‌های مختلف (استخوان، ریه پر از هوا و قلب) ساخته می‌شود.",
            src="اسلایدهای دکتر افضلی‌پور — ص۱۱")]),
        ("تفاوت‌های عدد اتمی و چگالی بین بخش‌های مختلف جسم", [dict(
            file="images/fig/fig03_low_high_energy.jpg", width="72%",
            caption="شکل — اثر انرژی پرتو بر کنتراست: در انرژی پایین (چپ) تفاوت بافت نرم و استخوان بهتر دیده می‌شود؛ در انرژی بالا (راست) پرتو از استخوان هم عبور می‌کند و کنتراست کاهش می‌یابد.",
            src="اسلایدهای دکتر افضلی‌پور — ص۷۷")]),
        ("اجزای زنجیره تصویر: لامپ فلوروسکوپی، صفحه فلورسنت", [dict(
            file="images/fig/fig03_fluoro_chain.jpg", width="56%",
            caption="شکل — زنجیره تصویربرداری فلوروسکوپی: شیشه سربی ([[Lead Glass]])، صفحه فلورسنت، [[Spotfilm]]، [[Slot Scatter Grid]] و لامپ اشعه ایکس.",
            src="اسلایدهای دکتر افضلی‌پور — ص۵۹ «فلوروسکوپی»")]),
        ("انژکتور اتوماتیک مواد حاجب", [dict(
            file="images/fig/fig03_angio_room.jpg", width="76%",
            caption="شکل — اتاق آنژیوگرافی: دستگاه سی‌آرم با تیوب اشعه ایکس در بالا و آشکارساز در پایین، در حال تصویربرداری از بیمار روی تخت.",
            src="اسلایدهای دکتر افضلی‌پور — ص۱۲")]),
        ("کاربردهای سی‌تی‌اسکن: تشخیص بیماری‌های مغز و اعصاب", [dict(
            file="images/fig/fig03_ct_brain.jpg", width="72%",
            caption="شکل — برش‌های سی‌تی مغز: توانایی سی‌تی‌اسکن در نشان‌دادن خون تازه و کهنه، تومورها و ضایعات داخل جمجمه.",
            src="اسلایدهای دکتر افضلی‌پور — ص۱۴"),
            dict(file="images/fig/fig03_ct_scanner.jpg", width="72%",
                 caption="شکل — دستگاه سی‌تی‌اسکن: گانتری (تیوب و آشکارساز چرخان) و تخت بیمار.",
                 src="اسلایدهای دکتر افضلی‌پور — ص۱۳")]),
        ("اجزای زنجیره تصویربرداری ماموگرافی", [dict(
            file="images/fig/fig03_mammo_unit.jpg", width="72%",
            caption="شکل — تجهیزات ماموگرافی و اجزای آن: تیوب اشعه ایکس، کمپرسور، گرید، فیلم و [[AEC]] (کنترل خودکار اکسپوژر).",
            src="اسلایدهای دکتر افضلی‌پور — ص۶۷")]),
    ],
    4: [
        ("مدت زمانی که طی آن نیمی از هسته‌های رادیواکتیو موجود", [dict(
            file="images/fig/fig04_half_life_chart.jpg", width="62%",
            caption="شکل — نمودار نیمه‌عمر: با گذشت هر نیمه‌عمر، انرژی/فعالیت پرتوزایی ماده به نصف کاهش می‌یابد.",
            src="اسلایدهای M.Ph.P.D — ص۴۲")]),
        ("ژنراتور [[Mo-99/Tc-99m]]: زنجیره واپاشی", [dict(
            file="images/fig/fig04_mo99_generator.jpg", width="52%",
            caption="شکل — نقشه استحاله ژنراتور: [[Mo-99]] ([[67 hr]]) ⟶ [[Tc-99m]] ([[6 hr]]) ⟶ [[Tc-99]] ([[2.1 × 10^5 yr]]) ⟶ [[Ru-99]] (پایدار).",
            src="اسلایدهای M.Ph.P.D — ص۴۷")]),
    ],
    6: [
        ("کاهش زمان در معرض قرارگیری پرتو", [dict(
            file="images/fig/fig06_three_principles.jpg", width="74%",
            caption="شکل — سه اصل کاهش پرتوگیری خارجی: کاهش زمان، افزایش فاصله و استفاده از حفاظ ([[Time / Distance / Shielding]]).",
            src="اسلایدهای دکتر افضلی‌پور — ص۸۹")]),
        ("وضعیت همه افراد حاضر طوری باشد", [dict(
            file="images/fig/fig06_lead_apron.jpg", width="58%",
            caption="شکل — رویوش و دستکش سربی: کارکنان و بیمارانی که باید در اتاق بمانند، با حداقل [[0.25 mm]] معادل سرب حفاظت می‌شوند.",
            src="اسلایدهای دکتر افضلی‌پور — ص۱۰۴")]),
        ("وسایل نگه‌دارنده می‌تواند شامل وسایل محدودکننده", [dict(
            file="images/fig/fig06_scatter_position.jpg", width="54%",
            caption="شکل — پرتوهای پراکنده و موقعیت کارکنان (A و B): نگه‌دارنده بیمار باید در زاویه [[90]] درجه نسبت به شعاع پرتو اولیه بایستد تا پرتوگیری به کمترین مقدار برسد.",
            src="اسلایدهای دکتر افضلی‌پور — ص۹۳")]),
        ("از همه زنانی که تحت پرتونگاری به‌ویژه از ناحیه شکم", [dict(
            file="images/fig/fig06_pregnancy.jpg", width="54%",
            caption="شکل — پرسش از وضعیت بارداری پیش از پرتونگاری: در صورت امکان، آزمایش به بعد از وضع حمل یا به سه ماه آخر حاملگی موکول می‌شود.",
            src="اسلایدهای دکتر افضلی‌پور — ص۸۷")]),
        ("کاهش زمان، افزایش فاصله و استفاده از حفاظ، سه راهکار عملی", [dict(
            file="images/fig/fig06_room_shielding.jpg", width="60%",
            caption="شکل — حفاظ‌های اتاق پرتونگاری: تفکیک موانع اولیه (دیوارها) و ثانویه (غرفه کنترل و شیشه سربی) برای کاهش پرتوگیری کارکنان مجاور.",
            src="اسلایدهای دکتر افضلی‌پور — ص۹۶")]),
    ],
    7: [
        ("صوت یک موج مکانیکی است", [dict(
            file="images/fig/fig07_wave_compression.jpg", width="66%",
            caption="شکل — موج صوتی: نواحی تراکم ([[Compression]]) و انبساط ([[Rarefaction]]) با طول موج [[λ]]؛ نمودار پایین تغییر فشار را نسبت به فاصله و زمان نشان می‌دهد.",
            src="اسلایدهای M.Ph.P.D — ص۶۳ و ص۶۴")]),
        ("لایه میراکننده ([[Backing]])", [dict(
            file="images/fig/fig07_transducer.jpg", width="60%",
            caption="شکل — برش ترانس‌دیوسر: کابل کواکسیال، محفظه پلاستیکی، حفاظ فلزی، جاذب صوتی، بلوک پشتی (میراکننده)، بلور پیزوالکتریک و لایه تطبیق ([[Matching layer]]).",
            src="اسلایدهای M.Ph.P.D — ص۸۵")]),
        ("محاسبه عمق در [[A-mode]]", [dict(
            file="images/fig/fig07_amode.jpg", width="58%",
            caption="شکل — A-mode با سه مرز: هر مرز بازتاب یک پیک (اسپایک) روی نمایشگر می‌سازد؛ فاصله زمانی پیک‌ها نشان‌دهنده عمق مرزها است.",
            src="اسلایدهای M.Ph.P.D — ص۹۰"),
            dict(file="images/fig/fig07_a_vs_b_mode.jpg", width="66%",
                 caption="شکل — مقایسه نمایش A-mode (تنها دامنه پیک‌ها) و B-mode (روشنایی نقاط روی تصویر دوبعدی).",
                 src="اسلایدهای M.Ph.P.D — ص۹۳")]),
        ("A-mode]] ([[Amplitude Mode", [dict(
            file="images/fig/fig07_fetus_bsan.jpg", width="56%",
            caption="شکل — نمونه تصویر B-mode: سونوگرافی جنین؛ بازتاب‌ها به‌صورت نقاط روشن روی زمینه تیره نمایش داده می‌شوند.",
            src="اسلایدهای M.Ph.P.D — ص۹۴")]),
        ("F_d = F_v - F_t", [dict(
            file="images/fig/fig07_doppler_effect.jpg", width="70%",
            caption="شکل — اثر داپلر: در حالت ساکن (الف) فرکانس دریافتی با ارسالی برابر است؛ در حالت متحرک (ب) امواج در جلو فشرده و در عقب باز می‌شوند و فرکانس دریافتی تغییر می‌کند.",
            src="اسلایدهای M.Ph.P.D — ص۹۶")]),
        ("کاربردهای بالینی داپلر: بررسی وجود یا عدم جریان خون", [dict(
            file="images/fig/fig07_stenosis.jpg", width="66%",
            caption="شکل — تشخیص تنگی (استنوز) با داپلر رنگی: ناحیه تنگ، جریان خون پرسرعت و تغییرات فرکانسی را نشان می‌دهد.",
            src="اسلایدهای M.Ph.P.D — ص۱۰۲"),
            dict(file="images/fig/fig07_mitral_mmode.jpg", width="60%",
                 caption="شکل — اکوکاردیوگرافی M-mode دریچه میترال: حرکت دریچه در طول زمان (نمایش M-mode) ثبت می‌شود.",
                 src="اسلایدهای M.Ph.P.D — ص۹۵")]),
    ],
    8: [
        ("۱۱. آسیب کروموزومی", [dict(
            file="images/fig/fig08_ring_chromosome.png", width="56%",
            caption="شکل — تشکیل حلقه کروموزومی ([[Ring chromosome]]): شکست در دو انتهای کروموزوم و اتصال انتهاها که در میکروسکوپ نوری دیده می‌شود.",
            src="اسلایدهای رادیوبیولوژی دکتر درویش ص۳۴")]),
    ],
    9: [
        ("[[MRI]] بر دو پایه استوار است", [dict(
            file="images/fig/fig09_mri_components.png", width="62%",
            caption="شکل — اجزای دستگاه MRI: آهنربای اصلی ([[Primary magnet]])، کوئل‌های گرادیان، کوئل‌های فرکانس رادیویی ([[RF]])، سیستم کامپیوتری و تخت بیمار.",
            src="اسلایدهای MRI دکتر درویش ص۲")]),
        ("اگر پروتون در میدان مغناطیسی قرار گیرد", [dict(
            file="images/fig/fig09_precession.png", width="52%",
            caption="شکل — حرکت تقدیمی ([[Precession]]) پروتون در میدان مغناطیسی: هسته مثل آهنربای کوچکی می‌چرخد و ممان مغناطیسی پیدا می‌کند.",
            src="اسلایدهای MRI دکتر درویش ص۵")]),
        ("نسبت ژیرومغناطیسی برای هر هسته مشخص، مقدار معینی دارد", [dict(
            file="images/fig/fig09_parallel_antiparallel.png", width="54%",
            caption="شکل — حالت‌های موازی و غیرموازی ([[Parallel / Anti-parallel]]) اسپین‌ها نسبت به میدان [[B0]] و اختلاف انرژی [[ΔE]] میان دو حالت.",
            src="اسلایدهای MRI دکتر درویش ص۶")]),
        ("زمان آسایش [[T1]]: مدت زمانی است که طول می‌کشد", [dict(
            file="images/fig/fig09_t1_t2_curves.png", width="66%",
            caption="شکل — منحنی‌های آسایش: بازگشت مغناطش طولی [[Mz(t) = M0(1 - e^{-t/T1})]] و کاهش نمایی مغناطش عرضی [[Mxy(t) = M0 e^{-t/T2}]] با گذشت زمان.",
            src="اسلایدهای MRI دکتر درویش ص۴۰")]),
        ("خون وقتی از رگ خارج می‌شود", [dict(
            file="images/fig/fig09_hemorrhage_contrast.png", width="62%",
            caption="شکل — کنتراست خون‌ریزی در MRI: سیگنال در [[T1]] و [[T2]] برحسب روزهای گذشته از خون‌ریزی و نوع هموگلوبین (دکسی‌هموگلوبین، متهموگلوبین داخل/خارج سلولی و هموسیدرین) تغییر می‌کند.",
            src="اسلایدهای MRI دکتر درویش ص۵۱")]),
    ],
}

FIG_RE = re.compile(r'\{"type": "figure",\s*\n\s*"file": "([^"]+)"')


def module_path(no: int) -> Path:
    spec = importlib.util.spec_from_file_location("bl", ROOT / "tools" / "build_lock.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return CONTENT / f"{mod.CHAPTERS[no]['module']}.py"


def block_texts(src: str) -> list[str]:
    """Return the raw text of each block dict (each begins with '    {"')."""
    parts = re.split(r"\n(?=    \{)", src)
    return parts


def fmt_fig(f: dict) -> str:
    lines = ['    {"type": "figure",']
    for k in ("file", "width", "caption", "src"):
        if f.get(k):
            lines.append(f'     "{k}": {f[k]!r},')
    lines[-1] = lines[-1].rstrip(",")
    lines.append("     },\n")
    return "\n".join(lines)


def main() -> int:
    only = {int(x) for x in sys.argv[1:]} if len(sys.argv) > 1 else None
    total = 0
    for no, entries in PLAN.items():
        if only and no not in only:
            continue
        path = module_path(no)
        src = path.read_text(encoding="utf-8")
        added = 0
        for anchor, figs in entries:
            for f in figs:
                if Path(f["file"]).name in src:
                    continue
                hits = [i for i, p in enumerate(block_texts(src)) if anchor in p]
                if len(hits) != 1:
                    print(f"!! ch{no}: anchor matched {len(hits)}x -> {anchor[:45]!r}")
                    continue
                parts = block_texts(src)
                # find the end of the matched block: insert right after it
                parts[hits[0]] = parts[hits[0]] + fmt_fig(f)
                src = "\n".join(parts)
                added += 1
        if added:
            path.write_text(src, encoding="utf-8")
            print(f"ch{no}: +{added} figures -> {path.name}")
            total += added
        else:
            print(f"ch{no}: nothing to do")
    print("added", total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
