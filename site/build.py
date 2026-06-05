#!/usr/bin/env python3
"""
Build a bilingual static insurance education site for Cloudflare Pages.

Input:
  ../reddit_crawler/reports/knowledge_base/knowledge_items.jsonl

Output:
  dist/
"""
from __future__ import annotations

import html
import json
import shutil
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
DIST = ROOT / "dist"
ASSETS = ROOT / "assets"
KB_PATH = REPO / "reddit_crawler" / "reports" / "knowledge_base" / "knowledge_items.jsonl"
SITE_URL = "https://segurotools.com"
TODAY = date.today().isoformat()


TEXT = {
    "en": {
        "brand": "SeguroTools",
        "tagline": "Insurance calculators and plain-English guides for U.S. households.",
        "home": "Home",
        "calculators": "Calculators",
        "blog": "Blog",
        "knowledge": "Knowledge Base",
        "about": "About",
        "contact": "Contact",
        "privacy": "Privacy",
        "disclaimer": "Disclaimer",
        "terms": "Terms",
        "author": "Author",
        "read_more": "Read guide",
        "use_tool": "Use calculator",
        "related": "Related reading",
        "sources": "Sources",
        "result": "Result",
        "calculator_intro": "Use this educational worksheet to estimate a planning range, then verify details with official sources or a licensed professional.",
        "email_label": "Email address",
        "email_help": "Send the result to your inbox and allow educational follow-up. A copy is sent to the site owner for follow-up only after consent.",
        "consent": "I agree to receive this report and occasional educational follow-up. I can ask to be removed at any time.",
        "not_advice": "Educational estimate only. This site does not sell insurance, negotiate coverage, or provide legal, tax, financial, or insurance advice.",
        "updated": "Reviewed",
    },
    "es": {
        "brand": "SeguroTools",
        "tagline": "Calculadoras y guías claras sobre seguros en Estados Unidos.",
        "home": "Inicio",
        "calculators": "Calculadoras",
        "blog": "Blog",
        "knowledge": "Base de conocimiento",
        "about": "Acerca de",
        "contact": "Contacto",
        "privacy": "Privacidad",
        "disclaimer": "Aviso",
        "terms": "Términos",
        "author": "Autor",
        "read_more": "Leer guía",
        "use_tool": "Usar calculadora",
        "related": "Lecturas relacionadas",
        "sources": "Fuentes",
        "result": "Resultado",
        "calculator_intro": "Usa esta hoja educativa para estimar un rango de planificación y luego verifica los detalles con fuentes oficiales o un profesional autorizado.",
        "email_label": "Correo electrónico",
        "email_help": "Envía el resultado a tu correo y permite seguimiento educativo. Una copia se envía al propietario del sitio solo con consentimiento.",
        "consent": "Acepto recibir este reporte y seguimiento educativo ocasional. Puedo pedir la eliminación de mi contacto en cualquier momento.",
        "not_advice": "Estimación educativa únicamente. Este sitio no vende seguros, negocia cobertura ni ofrece asesoría legal, fiscal, financiera o de seguros.",
        "updated": "Revisado",
    },
}


CATEGORY_LABELS = {
    "life": {"en": "Life and final expense", "es": "Vida y gastos finales"},
    "health": {"en": "Health, ACA, and Medicare", "es": "Salud, ACA y Medicare"},
    "property": {"en": "Auto, home, and property", "es": "Auto, vivienda y propiedad"},
    "income": {"en": "Income, business, and work", "es": "Ingresos, negocio y trabajo"},
    "consumer": {"en": "Consumer protection", "es": "Protección al consumidor"},
}


TOPIC_CATEGORY = {
    "life_insurance": "life",
    "final_expense": "life",
    "health_aca": "health",
    "immigrant_health": "health",
    "medicare": "health",
    "auto_insurance": "property",
    "home_renters_flood": "property",
    "pet_insurance": "property",
    "disability_insurance": "income",
    "business_liability": "income",
    "gig_worker_insurance": "income",
    "insurance_terms": "consumer",
    "insurance_scams": "consumer",
    "claims_appeals": "consumer",
}


CALCULATORS = [
    {
        "key": "life",
        "topic": "life_insurance",
        "category": "life",
        "slug": {"en": "life-insurance-needs", "es": "necesidad-seguro-vida"},
        "title": {"en": "Life insurance needs calculator", "es": "Calculadora de necesidad de seguro de vida"},
        "summary": {
            "en": "Estimate a coverage range using DIME and income replacement logic.",
            "es": "Estima un rango de cobertura usando DIME y reemplazo de ingresos.",
        },
        "fields": [
            ("debt", "Debts other than mortgage", "Deudas sin hipoteca", 12000),
            ("income", "Annual income to replace", "Ingreso anual a reemplazar", 65000),
            ("years", "Years of support", "Años de apoyo", 12),
            ("mortgage", "Mortgage balance", "Saldo hipotecario", 220000),
            ("education", "Education fund", "Fondo educativo", 60000),
            ("finalCosts", "Final expenses", "Gastos finales", 12000),
            ("savings", "Savings available", "Ahorros disponibles", 30000),
            ("existing", "Existing life coverage", "Cobertura de vida existente", 100000),
        ],
    },
    {
        "key": "final-expense",
        "topic": "final_expense",
        "category": "life",
        "slug": {"en": "final-expense", "es": "gastos-finales"},
        "title": {"en": "Final expense planning calculator", "es": "Calculadora de gastos finales"},
        "summary": {
            "en": "Estimate funeral, travel, debt, and immediate cash needs.",
            "es": "Estima funeral, viajes, deudas y necesidades inmediatas.",
        },
        "fields": [
            ("service", "Funeral or memorial services", "Servicios funerarios o memoriales", 9000),
            ("cemetery", "Burial, cremation, or cemetery items", "Entierro, cremación o cementerio", 3500),
            ("travel", "Family travel and lodging", "Viajes y alojamiento familiar", 1500),
            ("debts", "Small debts to clear", "Deudas menores", 2500),
            ("cushion", "Immediate cash cushion", "Reserva inmediata", 3000),
            ("assets", "Cash or existing coverage", "Efectivo o cobertura existente", 2000),
        ],
    },
    {
        "key": "aca",
        "topic": "health_aca",
        "category": "health",
        "slug": {"en": "aca-subsidy-estimator", "es": "estimador-subsidio-aca"},
        "title": {"en": "ACA subsidy planning estimator", "es": "Estimador de subsidio ACA"},
        "summary": {
            "en": "Estimate FPL percentage and a rough premium tax credit planning range.",
            "es": "Estima el porcentaje FPL y un rango aproximado de crédito fiscal.",
        },
        "fields": [
            ("household", "Household size", "Tamaño del hogar", 3),
            ("income", "Projected annual income", "Ingreso anual proyectado", 52000),
            ("benchmark", "Monthly benchmark premium", "Prima mensual de referencia", 780),
        ],
        "select": ("region", "FPL region", "Región FPL", [("contiguous", "48 states/DC", "48 estados/DC"), ("alaska", "Alaska", "Alaska"), ("hawaii", "Hawaii", "Hawái")]),
    },
    {
        "key": "home",
        "topic": "home_renters_flood",
        "category": "property",
        "slug": {"en": "home-renters-coverage-gap", "es": "brecha-cobertura-vivienda-inquilinos"},
        "title": {"en": "Home and renters coverage gap calculator", "es": "Calculadora de brecha para vivienda e inquilinos"},
        "summary": {
            "en": "Estimate personal property, additional living expense, liability, and flood gaps.",
            "es": "Estima propiedad personal, vivienda temporal, responsabilidad e inundación.",
        },
        "fields": [
            ("contents", "Personal property / dwelling gap", "Brecha de propiedad/vivienda", 45000),
            ("rent", "Monthly rent or temporary housing cost", "Renta mensual o vivienda temporal", 2200),
            ("months", "Months of extra living expenses", "Meses de gastos temporales", 6),
            ("liability", "Liability planning amount", "Monto de responsabilidad", 100000),
            ("deductible", "Deductible you can absorb", "Deducible que puedes absorber", 2500),
            ("flood", "Flood coverage gap", "Brecha por inundación", 25000),
        ],
    },
    {
        "key": "disability",
        "topic": "disability_insurance",
        "category": "income",
        "slug": {"en": "disability-income-gap", "es": "brecha-ingresos-incapacidad"},
        "title": {"en": "Disability income gap calculator", "es": "Calculadora de brecha por incapacidad"},
        "summary": {
            "en": "Estimate monthly income replacement and elimination-period cash needs.",
            "es": "Estima reemplazo mensual de ingresos y la brecha durante el periodo de espera.",
        },
        "fields": [
            ("monthlyIncome", "Monthly income", "Ingreso mensual", 6200),
            ("replacement", "Target replacement percent", "Porcentaje de reemplazo", 60),
            ("months", "Months to protect", "Meses a proteger", 24),
            ("existing", "Existing monthly benefit", "Beneficio mensual existente", 1200),
            ("emergency", "Emergency savings", "Ahorros de emergencia", 8000),
            ("waiting", "Elimination period in days", "Periodo de espera en días", 90),
        ],
    },
    {
        "key": "pet",
        "topic": "pet_insurance",
        "category": "property",
        "slug": {"en": "pet-insurance-breakeven", "es": "punto-equilibrio-seguro-mascotas"},
        "title": {"en": "Pet insurance break-even calculator", "es": "Calculadora de punto de equilibrio para mascotas"},
        "summary": {
            "en": "Compare annual premiums, deductibles, reimbursement, and emergency funds.",
            "es": "Compara primas, deducibles, reembolso y fondo de emergencia.",
        },
        "fields": [
            ("premium", "Monthly premium", "Prima mensual", 48),
            ("deductible", "Annual deductible", "Deducible anual", 500),
            ("reimbursement", "Reimbursement percent", "Porcentaje de reembolso", 80),
            ("expected", "Expected routine vet spend", "Gasto veterinario rutinario", 600),
            ("emergency", "Emergency fund for pet care", "Fondo de emergencia para mascota", 1000),
        ],
    },
    {
        "key": "auto",
        "topic": "auto_insurance",
        "category": "property",
        "slug": {"en": "auto-liability-gap", "es": "brecha-responsabilidad-auto"},
        "title": {"en": "Auto liability gap worksheet", "es": "Hoja de brecha de responsabilidad de auto"},
        "summary": {
            "en": "Compare assets, income, state minimums, current limits, and rideshare gaps.",
            "es": "Compara activos, ingresos, mínimos estatales, límites actuales y brechas por apps.",
        },
        "fields": [
            ("assets", "Assets exposed to liability", "Activos expuestos", 120000),
            ("income", "Annual income", "Ingreso anual", 75000),
            ("stateMinimum", "State minimum liability limit", "Mínimo estatal", 30000),
            ("currentLimit", "Current liability limit", "Límite actual", 100000),
            ("rideshare", "Rideshare/delivery gap allowance", "Brecha por rideshare/delivery", 50000),
        ],
    },
    {
        "key": "business",
        "topic": "business_liability",
        "category": "income",
        "slug": {"en": "small-business-liability-gap", "es": "brecha-responsabilidad-negocio"},
        "title": {"en": "Small business insurance gap worksheet", "es": "Hoja de brecha de seguro para negocio"},
        "summary": {
            "en": "Estimate liability, contract, payroll, and equipment gaps for small businesses.",
            "es": "Estima brechas de responsabilidad, contratos, nómina y equipo.",
        },
        "fields": [
            ("revenue", "Annual revenue", "Ingresos anuales", 180000),
            ("contracts", "Largest contract exposure", "Mayor exposición contractual", 75000),
            ("payroll", "Annual payroll", "Nómina anual", 90000),
            ("equipment", "Equipment replacement cost", "Costo de reemplazar equipo", 35000),
            ("current", "Current coverage limit", "Límite actual", 100000),
        ],
    },
]


