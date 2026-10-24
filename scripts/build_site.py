"""Builds index.html: injects medicines (data/drugs.json), providers and cities (dist/v1/),
release info and translations (i18n/) into scripts/template.html.

Run scripts/site_data.py and scripts/build_dist.py first if the data changed.
"""
import base64, glob, io, json, os
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
    meta = [{"position": s.get("position", "50% 50%"), "credit": s.get("credit", "")} for s in items]
    return css, meta


def js(x):
    return json.dumps(x, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


slides_css, slides = hero_slides()
page = (t.replace("/*__SLIDES_CSS__*/", slides_css).replace("__SLIDES__", js(slides))
         .replace("__DATA__", js(drugs))
         .replace("__PROVIDERS__", js(providers))
         .replace("__CITIES__", js({"cities": cities_doc["data"], "jurisdictionNotes": cities_doc.get("jurisdictionNotes", {})}))
         .replace("__RELEASE__", js({"version": release["version"], "released": release["released"]}))
         .replace("__I18N__", js(i18n)))
head = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n')
html = head + page.replace('<header id="sitebar">', '</head>\n<body>\n<header id="sitebar">', 1) + "\n</body>\n</html>\n"
open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(html)
print(f"wrote index.html ({len(html.encode())//1024} KB): {len(drugs)} medicines, {len(providers)} providers, "
      f"{len(cities_doc['data'])} cities, languages: en + {', '.join(sorted(i18n['content']))}")
