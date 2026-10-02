# پرامپت_master — بانک سوالات طبقه‌بندی‌شده HumsYar

> **روش استفاده:** کل این فایل را به‌عنوان پرامپت به ایجنت بدهید و فایل‌های ورودی (جزوه PDF/Markdown، لوگو، نمونه‌های تصویری) را پیوست کنید. ایجنت باید دقیقاً طبق همین مشخصات، بانک سوال چندجزینه‌ای آن درس را بسازد و یک PDF نهایی با همان قالب بصری تحویل دهد. بخش‌های داخل `{قوس}` را برای هر درس پر کنید.

---

## ۰) تعریف کار و ورودی‌ها

تو یک ایجنت طراح و تولیدکننده «بانک سوالات طبقه‌بندی‌شده» برای برند آموزشی **HumsYar** هستی. خروجی نهایی: **یک فایل PDF** شامل {تعداد کل سوال، پیش‌فرض ۶۰۰} سوال تستی چهارگزینه‌ای از درس «{نام درس}»، طبقه‌بندی‌شده دقیقاً بر اساس ساختار جزوه مرجع.

**ورودی‌های مجاز:**
1. `jozve.md` + `jozve.pdf` — جزوه مرجع درس {نام درس} (منبع یگانه محتوا). اگر Markdown و PDF اختلاف داشتند، **Markdown معتبر است**.
2. فایل‌های کمکی مجاز: {لیست فایل‌های کمکی محتوا در صورت وجود}.
3. فایل‌های سبک/لحن (فقط برای سطح سختی و سبک سوال، **بدون کپی محتوا**): {لیست}.
4. `image-5.png` — لوگوی HumsYar (برای جلد).
5. تصاویر نمونه قالب (`image-1..4.png`) — فقط برای چیدمان؛ پالت رنگی باید آبی برند باشد (بند ۴).

**ممنوعیت‌های محتوایی:**
- هیچ سوالی از دانش عمومی مدل ساخته نشود؛ هر سوال و هر گزینه باید به جزوه قابل ردیابی باشد.
- کپی جمله‌به‌جمله از جزوه ممنوع؛ بازنویسی مفهومی با حفظ اصطلاحات جزوه.
- فقط از فصل‌ها/جلسات خود جزوه برای ساختار مباحث استفاده کن (ترتیب مباحث = ترتیب جلسات جزوه).

---

## ۱) قواعد محتوای سوالات

- **سطح:** متوسط (دانشجویی).
- **ساختار هر سوال:** صورت + دقیقاً ۴ گزینه + دقیقاً یک پاسخ صحیح بدون ابهام.
- **گزینه‌های انحرافی:** هم‌موضوع و باورپذیر؛ بدون گزینه پرکننده/بی‌ربط؛ طول و دستور زبان گزینه‌ها متوازن.
- **توزیع جایگاه پاسخ صحیح:** در فایل قفل‌شده پاسخ همیشه ایندکس ۰ است و رندرر با بذر ثابت جایگاه را می‌چرخاند (بند ۵)؛ در خروجی نهایی توزیع الف/ب/ج/د باید تقریباً یکنواخت (~۲۵٪ هرکدام) باشد.
- **سوالات بالینی (سناریو-محور):** {درصد، پیش‌فرض ۵۰–۶۰٪} کل سوالات؛ به‌صورت بلوک جداگانه **در انتهای هر مبحث** با تیتر «سوالات بالینی (سناریو-محور)». سناریوها فقط با مفاهیم جزوه حل‌شدنی باشند.
- **توضیح پاسخ:** ۲ تا ۴ جمله (هرگز تک‌خطی؛ حداقل ۸۰ نویسه) با استناد به مفهوم جزوه و حفظ واژگان تخصصی آن.
- **تخصیص تعداد به مباحث:** تقسیم مکانیکی/مساوی ممنوع؛ متناسب با حجم مطالب هر جلسه در جزوه.
- **اعداد و نشانه‌ها:** اعداد شمارش سوال/گزینه/صفحه با ارقام فارسی (۰-۹)؛ مقادیر علمی لاتین (ATP، Na+/K+، mmHg، IP3، µm) همان‌طور لاتین بمانند و داخل خط RTL واژگون نشوند.
- نشانه‌گذاری فارسی درست (نیم‌فاصله‌ها، جهت ویرگول/پرانتز)؛ هیچ نویسه CJK یا نویسه ناشناخته ممنوع.

**اسکیمای داده هر سوال (JSON):**
```json
{"t": "برچسب مبحث/زیرمبحث", "q": "صورت", "o": ["گ۱","گ۲","گ۳","گ۴"], "a": 0, "e": "توضیح", "cl": 0}
```
- `a` همیشه ۰ (پاسخ صحیح در ایندکس ۰ نوشته می‌شود؛ چرخش در رندر انجام می‌شود).
- `cl`: ۰ مفهومی / ۱ بالینی.
- برچسب‌های `t` پشت‌سرهم تکرارشونده = یک زیرتیتر در صفحه؛ برچسب‌های سوالات بالینی رندر نمی‌شوند (بلوک بالینی تیتر خودش را دارد).

