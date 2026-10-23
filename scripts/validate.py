"""Validates the source data and the built dist/ files.

  python3 scripts/validate.py            # errors fail (exit 1), warnings are printed
  python3 scripts/validate.py --strict   # warnings fail too

Checks: required fields, enums, ID format and uniqueness, dates, URLs,
verification rules (a 'verified' record needs who/when/how), and staleness
(verified records older than REVIEW_DAYS). If the `jsonschema` package is
installed, dist/v1/*.json is also checked against schema/*.schema.json.
"""
import datetime as dt, glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REVIEW_DAYS = 90
TODAY = dt.date.today()
errors, warnings = [], []
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID = re.compile(r"^[a-z]{2}-[a-z]{3}-[a-z0-9-]+$")
COND_SERVICES = {
    "hiv": ("hivTesting", "prep", "pep", "art"),
    "adhd": ("adhdAssessmentChildren", "adhdAssessmentAdults", "adhdMedication"),
    "diabetes": ("diabetesCare", "diabetesCareChildren"),
}


def err(where, msg): errors.append(f"{where}: {msg}")
def warn(where, msg): warnings.append(f"{where}: {msg}")


def date_ok(v):
    if v is None or not DATE.match(v):
        return False
    try:
        dt.date.fromisoformat(v); return True
    except ValueError:
        return False


def check_providers():
    schema = json.load(open(os.path.join(ROOT, "schema", "provider.schema.json"), encoding="utf-8"))
    props = schema["properties"]
    types, operators = props["type"]["enum"], props["operator"]["enum"]
    statuses = props["verification"]["properties"]["status"]["enum"]
    seen = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "providers", "*.json"))):
        rel = os.path.relpath(path, ROOT)
        try:
            doc = json.load(open(path, encoding="utf-8"))
        except json.JSONDecodeError as e:
            err(rel, f"invalid JSON: {e}"); continue
        for i, p in enumerate(doc.get("providers", [])):
            w = f"{rel}[{i}] {p.get('id', '?')}"
            for k in schema["required"]:
                if k not in p:
                    err(w, f"missing '{k}'")
            pid = p.get("id", "")
            if not ID.match(pid): err(w, "id must look like 'th-bkk-some-name'")
            if pid in seen: err(w, f"duplicate id (also in {seen[pid]})")
            seen[pid] = rel
            if not p.get("name", {}).get("en"): err(w, "name.en is required")
            if p.get("type") not in types: err(w, f"type must be one of {types}")
            if p.get("operator") not in operators: err(w, f"operator must be one of {operators}")
            c = p.get("contact", {})
            if not (c.get("phone") or c.get("website") or c.get("line")):
                err(w, "needs at least one way to contact (phone, website or LINE)")
            for k in ("website", "booking"):
                if c.get(k) and not c[k].startswith(("http://", "https://")): err(w, f"contact.{k} must be a URL")
            s = p.get("services", {})
            conds = p.get("conditions") or []
            if not conds or any(c not in COND_SERVICES for c in conds):
                err(w, f"conditions must be a non-empty list of {sorted(COND_SERVICES)}")
            svc_keys = set(schema["properties"]["services"]["properties"]) - {"basis", "note"}
            for k, val in s.items():
                if k in ("basis", "note"): continue
                if k not in svc_keys: err(w, f"unknown service '{k}'")
                elif val not in (True, False, None): err(w, f"services.{k} must be true, false or null")
            for c in conds:
                for k in COND_SERVICES.get(c, ()):
                    if k not in s: err(w, f"{c} provider needs services.{k} (use null if unknown)")
                if not any(s.get(k) for k in COND_SERVICES.get(c, ())):
                    warn(w, f"no {c} service is confirmed (all false/null)")
            src = p.get("sources") or []
            if not src: err(w, "at least one source is required")
            for x in src:
                if not str(x.get("url", "")).startswith(("http://", "https://")): err(w, f"bad source url {x.get('url')}")
                if not date_ok(x.get("accessed")): err(w, "source.accessed must be YYYY-MM-DD")
            v = p.get("verification", {})
            if v.get("status") not in statuses: err(w, f"verification.status must be one of {statuses}")
            if not date_ok(v.get("sourceChecked")): err(w, "verification.sourceChecked must be YYYY-MM-DD")
            if v.get("status") == "verified":
                for k in ("lastVerified", "method", "verifiedBy"):
                    if not v.get(k): err(w, f"status is 'verified' but verification.{k} is empty")
                if date_ok(v.get("lastVerified")):
                    age = (TODAY - dt.date.fromisoformat(v["lastVerified"])).days
                    if age > REVIEW_DAYS:
                        warn(w, f"verified {age} days ago — re-check and update, or set status to 'needs_review'")
            elif v.get("lastVerified"):
                warn(w, f"has lastVerified but status is '{v.get('status')}'")
            if not date_ok(p.get("updated")): err(w, "updated must be YYYY-MM-DD")
    return len(seen)


def check_medicines():
    import csv
    seen = {}
    for cond in ("hiv", "adhd", "diabetes"):
        rel = f"data/{cond}-medicines.csv"
        for i, r in enumerate(csv.DictReader(open(os.path.join(ROOT, rel), encoding="utf-8")), start=2):
            w = f"{rel}:{i} {r.get('slug')}"
            for k in ("slug", "brandName", "genericName", "drugClass", "status", "sourceUrl"):
                if not r.get(k): err(w, f"missing {k}")
            if r.get("slug") in seen: err(w, f"duplicate slug (also in {seen[r['slug']]})")
            seen[r.get("slug")] = rel
            y = r.get("approvalYear")
            if y and not (y.isdigit() and 1900 <= int(y) <= 2100): err(w, f"bad approvalYear {y}")
            d = r.get("fdaApprovalDate")
            if d and not date_ok(d): err(w, f"bad fdaApprovalDate {d}")
    return len(seen)


def check_dist():
    man_path = os.path.join(ROOT, "dist", "v1", "manifest.json")
    if not os.path.exists(man_path):
        err("dist/v1", "not built — run python3 scripts/build_dist.py"); return
    try:
        import jsonschema
        Validator = jsonschema.Draft202012Validator
    except (ImportError, AttributeError):
        print("(jsonschema >= 4 not installed — skipping schema check of dist/; CI runs it)"); return
    for name, schema in (("medicines", "medicine"), ("providers", "provider")):
        sch = json.load(open(os.path.join(ROOT, "schema", f"{schema}.schema.json"), encoding="utf-8"))
        v = Validator(sch)
        doc = json.load(open(os.path.join(ROOT, "dist", "v1", f"{name}.json"), encoding="utf-8"))
        for rec in doc["data"]:
            for e in v.iter_errors(rec):
                err(f"dist/v1/{name}.json {rec.get('id')}", f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}")


if __name__ == "__main__":
    n_p, n_m = check_providers(), check_medicines()
    check_dist()
    for x in warnings: print("WARN ", x)
    for x in errors: print("ERROR", x)
    print(f"checked {n_m} medicines, {n_p} providers: {len(errors)} errors, {len(warnings)} warnings")
    sys.exit(1 if errors or ("--strict" in sys.argv and warnings) else 0)
