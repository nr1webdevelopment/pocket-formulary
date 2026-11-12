"""Fills in official identifiers and FDA evidence for library ingredients, from free public APIs:

  * RxNav (US National Library of Medicine):  RxNorm ingredient ID (RxCUI)
  * openFDA Drugs@FDA:                         FDA application numbers and UNII codes

    python3 scripts/enrich_library.py            # only ingredients without an RxCUI
    python3 scripts/enrich_library.py --all      # re-check everything

Needs internet access to rxnav.nlm.nih.gov and api.fda.gov. It runs in GitHub Actions
(.github/workflows/enrich.yml), which opens a pull request with the changes for review.
It never changes approval status by itself: when openFDA disagrees with the record, it marks the
ingredient "needs_review" and explains why, so a person decides.
"""
import glob
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ING = os.path.join(ROOT, "data", "library", "ingredients")
TODAY = time.strftime("%Y-%m-%d")
UA = {"User-Agent": "NomadCeuticals library enrichment (https://github.com/nr1webdevelopment/pocket-formulary)"}

# Names RxNorm / openFDA know these ingredients by, when ours differ. None = skip lookup.
RXNORM_NAME = {
    "mixed-amphetamine-salts": None,           # four amphetamine salts; RxNorm models it as a multi-ingredient
    "insulin-isophane-human": "insulin isophane, human",
    "insulin-human": "insulin, regular, human",
    "tenofovir-disoproxil": "tenofovir disoproxil",
}
FDA_NAME = {
    "mixed-amphetamine-salts": "dextroamphetamine saccharate",
    "insulin-isophane-human": "insulin isophane human",
    "insulin-human": "insulin human",
    "tenofovir-disoproxil": "tenofovir disoproxil fumarate",
}


def get_json(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 429 and i < tries - 1:
                time.sleep(5 * (i + 1))
                continue
            raise
        except urllib.error.URLError:
            if i < tries - 1:
                time.sleep(3)
                continue
            raise


def rxcui_for(name):
    q = urllib.parse.urlencode({"name": name, "search": 2})
    j = get_json(f"https://rxnav.nlm.nih.gov/REST/rxcui.json?{q}") or {}
    ids = (j.get("idGroup") or {}).get("rxnormId") or []
    return ids[0] if ids else None


def fda_evidence(name):
    """Returns (application numbers, UNIIs) from Drugs@FDA for a generic name."""
    q = urllib.parse.quote(f'openfda.generic_name:"{name}"')
    j = get_json(f"https://api.fda.gov/drug/drugsfda.json?search={q}&limit=100")
    apps, uniis = set(), set()
    for r in (j or {}).get("results", []):
        apps.add(r.get("application_number"))
        for u in (r.get("openfda") or {}).get("unii", []):
            uniis.add(u)
    return sorted(a for a in apps if a), sorted(uniis)


def main():
    redo = "--all" in sys.argv
    changed = flagged = 0
    for path in sorted(glob.glob(os.path.join(ING, "*.json"))):
        rec = json.load(open(path, encoding="utf-8"))
        ids = rec.setdefault("ids", {"rxcui": None, "unii": []})
        if ids.get("rxcui") and not redo:
            continue
        iid, before = rec["id"], json.dumps(rec, sort_keys=True)
        rx_name = RXNORM_NAME.get(iid, rec["name"])
        if rx_name:
            ids["rxcui"] = rxcui_for(rx_name) or ids.get("rxcui")
        time.sleep(0.1)
        apps, uniis = fda_evidence(FDA_NAME.get(iid, rec["name"]))
        time.sleep(0.3)
        if uniis:
            ids["unii"] = sorted(set(ids.get("unii") or []) | set(uniis))
        us = next((a for a in rec["approvals"] if a["jurisdiction"] == "US"), None)
        notes = []
        if us and us["status"] == "approved" and not apps:
            notes.append("openFDA Drugs@FDA has no application for this name (check the name, or it may be a biologic or OTC monograph product).")
        if us and us["status"] in ("not_approved", "investigational") and apps:
            notes.append(f"openFDA lists FDA applications ({', '.join(apps[:5])}) but the record says {us['status']}.")
        if rx_name and not ids.get("rxcui"):
            notes.append(f"RxNorm has no ingredient named '{rx_name}'.")
        if us and apps:
            us["note"] = (us.get("note") or "").split(" FDA applications:")[0].strip() or None
            us["note"] = ((us["note"] + " ") if us["note"] else "") + f"FDA applications: {', '.join(apps[:8])}{' …' if len(apps) > 8 else ''}."
            us["checked"] = TODAY
        if notes:
            rec["review"] = {"status": "needs_review", "checked": TODAY, "by": "enrich_library.py", "note": " ".join(notes)}
            flagged += 1
        if json.dumps(rec, sort_keys=True) != before:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(rec, f, ensure_ascii=False, indent=2)
                f.write("\n")
            changed += 1
            print(f"{iid:28} rxcui={ids.get('rxcui')} unii={len(ids.get('unii') or [])} apps={len(apps)}" + ("  NEEDS REVIEW" if notes else ""))
    print(f"\n{changed} ingredient files updated, {flagged} flagged for review")


if __name__ == "__main__":
    main()