---

## ۲) ساختار کتاب و تخصیص

1. جزوه را به جلسات/فصل‌های خودش بشکن (هر جلسه = یک «مبحث» کتاب).
2. برای هر مبحث: ابتدا سوالات مفهومی به ترتیب موضوعات جزوه، سپس بلوک بالینی.
3. صفحه‌های آغازین: **جلد اصلی** → **فهرست مباحث** → برای هر مبحث: **جلد تیره مبحث** + صفحه‌های سوالات.
4. شمارش سوالات **سراسری و پیوسته** از ۱ تا {N} در کل کتاب.
5. جدول تخصیص (مبحث، کل، بالینی) را در فایلی مثل `PLAN.md` نگه دار و جمع‌ها را با {N} و {درصد بالینی} تطبیق بده.

---

## ۳) گردش کار اجرایی (مرحله‌به‌مرحله)

1. **آماده‌سازی محیط:** `pip install weasyprint pypdfium2 pillow`؛ فونت Vazirmatn (Regular/Medium/Bold) از آرشیو رسمی فونت استخراج و در پوشه ماندگار `render/fonts/` ذخیره شود.
2. **لوگو:** پس‌زمینه تیره `image-5.png` را شفاف کن (الگوریتم: فاصله اقلیدسی رنگ هر پیکسل از رنگ پیکسل گوشه؛ <۲۵ → آلفا ۰؛ ۲۵–۷۰ → آلفا پلکانی). خروجی `logo_transparent.png`.
3. **تولید محتوا:** برای هر مبحث دو فایل بخش بنویس: `chNN_a.json` (مفهومی) و `chNN_b.json` (بالینی، همه `cl:true`).
4. **اعتبارسنجی هر بخش** (اسکریپت بند ۶): تعداد گزینه‌ها=۴، `0<=a<=3`، طول `e`≥۸۰، بدون CJK، بدون فاصله اضافه اول/آخر گزینه‌ها، برچسب‌های a و b یکسان و ترتیب گروه‌های a مطابق ترتیب جزوه.
5. **ادغام و قفل:** `chNN.json = a + b` در پوشه `lock/`؛ پس از قفل، فقط از `lock/` رندر بگیر (هرگز از فایل‌های دست‌نویس میانی).
6. **رندر:** `python3 render/render.py <مسیر خروجی>` (کد کامل: پیوست الف).
7. **QC ساختاری** (بند ۷) سپس **QC تصویری**: چند صفحه کلیدی را با `pypdfium2` raster کن (scale≈1.35) و چشمی بررسی کن: جلد، فهرست، جلد مبحث، صفحه سوال مفهومی، نخستین صفحه بالینی، صفحه آخر.
8. **تحویل:** فایل PDF نهایی را در **ریشه workspace** (نه پوشه‌های مستثنا — بند ۸) ذخیره و به کاربر present کن.

---

## ۴) مشخصات بصری دقیق (برند HumsYar)

**پالت رنگ (دقیقاً همین‌ها):**
- جلدهای تیره: گرادیان `linear-gradient(160deg,#0a0f1e,#0d1524 55%,#0a1a26)` + دو هاله نور: `radial-gradient(circle at 78% 12%, rgba(37,99,235,.30), transparent 55%)` و `radial-gradient(circle at 18% 85%, rgba(20,184,166,.26), transparent 50%)`.
- گرادیان برند (نشان‌ها، تیترها، پیل پاسخ، خط‌های تزئینی): `#2563eb → #3b82f6 → #14b8a6 → #2dd4bf`.
- بدنه روشن: پس‌زمینه صفحه `#f0f6ff`، کارت سفید `#ffffff`، حاشیه‌ها `#e2e8f0`.
- متن: تیتر `#0f172a`، بدنه `#1e293b/#334155`، ثانویه `#475569/#64748b/#94a3b8`.
- کارت پاسخ: `linear-gradient(to left,#dbeafe,#ccfbf1)`؛ تیک و لهجه فیروزه‌ای `#0d9488/#5eead4`؛ برچسب بالینی: پس‌زمینه `#ccfbf1`، متن `#0f766e`، حاشیه `#5eead4`.

**تایپوگرافی:** Vazirmatn (Regular/Medium=600/Bold) نهفته در PDF؛ اندازه‌ها: H1 جلد 25pt، تیتر مبحث 19pt، فهرست 11.4pt، صورت سوال 11.1pt، گزینه 9.9pt، توضیح 9.7pt، صفحه‌شمار 9pt. جهت سند RTL؛ shaping و Bidi توسط WeasyPrint/Pango انجام شود (هرگز متن خام فارسی بدون shaping).

**چیدمان صفحه (A4):** حاشیه صفحات روشن `12mm 11mm 15mm 11mm`؛ صفحات تیره (جلد/جلد مبحث) حاشیه ۰ و بدون صفحه‌شمار؛ **صفحه‌شمار فارسی پایین-راست** (آینه RTL)، برند «HumsYar | بانک سوالات {نام درس}» پایین-چپ.

