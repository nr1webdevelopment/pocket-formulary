"""Builds the static JSON API in api/v1/ from dist/v1/medicines.json.

Every endpoint is a plain JSON file, so it can be served by GitHub Pages (or any static host or CDN)
with no server. scripts/build_dist.py runs this automatically; run it on its own with:

    python3 scripts/build_api.py

Endpoints (relative to the API base URL in data/release.json -> apiBaseUrl):
    index.json                    API root: versions, counts, endpoint list
    medicines.json                every medicine, summary fields
    medicines/{id}.json           one medicine, full record + related medicines
    conditions.json               hiv, adhd, diabetes with counts
    conditions/{condition}.json   every medicine for one condition, full records
    classes.json                  every drug class with counts
    classes/{classId}.json        every medicine in one drug class, full records
    openapi.json                  OpenAPI 3.1 description of all of the above
"""
import json
import os
import re
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "api", "v1")
REPO = "https://github.com/nr1webdevelopment/pocket-formulary"
DEFAULT_BASE = "https://nomadceuticals.com/api/v1"
DEFAULT_SITE = "https://nomadceuticals.com/"

CONDITIONS = {
    "hiv": {"name": "HIV", "description": "Antiretroviral medicines for HIV treatment and prevention (PrEP)."},
    "adhd": {"name": "ADHD", "description": "Stimulant and non-stimulant medicines for attention-deficit/hyperactivity disorder."},
    "diabetes": {"name": "Diabetes", "description": "Insulins and other glucose-lowering medicines for type 1 and type 2 diabetes."},
}
SUMMARY_FIELDS = ["id", "brandName", "genericName", "condition", "drugClass", "status"]


