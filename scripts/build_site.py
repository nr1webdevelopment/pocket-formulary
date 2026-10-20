"""Injects data/drugs.json into scripts/template.html and writes index.html."""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
t = open(os.path.join(ROOT, "scripts", "template.html"), encoding="utf-8").read()
data = json.load(open(os.path.join(ROOT, "data", "drugs.json"), encoding="utf-8"))
page = t.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
head = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n')
html = head + page.replace('<div class="wrap">', '</head>\n<body>\n<div class="wrap">', 1) + "\n</body>\n</html>\n"
open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(html)
print("wrote index.html with", len(data), "medicines")