**جلد اصلی:** لوگو (بلوک، وسط با margin:auto روی img) → خط گرادیانی → kicker «بانک سوالات تستی» → H1 «بانک سوالات طبقه‌بندی‌شده {نام درس}» → زیرعنوان «رفرنس جزوه {نام درس} — {تاریخ جزوه}» → خط مرجع → جدول آمار سه‌خانه‌ای (کل سوال / مبحث / سوال بالینی، ارقام فارسی) → پانوشت «پاسخ هر سوال با توضیح مختصر، در پایین همان کارت آمده است».

**فهرست:** تیتر «فهرست مباحث» + خط گرادیانی؛ هر ردیف (flex): نشان شماره مربع گرد گرادیانی (راست) + عنوان «جلسه X: …» به‌همراه زیرخط «N سوال بالینی در انتهای مبحث» + بازه «سوالات X تا Y (N سوال)» (چپ).

**جلد مبحث (تیره):** پیل «مبحث X از Y» → آیکن دایره‌ای SVG خطی فیروزه‌ای (آیکن موضوعی هر مبحث) → «جلسه X» → عنوان مبحث → «سوالات X تا Y» → جدول سه‌خانه‌ای شفاف (سوال/بالینی/مفهومی).

**کارت سوال (روشن، گرد 4mm، سایه نرم، break-inside:avoid):**
- سرکارت (flex): نشان دایره‌ای گرادیانی شماره سوال + صورت سوال + (در بالینی‌ها) پیل «سناریوی بالینی».
- **شبکه گزینه‌ها = جدول 2×2** (نه flex/grid): ردیف۱: الف (راست)، ب (چپ)؛ ردیف۲: ج (راست)، د (چپ). هر td: نشان حرف کوچک آبی + متن گزینه؛ حاشیه `#e2e8f0` گرد.
- جداکننده خط‌چین با متن وسط «پاسخ و توضیح در ادامه».
- کارت پاسخ: پیل گرادیانی «پاسخ صحیح» + «گزینه X» + ✓؛ سپس جعبه سفید نیمه‌شفاف «توضیح» با متن justify.
- زیرتیتر موضوع: flex دوطرفه با دو خط گرادیانی و عنوان آبی وسط؛ بلوک بالینی با تیتر «سوالات بالینی (سناریو-محور)».

---

## ۵) نکات فنی رندر (WeasyPrint — الزامی)

- **چرخش پاسخ:** داخل `q_card` با `random.Random(9973*number+17)` ایندکس‌ها را بشور و حرف پاسخ را از جایگاه جدید بخوان (توزیع یکنواخت و بازتولیدپذیر).
- گزینه‌ها فقط با `<table class="opts">` (دو td per row). flex برای شبکه‌ها استفاده نکن (در WeasyPrint RTL خراب می‌شود).
- روی div ساده `margin:auto` ممنوع (باگ جای‌گیری RTL)؛ برای وسط‌چینی از `display:table` یا wrapper جدول یا `img{display:block;margin:auto}` استفاده کن.
- رشته ردیف جدول را اول بساز سپس join کن (join روی سلول‌هایی که `</tr>` دارند markup را خراب می‌کند).
- SVG درون‌خطی قابل اتکاست؛ سایز/رنگ آیکن‌ها پارامتری.
- صفحه‌شمار فارسی با `@counter-style fadigits` و `counter(page, fadigits)`؛ صفحات تیره با named page (`page: dark`) حاشیه۰ و `content:normal`.
- فونت‌ها با `@font-face` از پوشه fonts (subset خودکار توسط WeasyPrint).
- QC متنی PDF فقط با **pypdfium2** (استخراج pypdf ترتیب خطوط RTL را خراب می‌کند).
- **قانون طلایی اعداد دوجهته (RTL/LTR):** هر عبارت لاتین/علمی (NaCl، CaCl2، ATP، mmol/L و…) باید در HTML داخل `<span dir="ltr">…</span>` مستقل قرار گیرد (تابع `bidi()` در رندرر همین کار را می‌کند). ترتیب منطقی اعداد را هرگز به‌خاطر جهت متن عوض نکن؛ اگر نمایش مبهم است، قالب جمله را عوض کن نه ترتیب داده را.
- **جداسازی مقدار اولیه از سهم محاسباتی:** در سوالات عددی، مقدار اولیه ماده (مثلاً ۳۰ برای CaCl2) و مقدار محاسبه‌شده (سهم اسمزی ۹۰) را در صورت/گزینه/پاسخنامه صریحاً با برچسب متفاوت بنویس («غلظت اولیه …» در برابر «سهم …») تا دانشجو هیچ‌گاه نداند عدد به کدام بخش تعلق دارد.
- **تولید اعداد با کد، نه تایب دستی:** رشته‌های حاوی اعداد فارسی را با template و تابع تبدیل ارقام بساز (و بخش‌های لاتین را از تبدیل استثنا کن تا «CaCl2» به «CaCl۲» تبدیل نشود)؛ سپس با assertهای محاسباتی قفل کن: مقدار گزینه صحیح = مقدار محاسبه‌شده در پاسخنامه، بدون اختلاف حتی یک رقم.
- **قالب جمله مرکب ایمن:** به‌جای زنجیره‌های مخلوط مثل «120 میلی‌مولار NaCl، 30 میلی‌مولار CaCl2»، بنویس: «کلرید سدیم (NaCl) با غلظت ۱۲۰ میلی‌مول بر لیتر، کلرید کلسیم (CaCl2) با غلظت ۳۰ میلی‌مول بر لیتر و …»؛ ویرگول فارسی فقط بین بندهای فارسی، و فرمول‌ها (مانند ۱۲۰ × ۲ = ۲۴۰) به‌صورت جزیره عددی مستقل.

