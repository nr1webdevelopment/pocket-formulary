"""Builds the v2 medicine library outputs from data/library/:

  dist/v2/   bulk downloads: ingredients.json/.csv, products.json/.csv, conditions.json, library.json (everything)
  api/v2/    static JSON API:
               index.json                      root: counts and endpoints
               ingredients.json                every ingredient (summary + FDA label)
               ingredients/{id}.json           one ingredient: uses, approvals, controlled status, all its products
               products.json                   every product (summary)
               products/{id}.json              one product with its ingredients
               conditions.json                 every condition
               conditions/{id}.json            ingredients approved / used off-label for one condition
               search.json                     compact search index (names, brands, synonyms)
               openapi.json                    OpenAPI 3.1 description

scripts/build_dist.py runs this automatically.
"""
import csv
import glob
import io
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "data", "library")
DIST = os.path.join(ROOT, "dist", "v2")
API = os.path.join(ROOT, "api", "v2")
REPO = "https://github.com/nr1webdevelopment/pocket-formulary"

JURIS_NAMES = {"US": "US", "EU": "EU", "TH": "Thailand", "MX": "Mexico", "PT": "Portugal", "CN": "Mainland China", "HK": "Hong Kong",
               "MO": "Macau", "TW": "Taiwan", "SG": "Singapore", "GB": "UK", "CA": "Canada", "JP": "Japan", "AU": "Australia"}


def load_library():
    conditions = json.load(open(os.path.join(LIB, "conditions.json"), encoding="utf-8"))
    ingredients = [json.load(open(p, encoding="utf-8")) for p in sorted(glob.glob(os.path.join(LIB, "ingredients", "*.json")))]
    products = [json.load(open(p, encoding="utf-8")) for p in sorted(glob.glob(os.path.join(LIB, "products", "*.json")))]
    return conditions, ingredients, products


def fda_label(ing):
    """Plain-language US status: {"status", "label"}; for not-FDA-approved medicines, says where it is approved."""
    us = next((a for a in ing["approvals"] if a["jurisdiction"] == "US"), None)
    status = us["status"] if us else "unknown"
    elsewhere = [JURIS_NAMES.get(a["jurisdiction"], a["jurisdiction"]) for a in ing["approvals"]
                 if a["jurisdiction"] != "US" and a["status"] == "approved"]
    label = {
        "approved": "FDA approved",
        "otc_monograph": "FDA over-the-counter monograph",
        "withdrawn": "Withdrawn in the US",
        "investigational": "Investigational (not approved)",
        "not_approved": "Not FDA approved",
        "unknown": "FDA status not confirmed",
    }[status]
    if status in ("not_approved", "withdrawn", "unknown") and elsewhere:
        label += " · Approved in " + ", ".join(elsewhere)
    return {"status": status, "label": label, "approvedElsewhere": elsewhere}


