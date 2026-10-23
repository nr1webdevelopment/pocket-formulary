"""Builds index.html: injects data/drugs.json (medicines) and dist/v1/providers.json
(Bangkok HIV providers) into scripts/template.html.

Run scripts/site_data.py and scripts/build_dist.py first if the data changed.
"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
t = open(os.path.join(ROOT, "scripts", "template.html"), encoding="utf-8").read()
drugs = json.load(open(os.path.join(ROOT, "data", "drugs.json"), encoding="utf-8"))
prov_doc = json.load(open(os.path.join(ROOT, "dist", "v1", "providers.json"), encoding="utf-8"))
release = json.load(open(os.path.join(ROOT, "data", "release.json"), encoding="utf-8"))

def js(x):
    return json.dumps(x, ensure_ascii=False).replace("</", "<\\/")

page = (t.replace("__DATA__", js(drugs))
         .replace("__PROVIDERS__", js(prov_doc["data"]))
         .replace("__RELEASE__", js({"version": release["version"], "released": release["released"]})))
head = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n')
html = head + page.replace('<div class="wrap">', '</head>\n<body>\n<div class="wrap">', 1) + "\n</body>\n</html>\n"
open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(html)
print("wrote index.html with", len(drugs), "medicines and", len(prov_doc["data"]), "providers")