LONGTAILS = {
    "life_insurance": ["how much life insurance do I need with mortgage and kids", "cuánto seguro de vida necesito con hijos"],
    "final_expense": ["funeral cost estimator by family situation", "seguro para gastos finales en Estados Unidos"],
    "health_aca": ["ACA subsidy estimator for self employed income", "subsidio Obamacare para trabajadores independientes"],
    "immigrant_health": ["health insurance options for mixed status families", "seguro médico para inmigrantes en Estados Unidos"],
    "medicare": ["Medicare Advantage vs Original Medicare Spanish guide", "Medicare en español partes A B C D"],
    "auto_insurance": ["car insurance liability gap for delivery drivers", "seguro de auto para delivery y rideshare"],
    "home_renters_flood": ["renters insurance flood coverage gap checklist", "seguro de inquilinos cubre inundación"],
    "pet_insurance": ["pet insurance break even calculator deductible reimbursement", "seguro para mascotas vale la pena calculadora"],
    "disability_insurance": ["disability income gap calculator self employed", "seguro de incapacidad para trabajadores independientes"],
    "business_liability": ["small business liability insurance checklist home based", "seguro para negocio pequeño en casa"],
    "gig_worker_insurance": ["gig worker insurance checklist rideshare delivery health", "seguro para Uber Doordash independiente"],
    "insurance_terms": ["insurance deductible premium exclusion explained examples", "deducible prima cobertura ejemplos"],
    "insurance_scams": ["health insurance scam red flags Medicare calls", "estafas de seguro médico Medicare"],
    "claims_appeals": ["insurance claim denied what documents to gather", "reclamación de seguro denegada qué documentos reunir"],
}


def main() -> None:
    reset_dist()
    kb = load_knowledge()
    copy_assets()

    paths = []
    paths.append(write_page("index.html", root_redirect()))
    for lang in ("en", "es"):
        paths.extend(build_language(kb, lang))

    write_page("robots.txt", robots(), binary=False)
    write_page("sitemap.xml", sitemap(paths), binary=False)
    write_page("_redirects", redirects(), binary=False)
    write_page("_headers", headers(), binary=False)
    print(f"Built {len(paths)} pages into {DIST}")


def reset_dist() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)


def copy_assets() -> None:
    shutil.copytree(ASSETS, DIST / "assets")


def load_knowledge() -> list[dict]:
    if not KB_PATH.exists():
        raise SystemExit(f"Missing knowledge export: {KB_PATH}")
    with KB_PATH.open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    return sorted(rows, key=lambda row: row.get("priority", 999))


def build_language(kb: list[dict], lang: str) -> list[str]:
    paths = []
    paths.append(write_html(lang, "index.html", home_page(kb, lang), title=home_title(lang), desc=TEXT[lang]["tagline"], alt_path=alt("index.html", lang)))
    paths.append(write_html(lang, f"{calc_base(lang)}/index.html", calculators_index(kb, lang), title=page_title(lang, TEXT[lang]["calculators"]), desc=calculator_desc(lang), alt_path=f"{other_lang(lang)}/{calc_base(other_lang(lang))}/"))
    paths.append(write_html(lang, "blog/index.html", blog_index(kb, lang), title=page_title(lang, TEXT[lang]["blog"]), desc=blog_desc(lang), alt_path=alt("blog/index.html", lang)))
    paths.append(write_html(lang, f"{knowledge_base(lang)}/index.html", knowledge_index(kb, lang), title=page_title(lang, TEXT[lang]["knowledge"]), desc=knowledge_desc(lang), alt_path=f"{other_lang(lang)}/{knowledge_base(other_lang(lang))}/"))

    for category in CATEGORY_LABELS:
        rel = f"blog/{category_slug(category, lang)}/index.html"
        cat_alt = f"{other_lang(lang)}/blog/{category_slug(category, other_lang(lang))}/"
        paths.append(write_html(lang, rel, category_page(kb, lang, category), title=page_title(lang, CATEGORY_LABELS[category][lang]), desc=category_desc(lang, category), alt_path=cat_alt))

    for calc in CALCULATORS:
        rel = calc_path(calc, lang)
        other = other_lang(lang)
        calc_alt = f"{other}/{calc_path(calc, other)}"
        paths.append(write_html(lang, rel, calculator_page(kb, lang, calc), title=page_title(lang, calc["title"][lang]), desc=calc["summary"][lang], alt_path=calc_alt))
        guide_rel = article_path(guide_slug(calc, lang), lang)
        guide_alt_slug = guide_slug(calc, other)
        guide_alt = f"{other}/{article_path(guide_alt_slug, other)}"
        paths.append(write_html(lang, guide_rel, calculator_guide(kb, lang, calc), title=page_title(lang, guide_title(calc, lang)), desc=calc["summary"][lang], alt_path=guide_alt))

    for topic in kb:
        rel = article_path(topic_slug(topic, lang), lang)
        paths.append(write_html(lang, rel, topic_article(kb, lang, topic), title=page_title(lang, topic_name(topic, lang)), desc=topic_desc(topic, lang), alt_path=f"{other_lang(lang)}/{article_path(topic_slug(topic, other_lang(lang)), other_lang(lang))}"))
        krel = knowledge_path(topic, lang)
        paths.append(write_html(lang, krel, topic_knowledge_page(kb, lang, topic), title=page_title(lang, f"{topic_name(topic, lang)} sources"), desc=topic_desc(topic, lang), alt_path=f"{other_lang(lang)}/{knowledge_path(topic, other_lang(lang))}"))

    for slug, body_fn in legal_pages(lang).items():
        paths.append(write_html(lang, f"{slug}/index.html", body_fn(), title=page_title(lang, TEXT[lang][slug if slug != "terms" else "terms"]), desc=TEXT[lang]["not_advice"], alt_path=alt(f"{slug}/index.html", lang)))

    return paths


