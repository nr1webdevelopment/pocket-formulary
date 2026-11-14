"""Builds index.html: injects medicines (data/drugs.json), providers and cities (dist/v1/),
release info and translations (i18n/) into scripts/template.html.

Run scripts/site_data.py and scripts/build_dist.py first if the data changed.
"""
import base64, glob, io, json, os, re, urllib.parse
import site_header  # the shared top bar (scripts/site_header.*)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load = lambda *p: json.load(open(os.path.join(ROOT, *p), encoding="utf-8"))

t = open(os.path.join(ROOT, "scripts", "template.html"), encoding="utf-8").read()
drugs = load("data", "drugs.json")
providers = load("dist", "v1", "providers.json")["data"]
cities_doc = load("dist", "v1", "cities.json")
release = load("data", "release.json")
i18n = {"ui": load("i18n", "ui.json"), "content": {}}
for path in sorted(glob.glob(os.path.join(ROOT, "i18n", "content.*.json"))):
    lang = os.path.basename(path)[len("content."):-len(".json")]
    i18n["content"][lang] = json.load(open(path, encoding="utf-8"))


def encode_image(path, max_w=1400):
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    im.thumbnail((max_w, max_w))
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=70, method=6)
    print(f"  {os.path.basename(path)} -> {im.size[0]}x{im.size[1]} WebP, {len(buf.getvalue())//1024} KB")
    return 'url("data:image/webp;base64,' + base64.b64encode(buf.getvalue()).decode() + '")'


def hero_slides():
    """Header slideshow. Order and focal points come from images/slides.json; without it, every image in
    images/ is used alphabetically, then assets/hero.* as a single image. Returns (css, metadata)."""
    exts = (".jpg", ".jpeg", ".png", ".webp")
    cfg_path = os.path.join(ROOT, "images", "slides.json")
    if os.path.exists(cfg_path):
        items = json.load(open(cfg_path, encoding="utf-8"))["slides"]
        items = [dict(s, path=os.path.join(ROOT, "images", s["file"])) for s in items]
    else:
        items = [{"path": p} for p in sorted(glob.glob(os.path.join(ROOT, "images", "*"))) if p.lower().endswith(exts)]
        if not items:
            items = [{"path": os.path.join(ROOT, "assets", "hero" + e)} for e in exts if os.path.exists(os.path.join(ROOT, "assets", "hero" + e))][:1]
    items = [s for s in items if os.path.exists(s["path"])]
    print(f"header slideshow: {len(items)} image(s)")
    css = "\n".join(f".slide-{i} {{ background-image: {encode_image(s['path'])}; }}" for i, s in enumerate(items))
    meta = [{"position": s.get("position", "50% 50%"), "credit": s.get("credit", ""), "text": s.get("text"), "link": s.get("link")} for s in items]
    return css, meta


