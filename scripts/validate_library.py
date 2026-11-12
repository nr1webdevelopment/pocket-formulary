"""Checks data/library/ (the v2 medicine library). Run on its own or from scripts/validate.py.

    python3 scripts/validate_library.py

Errors (fail CI):  schema violations, duplicate ids, broken references (unknown ingredient, condition or
                   product), a "via" product that doesn't contain the ingredient, v1 medicines missing from
                   the library or disagreeing with it (brand name, discontinued status).
Warnings:          ingredients still unverified or flagged needs_review, missing official IDs.
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "data", "library")


def check():
    from jsonschema import Draft202012Validator, FormatChecker
    errors, warnings = [], []
    sch = lambda n: Draft202012Validator(json.load(open(os.path.join(ROOT, "schema", "v2", f"{n}.schema.json"))), format_checker=FormatChecker())
    v_ing, v_prod, v_cond = sch("ingredient"), sch("product"), sch("condition")

    conditions = json.load(open(os.path.join(LIB, "conditions.json"), encoding="utf-8"))
    cond_ids = set()
    for c in conditions:
        errors += [f"conditions.json {c.get('id')}: {e.message}" for e in v_cond.iter_errors(c)]
        if c["id"] in cond_ids:
            errors.append(f"conditions.json: duplicate id {c['id']}")
        cond_ids.add(c["id"])
    for c in conditions:
        if c.get("parent") and c["parent"] not in cond_ids:
            errors.append(f"conditions.json {c['id']}: unknown parent {c['parent']}")

    def load_dir(name, validator):
        out = {}
        for p in sorted(glob.glob(os.path.join(LIB, name, "*.json"))):
            rec = json.load(open(p, encoding="utf-8"))
            fname = os.path.basename(p)[:-5]
            errors.extend(f"{name}/{fname}.json: {e.message}" for e in validator.iter_errors(rec))
            if rec.get("id") != fname:
                errors.append(f"{name}/{fname}.json: id '{rec.get('id')}' must match the file name")
            out[rec.get("id")] = rec
        return out

    ings, prods = load_dir("ingredients", v_ing), load_dir("products", v_prod)
    for p in prods.values():
        for iid in p.get("ingredients", []):
            if iid not in ings:
                errors.append(f"products/{p['id']}: unknown ingredient {iid}")
        for c in p.get("indications", []):
            if c not in cond_ids:
                errors.append(f"products/{p['id']}: unknown condition {c}")
    used = {iid for p in prods.values() for iid in p.get("ingredients", [])}
    for i in ings.values():
        for u in i.get("uses", []):
            if u["condition"] not in cond_ids:
                errors.append(f"ingredients/{i['id']}: unknown condition {u['condition']}")
            for pid in u.get("via", []):
                if pid not in prods:
                    errors.append(f"ingredients/{i['id']}: use via unknown product {pid}")
                elif i["id"] not in prods[pid]["ingredients"]:
                    errors.append(f"ingredients/{i['id']}: use via {pid}, but {pid} doesn't contain {i['id']}")
        if not any(a["jurisdiction"] == "US" for a in i.get("approvals", [])):
            warnings.append(f"ingredients/{i['id']}: no US (FDA) status recorded")
        st = i.get("review", {}).get("status")
        if st == "needs_review":
            warnings.append(f"ingredients/{i['id']}: needs review: {i['review'].get('note')}")
        if i.get("kind") in ("drug", "biologic") and not (i.get("ids") or {}).get("rxcui"):
            warnings.append(f"ingredients/{i['id']}: no RxNorm ID yet (run the 'Look up official IDs' workflow)")
        if i["id"] not in used and i.get("tier") == "curated":
            warnings.append(f"ingredients/{i['id']}: no products linked")

    # API v1 must stay consistent with the library
    v1_path = os.path.join(ROOT, "dist", "v1", "medicines.json")
    if os.path.exists(v1_path):
        for m in json.load(open(v1_path, encoding="utf-8"))["data"]:
            p = prods.get(m["id"])
            if not p:
                errors.append(f"v1 medicine {m['id']} is missing from data/library/products/")
                continue
            if p["brandName"] != m["brandName"]:
                errors.append(f"products/{m['id']}: brand '{p['brandName']}' differs from v1 '{m['brandName']}'")
            if (p["status"] == "discontinued") != (m["status"].lower() == "discontinued"):
                errors.append(f"products/{m['id']}: status '{p['status']}' differs from v1 '{m['status']}'")
    unverified = sum(i.get("review", {}).get("status") == "unverified" for i in ings.values())
    summary = f"library: {len(ings)} ingredients, {len(prods)} products, {len(conditions)} conditions ({unverified} ingredients unverified)"
    return errors, warnings, summary


def main():
    errors, warnings, summary = check()
    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print(f"{summary}: {len(errors)} errors, {len(warnings)} warnings")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