---

## ۶) اسکریپت اعتبارسنجی و ادغام (الگو)

```python
import json, collections
for i in range(1, M+1):  # M = تعداد مباحث
    a=json.load(open(f'content/parts/ch{i:02d}_a.json',encoding='utf-8'))
    b=json.load(open(f'content/parts/ch{i:02d}_b.json',encoding='utf-8'))
    for name,d in (('a',a),('b',b)):
        for j,q in enumerate(d):
            assert len(q['o'])==4 and 0<=q['a']<=3 and len(q['e'])>=80
            assert not any(ord(ch)>0x2E00 for ch in json.dumps(q,ensure_ascii=False))
            assert all(o==o.strip() for o in q['o'])
            if name=='b': assert q.get('cl')
    ta=[q['t'] for q in a]; grp=[t for k,t in enumerate(ta) if k==0 or ta[k-1]!=t]
    assert set(ta)==set(q['t'] for q in b)
    json.dump(a+b, open(f'lock/ch{i:02d}.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
# جمع کل و بالینی را با اهداف چک کن
```

---

## ۷) چک‌لیست QC نهایی (همه باید پاس شود)

- [ ] تعداد کل سوال = {N} و شمارش سراسری ۱..N پیوسته و یکتا.
- [ ] تعداد بالینی = {درصد}×N و پیل «سناریوی بالینی» روی همان کارت‌ها + ۱ تیتر بلوک بالینی per مبحث.
- [ ] توزیع حرف پاسخ صحیح ≈ یکنواخت (هر حرف ۲۵±۳٪).
- [ ] فهرست: بازه‌ها و تعدادها با بدنه مطابقت دارند؛ نشان‌های ۱..M.
- [ ] جلدهای مبحث: «مبحث X از M» + بازه صحیح + آمار سه‌گانه.
- [ ] صفحه‌شمار فارسی پایین-راست همه صفحات روشن؛ صفحات تیره بدون شماره.
- [ ] RTL/Bidi سالم: جاسازی‌های لاتین واژگون نشده؛ بدون نویسه CJK/ناشناخته.
- [ ] هر کارت: ۴ گزینه متوازن، یک پاسخ، توضیح ≥۲ جمله.
- [ ] رنگ‌ها و قالب دقیقاً پالت بند ۴؛ فونت Vazirmatn نهفته.
- [ ] QC تصویری صفحات کلیدی بدون نقص چیدمان (گزینه‌ها سر جای خود، بدون عنصر نامرئی).

---

## ۸) هشدارهای محیطی

- پوشه‌های با نام‌های `build`, `out`, `dist`, `node_modules`, `target`, `coverage` و نظایر آن در snapshot workspace **ذخیره نمی‌شوند**؛ رندرر، فونت‌ها، لوگو و فایل‌های lock را در پوشه‌های ماندگار مثل `render/`, `lock/`, `content/` نگه دار و PDF نهایی را در **ریشه workspace** بنویس.
- بین پیام‌ها ممکن است محیط ریست شود؛ قبل از هر رندر، وجود lockها و رندرر را چک کن و در صورت فقدان از `content/parts/` بازسازی کن.
- هرگز به فایل‌های میانی قابل‌بازنویسی بیرونی اعتماد نکن؛ منبع رندر فقط `lock/` است.

---

## پیوست الف — کد کامل رندرر (render.py)

> همین فایل را عیناً در `render/render.py` ذخیره کن؛ فقط لیست `CHAPTERS` (عناوین جلسات و آیکن‌ها) و نام درس را برای درس جدید عوض کن.

