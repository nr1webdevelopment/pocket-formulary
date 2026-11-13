"""The one site header (black top bar) shared by every page on nomadceuticals.com.

Source of truth: scripts/site_header.css and scripts/site_header.js. This module fills in the logo,
menu counts, labels (from i18n/ui.json) and languages, and returns the pieces each build script inlines:

    build_site.py    index.html (via template.html) and otc-finder.html (via otc_finder.html)
    build_api.py     api/index.html (via api_docs.html)
    build_public.py  404.html

Pages put <!--__SITE_HEADER__--> where the bar goes; the home page template uses /*__SITE_HEADER_CSS__*/
and /*__SITE_HEADER_JS__*/ because it renders the bar itself on every route.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.join(ROOT, "scripts")

LANGS = [["en", "English"], ["zh-Hans", "简体中文"], ["zh-Hant", "繁體中文"], ["es", "Español"], ["pt", "Português"], ["th", "ไทย"]]
LABEL_KEYS = ["navMedicines", "navProviders", "navOtc", "language", "textSize", "tsDefault", "tsLarge", "tsLarger"]
PLACEHOLDER = "<!--__SITE_HEADER__-->"


def _read(*p):
    return open(os.path.join(ROOT, *p), encoding="utf-8").read()


def _js(x):
    return json.dumps(x, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def logo_svg():
    svg = re.sub(r"<title>.*?</title>", "", _read("assets", "logo-bar.svg").strip())
    return svg.replace('role="img"', 'aria-hidden="true" focusable="false"')


def config():
    ui = json.load(open(os.path.join(ROOT, "i18n", "ui.json"), encoding="utf-8"))
    missing = [k for k in LABEL_KEYS if k not in ui]
    assert not missing, f"i18n/ui.json is missing header labels: {missing}"
    counts = {
        "medicines": len(json.load(open(os.path.join(ROOT, "data", "drugs.json"), encoding="utf-8"))),
        "providers": len(json.load(open(os.path.join(ROOT, "dist", "v1", "providers.json"), encoding="utf-8"))["data"]),
    }
    return {"logo": logo_svg(), "counts": counts, "langs": LANGS, "labels": {k: ui[k] for k in LABEL_KEYS}}


def css():
    return _read("scripts", "site_header.css")


def js():
    return _read("scripts", "site_header.js").replace("__SITE_HEADER_CFG__", _js(config()))


def snippet(base, active=""):
    """Header for a standalone page: styles, the bar, and the script that draws it."""
    init = {"base": base, "active": active}
    return (f'<style>\n{css()}</style>\n<header id="sitebar"></header>\n'
            f"<script>\n{js()}\nNCHeader.render(Object.assign({_js(init)}, {{ lang: NCHeader.pickLang() }}));\n</script>")


def inject(html, base, active=""):
    assert html.count(PLACEHOLDER) == 1, f"page needs exactly one {PLACEHOLDER}"
    return html.replace(PLACEHOLDER, snippet(base, active))