def home_page(kb: list[dict], lang: str) -> str:
    t = TEXT[lang]
    top_topics = sorted(kb, key=lambda row: row.get("pain_link_count", 0), reverse=True)[:4]
    calc_cards = "\n".join(card(calc["title"][lang], calc["summary"][lang], rel(calc_path(calc, lang), lang), t["use_tool"]) for calc in CALCULATORS[:4])
    topic_cards = "\n".join(card(topic_name(topic, lang), topic_desc(topic, lang), rel(article_path(topic_slug(topic, lang), lang), lang), t["read_more"]) for topic in top_topics)
    return f"""
    <section class="hero">
      <div class="hero-inner">
        <div class="hero-copy">
          <p class="eyebrow">{esc(t["knowledge"])} + {esc(t["calculators"])}</p>
          <h1>{'Insurance decisions, explained before you buy.' if lang == 'en' else 'Decisiones de seguro, claras antes de comprar.'}</h1>
          <p class="lead">{esc(t["tagline"])} {'Built for long-tail questions that big comparison sites often skip.' if lang == 'en' else 'Diseñado para dudas específicas que los comparadores grandes suelen omitir.'}</p>
          <div class="hero-actions">
            <a class="button" href="{rel(f'{calc_base(lang)}/index.html', lang)}">{esc(t["calculators"])}</a>
            <a class="button secondary" href="{rel('blog/index.html', lang)}">{esc(t["blog"])}</a>
          </div>
        </div>
      </div>
    </section>
    <section class="section">
      <div class="container">
        <div class="section-head">
          <div><p class="eyebrow">{esc(t["calculators"])}</p><h2>{'Start with a worksheet' if lang == 'en' else 'Empieza con una hoja de cálculo'}</h2></div>
          <p>{esc(t["calculator_intro"])}</p>
        </div>
        <div class="grid cols-4">{calc_cards}</div>
      </div>
    </section>
    <section class="section alt">
      <div class="container">
        <div class="section-head">
          <div><p class="eyebrow">SEO</p><h2>{'High-intent guides from real questions' if lang == 'en' else 'Guías con intención real de búsqueda'}</h2></div>
          <p>{'Articles are grouped by user pain points and backed by official sources such as NAIC, CMS, Medicare, FEMA, FTC, IRS, and SBA.' if lang == 'en' else 'Los artículos se agrupan por problemas reales y se apoyan en fuentes oficiales como NAIC, CMS, Medicare, FEMA, FTC, IRS y SBA.'}</p>
        </div>
        <div class="grid cols-4">{topic_cards}</div>
      </div>
    </section>
    <section class="section">
      <div class="container grid cols-3">
        {stat_card('14', 'knowledge topics', 'temas de conocimiento', lang)}
        {stat_card('8', 'interactive calculators', 'calculadoras interactivas', lang)}
        {stat_card('36+', 'bilingual deep pages', 'páginas profundas bilingües', lang)}
      </div>
    </section>
    """


def calculators_index(kb: list[dict], lang: str) -> str:
    t = TEXT[lang]
    cards = "\n".join(card(calc["title"][lang], calc["summary"][lang], rel(calc_path(calc, lang), lang), t["use_tool"]) for calc in CALCULATORS)
    return page_intro(t["calculators"], calculator_desc(lang), lang) + f"""
    <section class="section"><div class="container grid cols-3">{cards}</div></section>
    """


def calculator_page(kb: list[dict], lang: str, calc: dict) -> str:
    topic = find_topic(kb, calc["topic"])
    fields = form_fields(calc, lang)
    related_articles = related_links(kb, lang, topic, current=calc["topic"])
    return page_intro(calc["title"][lang], calc["summary"][lang], lang) + f"""
    <section class="section">
      <div class="container calculator-shell">
        <div class="card">
          <p class="disclaimer">{esc(TEXT[lang]["calculator_intro"])}</p>
          <form id="{esc(calc['key'])}-form" class="calc-form" data-calculator="{esc(calc['key'])}" data-title="{esc(calc['title'][lang])}">
            <div class="field-grid">{fields}</div>
            <button class="button" type="submit">{'Update estimate' if lang == 'en' else 'Actualizar estimación'}</button>
          </form>
        </div>
        <aside class="result-panel" data-result-for="{esc(calc['key'])}-form">
          <p class="eyebrow">{esc(TEXT[lang]['calculator_intro'].split('.')[0])}</p>
          <h2>{esc(TEXT[lang]['result'])}</h2>
          <div class="result-main" data-result-main>$0</div>
          <div class="result-breakdown" data-result-breakdown></div>
          <ul data-result-notes></ul>
          <div class="email-box">
            <label>{esc(TEXT[lang]['email_label'])}<input type="email" name="email" placeholder="name@example.com" required></label>
            <label class="checkbox"><input type="checkbox" name="consent"><span>{esc(TEXT[lang]['consent'])}</span></label>
            <p class="small">{esc(TEXT[lang]['email_help'])}</p>
            <button type="button" class="button" data-send-report>{'Send report' if lang == 'en' else 'Enviar reporte'}</button>
            <div class="status" data-email-status></div>
          </div>
        </aside>
      </div>
    </section>
    <section class="section alt">
      <div class="container grid cols-2">
        <div>{article_teaser(guide_title(calc, lang), calc['summary'][lang], rel(article_path(guide_slug(calc, lang), lang), lang), lang)}</div>
        <div>{source_box(topic, lang)}</div>
      </div>
    </section>
    <section class="section"><div class="container"><h2>{esc(TEXT[lang]['related'])}</h2><div class="grid cols-3">{related_articles}</div></div></section>
    """


def form_fields(calc: dict, lang: str) -> str:
    fields = []
    if calc.get("select"):
        name, en, es, options = calc["select"]
        opts = "".join(f'<option value="{esc(value)}">{esc(en_label if lang == "en" else es_label)}</option>' for value, en_label, es_label in options)
        fields.append(f'<label>{esc(en if lang == "en" else es)}<select name="{esc(name)}">{opts}</select></label>')
    for name, en, es, default in calc["fields"]:
        fields.append(f'<label>{esc(en if lang == "en" else es)}<input type="number" name="{esc(name)}" value="{default}" min="0" step="1"></label>')
    return "\n".join(fields)