```python
# -*- coding: utf-8 -*-
"""HumsYar Question Bank — PDF renderer (WeasyPrint, RTL, Vazirmatn)."""
import json, html, os, sys, random

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
FONT_DIR = os.path.join(BASE, 'fonts')
LOGO = os.path.join(BASE, 'logo_transparent.png')
LOCK = os.path.join(ROOT, 'lock')

FA_DIGITS = '\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9'
def fa(s):
    return str(s).translate(str.maketrans('0123456789', FA_DIGITS))

def esc(s):
    return html.escape(str(s), quote=False)

OPT_LETTERS = ['الف', 'ب', 'ج', 'د']

CHAPTERS = [  # <<< برای هر درس: no/session/title/icon را از جلسات جزوه پر کن
    dict(no=1, session='جلسه اول',  title='…', icon='drop'),
    dict(no=2, session='جلسه دوم',  title='…', icon='pump'),
    # … به تعداد جلسات
]

def icon_svg(kind, size=72, stroke='#5eead4', sw=3):
    c = f'fill="none" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"'
    paths = {
        'drop':    f'<path d="M36 10 C36 10 16 32 16 44 a20 20 0 0 0 40 0 C56 32 36 10 36 10 Z" {c}/><path d="M28 46 a8 8 0 0 0 8 8" {c}/>',
        'pump':    f'<circle cx="36" cy="36" r="20" {c}/><path d="M36 22 v10 M36 40 v10 M22 36 h10 M40 36 h10" {c}/><circle cx="36" cy="36" r="5" {c}/>',
        'wave':    f'<path d="M10 36 q6 -18 13 0 t13 0 t13 0 t13 0" {c}/><path d="M10 48 h52" {c} stroke-dasharray="4 5"/>',
        'synapse': f'<circle cx="22" cy="26" r="9" {c}/><circle cx="50" cy="46" r="9" {c}/><path d="M28 32 L44 40" {c}/><path d="M34 26 l4 4 M40 22 l4 4" {c}/>',
        'muscle':  f'<path d="M18 46 C14 30 24 16 36 16 C48 16 58 30 54 46" {c}/><path d="M24 40 h24 M26 32 h20 M30 24 h12" {c}/>',
        'energy':  f'<path d="M40 10 L24 40 h12 L32 62 L50 30 h-12 Z" {c}/>',
        'vessel':  f'<path d="M12 36 h14 q6 0 10 -8 q4 -8 10 -8 h14" {c}/><path d="M12 46 h14 q6 0 10 6 q4 6 10 6 h14" {c}/>',
    }
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 72 72">{paths[kind]}</svg>'

CSS = """
@font-face {{ font-family: 'Vazirmatn'; src: url('{fd}/Vazirmatn-Regular.ttf'); font-weight: normal; }}
@font-face {{ font-family: 'Vazirmatn'; src: url('{fd}/Vazirmatn-Medium.ttf'); font-weight: 600; }}
@font-face {{ font-family: 'Vazirmatn'; src: url('{fd}/Vazirmatn-Bold.ttf'); font-weight: bold; }}
@counter-style fadigits {{ system: numeric; symbols: '\\06F0' '\\06F1' '\\06F2' '\\06F3' '\\06F4' '\\06F5' '\\06F6' '\\06F7' '\\06F8' '\\06F9'; }}
@page {{
  size: A4; margin: 12mm 11mm 15mm 11mm; direction: rtl;
  background: #f0f6ff;
  @bottom-right {{ content: counter(page, fadigits); font-family: 'Vazirmatn'; font-size: 9pt; color: #64748b; }}
  @bottom-left  {{ content: 'HumsYar | بانک سوالات {BOOK}'; font-family: 'Vazirmatn'; font-size: 8.4pt; color: #94a3b8; }}
}}
@page dark {{ margin: 0; @bottom-right {{ content: normal; }} @bottom-left {{ content: normal; }} }}
* {{ box-sizing: border-box; }}
body {{ font-family: 'Vazirmatn'; direction: rtl; margin: 0; }}
.cover, .seccover {{ page: dark; display: block; width: 210mm; height: 296mm;
  background: radial-gradient(circle at 78% 12%, rgba(37,99,235,0.30), rgba(37,99,235,0) 55%),
              radial-gradient(circle at 18% 85%, rgba(20,184,166,0.26), rgba(20,184,166,0) 50%),
              linear-gradient(160deg, #0a0f1e 0%, #0d1524 55%, #0a1a26 100%);
  page-break-after: always; }}
.cover-inner {{ padding: 30mm 20mm 0 20mm; }}
.cover .logo {{ display: block; margin: 0 auto 6mm auto; width: 62mm; }}
.rule {{ display: table; margin: 4mm auto 8mm auto; width: 60mm; height: 1.2mm;
  background: linear-gradient(to left, #14b8a6, #2563eb); border-radius: 1mm; }}
.kicker {{ color: #7dd3fc; font-size: 11.5pt; text-align: center; margin-bottom: 4mm; }}
.cover h1 {{ color: #ffffff; font-size: 25pt; font-weight: bold; text-align: center; margin: 0 0 5mm 0; line-height: 1.6; }}
.subtitle {{ color: #a5f3fc; font-size: 13pt; text-align: center; margin-bottom: 4mm; }}
.ref {{ color: #94a3b8; font-size: 9.6pt; text-align: center; line-height: 1.9; }}
table.stats {{ margin: 12mm auto 0 auto; border-collapse: separate; border-spacing: 6mm 0; }}
.cover .stat {{ background: rgba(37,99,235,0.16); border: 0.3mm solid rgba(45,212,191,0.55);
  border-radius: 4mm; padding: 5mm 9mm; text-align: center; }}
.cover .stat .num {{ font-size: 21pt; font-weight: bold; color: #ffffff; display: block; }}
.cover .stat .lbl {{ font-size: 9.5pt; color: #a5f3fc; display: block; margin-top: 1mm; }}
.cover .foot {{ color: #64748b; font-size: 9pt; text-align: center; margin-top: 42mm; }}
.toc {{ padding: 14mm 6mm 0 6mm; }}
.toc h2 {{ color: #0f172a; font-size: 20pt; font-weight: bold; margin: 0 0 5mm 0; }}
.tline {{ display: table; width: 100%; height: 1mm; background: linear-gradient(to left, #14b8a6, #2563eb);
  border-radius: 1mm; margin-bottom: 7mm; }}
.row {{ display: flex; align-items: center; gap: 4mm; padding: 4.6mm 2mm; border-bottom: 0.2mm solid #e2e8f0; }}
.nbadge {{ flex: none; width: 10mm; height: 10mm; border-radius: 3mm; color: #ffffff; font-weight: bold;
  font-size: 13pt; background: linear-gradient(135deg, #2563eb, #2dd4bf);
  display: flex; align-items: center; justify-content: center; }}
.ttl {{ flex: 1; color: #1e293b; font-size: 11.4pt; font-weight: 600; line-height: 1.7; }}
.ttl small {{ display: block; color: #0d9488; font-size: 8.8pt; font-weight: normal; margin-top: 1mm; }}
.rng {{ flex: none; color: #475569; font-size: 9.6pt; }}
.seccover-inner {{ padding: 42mm 24mm 0 24mm; text-align: center; }}
.seccover .pill {{ display: inline-block; padding: 2mm 7mm; border-radius: 20mm;
  background: linear-gradient(to left, #2563eb, #2dd4bf); color: #ffffff; font-size: 10.5pt; font-weight: 600; }}
table.icnt {{ display: table; margin: 12mm auto 8mm auto; }}
.icn {{ width: 34mm; height: 34mm; border-radius: 50%; border: 0.4mm solid rgba(94,234,212,0.55);
  background: rgba(13,21,36,0.55); text-align: center; vertical-align: middle; }}
.sess {{ color: #7dd3fc; font-size: 11pt; margin-bottom: 4mm; }}
.seccover h2 {{ color: #ffffff; font-size: 19pt; font-weight: bold; line-height: 1.7; margin: 0 0 6mm 0; }}
.range {{ color: #cbd5e1; font-size: 10.5pt; margin-bottom: 10mm; }}
table.meta {{ margin: 0 auto; border-collapse: separate; border-spacing: 5mm 0; }}
.mbox {{ background: rgba(255,255,255,0.06); border: 0.3mm solid rgba(148,163,184,0.35);
  border-radius: 3.5mm; padding: 4mm 8mm; text-align: center; }}
.mbox .n {{ display: block; font-size: 14pt; font-weight: bold; color: #2dd4bf; }}
.mbox .l {{ display: block; font-size: 9pt; color: #94a3b8; margin-top: 1mm; }}
.qbody {{ padding: 6mm 1mm 2mm 1mm; }}
.subhead {{ display: flex; align-items: center; gap: 3mm; margin: 6mm 2mm 4.5mm 2mm; }}
.subhead .sd, .subhead .sl {{ flex: 1; height: 0.6mm; border-radius: 1mm;
  background: linear-gradient(to left, #2563eb, #2dd4bf); opacity: 0.75; }}
.subhead .st {{ color: #1d4ed8; font-size: 12pt; font-weight: bold; }}
.qcard {{ background: #ffffff; border: 0.2mm solid #e2e8f0; border-radius: 4mm;
  box-shadow: 0 1mm 4mm rgba(15,23,42,0.08); margin-bottom: 6mm; break-inside: avoid; }}
.qhead {{ display: flex; align-items: flex-start; gap: 3mm; padding: 4mm 4.5mm;
  background: linear-gradient(to left, #eff6ff, #f8fafc); border-bottom: 0.2mm solid #e2e8f0; }}
.qnum {{ flex: none; width: 9mm; height: 9mm; border-radius: 50%; color: #ffffff; font-size: 10.6pt;
  font-weight: bold; background: linear-gradient(135deg, #2563eb, #14b8a6);
  display: flex; align-items: center; justify-content: center; }}
.qtext {{ flex: 1; color: #0f172a; font-size: 11.1pt; font-weight: 600; line-height: 1.9; }}
.clin {{ flex: none; background: #ccfbf1; color: #0f766e; border: 0.2mm solid #5eead4;
  font-size: 8.2pt; border-radius: 8mm; padding: 1mm 3.2mm; margin-top: 1.2mm; }}
.optswrap {{ padding: 2.5mm 3mm 0 3mm; }}
table.opts {{ width: 100%; border-collapse: separate; border-spacing: 2.6mm; }}
td.opt {{ width: 50%; background: #ffffff; border: 0.25mm solid #e2e8f0; border-radius: 3mm;
  padding: 3mm 3mm; vertical-align: middle; }}
.ol {{ display: inline-block; min-width: 6.5mm; height: 6.5mm; border-radius: 2mm; background: #eff6ff;
  color: #2563eb; font-size: 9pt; font-weight: bold; text-align: center; line-height: 6.5mm;
  margin-left: 2.5mm; vertical-align: middle; }}
.ot {{ color: #334155; font-size: 9.9pt; line-height: 1.85; vertical-align: middle; }}
.divider {{ display: flex; align-items: center; gap: 3mm; color: #94a3b8; font-size: 8.6pt;
  padding: 1mm 6mm 3mm 6mm; }}
.divider .dl {{ flex: 1; border-top: 0.3mm dashed #cbd5e1; }}
.answer {{ background: linear-gradient(to left, #dbeafe, #ccfbf1); padding: 3.2mm 4mm 3.6mm 4mm;
  border-top: 0.25mm solid #cde8f5; }}
.arow {{ display: flex; align-items: center; gap: 2.6mm; margin-bottom: 2.2mm; }}
.apill {{ background: linear-gradient(to left, #2563eb, #14b8a6); color: #ffffff; font-size: 8.8pt;
  font-weight: 600; border-radius: 10mm; padding: 0.9mm 3.6mm; }}
.aletter {{ font-weight: bold; color: #0f172a; font-size: 10.6pt; }}
.atick {{ color: #0d9488; font-weight: bold; }}
.expl {{ background: rgba(255,255,255,0.82); border-radius: 2.6mm; padding: 2.6mm 3.2mm; }}
.expl .eh {{ color: #1d4ed8; font-weight: bold; font-size: 9.4pt; margin-bottom: 0.8mm; }}
.expl .et {{ color: #334155; font-size: 9.7pt; line-height: 1.95; text-align: justify; }}
"""

def q_card(q, number):
    rng = random.Random(9973 * number + 17)   # چرخش تعیین‌گرا گزینه‌ها
    idx = list(range(len(q['o'])))
    rng.shuffle(idx)
    opts = [q['o'][i] for i in idx]
    ans = idx.index(q['a'])
    cells = []
    for i, o in enumerate(opts):
        cells.append(f'<td class="opt"><span class="ol">{OPT_LETTERS[i]}</span>'
                     f'<span class="ot">{esc(o)}</span></td>')
    while len(cells) % 2:
        cells.append('<td class="opt"></td>')
    rows = [''.join(cells[i:i+2]) for i in range(0, len(cells), 2)]
    opts_table = '<table class="opts"><tr>' + '</tr><tr>'.join(rows) + '</tr></table>'
    clin = '<span class="clin">سناریوی بالینی</span>' if q.get('cl') else ''
    return f"""
<div class="qcard">
  <div class="qhead">
    <span class="qnum">{fa(number)}</span>
    <span class="qtext">{esc(q['q'])}</span>
    {clin}
  </div>
  <div class="optswrap">{opts_table}</div>
  <div class="divider"><span class="dl"></span><span>پاسخ و توضیح در ادامه</span><span class="dl"></span></div>
  <div class="answer">
    <div class="arow">
      <span class="apill">پاسخ صحیح</span>
      <span class="aletter">گزینه {OPT_LETTERS[ans]}</span>
      <span class="atick">✓</span>
    </div>
    <div class="expl">
      <div class="eh">توضیح</div>
      <div class="et">{esc(q['e'])}</div>
    </div>
  </div>
</div>"""

def build(chapters_data, out_path, book_label='فیزیولوژی پزشکی'):
    parts = []
    total_q = sum(len(ch['qs']) for ch in chapters_data)
    total_clin = sum(1 for ch in chapters_data for q in ch['qs'] if q.get('cl'))
    parts.append(f"""
<div class="cover"><div class="cover-inner">
  <img class="logo" src="{LOGO}"/>
  <div class="rule"></div>
  <div class="kicker">بانک سوالات تستی</div>
  <h1>بانک سوالات طبقه‌بندی‌شده {book_label}</h1>
  <div class="subtitle">رفرنس جزوه {book_label} — {REF_DATE}</div>
  <div class="ref">مرجع: جزوه {book_label} — {REF_DATE} | همه سوالات به‌ترتیب مباحث جزوه طبقه‌بندی شده‌اند</div>
  <table class="stats"><tr>
    <td class="stat"><span class="num">{fa(total_q)}</span><span class="lbl">سوال</span></td>
    <td class="stat"><span class="num">{fa(len(chapters_data))}</span><span class="lbl">مبحث</span></td>
    <td class="stat"><span class="num">{fa(total_clin)}</span><span class="lbl">سوال بالینی</span></td>
  </tr></table>
  <div class="foot">پاسخ هر سوال با توضیح مختصر، در پایین همان کارت آمده است</div>
</div></div>""")
    rows, num, ranges = [], 1, []
    for ch in chapters_data:
        n = len(ch['qs']); nclin = sum(1 for q in ch['qs'] if q.get('cl'))
        ranges.append((num, num + n - 1))
        meta = CHAPTERS[ch['no'] - 1]
        rows.append(f"""<div class="row">
          <span class="nbadge">{fa(ch['no'])}</span>
          <span class="ttl">{esc(meta['session'])}: {esc(meta['title'])}<small>{fa(nclin)} سوال بالینی در انتهای مبحث</small></span>
          <span class="rng">سوالات {fa(num)} تا {fa(num+n-1)} ({fa(n)} سوال)</span>
        </div>""")
        num += n
    parts.append(f'<div class="toc"><h2>فهرست مباحث</h2><div class="tline"></div>{"".join(rows)}</div>')
    num = 1
    for ch, rng in zip(chapters_data, ranges):
        meta = CHAPTERS[ch['no'] - 1]
        n = len(ch['qs']); nclin = sum(1 for q in ch['qs'] if q.get('cl'))
        parts.append(f"""
<div class="seccover"><div class="seccover-inner">
  <span class="pill">مبحث {fa(ch['no'])} از {fa(len(chapters_data))}</span>
  <table class="icnt"><tr><td class="icn">{icon_svg(meta['icon'], size=72, stroke='#5eead4', sw=3)}</td></tr></table>
  <div class="sess">{esc(meta['session'])}</div>
  <h2>{esc(meta['title'])}</h2>
  <div class="range">سوالات {fa(rng[0])} تا {fa(rng[1])}</div>
  <table class="meta"><tr>
    <td class="mbox"><span class="n">{fa(n)}</span><span class="l">سوال</span></td>
    <td class="mbox"><span class="n">{fa(nclin)}</span><span class="l">بالینی</span></td>
    <td class="mbox"><span class="n">{fa(n - nclin)}</span><span class="l">مفهومی</span></td>
  </tr></table>
</div></div>""")
        cur_sub, body = None, []
        for q in ch['qs']:
            sub = q.get('t')
            if sub and sub != cur_sub and not q.get('cl'):
                cur_sub = sub
                body.append(f'<div class="subhead"><span class="sd"></span><span class="st">{esc(sub)}</span><span class="sl"></span></div>')
            if q.get('cl') and cur_sub != '__clin__':
                cur_sub = '__clin__'
                body.append('<div class="subhead"><span class="sd"></span><span class="st">سوالات بالینی (سناریو-محور)</span><span class="sl"></span></div>')
            body.append(q_card(q, num)); num += 1
        parts.append('<div class="qbody">' + ''.join(body) + '</div>')
    doc = ('<html><head><meta charset="utf-8"/><style>' + CSS.format(fd=FONT_DIR, BOOK=book_label) +
           '</style></head><body>' + ''.join(parts) + '</body></html>')
    open(out_path.replace('.pdf', '.html'), 'w', encoding='utf-8').write(doc)
    from weasyprint import HTML
    HTML(string=doc, base_url=BASE).write_pdf(out_path)
    return out_path

REF_DATE = 'بهمن ۱۴۰۴'  # <<< تاریخ جزوه درس جدید

if __name__ == '__main__':
    data = []
    for i in range(1, 8):
        p = os.path.join(LOCK, f'ch{i:02d}.json')
        if os.path.exists(p):
            data.append(dict(no=i, qs=json.load(open(p, encoding='utf-8'))))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'HumsYar_Bank.pdf')
    build(data, out)
    print('rendered', out)
```

