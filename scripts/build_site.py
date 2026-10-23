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


def hero_css():
    """assets/hero.(webp|jpg|jpeg|png) -> resized WebP data URI. Falls back to a soft gradient."""
    for ext in ("webp", "jpg", "jpeg", "png"):
        path = os.path.join(ROOT, "assets", "hero." + ext)
        if os.path.exists(path):
            from PIL import Image
            im = Image.open(path).convert("RGB")
            im.thumbnail((1800, 1800))
            buf = io.BytesIO()
            im.save(buf, "WEBP", quality=72, method=6)
            print(f"hero image: {os.path.basename(path)} -> {im.size[0]}x{im.size[1]} WebP, {len(buf.getvalue())//1024} KB")
            return 'url("data:image/webp;base64,' + base64.b64encode(buf.getvalue()).decode() + '")'
    print("hero image: none found in assets/, using gradient placeholder")
    return ("radial-gradient(60% 90% at 85% 30%, #9FE3D6 0%, transparent 70%), "
            "radial-gradient(45% 70% at 65% 95%, #BFD7FF 0%, transparent 70%), "
            "radial-gradient(35% 60% at 98% 85%, #FFD9B5 0%, transparent 70%), #EEF6F4")


def js(x):
    return json.dumps(x, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


page = (t.replace("__HERO__", hero_css())
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