def blog_index(kb: list[dict], lang: str) -> str:
    blocks = []
    for category, label in CATEGORY_LABELS.items():
        topics = [topic for topic in kb if TOPIC_CATEGORY.get(topic["slug"]) == category]
        cards = "\n".join(card(topic_name(topic, lang), topic_desc(topic, lang), rel(article_path(topic_slug(topic, lang), lang), lang), TEXT[lang]["read_more"]) for topic in topics[:4])
        blocks.append(f'<section class="section"><div class="container"><div class="section-head"><h2>{esc(label[lang])}</h2><a class="button ghost" href="{rel(f"blog/{category_slug(category, lang)}/index.html", lang)}">{esc(TEXT[lang]["read_more"])}</a></div><div class="grid cols-4">{cards}</div></div></section>')
    return page_intro(TEXT[lang]["blog"], blog_desc(lang), lang) + "\n".join(blocks)


def category_page(kb: list[dict], lang: str, category: str) -> str:
    topics = [topic for topic in kb if TOPIC_CATEGORY.get(topic["slug"]) == category]
    topic_cards = "\n".join(card(topic_name(topic, lang), topic_desc(topic, lang), rel(article_path(topic_slug(topic, lang), lang), lang), TEXT[lang]["read_more"]) for topic in topics)
    calc_cards = "\n".join(card(calc["title"][lang], calc["summary"][lang], rel(calc_path(calc, lang), lang), TEXT[lang]["use_tool"]) for calc in CALCULATORS if calc["category"] == category)
    return page_intro(CATEGORY_LABELS[category][lang], category_desc(lang, category), lang) + f"""
    <section class="section"><div class="container"><h2>{esc(TEXT[lang]['blog'])}</h2><div class="grid cols-3">{topic_cards}</div></div></section>
    <section class="section alt"><div class="container"><h2>{esc(TEXT[lang]['calculators'])}</h2><div class="grid cols-3">{calc_cards}</div></div></section>
    """


def knowledge_index(kb: list[dict], lang: str) -> str:
    rows = []
    for topic in kb:
        rows.append(f"""
        <div class="card">
          <h3><a href="{rel(knowledge_path(topic, lang), lang)}">{esc(topic_name(topic, lang))}</a></h3>
          <p>{esc(topic_desc(topic, lang))}</p>
          <div class="tag-list"><span class="pill">{topic.get('source_count', 0)} sources</span><span class="pill">{topic.get('pain_link_count', 0)} pain signals</span></div>
        </div>
        """)
    return page_intro(TEXT[lang]["knowledge"], knowledge_desc(lang), lang) + f'<section class="section"><div class="container grid cols-3">{"".join(rows)}</div></section>'


def topic_knowledge_page(kb: list[dict], lang: str, topic: dict) -> str:
    sources = source_list(topic)
    pain = pain_samples(topic, lang)
    related = related_links(kb, lang, topic)
    return page_intro(topic_name(topic, lang), topic_desc(topic, lang), lang) + f"""
    <section class="section">
      <div class="container two-col">
        <article class="article-body">
          <h2>{'Source shelf' if lang == 'en' else 'Fuentes principales'}</h2>
          {sources}
          <h2>{'User pain signals' if lang == 'en' else 'Señales de dolor del usuario'}</h2>
          {pain}
          <h2>{'Long-tail SEO angles' if lang == 'en' else 'Ángulos SEO de cola larga'}</h2>
          <ul>{''.join(f'<li>{esc(item)}</li>' for item in LONGTAILS.get(topic['slug'], []))}</ul>
        </article>
        <aside class="sidebar card">{source_box(topic, lang)}<div class="ad-slot" aria-label="Advertisement space"></div></aside>
      </div>
    </section>
    <section class="section alt"><div class="container"><h2>{esc(TEXT[lang]['related'])}</h2><div class="grid cols-3">{related}</div></div></section>
    """


def topic_article(kb: list[dict], lang: str, topic: dict) -> str:
    calc = next((c for c in CALCULATORS if c["topic"] == topic["slug"]), None)
    related = related_links(kb, lang, topic)
    body = deep_topic_body(topic, lang, calc)
    return page_intro(topic_name(topic, lang), topic_desc(topic, lang), lang) + f"""
    <section class="section">
      <div class="container two-col">
        <article class="article-body">
          <p class="small">{esc(TEXT[lang]['updated'])}: {TODAY} · {esc('Educational guide' if lang == 'en' else 'Guía educativa')}</p>
          {body}
        </article>
        <aside class="sidebar card">
          {toc_box(lang)}
          {source_box(topic, lang)}
          <div class="ad-slot" aria-label="Advertisement space"></div>
        </aside>
      </div>
    </section>
    <section class="section alt"><div class="container"><h2>{esc(TEXT[lang]['related'])}</h2><div class="grid cols-3">{related}</div></div></section>
    """