def slug(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


def class_id(m):
    return f"{m['condition']}-{slug(m['drugClass'])}"


def load(*p):
    return json.load(open(os.path.join(ROOT, *p), encoding="utf-8"))


def main():
    release = load("data", "release.json")
    meds_doc = load("dist", "v1", "medicines.json")
    meds = sorted(meds_doc["data"], key=lambda m: (m["condition"], m["brandName"].lower()))
    base = release.get("apiBaseUrl", DEFAULT_BASE).rstrip("/")
    site = release.get("siteUrl", DEFAULT_SITE)
    url = lambda path: f"{base}/{path}"

    def envelope(path, data, **extra):
        doc = {
            "api": "NomadCeuticals Medicines API",
            "apiVersion": "v1",
            "dataVersion": release["version"],
            "released": release["released"],
            "license": "CC-BY-4.0",
            "attribution": f"Data from NomadCeuticals ({REPO}), CC BY 4.0",
            "disclaimer": "For general reference only, not medical advice. Check the current label and talk with a clinician or pharmacist.",
            "links": {"self": url(path), "index": url("index.json"), "docs": f"{site}api/"},
        }
        doc.update(extra)
        if isinstance(data, list):
            doc["count"] = len(data)
        doc["data"] = data
        return doc

    def summary(m):
        s = {k: m.get(k) for k in SUMMARY_FIELDS}
        s["classId"] = class_id(m)
        s["url"] = url(f"medicines/{m['id']}.json")
        return s

    def full(m):
        r = dict(m)
        r["classId"] = class_id(m)
        r["links"] = {
            "self": url(f"medicines/{m['id']}.json"),
            "condition": url(f"conditions/{m['condition']}.json"),
            "class": url(f"classes/{class_id(m)}.json"),
            "website": f"{site}#{m['id']}",
            "source": m["sourceUrl"],
        }
        return r

    classes = {}
    for m in meds:
        c = classes.setdefault(class_id(m), {"id": class_id(m), "name": m["drugClass"], "condition": m["condition"], "members": []})
        c["members"].append(m)

    files = {}
    files["medicines.json"] = envelope("medicines.json", [summary(m) for m in meds])
    for m in meds:
        related = [summary(o) for o in classes[class_id(m)]["members"] if o["id"] != m["id"]]
        files[f"medicines/{m['id']}.json"] = envelope(f"medicines/{m['id']}.json", full(m), related=related)

    cond_list = []
    for k, info in CONDITIONS.items():
        members = [m for m in meds if m["condition"] == k]
        cls = sorted({class_id(m) for m in members})
        entry = {"id": k, **info, "medicineCount": len(members), "classCount": len(cls), "url": url(f"conditions/{k}.json")}
        cond_list.append(entry)
        files[f"conditions/{k}.json"] = envelope(f"conditions/{k}.json", [full(m) for m in members],
                                                 condition={kk: vv for kk, vv in entry.items() if kk != "url"},
                                                 classes=[{"id": c, "name": classes[c]["name"], "url": url(f"classes/{c}.json")} for c in cls])
    files["conditions.json"] = envelope("conditions.json", cond_list)

    class_list = []
    for cid, c in sorted(classes.items(), key=lambda kv: (kv[1]["condition"], kv[1]["name"].lower())):
        entry = {"id": cid, "name": c["name"], "condition": c["condition"], "medicineCount": len(c["members"]), "url": url(f"classes/{cid}.json")}
        class_list.append(entry)
        files[f"classes/{cid}.json"] = envelope(f"classes/{cid}.json", [full(m) for m in c["members"]],
                                                drugClass={kk: vv for kk, vv in entry.items() if kk != "url"})
    files["classes.json"] = envelope("classes.json", class_list)

    files["index.json"] = envelope("index.json", {
        "description": "Free, read-only JSON API of FDA-approved medicines for HIV, ADHD and diabetes. Every endpoint is a static file: use GET, no API key needed.",
        "counts": {"medicines": len(meds), "conditions": len(CONDITIONS), "classes": len(classes),
                   "byCondition": {k: sum(m["condition"] == k for m in meds) for k in CONDITIONS}},
        "endpoints": {
            "medicines": url("medicines.json"),
            "medicine": url("medicines/{id}.json"),
            "conditions": url("conditions.json"),
            "condition": url("conditions/{condition}.json"),
            "classes": url("classes.json"),
            "class": url("classes/{classId}.json"),
            "openapi": url("openapi.json"),
            "bulkJson": f"{site}dist/v1/medicines.json",
            "bulkCsv": f"{site}dist/v1/medicines.csv",
        },
        "schema": f"{site}schema/medicine.schema.json",
    })
    files["openapi.json"] = openapi(base, site, release, sorted(CONDITIONS), sorted(classes))

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    for path, doc in files.items():
        full_path = os.path.join(OUT, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
            f.write("\n")
    write_docs(base, site, release, len(meds), len(classes))
    print(f"api/v1: {len(files)} files ({len(meds)} medicines, {len(CONDITIONS)} conditions, {len(classes)} classes)")


def write_docs(base, site, release, n_meds, n_classes):
    """api/index.html: human-readable docs, rendered from scripts/api_docs.html."""
    import urllib.parse
    svg = lambda name: re.sub(r"<title>.*?</title>", "", open(os.path.join(ROOT, "assets", name), encoding="utf-8").read().strip())
    html = open(os.path.join(ROOT, "scripts", "api_docs.html"), encoding="utf-8").read()
    for k, v in {
        "__BASE__": base, "__REPO__": REPO, "__DATA_VERSION__": release["version"], "__RELEASED__": release["released"],
        "__N_MEDS__": str(n_meds), "__N_CLASSES__": str(n_classes),
        "__CDN__": "https://cdn.jsdelivr.net/gh/nr1webdevelopment/pocket-formulary@main/api/v1",
        "__FAVICON__": "data:image/svg+xml," + urllib.parse.quote(svg("logo-icon.svg"), safe=""),
    }.items():
        html = html.replace(k, v)
    import site_header  # the shared top bar (scripts/site_header.*)
    html = site_header.inject(html, base="../")
    left = re.findall(r"__[A-Z_]+__", html)
    assert not left, f"unfilled placeholders in api docs: {left}"
    with open(os.path.join(ROOT, "api", "index.html"), "w", encoding="utf-8") as f:
        f.write(html)


def openapi(base, site, release, conditions, class_ids):
    ref = lambda n: {"$ref": f"#/components/schemas/{n}"}

    def ok(desc, data_schema, extra=None):
        props = {"api": {"type": "string"}, "apiVersion": {"type": "string"}, "dataVersion": {"type": "string"},
                 "released": {"type": "string", "format": "date"}, "license": {"type": "string"},
                 "attribution": {"type": "string"}, "disclaimer": {"type": "string"},
                 "links": {"type": "object", "additionalProperties": {"type": "string"}},
                 "count": {"type": "integer"}, "data": data_schema}
        props.update(extra or {})
        return {"200": {"description": desc, "content": {"application/json": {"schema": {"type": "object", "properties": props}}}},
                "404": {"description": "Unknown id"}}

    def op(summary, desc, data_schema, params=None, extra=None, opid=None):
        o = {"summary": summary, "operationId": opid, "responses": ok(desc, data_schema, extra)}
        if params:
            o["parameters"] = params
        return {"get": o}

    arr = lambda s: {"type": "array", "items": s}
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "NomadCeuticals Medicines API",
            "version": f"v1 (data {release['version']})",
            "description": "Free, read-only API of FDA-approved medicines for HIV, ADHD and diabetes. Static JSON files: GET only, "
                           "no authentication. Paths end in .json. For general reference only, not medical advice.",
            "license": {"name": "CC BY 4.0 (data)", "url": "https://creativecommons.org/licenses/by/4.0/"},
            "contact": {"url": REPO},
        },
        "servers": [{"url": base}],
        "paths": {
            "/index.json": op("API root", "Versions, counts and endpoint list", {"type": "object"}, opid="getIndex"),
            "/medicines.json": op("List medicines", "Every medicine (summary fields)", arr(ref("MedicineSummary")), opid="listMedicines"),
            "/medicines/{id}.json": op("Get a medicine", "One medicine with related medicines in the same class", ref("Medicine"),
                                       [{"name": "id", "in": "path", "required": True, "schema": {"type": "string", "pattern": "^[a-z0-9-]+$"},
                                         "example": "biktarvy"}], {"related": arr(ref("MedicineSummary"))}, "getMedicine"),
            "/conditions.json": op("List conditions", "hiv, adhd and diabetes with counts", arr(ref("Condition")), opid="listConditions"),
            "/conditions/{condition}.json": op("Medicines for a condition", "Every medicine for one condition (full records)", arr(ref("Medicine")),
                                               [{"name": "condition", "in": "path", "required": True, "schema": {"enum": conditions}}],
                                               {"condition": ref("Condition"), "classes": arr({"type": "object"})}, "getCondition"),
            "/classes.json": op("List drug classes", "Every drug class with counts", arr(ref("DrugClass")), opid="listClasses"),
            "/classes/{classId}.json": op("Medicines in a drug class", "Every medicine in one class (full records)", arr(ref("Medicine")),
                                          [{"name": "classId", "in": "path", "required": True, "schema": {"enum": class_ids}}],
                                          {"drugClass": ref("DrugClass")}, "getClass"),
        },
        "components": {"schemas": {
            "MedicineSummary": {"type": "object", "properties": {
                "id": {"type": "string"}, "brandName": {"type": "string"}, "genericName": {"type": "string"},
                "condition": {"enum": conditions}, "drugClass": {"type": "string"}, "classId": {"type": "string"},
                "status": {"type": "string"}, "url": {"type": "string", "format": "uri"}}},
            "Medicine": {"description": f"Full record. Fields follow {site}schema/medicine.schema.json, plus classId and links.",
                         "type": "object", "properties": {
                             "id": {"type": "string"}, "condition": {"enum": conditions}, "brandName": {"type": "string"},
                             "genericName": {"type": "string"}, "drugClass": {"type": "string"}, "classId": {"type": "string"},
                             "formulation": {"type": ["string", "null"]}, "route": {"type": ["string", "null"]},
                             "dosingFrequency": {"type": ["string", "null"]}, "manufacturer": {"type": ["string", "null"]},
                             "approvalYear": {"type": ["integer", "null"]}, "approvalDate": {"type": ["string", "null"]},
                             "status": {"type": "string"}, "description": {"type": ["string", "null"]}, "notes": {"type": ["string", "null"]},
                             "sourceUrl": {"type": "string"}, "attributes": {"type": "object"},
                             "links": {"type": "object", "additionalProperties": {"type": "string"}}}},
            "Condition": {"type": "object", "properties": {"id": {"enum": conditions}, "name": {"type": "string"}, "description": {"type": "string"},
                                                           "medicineCount": {"type": "integer"}, "classCount": {"type": "integer"}, "url": {"type": "string"}}},
            "DrugClass": {"type": "object", "properties": {"id": {"type": "string"}, "name": {"type": "string"}, "condition": {"enum": conditions},
                                                           "medicineCount": {"type": "integer"}, "url": {"type": "string"}}},
        }},
    }


if __name__ == "__main__":
    main()