def js(x):
    return json.dumps(x, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def svg_asset(name):
    svg = open(os.path.join(ROOT, "assets", name), encoding="utf-8").read().strip()
    return re.sub(r"<title>.*?</title>", "", svg)


favicon = "data:image/svg+xml," + urllib.parse.quote(svg_asset("logo-icon.svg"), safe="")
def library_compact():
    """Compact copy of the v2 medicine library (data/library/) for site search and ingredient pages."""
    import build_library
    conditions, ingredients, products = build_library.load_library()
    prods_of = {}
    for p in products:
        for iid in p["ingredients"]:
            prods_of.setdefault(iid, []).append(p["id"])
    return {
        "areas": {c["id"]: c["area"] for c in conditions},
        "prod": {p["id"]: [p["brandName"], p["status"], p.get("form"), p["ingredients"]] for p in products},
        "ing": [{
            "id": i["id"], "n": i["name"], "s": i.get("synonyms", []), "c": [c["name"] for c in i["classes"]],
            "f": build_library.fda_label(i)["status"], "ae": build_library.fda_label(i)["approvedElsewhere"],
            "u": [[u["condition"], u["type"], u.get("note"), u.get("via", [])] for u in i["uses"]],
            "ctl": next((c["schedule"] for c in i.get("controlled", []) if c["jurisdiction"] == "US"), None),
            "p": prods_of.get(i["id"], []), "rev": i["review"]["status"], "uc": bool(i.get("usesComplete")),
            "src": [[s["url"], s.get("title", "")] for s in i["sources"]][:8],
        } for i in ingredients],
    }


slides_css, slides = hero_slides()
SITE = release.get("siteUrl", "https://nomadceuticals.com/")
gsv = release.get("googleSiteVerification")  # optional: Google Search Console meta-tag verification
JSONLD = [
    {"@context": "https://schema.org", "@type": "WebSite", "name": "NomadCeuticals", "url": SITE, "inLanguage": ["en", "zh-Hans", "zh-Hant", "es", "pt", "th"]},
    {"@context": "https://schema.org", "@type": "Organization", "name": "NomadCeuticals", "url": SITE, "logo": SITE + "assets/og-image.png",
     "sameAs": ["https://github.com/nr1webdevelopment/pocket-formulary"]},
]
t = (t.replace("__SITE__", SITE).replace("__JSONLD__", js(JSONLD))
      .replace("__GSV__", f'<meta name="google-site-verification" content="{gsv}">\n' if gsv else ""))
page = (t.replace("/*__SITE_HEADER_CSS__*/", site_header.css()).replace("/*__SITE_HEADER_JS__*/", site_header.js())
         .replace("__FAVICON__", favicon).replace("/*__SLIDES_CSS__*/", slides_css).replace("__SLIDES__", js(slides))
         .replace("__LIBRARY__", js(library_compact()))
         .replace("__DATA__", js(drugs))
         .replace("__PROVIDERS__", js(providers))
         .replace("__CITIES__", js({"cities": cities_doc["data"], "jurisdictionNotes": cities_doc.get("jurisdictionNotes", {})}))
         .replace("__RELEASE__", js({"version": release["version"], "released": release["released"]}))
         .replace("__I18N__", js(i18n)))
head = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n')
html = head + page.replace('<header id="sitebar">', '</head>\n<body>\n<header id="sitebar">', 1) + "\n</body>\n</html>\n"
import analytics
TAG = release.get("googleTagId")
html = analytics.inject(html, TAG)
open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(html)
print(f"wrote index.html ({len(html.encode())//1024} KB): {len(drugs)} medicines, {len(providers)} providers, "
      f"{len(cities_doc['data'])} cities, languages: en + {', '.join(sorted(i18n['content']))}")

# OTC finder subpage (nomadceuticals.com/otc-finder.html): scripts/otc_finder.html -> otc-finder.html
otc = open(os.path.join(ROOT, "scripts", "otc_finder.html"), encoding="utf-8").read()
# translations: i18n/otc/<lang>.json (English text -> translation), same languages as the main site
otc_i18n = {}
for lang in sorted(i18n["content"]):
    path = os.path.join(ROOT, "i18n", "otc", lang + ".json")
    assert os.path.exists(path), f"missing OTC finder translation: i18n/otc/{lang}.json"
    otc_i18n[lang] = json.load(open(path, encoding="utf-8"))
otc = otc.replace("__OTC_I18N__", js(otc_i18n))
otc = site_header.inject(otc.replace("__FAVICON__", favicon), base="./", active="otc")
assert not re.findall(r"__[A-Z_]+__", otc), "unfilled placeholder in otc_finder.html"
otc = analytics.inject(otc, TAG)
open(os.path.join(ROOT, "otc-finder.html"), "w", encoding="utf-8").write(otc)
print(f"wrote otc-finder.html ({len(otc.encode())//1024} KB): languages en + {', '.join(sorted(otc_i18n))} "
      f"({min(len(d) for d in otc_i18n.values())} strings each)")