def deep_topic_body(topic: dict, lang: str, calc: dict | None) -> str:
    name = topic_name(topic, lang)
    desc = topic_desc(topic, lang)
    pain_items = [p.get("excerpt") or p.get("title") for p in topic.get("pain_samples", [])[:5]]
    pain_list = "".join(f"<li>{esc(item)}</li>" for item in pain_items if item)
    source_titles = ", ".join(source.get("authority") or source.get("domain", "") for source in topic.get("sources", [])[:4])
    longtails = LONGTAILS.get(topic["slug"], [])
    longtail_list = "".join(f"<li>{esc(item)}</li>" for item in longtails)
    tool_link = ""
    if calc:
        tool_link = f'<p><a class="button" href="{rel(calc_path(calc, lang), lang)}">{esc(TEXT[lang]["use_tool"])}: {esc(calc["title"][lang])}</a></p>'

    if lang == "en":
        return f"""
        <h2 id="what-it-means">What this topic means for a real household</h2>
        <p>{esc(desc)} The practical problem is not a lack of insurance information. The problem is that official documents, carrier brochures, and social-media answers rarely line up in one place. This guide treats {esc(name)} as a decision workflow: identify the user question, separate official rules from sales language, and turn the result into a checklist or calculator input.</p>
        <p>The knowledge base flagged {topic.get('pain_link_count', 0)} related pain signals. That volume matters because repeated confusion is a product signal: a future page should not only define terms, it should show examples, expose tradeoffs, and point to the official source that settles the question.</p>
        <h2 id="questions">Questions people are already asking</h2>
        <ul>{pain_list}</ul>
        <p>These are not quoted as legal facts. They are research prompts. Each one should be answered with an official source first, then translated into plain language and, where possible, a calculator field.</p>
        <h2 id="official">How to verify the answer</h2>
        <p>Start with official or quasi-official sources such as {esc(source_titles or 'state insurance departments and federal agencies')}. For YMYL insurance content, this source layer is not optional. It gives the page a defensible audit trail and reduces the risk of publishing recycled comparison-site claims.</p>
        {source_list(topic)}
        <h2 id="framework">A practical decision framework</h2>
        <ol>
          <li>Define the coverage question in one sentence.</li>
          <li>Identify whether the issue is eligibility, cost, coverage, claims, fraud, or documentation.</li>
          <li>Check the official source before using marketplace or carrier examples.</li>
          <li>Translate the rule into a user action: gather a document, compare a limit, estimate a gap, or ask a licensed professional.</li>
          <li>Link to a related calculator only after the reader understands the limitation of the estimate.</li>
        </ol>
        <h2 id="example">Example workflow for a page cluster</h2>
        <p>A strong content cluster starts with one narrow question rather than a broad keyword. For {esc(name)}, that question might involve a family status change, a confusing policy term, a surprise premium, a denied claim, or a Spanish-language search that does not have a good answer from large sites. The article should open with the scenario, define the rule, show a small table or calculator input, and then link to the source shelf.</p>
        <p>Next, build a comparison path. A reader who arrives through a claims question may also need a glossary page, a calculator, and a complaint checklist. A reader who arrives through a cost question may need subsidy, deductible, and cash-reserve examples. Internal links should follow those user paths, not just alphabetical topic lists.</p>
        <h2 id="documents">Documents and numbers to collect</h2>
        <p>Useful insurance education usually starts with documents. Depending on the topic, the reader may need a declarations page, benefit summary, quote, pay stub, tax estimate, mortgage statement, lease, funeral price list, pet veterinary invoice, or business contract. A page that names the document helps the user take action and also makes the article more original than a generic definition page.</p>
        <p>For state-sensitive topics, add a state review step before publishing final copy. State insurance departments can control complaint processes, minimum limits, rate filings, flood disclosure rules, and licensing checks. A future state module should store state, topic, source URL, effective date, and the page section that needs the state-specific note.</p>
        <h2 id="mistakes">Common mistakes to avoid</h2>
        <p>Do not treat a premium quote as a complete policy comparison. Do not assume a covered category means every event is covered. Do not publish state-specific conclusions without state-specific source review. For Spanish pages, avoid literal translation of policy terms when the U.S. usage is different from everyday Spanish.</p>
        <p>Another common mistake is hiding uncertainty. If a rule depends on income, immigration status, enrollment period, underwriting, state law, or policy wording, say so clearly. Trust is built when the page tells readers what can be estimated, what must be verified, and what requires a licensed or official channel.</p>
        <h2 id="spanish">Spanish localization notes</h2>
        <p>Spanish pages should not be simple mirrors of English pages. U.S. Spanish insurance searches often mix English program names with Spanish explanations: Medicare, Marketplace, deductible, Obamacare, claim, and premium can appear alongside seguro médico, cobertura, prima, and reclamación. Use both when it helps searchers, but define the U.S. meaning before giving an example.</p>
        <p>For Hispanic households, mixed-language documents are common. A useful page should acknowledge that a user may receive a policy in English, ask a question in Spanish, and need a bilingual checklist to compare both. That is a practical product advantage over broad comparison sites.</p>
        <h2 id="seo">Long-tail SEO opportunities</h2>
        <ul>{longtail_list}</ul>
        <p>These angles avoid the broad keywords dominated by large marketplaces. They focus on scenario, language, document, and calculator intent.</p>
        <p>When choosing titles, avoid competing directly for one-word insurance categories. Use modifiers that show scenario and intent: self-employed, mixed-status family, after a denial, with a mortgage, before open enrollment, for delivery drivers, with pre-existing conditions, or in Spanish. These pages can still link upward to pillar guides, but the entry point should be specific enough to be winnable.</p>
        <h2 id="next">What to build next</h2>
        <p>Turn this topic into a page cluster: one calculator or worksheet, one plain-language guide, one Spanish version, one source shelf, and at least three internal links to adjacent coverage questions.</p>
        <p>Before applying for AdSense, each page in the cluster should have a visible author method, a last-reviewed date, source links, a disclaimer, and enough original explanation to stand on its own without the calculator. The calculator is useful, but the surrounding explanation is what makes the page defensible as educational content.</p>
        {tool_link}
        <p class="disclaimer">{esc(TEXT[lang]['not_advice'])}</p>
        """

    return f"""
        <h2 id="what-it-means">Qué significa este tema para una familia real</h2>
        <p>{esc(desc)} El problema práctico no es que falte información. El problema es que las reglas oficiales, los folletos de compañías y las respuestas en redes sociales no aparecen en un mismo lugar. Esta guía trata {esc(name)} como un flujo de decisión: identificar la pregunta, separar reglas oficiales de lenguaje de ventas y convertir el resultado en una lista o campo de calculadora.</p>
        <p>La base de conocimiento marcó {topic.get('pain_link_count', 0)} señales relacionadas. Esa repetición indica que la página no debe limitarse a definir términos: debe mostrar ejemplos, explicar tradeoffs y enlazar la fuente oficial que resuelve la duda.</p>
        <h2 id="questions">Preguntas que la gente ya está haciendo</h2>
        <ul>{pain_list}</ul>
        <p>Estas señales no se usan como hechos legales. Son temas de investigación. Cada una debe responderse primero con una fuente oficial, luego traducirse a lenguaje claro y, si aplica, convertirse en un campo de calculadora.</p>
        <h2 id="official">Cómo verificar la respuesta</h2>
        <p>Empieza con fuentes oficiales o cuasi oficiales como {esc(source_titles or 'departamentos estatales de seguros y agencias federales')}. En contenido YMYL sobre seguros, esta capa de fuentes no es opcional: deja una ruta de auditoría y reduce el riesgo de repetir afirmaciones de sitios comerciales.</p>
        {source_list(topic)}
        <h2 id="framework">Marco práctico de decisión</h2>
        <ol>
          <li>Define la pregunta de cobertura en una frase.</li>
          <li>Identifica si el problema es elegibilidad, costo, cobertura, reclamación, fraude o documentación.</li>
          <li>Revisa la fuente oficial antes de usar ejemplos de mercado o compañías.</li>
          <li>Traduce la regla a una acción: reunir documentos, comparar límites, estimar una brecha o consultar a un profesional autorizado.</li>
          <li>Enlaza una calculadora solo después de explicar sus límites.</li>
        </ol>
        <h2 id="example">Ejemplo de flujo para un grupo de páginas</h2>
        <p>Un grupo fuerte empieza con una pregunta estrecha, no con una palabra clave amplia. Para {esc(name)}, la pregunta puede venir de un cambio familiar, un término confuso, una prima inesperada, una reclamación denegada o una búsqueda en español sin buena respuesta de sitios grandes. El artículo debe abrir con el escenario, definir la regla, mostrar una tabla o campo de calculadora y enlazar la fuente oficial.</p>
        <p>Después conviene crear una ruta de comparación. Quien llega por una reclamación quizá necesite glosario, calculadora y lista de queja. Quien llega por costo quizá necesite ejemplos de subsidio, deducible y reserva de efectivo. Los enlaces internos deben seguir esos caminos de usuario, no solo listas alfabéticas.</p>
        <h2 id="documents">Documentos y números que conviene reunir</h2>
        <p>La educación útil sobre seguros empieza con documentos. Según el tema, el lector puede necesitar página de declaraciones, resumen de beneficios, cotización, recibo de pago, estimación fiscal, estado hipotecario, contrato de renta, lista de precios funerarios, factura veterinaria o contrato comercial. Nombrar el documento ayuda al usuario a actuar y hace que la página sea más original que una definición genérica.</p>
        <p>Para temas sensibles por estado, agrega un paso de revisión estatal antes de publicar conclusiones. Los departamentos estatales pueden controlar quejas, límites mínimos, tarifas, reglas de inundación y verificación de licencias. Un módulo futuro por estado debería guardar estado, tema, fuente, fecha efectiva y la sección de la página que necesita nota estatal.</p>
        <h2 id="mistakes">Errores comunes que conviene evitar</h2>
        <p>No trates una prima como comparación completa de pólizas. No asumas que una categoría cubierta significa que cualquier evento está cubierto. No publiques conclusiones por estado sin revisar fuentes del estado. En español, evita traducciones literales cuando el término de seguro en EE. UU. tiene un uso específico.</p>
        <p>Otro error común es ocultar la incertidumbre. Si una regla depende de ingreso, estatus migratorio, periodo de inscripción, suscripción, ley estatal o lenguaje de la póliza, dilo claramente. La confianza aumenta cuando la página explica qué puede estimarse, qué debe verificarse y qué requiere un canal oficial o autorizado.</p>
        <h2 id="spanish">Notas de localización en español</h2>
        <p>Las páginas en español no deben ser simples copias del inglés. En búsquedas de seguros en EE. UU. se mezclan nombres de programas en inglés con explicaciones en español: Medicare, Marketplace, deductible, Obamacare, claim y premium pueden aparecer junto con seguro médico, cobertura, prima y reclamación. Usa ambos cuando ayude, pero define el significado estadounidense antes del ejemplo.</p>
        <p>En hogares hispanos es común recibir documentos en inglés, hacer la pregunta en español y necesitar una lista bilingüe para comparar. Reconocer esa realidad es una ventaja práctica frente a comparadores generales.</p>
        <h2 id="seo">Oportunidades SEO de cola larga</h2>
        <ul>{longtail_list}</ul>
        <p>Estos ángulos evitan palabras amplias dominadas por marketplaces grandes y se enfocan en escenario, idioma, documento e intención de cálculo.</p>
        <p>Al elegir títulos, evita competir de frente por categorías de una sola palabra. Usa modificadores que muestren escenario e intención: trabajador independiente, familia de estatus mixto, después de una denegación, con hipoteca, antes de inscripción abierta, para repartidores, con condiciones preexistentes o en español. Estas páginas pueden enlazar a guías principales, pero la entrada debe ser específica y ganable.</p>
        <h2 id="next">Qué construir después</h2>
        <p>Convierte este tema en un grupo de páginas: una calculadora u hoja de trabajo, una guía clara, una versión en español, una lista de fuentes y al menos tres enlaces internos a preguntas relacionadas.</p>
        <p>Antes de solicitar AdSense, cada página del grupo debería mostrar método editorial, fecha de revisión, fuentes, aviso legal y explicación original suficiente para sostenerse sin la calculadora. La herramienta ayuda, pero la explicación alrededor es lo que convierte la página en contenido educativo defendible.</p>
        {tool_link}
        <p class="disclaimer">{esc(TEXT[lang]['not_advice'])}</p>
        """