> نکته: در CSS بالا `{BOOK}` نام درس در پانوشت صفحه است؛ چون CSS با `.format()` پر می‌شود، تمام آکولادهای CSS دوتایی نوشته شده‌اند — این الگو را حفظ کن.

---

## پیوست ب — دستورهای آماده محیط

```bash
pip install weasyprint pypdfium2 pillow
# فونت:
unzip vazir.zip && cp …/fonts/ttf/Vazirmatn-{Regular,Medium,Bold}.ttf render/fonts/
# لوگو (شفاف‌سازی پس‌زمینه تیره):
python3 - <<'EOF'
from PIL import Image
im=Image.open('uploads/image-5.png').convert('RGBA'); px=im.load(); w,h=im.size
br,bg,bb,_=px[0,0]
for y in range(h):
    for x in range(w):
        r,g,b,a=px[x,y]; d=((r-br)**2+(g-bg)**2+(b-bb)**2)**0.5
        if d<25: px[x,y]=(r,g,b,0)
        elif d<70: px[x,y]=(r,g,b,int(255*(d-25)/45))
im.save('render/logo_transparent.png')
EOF
# رندر + QC سریع:
python3 render/render.py /home/user/HumsYar_<درس>.pdf
python3 - <<'EOF'
import pypdfium2 as pdfium, re, collections
pdf=pdfium.PdfDocument('<فایل>'); print('pages:',len(pdf))
h=open('<فایل html>',encoding='utf-8').read()
fa='۰۱۲۳۴۵۶۷۸۹'; unfa=lambda s:int(''.join(str(fa.index(c)) for c in s))
nums=[unfa(x) for x in re.findall(r'<span class="qnum">([۰-۹]+)</span>',h)]
print('seq ok:', nums==list(range(1,len(nums)+1)))
print(collections.Counter(re.findall(r'<span class="aletter">گزینه (الف|ب|ج|د)</span>',h)))
EOF
```

---

## پیوست ج — چک‌لیست تحویل به کاربر

- [ ] PDF در ریشه workspace ذخیره و present شده.
- [ ] گزارش کوتاه: تعداد صفحه/سوال/بالینی/مبحث + نتیجه QC + مسیر فایل‌های منبع (lock/render).

*پایان پرامپت master — نسخه ۱.۰ (برگرفته از پروژه بانک فیزیولوژی HumsYar، مهر ۱۴۰۴)*
