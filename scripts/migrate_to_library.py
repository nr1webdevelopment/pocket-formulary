"""ONE-OFF migration (2026-11-12): builds the v2 library in data/library/ from
  1. the 124 API v1 medicines (dist/v1/medicines.json, brand-level, FDA-approved for HIV/ADHD/diabetes)
  2. the PSY96 CBT Study Hub medication list (43 ingredients: depression, anxiety, ADHD, postpartum depression)
  3. the ENT Study Hub medicines (named in its text; entered here by hand)

    python3 scripts/migrate_to_library.py "Stanford PSY96 App/index.html"

After this runs once, data/library/ is the source of truth and is edited by hand (or by
scripts/enrich_library.py). Re-running this script overwrites data/library/ and loses those edits:
it refuses to run if data/library/ exists, unless you pass --force.
"""
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "data", "library")
TODAY = "2026-11-12"
DAILYMED = "https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query="
DEA = "https://www.deadiversion.usdoj.gov/schedules/orangebook/c_cs_alpha.pdf"


def slug(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


# ---------------------------------------------------------------- conditions
CONDITIONS = [
    ("hiv", "HIV (treatment and prevention)", "infectious-disease", ["HIV-1", "PrEP"], None),
    ("hepatitis-b", "Chronic hepatitis B", "infectious-disease", ["HBV"], None),
    ("adhd", "ADHD", "mental-health", ["attention-deficit/hyperactivity disorder"], None),
    ("depression", "Depression", "mental-health", ["major depressive disorder", "MDD"], None),
    ("postpartum-depression", "Postpartum depression", "mental-health", ["PPD", "perinatal depression"], "depression"),
    ("anxiety", "Anxiety disorders", "mental-health", ["generalized anxiety disorder", "GAD", "panic disorder", "social anxiety"], None),
    ("diabetes", "Diabetes", "endocrine", ["type 1 diabetes", "type 2 diabetes"], None),
    ("allergic-rhinitis", "Allergic rhinitis (hay fever)", "ent", ["hay fever", "nasal allergies"], None),
    ("nasal-polyps", "Nasal polyps (chronic rhinosinusitis with nasal polyps)", "ent", ["CRSwNP"], None),
    ("nasal-congestion", "Nasal congestion", "ent", ["stuffy nose"], None),
    ("otitis-media", "Middle-ear infection (otitis media)", "ent", ["ear infection", "AOM"], None),
    ("otitis-externa", "Swimmer's ear (otitis externa)", "ent", ["outer-ear infection"], None),
    ("pharyngitis", "Sore throat and tonsillitis (bacterial pharyngitis)", "ent", ["strep throat", "tonsillitis"], None),
    ("vertigo", "Vertigo", "ent", ["dizziness", "motion sickness"], None),
    ("urticaria", "Chronic hives (urticaria)", "dermatology", ["hives"], None),
]

# ---------------------------------------------------------------- v1 generic name -> ingredient ids
QUALIFIERS = r"\((?:extended-release(?: injections?)?|transdermal|nasal|inhaled|oral|faster-acting|NPH|delayed- and extended-release)\)"
CANON = {
    "mixed amphetamine salts": "mixed amphetamine salts",
    "amphetamine sulfate": "amphetamine",
    "tenofovir disoproxil fumarate": "tenofovir disoproxil",
    "insulin human regular": "insulin human",
    "insulin human": "insulin human",
    "insulin isophane": "insulin isophane human",
    "insulin glargine u-300": "insulin glargine",
}
SYNONYMS = {
    "tenofovir disoproxil": ["tenofovir disoproxil fumarate", "TDF"],
    "tenofovir alafenamide": ["TAF"],
    "mixed amphetamine salts": ["dextroamphetamine and amphetamine", "amphetamine aspartate, amphetamine sulfate, dextroamphetamine saccharate, dextroamphetamine sulfate"],
    "insulin isophane human": ["NPH insulin", "isophane insulin"],
    "insulin human": ["regular insulin", "human insulin"],
    "emtricitabine": ["FTC"], "lamivudine": ["3TC"], "zidovudine": ["AZT", "ZDV"], "abacavir": ["ABC"],
    "bupropion": ["bupropion hydrochloride", "amfebutamone"],
    "dextroamphetamine": ["dexamfetamine"], "lisdexamfetamine": ["lisdexamfetamine dimesylate"],
}
BIOLOGIC = re.compile(r"^insulin|mab$|^teplizumab|^ibalizumab|^dupilumab")


def split_generic(g):
    g = re.sub(QUALIFIERS, "", g, flags=re.I).strip()
    parts = [p.strip() for p in re.split(r",\s*(?:and\s+)?|\s+and\s+", g) if p.strip()]
    out = []
    for p in parts:
        p = p.lower()
        m = re.match(r"^(.*?)-([a-z]{4})$", p)  # biologic suffixes: insulin glargine-yfgn, teplizumab-mzwv
        if m and (m.group(1).startswith("insulin") or m.group(1).endswith("mab")):
            p = m.group(1)
        out.append(CANON.get(p, p))
    return out


# classes for ingredients that only appear inside combinations
COMBO_CLASSES = {
    "bictegravir": "INSTI", "elvitegravir": "INSTI", "cobicistat": "Pharmacokinetic Enhancer", "islatravir": "NRTTI",
    "lopinavir": "PI", "serdexmethylphenidate": "CNS stimulant (methylphenidate prodrug)", "lixisenatide": "GLP-1 receptor agonist",
    "dextromethorphan": "NMDA receptor antagonist",
}
V1_CLASS_FIX = {"Combination": None}


# ---------------------------------------------------------------- PSY96: generic -> (ingredients, [(brand, status, existing v1 id or None, form)])
PSY_CLASS = {
    "ssri": "SSRI (selective serotonin reuptake inhibitor)", "snri": "SNRI (serotonin-norepinephrine reuptake inhibitor)",
    "atyp": "Atypical antidepressant", "rapid": "Rapid-acting antidepressant", "ppd": "Neuroactive steroid (GABA-A modulator)",
    "older": "Older antidepressant (TCA or MAOI)", "aug": "Atypical antipsychotic (add-on for depression)",
    "anx": "Anti-anxiety medicine", "stim": "CNS stimulant", "nonstim": "ADHD non-stimulant",
}
PSY_OLDER = {"amitriptyline": "Tricyclic antidepressant (TCA)", "nortriptyline": "Tricyclic antidepressant (TCA)",
             "phenelzine": "MAO inhibitor (MAOI)", "selegiline": "MAO inhibitor (MAOI)",
             "alprazolam": "Benzodiazepine", "clonazepam": "Benzodiazepine", "lorazepam": "Benzodiazepine", "diazepam": "Benzodiazepine",
             "buspirone": "Azapirone anxiolytic", "hydroxyzine": "Antihistamine (anxiolytic)", "propranolol": "Beta blocker",
             "bupropion": "Atypical antidepressant (NDRI)", "esketamine": "NMDA receptor antagonist"}
A, D, U = "available", "discontinued", "unknown"
PSY_PRODUCTS = {
    "Sertraline": (["sertraline"], [("Zoloft", A, None, "Tablet; oral solution")]),
    "Fluoxetine": (["fluoxetine"], [("Prozac", A, None, "Capsule")]),
    "Escitalopram": (["escitalopram"], [("Lexapro", A, None, "Tablet; oral solution")]),
    "Citalopram": (["citalopram"], [("Celexa", A, None, "Tablet")]),
    "Paroxetine": (["paroxetine"], [("Paxil", A, None, "Tablet"), ("Pexeva", A, None, "Tablet")]),
    "Venlafaxine XR": (["venlafaxine"], [("Effexor XR", A, None, "Extended-release capsule")]),
    "Desvenlafaxine": (["desvenlafaxine"], [("Pristiq", A, None, "Extended-release tablet")]),
    "Duloxetine": (["duloxetine"], [("Cymbalta", A, None, "Delayed-release capsule"), ("Drizalma Sprinkle", A, None, "Delayed-release capsule")]),
    "Levomilnacipran": (["levomilnacipran"], [("Fetzima", A, None, "Extended-release capsule")]),
    "Bupropion": (["bupropion"], [("Wellbutrin SR", A, None, "Extended-release tablet"), ("Wellbutrin XL", A, None, "Extended-release tablet"),
                                   ("Aplenzin", A, None, "Extended-release tablet"), ("Zyban", U, None, "Extended-release tablet")]),
    "Mirtazapine": (["mirtazapine"], [("Remeron", A, None, "Tablet"), ("Remeron SolTab", A, None, "Orally disintegrating tablet")]),
    "Trazodone": (["trazodone"], [("Desyrel", D, None, "Tablet")]),
    "Vilazodone": (["vilazodone"], [("Viibryd", A, None, "Tablet")]),
    "Vortioxetine": (["vortioxetine"], [("Trintellix", A, None, "Tablet")]),
    "Gepirone ER": (["gepirone"], [("Exxua", A, None, "Extended-release tablet")]),
    "Esketamine (nasal spray)": (["esketamine"], [("Spravato", A, None, "Nasal spray")]),
    "Dextromethorphan–bupropion": (["dextromethorphan", "bupropion"], [("Auvelity", A, None, "Extended-release tablet")]),
    "Zuranolone": (["zuranolone"], [("Zurzuvae", A, None, "Capsule")]),
    "Brexanolone": (["brexanolone"], [("Zulresso", D, None, "IV infusion")]),
    "Amitriptyline": (["amitriptyline"], [("Elavil", D, None, "Tablet")]),
    "Nortriptyline": (["nortriptyline"], [("Pamelor", A, None, "Capsule")]),
    "Phenelzine": (["phenelzine"], [("Nardil", A, None, "Tablet")]),
    "Selegiline (skin patch)": (["selegiline"], [("Emsam", A, None, "Transdermal patch")]),
    "Aripiprazole": (["aripiprazole"], [("Abilify", A, None, "Tablet")]),
    "Brexpiprazole": (["brexpiprazole"], [("Rexulti", A, None, "Tablet")]),
    "Quetiapine XR": (["quetiapine"], [("Seroquel XR", A, None, "Extended-release tablet")]),
    "Cariprazine": (["cariprazine"], [("Vraylar", A, None, "Capsule")]),
    "Buspirone": (["buspirone"], [("Buspar", D, None, "Tablet")]),
    "Hydroxyzine": (["hydroxyzine"], [("Vistaril", A, None, "Capsule"), ("Atarax", U, None, "Tablet")]),
    "Alprazolam": (["alprazolam"], [("Xanax", A, None, "Tablet"), ("Xanax XR", A, None, "Extended-release tablet")]),
    "Clonazepam": (["clonazepam"], [("Klonopin", A, None, "Tablet")]),
    "Lorazepam": (["lorazepam"], [("Ativan", A, None, "Tablet")]),
    "Diazepam": (["diazepam"], [("Valium", A, None, "Tablet")]),
    "Propranolol": (["propranolol"], [("Inderal", U, None, "Tablet")]),
    "Methylphenidate": (["methylphenidate"], [("Ritalin", A, "ritalin", None), ("Concerta", A, "concerta", None), ("Jornay PM", A, "jornay-pm", None),
                                               ("Daytrana", A, "daytrana", None), ("QuilliChew ER", A, "quillichew-er", None)]),
    "Dexmethylphenidate": (["dexmethylphenidate"], [("Focalin", A, "focalin", None), ("Focalin XR", A, "focalin-xr", None), ("Azstarys", A, "azstarys", None)]),
    "Mixed amphetamine salts": (["mixed amphetamine salts"], [("Adderall", A, "adderall", None), ("Adderall XR", A, "adderall-xr", None), ("Mydayis", A, "mydayis", None)]),
    "Lisdexamfetamine": (["lisdexamfetamine"], [("Vyvanse", A, "vyvanse", None)]),
    "Dextroamphetamine": (["dextroamphetamine"], [("Dexedrine Spansule", A, None, "Extended-release capsule"), ("Zenzedi", A, None, "Tablet"),
                                                   ("ProCentra", A, None, "Oral solution"), ("Xelstrym", A, "xelstrym", None)]),
    "Atomoxetine": (["atomoxetine"], [("Strattera", A, "strattera", None)]),
    "Viloxazine ER": (["viloxazine"], [("Qelbree", A, "qelbree", None)]),
    "Guanfacine ER": (["guanfacine"], [("Intuniv", A, "intuniv", None)]),
    "Clonidine ER": (["clonidine"], [("Kapvay", U, None, "Extended-release tablet")]),
}
PSY_COND = {"dep": "depression", "anx": "anxiety", "adhd": "adhd", "ppd": "postpartum-depression"}
US_SCHEDULE = {  # DEA controlled-substance schedules (US)
    "esketamine": "CIII", "alprazolam": "CIV", "clonazepam": "CIV", "lorazepam": "CIV", "diazepam": "CIV",
    "zuranolone": "CIV", "brexanolone": "CIV", "dextroamphetamine": "CII", "lisdexamfetamine": "CII",
}

# ---------------------------------------------------------------- ENT Study Hub medicines (US labels)
ENT = [
    # ingredient, class, kind, US status, ingredient uses [(condition, note)], products [(brand, status, form, route, indications, otc)]
    ("amoxicillin", "Penicillin antibiotic", "drug", "approved",
     [("otitis-media", None), ("pharyngitis", "Infections of the ear, nose and throat")],
     [("Amoxil", U, "Capsule; tablet; oral suspension", "Oral", ["otitis-media", "pharyngitis"], False)]),
    ("ofloxacin", "Fluoroquinolone antibiotic", "drug", "approved",
     [("otitis-externa", "Ear drops"), ("otitis-media", "Ear drops: chronic draining ear with a perforated eardrum, or infection with ear tubes")],
     [("Ofloxacin Otic", A, "Ear drops", "Otic", ["otitis-externa", "otitis-media"], False)]),
    ("ciprofloxacin", "Fluoroquinolone antibiotic", "drug", "approved",
     [("otitis-externa", "Ear drops"), ("otitis-media", "Ear drops with dexamethasone, for infections with ear tubes")],
     [("Cetraxal", U, "Ear drops", "Otic", ["otitis-externa"], False),
      ("Ciprodex", A, "Ear drops (suspension)", "Otic", ["otitis-media", "otitis-externa"], False)]),
    ("dexamethasone", "Corticosteroid", "drug", "approved", [], []),
    ("fluticasone", "Corticosteroid (nasal)", "drug", "approved",
     [("allergic-rhinitis", "Nasal spray (fluticasone propionate or furoate)"), ("nasal-polyps", "Nasal spray (fluticasone propionate, Xhance)")],
     [("Flonase", A, "Nasal spray", "Nasal", ["allergic-rhinitis"], True), ("Xhance", A, "Nasal spray", "Nasal", ["nasal-polyps"], False)]),
    ("mometasone", "Corticosteroid (nasal)", "drug", "approved",
     [("allergic-rhinitis", "Nasal spray"), ("nasal-polyps", "Nasal spray")],
     [("Nasonex", A, "Nasal spray", "Nasal", ["allergic-rhinitis", "nasal-polyps"], True)]),
    ("cetirizine", "Antihistamine (second-generation)", "drug", "approved",
     [("allergic-rhinitis", None), ("urticaria", None)], [("Zyrtec", A, "Tablet; oral solution", "Oral", ["allergic-rhinitis", "urticaria"], True)]),
    ("azelastine", "Antihistamine (nasal)", "drug", "approved",
     [("allergic-rhinitis", "Nasal spray")], [("Astepro", A, "Nasal spray", "Nasal", ["allergic-rhinitis"], True)]),
    ("oxymetazoline", "Decongestant (nasal)", "drug", "otc_monograph",
     [("nasal-congestion", "Short-term use only (up to 3 days) to avoid rebound congestion")],
     [("Afrin", A, "Nasal spray", "Nasal", ["nasal-congestion"], True)]),
    ("dupilumab", "Monoclonal antibody (IL-4/IL-13 blocker)", "biologic", "approved",
     [("nasal-polyps", "Also approved for other conditions, including atopic dermatitis and asthma")],
     [("Dupixent", A, "Injection (pen, prefilled syringe)", "Subcutaneous", ["nasal-polyps"], False)]),
    ("meclizine", "Antihistamine (antivertigo)", "drug", "approved",
     [("vertigo", "Vertigo from inner-ear (vestibular) problems")], [("Antivert", A, "Tablet", "Oral", ["vertigo"], False)]),
]
ENT_COMBOS = {"ciprodex": ["ciprofloxacin", "dexamethasone"]}


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if os.path.exists(LIB) and "--force" not in sys.argv:
        sys.exit("data/library/ already exists; it is now edited by hand. Pass --force to overwrite.")
    psy_path = args[0] if args else os.path.join(ROOT, "Stanford PSY96 App", "index.html")
    v1 = json.load(open(os.path.join(ROOT, "dist", "v1", "medicines.json"), encoding="utf-8"))["data"]

    ingredients, products = {}, {}

    def ing(name, cls=None, kind=None, source=None):
        iid = slug(name)
        if iid not in ingredients:
            ingredients[iid] = {
                "id": iid, "name": name, "synonyms": SYNONYMS.get(name, []),
                "kind": kind or ("biologic" if BIOLOGIC.search(name) else "drug"),
                "classes": [], "ids": {"rxcui": None, "unii": []},
                "approvals": [], "uses": [], "controlled": [], "summary": None, "tier": "curated",
                "review": {"status": "unverified", "checked": TODAY, "by": None,
                           "note": "Migrated from earlier NomadCeuticals, PSY96 and ENT data; check against the FDA label."},
                "sources": [{"url": DAILYMED + name.replace(" ", "+"), "title": f"DailyMed labels for {name}", "type": "label"}],
            }
        r = ingredients[iid]
        if cls and not r["classes"]:
            r["classes"].append({"name": cls, "system": "nomad"})
        if source and not any(s["url"] == source for s in r["sources"]):
            r["sources"].append({"url": source, "title": "Source", "type": "reference"})
        return r

    def add_use(r, cond, typ, note=None, via=None, source=None):
        for u in r["uses"]:
            if u["condition"] == cond and u["type"] == typ and u["jurisdiction"] == "US":
                if not via:
                    u.pop("via", None)  # approved on its own: no longer "only via combinations"
                elif "via" in u:
                    u["via"] = sorted(set(u["via"]) | set(via))
                return
        u = {"condition": cond, "type": typ, "jurisdiction": "US"}
        if note:
            u["note"] = note
        if via:
            u["via"] = sorted(via)
        if source:
            u["source"] = source
        r["uses"].append(u)

    def set_us(r, status, source=None, note=None):
        for a in r["approvals"]:
            if a["jurisdiction"] == "US":
                return
        a = {"jurisdiction": "US", "regulator": "FDA", "status": status, "checked": TODAY}
        if source:
            a["source"] = source
        if note:
            a["note"] = note
        r["approvals"].append(a)

    def add_control(r, schedule, source=DEA):
        if not any(c["jurisdiction"] == "US" for c in r["controlled"]):
            r["controlled"].append({"jurisdiction": "US", "schedule": schedule, "source": source})

    # 1) v1 medicines -> products + ingredients
    for m in v1:
        parts = split_generic(m["genericName"])
        single = len(parts) == 1
        cond = m["condition"]
        if m["id"] == "vemlidy":
            cond = "hepatitis-b"
        for p in parts:
            cls = m["drugClass"] if single and m["drugClass"] != "Combination" else COMBO_CLASSES.get(p)
            r = ing(p, cls)
            set_us(r, "approved", "https://www.accessdata.fda.gov/scripts/cder/daf/")
            add_use(r, cond, "approved", via=None if single else [m["id"]], source=m["sourceUrl"])
        sched = (m.get("attributes") or {}).get("controlledSubstance") or ""
        sm = re.match(r"Schedule (I{1,3}V?|IV|V)$", sched)
        if sm:
            for p in parts:
                add_control(ingredients[slug(p)], "C" + sm.group(1))
        attrs = dict(m.get("attributes") or {})
        attrs.pop("controlledSubstance", None)
        prod = {
            "id": m["id"], "brandName": m["brandName"], "ingredients": [slug(p) for p in parts], "jurisdiction": "US",
            "status": "discontinued" if m["status"].lower() == "discontinued" else "available",
            "form": m.get("formulation"), "route": m.get("route"), "dosingFrequency": m.get("dosingFrequency"),
            "manufacturer": m.get("manufacturer"),
            "approval": {"date": m.get("approvalDate"), "year": m.get("approvalYear"), "application": None},
            "indications": [cond], "controlled": ("C" + sm.group(1)) if sm else None,
            "description": m.get("description"), "notes": m.get("notes"), "attributes": attrs,
            "v1": {"condition": m["condition"], "drugClass": m["drugClass"], "genericName": m["genericName"]},
            "sources": [{"url": m["sourceUrl"], "title": "Original source (API v1)", "type": "reference"}],
        }
        if m["id"] == "vemlidy":
            prod["notes"] = ("Vemlidy is FDA-approved for chronic hepatitis B, not HIV. Its ingredient, tenofovir alafenamide, "
                             "is part of several HIV combination medicines. (Corrected in the v2 library; API v1 still lists it under HIV.)")
        products[m["id"]] = prod

    # 2) PSY96
    h = open(psy_path, encoding="utf-8").read()
    i = h.index("window.PSY96_DATA=") + len("window.PSY96_DATA=")
    psy, _ = json.JSONDecoder().raw_decode(h[i:])
    seen = set()
    for x in psy["meds"]["list"]:
        names, prods = PSY_PRODUCTS[x["g"]]
        seen.add(x["g"])
        for n in names:
            cls = PSY_OLDER.get(n) or (PSY_CLASS[x["c"]] if len(names) == 1 or n == "dextromethorphan" else None)
            if n == "dextromethorphan":
                cls = COMBO_CLASSES["dextromethorphan"]
            r = ing(n, cls)
            set_us(r, "approved", "https://www.accessdata.fda.gov/scripts/cder/daf/")
            if n in US_SCHEDULE:
                add_control(r, US_SCHEDULE[n])
            combo = len(names) > 1
            via = [slug(prods[0][0])] if combo else None
            for k in x.get("k", []):
                add_use(r, PSY_COND[k], "approved", via=via)
            for k in x.get("o", []):
                if not combo:
                    add_use(r, PSY_COND[k], "off-label")
        for brand, status, existing, form in prods:
            pid = existing or slug(brand)
            if existing:
                assert pid in products, f"PSY96 brand {brand} expects v1 product {pid}"
                continue
            if pid in products:
                continue
            products[pid] = {
                "id": pid, "brandName": brand, "ingredients": [slug(n) for n in names], "jurisdiction": "US", "status": status,
                "form": form, "route": None, "dosingFrequency": None, "manufacturer": None,
                "approval": {"date": None, "year": None, "application": None},
                "indications": [PSY_COND[k] for k in x.get("k", [])], "controlled": US_SCHEDULE.get(names[0]) if len(names) == 1 else None,
                "description": None, "notes": None, "attributes": {},
                "sources": [{"url": DAILYMED + brand.split(" (")[0].replace(" ", "+"), "title": f"DailyMed: {brand}", "type": "label"}],
            }
    missing = set(PSY_PRODUCTS) - seen
    assert not missing, f"PSY96 entries not found in the file: {missing}"

    # 3) ENT Study Hub
    for name, cls, kind, status, uses, prods in ENT:
        r = ing(name, cls, kind)
        set_us(r, status, "https://www.accessdata.fda.gov/scripts/cder/daf/" if status == "approved" else
               "https://www.fda.gov/drugs/over-counter-otc-nonprescription-drugs/over-counter-otc-monograph-drug-products",
               "Sold over the counter under an FDA monograph, without individual approval." if status == "otc_monograph" else None)
        for cond, note in uses:
            add_use(r, cond, "approved", note)
        for brand, pstatus, form, route, inds, otc in prods:
            pid = slug(brand)
            ings = ENT_COMBOS.get(pid, [name])
            products[pid] = {
                "id": pid, "brandName": brand, "ingredients": ings, "jurisdiction": "US", "status": pstatus,
                "form": form, "route": route, "dosingFrequency": None, "manufacturer": None,
                "approval": {"date": None, "year": None, "application": None},
                "indications": inds, "controlled": None, "description": None,
                "notes": "Over the counter (no prescription needed) in the US." if otc else None,
                "attributes": {},
                "sources": [{"url": DAILYMED + brand.replace(" ", "+"), "title": f"DailyMed: {brand}", "type": "label"}],
            }
    # Ciprodex's dexamethasone use
    add_use(ingredients["dexamethasone"], "otitis-media", "approved", "Ear drops with ciprofloxacin (Ciprodex)", via=["ciprodex"])
    add_use(ingredients["dexamethasone"], "otitis-externa", "approved", "Ear drops with ciprofloxacin (Ciprodex)", via=["ciprodex"])

    # write
    if os.path.exists(LIB):
        shutil.rmtree(LIB)
    write_json(os.path.join(LIB, "conditions.json"),
               [{"id": c, "name": n, "area": a, "aliases": al, "parent": p} for c, n, a, al, p in CONDITIONS])
    cond_ids = {c[0] for c in CONDITIONS}
    for r in ingredients.values():
        for u in r["uses"]:
            assert u["condition"] in cond_ids, (r["id"], u["condition"])
        r["uses"].sort(key=lambda u: (u["type"] != "approved", u["condition"]))
        write_json(os.path.join(LIB, "ingredients", r["id"] + ".json"), r)
    for p in products.values():
        for iid in p["ingredients"]:
            assert iid in ingredients, (p["id"], iid)
        write_json(os.path.join(LIB, "products", p["id"] + ".json"), p)
    print(f"data/library: {len(ingredients)} ingredients, {len(products)} products, {len(CONDITIONS)} conditions")


if __name__ == "__main__":
    main()