def main():
    release = json.load(open(os.path.join(ROOT, "data", "release.json"), encoding="utf-8"))
    site = release.get("siteUrl", "https://nomadceuticals.com/")
    base = site.rstrip("/") + "/api/v2"
    url = lambda p: f"{base}/{p}"
    conditions, ingredients, products = load_library()
    cond_by = {c["id"]: c for c in conditions}
    ing_by = {i["id"]: i for i in ingredients}
    prods_of = {i["id"]: [] for i in ingredients}
    for p in products:
        for iid in p["ingredients"]:
            prods_of[iid].append(p)

    def env(path, data, **extra):
        doc = {"api": "NomadCeuticals Medicine Library API", "apiVersion": "v2", "dataVersion": release["version"],
               "released": release["released"], "license": "CC-BY-4.0", "attribution": f"Data from NomadCeuticals ({REPO}), CC BY 4.0",
               "disclaimer": "For general reference only, not medical advice. Approval status and uses differ by country; check the official label and ask a clinician or pharmacist.",
               "links": {"self": url(path), "index": url("index.json"), "docs": f"{site}api/"}}
        doc.update(extra)
        if isinstance(data, list):
            doc["count"] = len(data)
        doc["data"] = data
        return doc

    def ing_summary(i):
        fda = fda_label(i)
        return {"id": i["id"], "name": i["name"], "kind": i["kind"], "classes": [c["name"] for c in i["classes"]],
                "fda": {"status": fda["status"], "label": fda["label"]},
                "approvedFor": sorted({u["condition"] for u in i["uses"] if u["type"] == "approved"}),
                "offLabelFor": sorted({u["condition"] for u in i["uses"] if u["type"] == "off-label"}),
                "controlled": {c["jurisdiction"]: c["schedule"] for c in i.get("controlled", [])},
                "brands": sorted({p["brandName"] for p in prods_of[i["id"]]}), "tier": i["tier"], "review": i["review"]["status"],
                "url": url(f"ingredients/{i['id']}.json")}

    def prod_summary(p):
        return {"id": p["id"], "brandName": p["brandName"], "ingredients": p["ingredients"], "jurisdiction": p["jurisdiction"],
                "status": p["status"], "form": p.get("form"), "url": url(f"products/{p['id']}.json")}

    def ing_full(i):
        r = dict(i)
        r["fda"] = fda_label(i)
        r["uses"] = [dict(u, conditionName=cond_by[u["condition"]]["name"]) for u in i["uses"]]
        r["products"] = [prod_summary(p) for p in prods_of[i["id"]]]
        r["links"] = {"self": url(f"ingredients/{i['id']}.json"), "website": f"{site}#ingredient/{i['id']}"}
        return r

    files = {}
    files["ingredients.json"] = env("ingredients.json", [ing_summary(i) for i in ingredients])
    for i in ingredients:
        files[f"ingredients/{i['id']}.json"] = env(f"ingredients/{i['id']}.json", ing_full(i))
    files["products.json"] = env("products.json", [prod_summary(p) for p in products])
    for p in products:
        r = {k: v for k, v in p.items() if k != "v1"}
        r["ingredientDetails"] = [ing_summary(ing_by[iid]) for iid in p["ingredients"]]
        r["indicationNames"] = [cond_by[c]["name"] for c in p.get("indications", [])]
        r["links"] = {"self": url(f"products/{p['id']}.json")}
        if p.get("v1"):
            r["links"]["v1"] = site.rstrip("/") + f"/api/v1/medicines/{p['id']}.json"
        files[f"products/{p['id']}.json"] = env(f"products/{p['id']}.json", r)
    cond_list = []
    for c in conditions:
        appr = [ing_summary(i) for i in ingredients if any(u["condition"] == c["id"] and u["type"] == "approved" for u in i["uses"])]
        off = [ing_summary(i) for i in ingredients if any(u["condition"] == c["id"] and u["type"] == "off-label" for u in i["uses"])]
        entry = dict(c, approvedCount=len(appr), offLabelCount=len(off), url=url(f"conditions/{c['id']}.json"))
        cond_list.append(entry)
        files[f"conditions/{c['id']}.json"] = env(f"conditions/{c['id']}.json", {"approved": appr, "offLabel": off},
                                                  condition={k: v for k, v in entry.items() if k != "url"})
    files["conditions.json"] = env("conditions.json", cond_list)

    # compact search index: one row per ingredient and per product
    search = []
    for i in ingredients:
        fda = fda_label(i)
        search.append({"t": "i", "id": i["id"], "n": i["name"], "s": i.get("synonyms", []), "f": fda["status"],
                       "a": sorted({u["condition"] for u in i["uses"] if u["type"] == "approved"}),
                       "o": sorted({u["condition"] for u in i["uses"] if u["type"] == "off-label"}),
                       "b": sorted({p["brandName"] for p in prods_of[i["id"]]})})
    for p in products:
        search.append({"t": "p", "id": p["id"], "n": p["brandName"], "i": p["ingredients"], "j": p["jurisdiction"], "st": p["status"]})
    files["search.json"] = env("search.json", search, legend={"t": "i = ingredient, p = product", "n": "name", "s": "synonyms",
                                                              "f": "US FDA status", "a": "approved for (condition ids)",
                                                              "o": "used off-label for", "b": "brand names", "i": "ingredient ids",
                                                              "j": "jurisdiction", "st": "product status"})
    files["index.json"] = env("index.json", {
        "description": "Ingredient-centred medicine library: approval status per country, approved and off-label uses, controlled status, and brands. Static JSON, GET only, no key.",
        "counts": {"ingredients": len(ingredients), "products": len(products), "conditions": len(conditions),
                   "fdaStatus": {s: sum(fda_label(i)["status"] == s for i in ingredients) for s in sorted({fda_label(i)["status"] for i in ingredients})},
                   "review": {s: sum(i["review"]["status"] == s for i in ingredients) for s in sorted({i["review"]["status"] for i in ingredients})}},
        "endpoints": {k: url(v) for k, v in {
            "ingredients": "ingredients.json", "ingredient": "ingredients/{id}.json", "products": "products.json",
            "product": "products/{id}.json", "conditions": "conditions.json", "condition": "conditions/{id}.json",
            "search": "search.json", "openapi": "openapi.json"}.items()} | {
            "bulk": f"{site}dist/v2/library.json", "v1": f"{site}api/v1/index.json"},
        "schemas": {n: f"{site}schema/v2/{n}.schema.json" for n in ("ingredient", "product", "condition")},
    })
    files["openapi.json"] = openapi(base, release, [c["id"] for c in conditions])

    for d in (API, DIST):
        if os.path.isdir(d):
            shutil.rmtree(d)
    for path, doc in files.items():
        fp = os.path.join(API, path)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
            f.write("\n")

    # bulk downloads
    os.makedirs(DIST)
    meta = {"dataset": "nomadceuticals-library", "version": release["version"], "released": release["released"], "license": "CC-BY-4.0",
            "schemas": {n: f"{site}schema/v2/{n}.schema.json" for n in ("ingredient", "product", "condition")}}
    dump = lambda name, obj: open(os.path.join(DIST, name), "w", encoding="utf-8").write(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
    dump("library.json", dict(meta, conditions=conditions, ingredients=ingredients, products=products))
    dump("ingredients.json", dict(meta, count=len(ingredients), data=ingredients))
    dump("products.json", dict(meta, count=len(products), data=products))
    dump("conditions.json", dict(meta, count=len(conditions), data=conditions))
    write_csv(os.path.join(DIST, "ingredients.csv"),
              ["id", "name", "kind", "classes", "fdaStatus", "fdaLabel", "approvedFor", "offLabelFor", "usControlled", "brands", "rxcui", "unii", "tier", "review"],
              [[i["id"], i["name"], i["kind"], "; ".join(c["name"] for c in i["classes"]), fda_label(i)["status"], fda_label(i)["label"],
                "; ".join(sorted({u["condition"] for u in i["uses"] if u["type"] == "approved"})),
                "; ".join(sorted({u["condition"] for u in i["uses"] if u["type"] == "off-label"})),
                next((c["schedule"] for c in i.get("controlled", []) if c["jurisdiction"] == "US"), ""),
                "; ".join(sorted({p["brandName"] for p in prods_of[i["id"]]})), i.get("ids", {}).get("rxcui") or "",
                "; ".join(i.get("ids", {}).get("unii") or []), i["tier"], i["review"]["status"]] for i in ingredients])
    write_csv(os.path.join(DIST, "products.csv"),
              ["id", "brandName", "ingredients", "jurisdiction", "status", "form", "route", "manufacturer", "approvalDate", "approvalYear", "indications", "controlled"],
              [[p["id"], p["brandName"], "; ".join(p["ingredients"]), p["jurisdiction"], p["status"], p.get("form") or "", p.get("route") or "",
                p.get("manufacturer") or "", (p.get("approval") or {}).get("date") or "", (p.get("approval") or {}).get("year") or "",
                "; ".join(p.get("indications", [])), p.get("controlled") or ""] for p in products])
    print(f"library v2: {len(ingredients)} ingredients, {len(products)} products, {len(conditions)} conditions -> dist/v2, api/v2 ({len(files)} files)")


def write_csv(path, header, rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    open(path, "w", encoding="utf-8").write(buf.getvalue())


def openapi(base, release, cond_ids):
    ref = lambda n: {"$ref": f"#/components/schemas/{n}"}
    arr = lambda s: {"type": "array", "items": s}

    def op(opid, summary, data, params=None):
        o = {"operationId": opid, "summary": summary, "responses": {
            "200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object", "properties": {
                "apiVersion": {"type": "string"}, "dataVersion": {"type": "string"}, "license": {"type": "string"},
                "links": {"type": "object"}, "count": {"type": "integer"}, "data": data}}}}},
            "404": {"description": "Unknown id"}}}
        if params:
            o["parameters"] = params
        return {"get": o}

    pid = lambda n, ex: [{"name": n, "in": "path", "required": True, "schema": {"type": "string", "pattern": "^[a-z0-9-]+$"}, "example": ex}]
    return {
        "openapi": "3.1.0",
        "info": {"title": "NomadCeuticals Medicine Library API", "version": f"v2 (data {release['version']})",
                 "description": "Ingredient-centred medicine library with approval status per country, approved and off-label uses, "
                                "controlled status and brands. Static JSON files: GET only, no authentication. Not medical advice.",
                 "license": {"name": "CC BY 4.0 (data)", "url": "https://creativecommons.org/licenses/by/4.0/"}, "contact": {"url": REPO}},
        "servers": [{"url": base}],
        "paths": {
            "/index.json": op("getIndex", "API root", {"type": "object"}),
            "/ingredients.json": op("listIngredients", "Every ingredient (summary)", arr(ref("IngredientSummary"))),
            "/ingredients/{id}.json": op("getIngredient", "One ingredient with uses, approvals and products", {"type": "object"}, pid("id", "bupropion")),
            "/products.json": op("listProducts", "Every product (summary)", arr(ref("ProductSummary"))),
            "/products/{id}.json": op("getProduct", "One product with its ingredients", {"type": "object"}, pid("id", "wellbutrin-xl")),
            "/conditions.json": op("listConditions", "Every condition", arr({"type": "object"})),
            "/conditions/{id}.json": op("getCondition", "Ingredients approved or used off-label for a condition",
                                        {"type": "object", "properties": {"approved": arr(ref("IngredientSummary")), "offLabel": arr(ref("IngredientSummary"))}},
                                        [{"name": "id", "in": "path", "required": True, "schema": {"enum": cond_ids}}]),
            "/search.json": op("getSearchIndex", "Compact search index of ingredients and products", arr({"type": "object"})),
        },
        "components": {"schemas": {
            "IngredientSummary": {"type": "object", "properties": {
                "id": {"type": "string"}, "name": {"type": "string"}, "kind": {"type": "string"}, "classes": arr({"type": "string"}),
                "fda": {"type": "object", "properties": {"status": {"enum": ["approved", "otc_monograph", "not_approved", "withdrawn", "investigational", "unknown"]},
                                                         "label": {"type": "string"}}},
                "approvedFor": arr({"type": "string"}), "offLabelFor": arr({"type": "string"}), "controlled": {"type": "object"},
                "brands": arr({"type": "string"}), "tier": {"enum": ["curated", "basic"]}, "review": {"type": "string"}, "url": {"type": "string"}}},
            "ProductSummary": {"type": "object", "properties": {
                "id": {"type": "string"}, "brandName": {"type": "string"}, "ingredients": arr({"type": "string"}), "jurisdiction": {"type": "string"},
                "status": {"enum": ["available", "discontinued", "unknown"]}, "form": {"type": ["string", "null"]}, "url": {"type": "string"}}},
        }},
    }


if __name__ == "__main__":
    main()
