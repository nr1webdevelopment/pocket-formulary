"""Builds the public, versioned dataset in dist/v1/ from the source files in data/.

Sources (edit these):
  data/hiv-medicines.csv, data/adhd-medicines.csv, data/diabetes-medicines.csv
  data/providers/*.json
  data/release.json                 (version + release date)

Outputs (never edit by hand, always rebuild):
  dist/v1/medicines.json  dist/v1/medicines.csv
  dist/v1/providers.json  dist/v1/providers.csv
  dist/v1/manifest.json   (version, record counts, sha256 checksums)

The build is deterministic (no timestamps from the clock), so CI can check
that the committed dist/ matches the sources.
"""
import csv, glob, hashlib, io, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "dist", "v1")
RAW = "https://raw.githubusercontent.com/nr1webdevelopment/pocket-formulary/main"

COMMON = {  # csv column -> output field
    "slug": "id", "brandName": "brandName", "genericName": "genericName", "drugClass": "drugClass",
    "formulation": "formulation", "route": "route", "dosingFrequency": "dosingFrequency",
    "manufacturer": "manufacturer", "approvalYear": "approvalYear", "fdaApprovalDate": "approvalDate",
    "status": "status", "description": "description", "notes": "notes", "sourceUrl": "sourceUrl",
}


def coerce(v):
    if v is None or v == "":
        return None
    if v in ("true", "false"):
        return v == "true"
    if v.isdigit() and len(v) < 6:
        return int(v)
    return v


def load_medicines():
    out = []
    for cond in ("hiv", "adhd", "diabetes"):
        with open(os.path.join(DATA, f"{cond}-medicines.csv"), encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rec = {"id": None, "condition": cond}
                attrs = {}
                for k, v in row.items():
                    if k in COMMON:
                        rec[COMMON[k]] = coerce(v) if k == "approvalYear" else (v or None)
                    else:
                        attrs[k] = coerce(v)
                for field in COMMON.values():
                    rec.setdefault(field, None)
                rec["attributes"] = attrs
                out.append(rec)
    return sorted(out, key=lambda r: (r["condition"], r["id"]))


def load_cities():
    with open(os.path.join(DATA, "cities.json"), encoding="utf-8") as f:
        return json.load(f)


def load_providers():
    out = []
    for path in sorted(glob.glob(os.path.join(DATA, "providers", "*.json"))):
        with open(path, encoding="utf-8") as f:
            out.extend(json.load(f)["providers"])
    return sorted(out, key=lambda r: r["id"])


def flatten(d, prefix=""):
    flat = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            flat.update(flatten(v, key + "."))
        elif isinstance(v, list):
            if v and isinstance(v[0], dict):  # sources
                flat[key] = " | ".join(x.get("url", "") for x in v)
            else:
                flat[key] = "; ".join(str(x) for x in v)
        elif isinstance(v, bool):
            flat[key] = "true" if v else "false"
        else:
            flat[key] = "" if v is None else v
    return flat


def to_csv(rows):
    flat = [flatten(r) for r in rows]
    cols = []
    for r in flat:
        for k in r:
            if k not in cols:
                cols.append(k)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    w.writerows(flat)
    return buf.getvalue()


def write(name, text, files):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    raw = text.encode("utf-8")
    files[name] = {"url": f"{RAW}/dist/v1/{name}", "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    rel = json.load(open(os.path.join(DATA, "release.json"), encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    meds, provs, cdoc = load_medicines(), load_providers(), load_cities()
    cities = cdoc["cities"]
    files = {}
    for name, rows, schema in (("medicines", meds, "medicine"), ("providers", provs, "provider"), ("cities", cities, "city")):
        doc = {"dataset": name, "version": rel["version"], "released": rel["released"], "license": rel["license"],
               "schema": f"{RAW}/schema/{schema}.schema.json", "count": len(rows), "data": rows}
        if name == "cities":
            doc["jurisdictionNotes"] = cdoc.get("jurisdictionNotes", {})
        write(f"{name}.json", json.dumps(doc, ensure_ascii=False, indent=2) + "\n", files)
        write(f"{name}.csv", to_csv(rows), files)
    status = {}
    for p in provs:
        s = p["verification"]["status"]
        status[s] = status.get(s, 0) + 1
    by_cond, by_city = {}, {}
    for p in provs:
        by_city[p["city"]] = by_city.get(p["city"], 0) + 1
        for c in p["conditions"]:
            by_cond[c] = by_cond.get(c, 0) + 1
    manifest = {**rel, "counts": {"medicines": len(meds), "providers": len(provs),
                                  "providersByCity": dict(sorted(by_city.items())),
                                  "providersByCondition": dict(sorted(by_cond.items())),
                                  "providersByVerification": dict(sorted(status.items()))},
                "files": files}
    # translations: copy i18n/*.json to dist/v1/i18n/ so API users get them too
    os.makedirs(os.path.join(OUT, "i18n"), exist_ok=True)
    for src in sorted(glob.glob(os.path.join(ROOT, "i18n", "*.json"))):
        name = os.path.basename(src)
        with open(src, encoding="utf-8") as f:
            write(f"i18n/{name}", json.dumps(json.load(f), ensure_ascii=False, indent=1) + "\n", files)
    manifest["files"] = files
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"dist/v1: {len(meds)} medicines, {len(provs)} providers (v{rel['version']})")


if __name__ == "__main__":
    main()