def calculator_guide(kb: list[dict], lang: str, calc: dict) -> str:
    topic = find_topic(kb, calc["topic"])
    title = guide_title(calc, lang)
    fields = "".join(f"<li>{esc(en if lang == 'en' else es)}</li>" for _, en, es, _ in calc["fields"])
    body_en = f"""
      <h2>When this calculator is useful</h2>
      <p>This worksheet is designed for users who know they need a starting point but do not want a sales quote yet. It turns the most common {esc(calc['title'][lang]).lower()} inputs into a documented estimate and links the result back to official education sources.</p>
      <p>The best use case is comparison, not final selection. Run the calculator once with conservative numbers, once with a more stressful household scenario, and once with only the expenses you are certain about. The spread between those three results usually teaches more than a single number, because insurance decisions are about tradeoffs between risk, premium, cash reserves, and policy limits.</p>
      <h2>Inputs to gather first</h2>
      <ul>{fields}</ul>
      <p>Use current documents where possible: a mortgage statement, lease, pay stub, Marketplace estimate, carrier declaration page, funeral quote, bank balance, or benefit summary. If you do not have a document, enter a realistic placeholder and mark the result for review. A clean estimate with one known assumption is more useful than a precise-looking estimate built from guesses.</p>
      <h2>How to interpret the result</h2>
      <p>The number is a planning range, not a purchase recommendation. Use it to identify gaps, compare scenarios, and prepare better questions before speaking with a licensed agent or visiting an official marketplace.</p>
      <p>If the result is much higher than expected, do not immediately assume you need the full amount in one policy. Look for smaller decisions: raising a liability limit, adding a rider, adjusting a deductible, increasing emergency savings, or separating one risk into a dedicated policy. If the result is lower than expected, check whether the inputs accidentally ignored taxes, childcare, debt payoff timing, inflation, or a coverage exclusion.</p>
      <h2>What this calculator does not know</h2>
      <p>It does not read your policy contract, verify eligibility, compare insurers, or account for every state rule. State insurance departments, federal agencies, and plan documents remain the controlling sources. This matters for AdSense quality as well: a useful tool page should make its limits obvious, link to source material, and avoid pretending that a simple estimate is professional advice.</p>
      <h2>How to turn the estimate into action</h2>
      <ol>
        <li>Save the result and the assumptions used.</li>
        <li>Open the related source guide and check which rule or document controls the decision.</li>
        <li>Write down the three questions you still cannot answer from official sources.</li>
        <li>Compare the result against your current policy, benefit summary, emergency fund, or quote.</li>
        <li>Before submitting personal data to any seller, verify licensing, complaint history, and privacy terms.</li>
      </ol>
      <h2>Internal links that help</h2>
      <p>Read the related topic guide, then use adjacent calculators to check whether the same household has life, health, property, and income-protection gaps.</p>
      <p><a class="button" href="{rel(calc_path(calc, lang), lang)}">{esc(TEXT[lang]['use_tool'])}</a></p>
    """
    body_es = f"""
      <h2>Cuándo sirve esta calculadora</h2>
      <p>Esta hoja es para usuarios que necesitan un punto de partida pero todavía no quieren una cotización de venta. Convierte los datos más comunes de {esc(calc['title'][lang]).lower()} en una estimación documentada y enlaza el resultado con fuentes oficiales.</p>
      <p>El mejor uso es comparar escenarios, no elegir una póliza final. Haz un cálculo conservador, uno con una situación familiar más estresante y otro solo con los gastos que conoces con seguridad. La diferencia entre esos tres resultados suele enseñar más que un solo número, porque las decisiones de seguro mezclan riesgo, prima, ahorro disponible y límites de póliza.</p>
      <h2>Datos que conviene reunir primero</h2>
      <ul>{fields}</ul>
      <p>Usa documentos recientes cuando sea posible: estado hipotecario, contrato de renta, recibo de pago, estimación del Mercado, página de declaraciones de la póliza, cotización funeraria, saldo bancario o resumen de beneficios. Si no tienes un documento, escribe una suposición realista y marca el resultado para revisión. Una estimación clara con una suposición conocida es más útil que un número exacto basado en adivinanzas.</p>
      <h2>Cómo interpretar el resultado</h2>
      <p>El número es un rango educativo, no una recomendación de compra. Úsalo para detectar brechas, comparar escenarios y preparar mejores preguntas antes de hablar con un agente autorizado o visitar un mercado oficial.</p>
      <p>Si el resultado es mucho más alto de lo esperado, no asumas de inmediato que necesitas todo en una sola póliza. Busca decisiones más pequeñas: subir un límite de responsabilidad, agregar un endoso, ajustar un deducible, aumentar el fondo de emergencia o separar un riesgo en una póliza dedicada. Si el resultado es más bajo de lo esperado, revisa si olvidaste impuestos, cuidado de niños, deudas, inflación o exclusiones de cobertura.</p>
      <h2>Lo que esta calculadora no sabe</h2>
      <p>No lee tu contrato de póliza, no verifica elegibilidad, no compara compañías y no incorpora todas las reglas estatales. Los departamentos estatales, las agencias federales y los documentos del plan siguen siendo las fuentes que controlan la decisión. Esto también importa para calidad editorial: una página útil debe explicar sus límites, enlazar fuentes y evitar presentar una estimación simple como asesoría profesional.</p>
      <h2>Cómo convertir la estimación en acción</h2>
      <ol>
        <li>Guarda el resultado y las suposiciones usadas.</li>
        <li>Abre la guía relacionada y verifica qué regla o documento controla la decisión.</li>
        <li>Escribe las tres preguntas que todavía no puedes responder con fuentes oficiales.</li>
        <li>Compara el resultado con tu póliza actual, resumen de beneficios, ahorro o cotización.</li>
        <li>Antes de enviar datos personales a un vendedor, verifica licencia, quejas y privacidad.</li>
      </ol>
      <h2>Enlaces internos útiles</h2>
      <p>Lee la guía del tema relacionado y luego usa calculadoras cercanas para revisar si la misma familia tiene brechas de vida, salud, propiedad o protección de ingresos.</p>
      <p><a class="button" href="{rel(calc_path(calc, lang), lang)}">{esc(TEXT[lang]['use_tool'])}</a></p>
    """
    return page_intro(title, calc["summary"][lang], lang) + f"""
    <section class="section">
      <div class="container two-col">
        <article class="article-body">{body_en if lang == 'en' else body_es}<p class="disclaimer">{esc(TEXT[lang]['not_advice'])}</p></article>
        <aside class="sidebar card">{source_box(topic, lang)}</aside>
      </div>
    </section>
    <section class="section alt"><div class="container"><h2>{esc(TEXT[lang]['related'])}</h2><div class="grid cols-3">{related_links(kb, lang, topic)}</div></div></section>
    """


