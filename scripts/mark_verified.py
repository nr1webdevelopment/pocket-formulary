"""Record that you confirmed a provider directly (phone, email or visit).

  python3 scripts/mark_verified.py th-bkk-swing-silom --by "Gary" --method phone \
      --set prep=true pep=false art=true walkIn=true foreignersAccepted=true \
      --hours "Mon–Fri 10:00–18:00" --languages Thai English --note "Spoke to reception"

  python3 scripts/mark_verified.py th-bkk-xyz --by "Gary" --method phone --closed

Sets verification.status=verified (or closed), lastVerified=today, nextReviewDue=today+90d,
adds a source entry for the contact, then you rebuild:  python3 scripts/build_dist.py
"""
import argparse, datetime as dt, glob, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVICES = {"hivTesting", "prep", "pep", "art", "stiTesting", "genderAffirmingHormones",
            "adhdAssessmentChildren", "adhdAssessmentAdults", "adhdMedication",
            "diabetesCare", "diabetesCareChildren", "endocrinologist", "insulinPump", "cgm",
            "diabetesEducation", "diabeticFootCare"}
ACCESS = {"walkIn", "foreignersAccepted"}

ap = argparse.ArgumentParser()
ap.add_argument("id")
ap.add_argument("--by", required=True, help="who checked")
ap.add_argument("--method", required=True, choices=["phone", "email", "in_person", "official_registry"])
ap.add_argument("--set", nargs="*", default=[], metavar="field=true|false|null")
ap.add_argument("--hours")
ap.add_argument("--languages", nargs="*")
ap.add_argument("--note")
ap.add_argument("--closed", action="store_true", help="provider has closed / no longer offers HIV services")
a = ap.parse_args()

today = dt.date.today()
for path in glob.glob(os.path.join(ROOT, "data", "providers", "*.json")):
    doc = json.load(open(path, encoding="utf-8"))
    for p in doc["providers"]:
        if p["id"] != a.id:
            continue
        for kv in a.set:
            k, v = kv.split("=", 1)
            val = {"true": True, "false": False, "null": None}[v.lower()]
            if k in SERVICES:
                p["services"][k] = val
                p["services"]["basis"] = "site"
            elif k in ACCESS:
                p["access"][k] = val
            else:
                raise SystemExit(f"unknown field {k}; use one of {sorted(SERVICES | ACCESS)}")
        if a.hours: p["hours"] = a.hours
        if a.languages: p["access"]["languages"] = a.languages
        if a.note: p["notes"] = ((p.get("notes") or "") + f" [{today}] {a.note}").strip()
        p["verification"].update(status="closed" if a.closed else "verified", lastVerified=today.isoformat(),
                                 method=a.method, verifiedBy=a.by,
                                 nextReviewDue=(today + dt.timedelta(days=90)).isoformat())
        src_type = {"phone": "phone_call", "email": "email"}.get(a.method)
        if src_type:
            p["sources"].append({"url": p["contact"].get("website") or p["sources"][0]["url"],
                                 "title": f"Direct {a.method} confirmation by {a.by}", "publisher": p["organization"],
                                 "type": src_type, "accessed": today.isoformat()})
        p["updated"] = today.isoformat()
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
        print(f"{a.id}: {p['verification']['status']} on {today} by {a.by} ({a.method})")
        raise SystemExit(0)
raise SystemExit(f"no provider with id {a.id}")