def legal_pages(lang: str) -> dict:
    def about():
        return page_intro(TEXT[lang]["about"], "Independent insurance education tools for U.S. consumers." if lang == "en" else "Herramientas educativas independientes sobre seguros en EE. UU.", lang) + f"""
        <section class="section"><div class="container article-body">
          <p>{'SeguroTools is built as an educational content asset: calculators, source shelves, and bilingual explanations before any monetization layer.' if lang == 'en' else 'SeguroTools se construye como un activo educativo: calculadoras, fuentes y explicaciones bilingües antes de cualquier capa de monetización.'}</p>
          <p>{esc(TEXT[lang]['not_advice'])}</p>
        </div></section>"""

    def contact():
        intro = "Questions, corrections, source suggestions, and privacy requests." if lang == "en" else "Preguntas, correcciones, sugerencias de fuentes y solicitudes de privacidad."
        note = "Role inboxes are centrally monitored so requests can be routed by topic without implying a separate person for every address." if lang == "en" else "Los buzones por función se revisan de forma centralizada para enrutar solicitudes por tema sin implicar una persona separada para cada dirección."
        return page_intro(TEXT[lang]["contact"], intro, lang) + f"""
        <section class="section"><div class="container article-body">
          <p>General: <a href="mailto:hello@segurotools.com">hello@segurotools.com</a></p>
          <p>Spanish support: <a href="mailto:hola@segurotools.com">hola@segurotools.com</a></p>
          <p>Support: <a href="mailto:support@segurotools.com">support@segurotools.com</a></p>
          <p>Calculators: <a href="mailto:calculators@segurotools.com">calculators@segurotools.com</a></p>
          <p>Editorial: <a href="mailto:editorial@segurotools.com">editorial@segurotools.com</a></p>
          <p>Corrections: <a href="mailto:corrections@segurotools.com">corrections@segurotools.com</a></p>
          <p>Source suggestions: <a href="mailto:sources@segurotools.com">sources@segurotools.com</a></p>
          <p>Research: <a href="mailto:research@segurotools.com">research@segurotools.com</a></p>
          <p>Privacy requests: <a href="mailto:privacy@segurotools.com">privacy@segurotools.com</a></p>
          <p>Legal notices: <a href="mailto:legal@segurotools.com">legal@segurotools.com</a></p>
          <p>Advertising: <a href="mailto:ads@segurotools.com">ads@segurotools.com</a></p>
          <p>Partnerships: <a href="mailto:partners@segurotools.com">partners@segurotools.com</a></p>
          <p class="small">{esc(note)}</p>
        </div></section>"""

    def privacy():
        text = "Calculator reports require an email address and consent. The email is used to send the report and notify the site owner for follow-up. No payment data, Social Security number, medical records, or policy documents should be submitted." if lang == "en" else "Los reportes de calculadora requieren correo y consentimiento. El correo se usa para enviar el reporte y notificar al propietario del sitio para seguimiento. No envíes datos de pago, número de Seguro Social, registros médicos ni documentos de póliza."
        return page_intro(TEXT[lang]["privacy"], text, lang) + f'<section class="section"><div class="container article-body"><p>{esc(text)}</p><p>Google AdSense placeholders are reserved but not activated until approval and publisher configuration.</p></div></section>'

    def disclaimer():
        return page_intro(TEXT[lang]["disclaimer"], TEXT[lang]["not_advice"], lang) + f'<section class="section"><div class="container article-body"><p>{esc(TEXT[lang]["not_advice"])}</p><p>{"Always verify plan, tax, state, and eligibility details with official sources." if lang == "en" else "Verifica detalles de planes, impuestos, estado y elegibilidad con fuentes oficiales."}</p></div></section>'

    def terms():
        return page_intro(TEXT[lang]["terms"], "Use of this site." if lang == "en" else "Uso de este sitio.", lang) + f'<section class="section"><div class="container article-body"><p>{"Use calculators at your own discretion. Do not submit sensitive personal information." if lang == "en" else "Usa las calculadoras bajo tu criterio. No envíes información personal sensible."}</p></div></section>'

    def author():
        return page_intro(TEXT[lang]["author"], "Editorial method and source review." if lang == "en" else "Método editorial y revisión de fuentes.", lang) + f'<section class="section"><div class="container article-body"><p>{"Articles are produced from a local knowledge base, social pain-point research, and official source review. Each page should be human-reviewed before monetization." if lang == "en" else "Los artículos se producen desde una base local de conocimiento, investigación de problemas reales y revisión de fuentes oficiales. Cada página debe revisarse manualmente antes de monetizar."}</p></div></section>'

    return {"about": about, "contact": contact, "privacy": privacy, "disclaimer": disclaimer, "terms": terms, "author": author}


def render_layout(lang: str, body: str, title: str, desc: str, rel_path: str, alt_path: str | None = None) -> str:
    t = TEXT[lang]
    alternate = ""
    if alt_path:
        alt_url = f"{SITE_URL}/{alt_path}".replace("/index.html", "/")
        alternate = f'<link rel="alternate" hreflang="{other_lang(lang)}-us" href="{alt_url}">\n'
    canonical = f"{SITE_URL}/{rel_path}".replace("/index.html", "/")
    return f"""<!doctype html>
<html lang="{lang}-US">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}">
  <link rel="canonical" href="{canonical}">
  <link rel="alternate" hreflang="{lang}-us" href="{canonical}">
  {alternate}<link rel="stylesheet" href="/assets/styles.css">
  <script defer src="/assets/app.js"></script>
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:type" content="website">
  <script type="application/ld+json">{json.dumps(schema(title, desc, canonical, lang), ensure_ascii=False)}</script>
</head>
<body>
  <header class="site-header">
    <nav class="nav" aria-label="Primary">
      <a class="brand" href="/{lang}/"><span class="brand-mark">ST</span><span>{esc(t['brand'])}</span></a>
      <div class="nav-links">
        <a href="/{lang}/">{esc(t['home'])}</a>
        <a href="/{lang}/{calc_base(lang)}/">{esc(t['calculators'])}</a>
        <a href="/{lang}/blog/">{esc(t['blog'])}</a>
        <a href="/{lang}/{knowledge_base(lang)}/">{esc(t['knowledge'])}</a>
        <a href="/{lang}/about/">{esc(t['about'])}</a>
        <a class="lang-switch" href="/{other_lang(lang)}/">{'Español' if lang == 'en' else 'English'}</a>
      </div>
    </nav>
  </header>
  <main>{body}</main>
  <footer class="footer">
    <div class="container footer-grid">
      <div><h3>{esc(t['brand'])}</h3><p>{esc(t['tagline'])}</p><p>{esc(t['not_advice'])}</p></div>
      <div><h3>{esc(t['calculators'])}</h3><p><a href="/{lang}/{calc_base(lang)}/">{esc(t['calculators'])}</a></p><p><a href="/{lang}/{knowledge_base(lang)}/">{esc(t['knowledge'])}</a></p></div>
      <div><h3>{esc(t['blog'])}</h3><p><a href="/{lang}/blog/{category_slug('life', lang)}/">{esc(CATEGORY_LABELS['life'][lang])}</a></p><p><a href="/{lang}/blog/{category_slug('health', lang)}/">{esc(CATEGORY_LABELS['health'][lang])}</a></p></div>
      <div><h3>{'Policy' if lang == 'en' else 'Política'}</h3><p><a href="/{lang}/privacy/">{esc(t['privacy'])}</a></p><p><a href="/{lang}/disclaimer/">{esc(t['disclaimer'])}</a></p><p><a href="/{lang}/contact/">{esc(t['contact'])}</a></p></div>
    </div>
  </footer>
</body>
</html>"""


def page_intro(title: str, desc: str, lang: str) -> str:
    return f"""
    <section class="page-title">
      <div class="container">
        <p class="eyebrow">{esc(TEXT[lang]['brand'])}</p>
        <h1>{esc(title)}</h1>
        <p class="lead">{esc(desc)}</p>
      </div>
    </section>
    """


def source_box(topic: dict, lang: str) -> str:
    return f"<h3>{esc(TEXT[lang]['sources'])}</h3>{source_list(topic)}"


def source_list(topic: dict) -> str:
    if not topic.get("sources"):
        return "<p>No sources stored yet.</p>"
    items = "".join(f'<li><a href="{esc(source["url"])}">{esc(source["title"])}</a> <span class="small">({esc(source.get("authority") or source.get("domain", ""))})</span></li>' for source in topic.get("sources", [])[:8])
    return f'<ol class="source-list">{items}</ol>'


def pain_samples(topic: dict, lang: str) -> str:
    samples = topic.get("pain_samples", [])[:8]
    if not samples:
        return "<p>No pain samples yet.</p>"
    return "<ul>" + "".join(f'<li><strong>{esc(sample.get("platform", ""))}:</strong> {esc(sample.get("excerpt") or sample.get("title") or "")}</li>' for sample in samples) + "</ul>"


def related_links(kb: list[dict], lang: str, topic: dict, current: str | None = None) -> str:
    category = TOPIC_CATEGORY.get(topic["slug"], "consumer")
    related_topics = [row for row in kb if row["slug"] != topic["slug"] and TOPIC_CATEGORY.get(row["slug"]) == category][:3]
    cards = [card(topic_name(row, lang), topic_desc(row, lang), rel(article_path(topic_slug(row, lang), lang), lang), TEXT[lang]["read_more"]) for row in related_topics]
    for calc in CALCULATORS:
        if calc["topic"] == topic["slug"] and calc["topic"] != current:
            cards.append(card(calc["title"][lang], calc["summary"][lang], rel(calc_path(calc, lang), lang), TEXT[lang]["use_tool"]))
    return "\n".join(cards[:4])


def card(title: str, desc: str, href: str, cta: str) -> str:
    return f'<article class="card"><h3><a href="{href}">{esc(title)}</a></h3><p>{esc(desc)}</p><a class="button ghost" href="{href}">{esc(cta)}</a></article>'


def article_teaser(title: str, desc: str, href: str, lang: str) -> str:
    return card(title, desc, href, TEXT[lang]["read_more"])


def stat_card(num: str, en: str, es: str, lang: str) -> str:
    return f'<div class="card highlight"><div class="metric">{esc(num)}</div><p>{esc(en if lang == "en" else es)}</p></div>'


def toc_box(lang: str) -> str:
    labels = ["What this means", "Questions", "Verify", "Framework", "Workflow", "Documents", "Mistakes", "Spanish notes", "SEO", "Next"] if lang == "en" else ["Qué significa", "Preguntas", "Verificar", "Marco", "Flujo", "Documentos", "Errores", "Notas en español", "SEO", "Siguiente"]
    ids = ["what-it-means", "questions", "official", "framework", "example", "documents", "mistakes", "spanish", "seo", "next"]
    return "<h3>Contents</h3><ol>" + "".join(f'<li><a href="#{ids[i]}">{esc(labels[i])}</a></li>' for i in range(len(ids))) + "</ol>"


def write_html(lang: str, rel_path: str, body: str, title: str, desc: str, alt_path: str | None = None) -> str:
    full_rel = f"{lang}/{rel_path}"
    content = render_layout(lang, body, title, desc, full_rel, alt_path)
    return write_page(full_rel, content)


def write_page(rel_path: str, content: str, binary: bool = False) -> str:
    path = DIST / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    if binary:
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return rel_path


def root_redirect() -> str:
    return """<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="refresh" content="0; url=/en/"><link rel="canonical" href="/en/"><title>SeguroTools</title></head><body><a href="/en/">English</a> · <a href="/es/">Español</a></body></html>"""


def sitemap(paths: list[str]) -> str:
    urls = []
    for path in paths:
        if not path.endswith(".html"):
            continue
        loc = f"{SITE_URL}/{path}".replace("/index.html", "/")
        urls.append(f"<url><loc>{loc}</loc><lastmod>{TODAY}</lastmod></url>")
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>"


def robots() -> str:
    return f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n"


def redirects() -> str:
    return "/ /en/ 302\n"


def headers() -> str:
    return """/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
"""


def schema(title: str, desc: str, url: str, lang: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "description": desc,
        "url": url,
        "inLanguage": f"{lang}-US",
        "dateModified": TODAY,
        "isAccessibleForFree": True,
        "publisher": {"@type": "Organization", "name": "SeguroTools"},
    }


def home_title(lang: str) -> str:
    return "SeguroTools | U.S. insurance calculators and bilingual guides" if lang == "en" else "SeguroTools | Calculadoras y guías bilingües de seguros"


def page_title(lang: str, title: str) -> str:
    return f"{title} | {TEXT[lang]['brand']}"


def calculator_desc(lang: str) -> str:
    return "Educational calculators for life, ACA, final expense, home, disability, pet, auto, and small business insurance." if lang == "en" else "Calculadoras educativas para vida, ACA, gastos finales, vivienda, incapacidad, mascotas, auto y pequeños negocios."


def blog_desc(lang: str) -> str:
    return "Deep bilingual insurance education guides built around long-tail questions and official sources." if lang == "en" else "Guías bilingües profundas sobre seguros, basadas en preguntas específicas y fuentes oficiales."


def knowledge_desc(lang: str) -> str:
    return "A source-linked index connecting consumer pain points to official insurance education material." if lang == "en" else "Índice con fuentes que conecta problemas del consumidor con material oficial de educación sobre seguros."


def category_desc(lang: str, category: str) -> str:
    return f"{CATEGORY_LABELS[category][lang]} guides, tools, and source-backed answers."


def guide_title(calc: dict, lang: str) -> str:
    return f"How to use the {calc['title'][lang].lower()}" if lang == "en" else f"Cómo usar la {calc['title'][lang].lower()}"


def find_topic(kb: list[dict], slug: str) -> dict:
    return next(row for row in kb if row["slug"] == slug)


def topic_name(topic: dict, lang: str) -> str:
    return topic["name_en"] if lang == "en" else topic.get("name_es") or topic["name_en"]


def topic_desc(topic: dict, lang: str) -> str:
    return topic["description_en"] if lang == "en" else topic.get("description_es") or topic["description_en"]


def topic_slug(topic: dict, lang: str) -> str:
    if lang == "en":
        return topic["slug"].replace("_", "-")
    mapping = {
        "insurance_terms": "terminos-basicos-seguros",
        "life_insurance": "seguro-vida-necesidad-tipos",
        "final_expense": "gastos-finales-funeral",
        "health_aca": "seguro-medico-aca-costos",
        "immigrant_health": "seguro-medico-inmigrantes-daca",
        "medicare": "medicare-basico-opciones",
        "auto_insurance": "seguro-auto-cobertura-costos",
        "home_renters_flood": "seguro-vivienda-inquilinos-inundacion",
        "pet_insurance": "seguro-mascotas",
        "disability_insurance": "seguro-incapacidad-ingresos",
        "business_liability": "seguro-negocio-responsabilidad",
        "gig_worker_insurance": "seguro-trabajadores-plataformas",
        "insurance_scams": "estafas-seguros-fraude",
        "claims_appeals": "reclamaciones-denegaciones-quejas",
    }
    return mapping.get(topic["slug"], topic["slug"].replace("_", "-"))


def article_path(slug: str, lang: str) -> str:
    return f"blog/{slug}/index.html"


def knowledge_path(topic: dict, lang: str) -> str:
    return f"{knowledge_base(lang)}/{topic_slug(topic, lang)}/index.html"


def calc_path(calc: dict, lang: str) -> str:
    return f"{calc_base(lang)}/{calc['slug'][lang]}/index.html"


def calc_base(lang: str) -> str:
    return "calculators" if lang == "en" else "calculadoras"


def knowledge_base(lang: str) -> str:
    return "knowledge" if lang == "en" else "base-conocimiento"


def category_slug(category: str, lang: str) -> str:
    if lang == "en":
        return category
    mapping = {
        "life": "vida",
        "health": "salud",
        "property": "propiedad",
        "income": "ingresos",
        "consumer": "consumidor",
    }
    return mapping[category]


def guide_slug(calc: dict, lang: str) -> str:
    suffix = "guide" if lang == "en" else "guia"
    return f"{calc['slug'][lang]}-{suffix}"


def rel(path: str, lang: str) -> str:
    return f"/{lang}/{path}".replace("index.html", "")


def alt(path: str, lang: str, calculators: bool = False) -> str:
    other = other_lang(lang)
    return f"{other}/{path}".replace("index.html", "")


def other_lang(lang: str) -> str:
    return "es" if lang == "en" else "en"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


if __name__ == "__main__":
    main()
