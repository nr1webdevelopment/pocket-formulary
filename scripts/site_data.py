"""Builds the unified drug dataset (HIV + ADHD + Diabetes) as JSON + CSVs."""
import csv, json, re, sys

import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data")
HIV_CSV = os.path.join(OUT, "hiv-medicines.csv")
FDA = "https://www.accessdata.fda.gov/scripts/cder/daf/"
NIH = "https://hivinfo.nih.gov/understanding-hiv/fact-sheets/fda-approved-hiv-medicines"

def slugify(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

# ---------------- HIV (from the researched CSV) ----------------
HIV_GROUPS = {
 "NRTI": "Nucleoside reverse transcriptase inhibitors (NRTIs)",
 "NNRTI": "Non-nucleoside reverse transcriptase inhibitors (NNRTIs)",
 "INSTI": "Integrase inhibitors (INSTIs)",
 "PI": "Protease inhibitors (PIs)",
 "Fusion Inhibitor": "Fusion inhibitors", "CCR5 Antagonist": "CCR5 antagonists",
 "Attachment Inhibitor": "Attachment inhibitors", "Post-Attachment Inhibitor": "Post-attachment inhibitors",
 "Capsid Inhibitor": "Capsid inhibitors", "Pharmacokinetic Enhancer": "Pharmacokinetic enhancers",
 "Combination": "Combination medicines",
}
drugs = []
for r in csv.DictReader(open(HIV_CSV, encoding="utf-8")):
    cls = r["drugClass"] if r["drugClass"] != "Combination" else "Combination: " + r["componentClasses"].replace(", ", " + ")
    extra = [["Abbreviation", r["abbreviation"]], ["Used for", r["use"]],
             ["Complete regimen on its own", "Yes" if r["completeRegimen"] == "true" else "No"],
             ["Long-acting", "Yes" if r["longActing"] == "true" else "No"]]
    if r["pediatricVersion"] == "true": extra.append(["Pediatric formulation", "Yes"])
    drugs.append(dict(slug=r["slug"], brand=r["brandName"], generic=r["genericName"], condition="hiv",
        group=HIV_GROUPS[r["drugClass"]], cls=cls, form=r["formulation"], route=r["route"],
        dosing=r["dosingFrequency"], mfr=r["manufacturer"], approved=r["fdaApprovalDate"],
        status=r["status"], desc=r["description"], notes=r["notes"], extra=extra, source=NIH,
        sourceName="NIH HIVinfo: FDA-Approved HIV Medicines"))

# ---------------- ADHD ----------------
TAK, TRIS, NOV, JNJ = "Takeda", "Tris Pharma", "Novartis", "Johnson & Johnson (Janssen)"
S2 = "Schedule II"
# brand, generic, group, class, form, route, dosing, mfr, year, schedule, desc, notes
ADHD = [
 ("Ritalin","methylphenidate","Methylphenidate","CNS stimulant (methylphenidate)","Tablet","Oral","2–3 times daily",NOV,"1955",S2,
  "Short-acting methylphenidate; one of the oldest ADHD medicines still in use.","Effect lasts about 3–4 hours per dose."),
 ("Ritalin LA","methylphenidate (extended-release)","Methylphenidate","CNS stimulant (methylphenidate)","Extended-release capsule","Oral","Once daily (morning)",NOV,"2002",S2,
  "Long-acting methylphenidate with a bimodal release that mimics two doses.","Capsule can be opened and sprinkled on applesauce."),
 ("Concerta","methylphenidate (extended-release)","Methylphenidate","CNS stimulant (methylphenidate)","Extended-release tablet (OROS)","Oral","Once daily (morning)",JNJ,"2000",S2,
  "Long-acting methylphenidate using an osmotic pump that releases medicine over about 12 hours.","Swallow whole; do not crush or chew."),
 ("Daytrana","methylphenidate (transdermal)","Methylphenidate","CNS stimulant (methylphenidate)","Transdermal patch","Skin patch","Once daily (worn up to 9 hours)","Noven Pharmaceuticals","2006",S2,
  "The first methylphenidate skin patch.","Approved for children and adolescents 6–17."),
 ("Quillivant XR","methylphenidate (extended-release)","Methylphenidate","CNS stimulant (methylphenidate)","Extended-release oral suspension","Oral","Once daily (morning)",TRIS,"2012",S2,
  "Long-acting liquid methylphenidate for people who cannot swallow pills.",""),
 ("QuilliChew ER","methylphenidate (extended-release)","Methylphenidate","CNS stimulant (methylphenidate)","Extended-release chewable tablet","Oral","Once daily (morning)",TRIS,"2015",S2,
  "Long-acting chewable methylphenidate tablet.",""),
 ("Aptensio XR","methylphenidate (extended-release)","Methylphenidate","CNS stimulant (methylphenidate)","Extended-release capsule","Oral","Once daily (morning)","Rhodes Pharmaceuticals","2015",S2,
  "Long-acting methylphenidate capsule with immediate and extended-release beads.",""),
 ("Cotempla XR-ODT","methylphenidate (extended-release)","Methylphenidate","CNS stimulant (methylphenidate)","Extended-release orally disintegrating tablet","Oral","Once daily (morning)","Aytu BioPharma","2017",S2,
  "Long-acting methylphenidate that dissolves in the mouth.","Approved for children 6–17."),
 ("Jornay PM","methylphenidate (delayed- and extended-release)","Methylphenidate","CNS stimulant (methylphenidate)","Delayed-release/extended-release capsule","Oral","Once daily (evening)","Collegium Pharmaceutical","2018",S2,
  "Taken in the evening so it starts working on waking the next morning.",""),
 ("Focalin","dexmethylphenidate","Dexmethylphenidate","CNS stimulant (methylphenidate)","Tablet","Oral","Twice daily",NOV,"2001",S2,
  "Short-acting dexmethylphenidate, the more active half of the methylphenidate molecule.",""),
 ("Focalin XR","dexmethylphenidate (extended-release)","Dexmethylphenidate","CNS stimulant (methylphenidate)","Extended-release capsule","Oral","Once daily (morning)",NOV,"2005",S2,
  "Long-acting dexmethylphenidate.",""),
 ("Azstarys","serdexmethylphenidate and dexmethylphenidate","Dexmethylphenidate","CNS stimulant (methylphenidate)","Capsule","Oral","Once daily (morning)","Corium","2021",S2,
  "Combines fast-acting dexmethylphenidate with a prodrug that releases more through the day.",""),
 ("Adderall","mixed amphetamine salts","Amphetamine","CNS stimulant (amphetamine)","Tablet","Oral","1–3 times daily","Teva","1996",S2,
  "Short-acting mix of four amphetamine salts.","Effect lasts about 4–6 hours per dose."),
 ("Adderall XR","mixed amphetamine salts (extended-release)","Amphetamine","CNS stimulant (amphetamine)","Extended-release capsule","Oral","Once daily (morning)",TAK,"2001",S2,
  "Long-acting version of Adderall.",""),
 ("Mydayis","mixed amphetamine salts (extended-release)","Amphetamine","CNS stimulant (amphetamine)","Extended-release capsule","Oral","Once daily (morning)",TAK,"2017",S2,
  "Extra-long-acting amphetamine designed to last up to 16 hours.","Approved for ages 13 and older."),
 ("Vyvanse","lisdexamfetamine","Amphetamine","CNS stimulant (amphetamine)","Capsule; chewable tablet","Oral","Once daily (morning)",TAK,"2007",S2,
  "Prodrug the body converts into dextroamphetamine, giving a smooth, long effect.","Also approved for moderate to severe binge eating disorder in adults."),
 ("Xelstrym","dextroamphetamine (transdermal)","Amphetamine","CNS stimulant (amphetamine)","Transdermal patch","Skin patch","Once daily (worn up to 9 hours)","Noven Pharmaceuticals","2022",S2,
  "The first dextroamphetamine skin patch.",""),
 ("Evekeo","amphetamine sulfate","Amphetamine","CNS stimulant (amphetamine)","Tablet; orally disintegrating tablet (Evekeo ODT)","Oral","1–3 times daily","Azurity Pharmaceuticals","2012",S2,
  "Short-acting racemic amphetamine.",""),
 ("Adzenys XR-ODT","amphetamine (extended-release)","Amphetamine","CNS stimulant (amphetamine)","Extended-release orally disintegrating tablet","Oral","Once daily (morning)","Aytu BioPharma","2016",S2,
  "Long-acting amphetamine that dissolves in the mouth.",""),
 ("Dyanavel XR","amphetamine (extended-release)","Amphetamine","CNS stimulant (amphetamine)","Extended-release oral suspension; tablet","Oral","Once daily (morning)",TRIS,"2015",S2,
  "Long-acting amphetamine available as a liquid or tablet.",""),
 ("Strattera","atomoxetine","Non-stimulant","Selective norepinephrine reuptake inhibitor","Capsule","Oral","Once or twice daily","Eli Lilly","2002","Not controlled",
  "The first non-stimulant approved for ADHD.","Full effect can take several weeks."),
 ("Qelbree","viloxazine (extended-release)","Non-stimulant","Selective norepinephrine reuptake inhibitor","Extended-release capsule","Oral","Once daily","Supernus Pharmaceuticals","2021","Not controlled",
  "Non-stimulant option for children 6 and older and adults.",""),
 ("Intuniv","guanfacine (extended-release)","Non-stimulant","Alpha-2A adrenergic agonist","Extended-release tablet","Oral","Once daily",TAK,"2009","Not controlled",
  "Non-stimulant that can be used alone or added to a stimulant.","Should be tapered, not stopped suddenly."),
 ("Onyda XR","clonidine (extended-release)","Non-stimulant","Alpha-2 adrenergic agonist","Extended-release oral suspension","Oral","Once daily (at bedtime)",TRIS,"2024","Not controlled",
  "Long-acting liquid clonidine for ADHD.","Approved for ages 6 and older."),
 ("Simtriyo","centanafadine (extended-release)","Non-stimulant","Norepinephrine, dopamine and serotonin reuptake inhibitor (NDSRI)","Extended-release capsule","Oral","Once daily","Otsuka","2026","See label",
  "First-in-class triple reuptake inhibitor for ADHD, approved in July 2026.","Approved for patients 6 and older weighing at least 20 kg. New in 2026."),
]
for (b,g,grp,cls,form,route,dose,mfr,yr,sched,desc,notes) in ADHD:
    drugs.append(dict(slug=slugify(b), brand=b, generic=g, condition="adhd", group=grp, cls=cls, form=form, route=route,
        dosing=dose, mfr=mfr, approved=yr, status="Available", desc=desc, notes=notes,
        extra=[["Type", "Stimulant" if grp != "Non-stimulant" else "Non-stimulant"], ["Controlled substance", sched]],
        source=FDA, sourceName="Drugs@FDA (U.S. Food and Drug Administration)"))

# ---------------- Diabetes ----------------
LILLY, NOVO, SANOFI, AZ, BI, MERCK = "Eli Lilly", "Novo Nordisk", "Sanofi", "AstraZeneca", "Boehringer Ingelheim", "Merck"
T1, T2, BOTH = "Type 1", "Type 2", "Type 1 and type 2"
# brand, generic, group, class, form, route, dosing, mfr, year, type, status, desc, notes
DM = [
 ("Humalog","insulin lispro","Insulin: rapid-acting","Rapid-acting insulin analog","Injection (pen, vial, cartridge)","Subcutaneous","With meals",LILLY,"1996",BOTH,"Available",
  "The first rapid-acting insulin analog, taken at mealtimes.",""),
 ("NovoLog","insulin aspart","Insulin: rapid-acting","Rapid-acting insulin analog","Injection (pen, vial, cartridge)","Subcutaneous","With meals",NOVO,"2000",BOTH,"Available",
  "Rapid-acting mealtime insulin.",""),
 ("Apidra","insulin glulisine","Insulin: rapid-acting","Rapid-acting insulin analog","Injection (pen, vial)","Subcutaneous","With meals",SANOFI,"2004",BOTH,"Available",
  "Rapid-acting mealtime insulin.",""),
 ("Fiasp","insulin aspart (faster-acting)","Insulin: rapid-acting","Rapid-acting insulin analog","Injection (pen, vial, cartridge)","Subcutaneous","At the start of a meal or within 20 minutes after",NOVO,"2017",BOTH,"Available",
  "Faster-acting formulation of insulin aspart.",""),
 ("Lyumjev","insulin lispro-aabc","Insulin: rapid-acting","Rapid-acting insulin analog","Injection (pen, vial)","Subcutaneous","At the start of a meal or within 20 minutes after",LILLY,"2020",BOTH,"Available",
  "Faster-acting formulation of insulin lispro.",""),
 ("Afrezza","insulin human (inhaled)","Insulin: rapid-acting","Inhaled rapid-acting insulin","Inhalation powder (cartridge)","Inhaled","At the start of meals","MannKind","2014",BOTH,"Available",
  "The only inhaled mealtime insulin in the US.","Adults only; not for people who smoke or have chronic lung disease."),
 ("Humulin R","insulin human regular","Insulin: short- and intermediate-acting","Short-acting human insulin","Injection (vial, pen)","Subcutaneous / IV","About 30 minutes before meals",LILLY,"1982",BOTH,"Available",
  "The first medicine made with recombinant DNA technology.",""),
 ("Humulin N","insulin isophane (NPH)","Insulin: short- and intermediate-acting","Intermediate-acting human insulin","Injection (vial, pen)","Subcutaneous","Once or twice daily",LILLY,"1982",BOTH,"Available",
  "Intermediate-acting NPH insulin, often used as a lower-cost basal option.",""),
 ("Lantus","insulin glargine","Insulin: long-acting","Long-acting insulin analog","Injection (pen, vial)","Subcutaneous","Once daily",SANOFI,"2000",BOTH,"Available",
  "The first long-acting basal insulin analog.",""),
 ("Basaglar","insulin glargine","Insulin: long-acting","Long-acting insulin analog","Injection (pen)","Subcutaneous","Once daily",LILLY,"2015",BOTH,"Available",
  "Follow-on insulin glargine, similar to Lantus.",""),
 ("Semglee","insulin glargine-yfgn","Insulin: long-acting","Long-acting insulin analog (biosimilar)","Injection (pen, vial)","Subcutaneous","Once daily","Biocon Biologics","2020",BOTH,"Available",
  "Insulin glargine biosimilar.","In 2021 it became the first interchangeable biosimilar insulin, so pharmacies can substitute it for Lantus."),
 ("Toujeo","insulin glargine U-300","Insulin: long-acting","Long-acting insulin analog","Injection (pen)","Subcutaneous","Once daily",SANOFI,"2015",BOTH,"Available",
  "Concentrated (300 units/mL) insulin glargine with a flatter, longer profile.",""),
 ("Levemir","insulin detemir","Insulin: long-acting","Long-acting insulin analog","Injection (pen, vial)","Subcutaneous","Once or twice daily",NOVO,"2005",BOTH,"Discontinued",
  "Long-acting basal insulin.","Discontinued in the US at the end of 2024."),
 ("Tresiba","insulin degludec","Insulin: long-acting","Ultra-long-acting insulin analog","Injection (pen, vial)","Subcutaneous","Once daily (flexible timing)",NOVO,"2015",BOTH,"Available",
  "Ultra-long-acting basal insulin lasting over 42 hours.",""),
 ("Awiqli","insulin icodec-abae","Insulin: long-acting","Once-weekly basal insulin","Injection (pen, 700 units/mL)","Subcutaneous","Once weekly",NOVO,"2026",T2,"Available",
  "The first once-weekly basal insulin, approved March 2026.","Adults with type 2 diabetes only. New in 2026."),
 ("Glucophage","metformin","Oral: biguanide","Biguanide","Tablet; extended-release tablet (Glucophage XR)","Oral","Once or twice daily with meals","Bristol Myers Squibb","1994",T2,"Available",
  "First-line medicine for type 2 diabetes; lowers glucose made by the liver.","Most people take generic metformin."),
 ("Glucotrol","glipizide","Oral: sulfonylurea","Sulfonylurea","Tablet; extended-release tablet (Glucotrol XL)","Oral","Once or twice daily before meals","Pfizer","1984",T2,"Available",
  "Helps the pancreas release more insulin.","Can cause low blood sugar."),
 ("Amaryl","glimepiride","Oral: sulfonylurea","Sulfonylurea","Tablet","Oral","Once daily with breakfast",SANOFI,"1995",T2,"Available",
  "Once-daily sulfonylurea that boosts insulin release.","Can cause low blood sugar."),
 ("Actos","pioglitazone","Oral: thiazolidinedione","Thiazolidinedione (TZD)","Tablet","Oral","Once daily","Takeda","1999",T2,"Available",
  "Improves the body's sensitivity to insulin.","Not recommended for people with heart failure."),
 ("Januvia","sitagliptin","Oral: DPP-4 inhibitor","DPP-4 inhibitor","Tablet","Oral","Once daily",MERCK,"2006",T2,"Available",
  "The first DPP-4 inhibitor; boosts the body's own incretin hormones.",""),
 ("Onglyza","saxagliptin","Oral: DPP-4 inhibitor","DPP-4 inhibitor","Tablet","Oral","Once daily",AZ,"2009",T2,"Available",
  "DPP-4 inhibitor taken once daily.",""),
 ("Tradjenta","linagliptin","Oral: DPP-4 inhibitor","DPP-4 inhibitor","Tablet","Oral","Once daily",BI,"2011",T2,"Available",
  "DPP-4 inhibitor that needs no dose change for kidney function.",""),
 ("Nesina","alogliptin","Oral: DPP-4 inhibitor","DPP-4 inhibitor","Tablet","Oral","Once daily","Takeda","2013",T2,"Available",
  "DPP-4 inhibitor taken once daily.",""),
 ("Invokana","canagliflozin","Oral: SGLT2 inhibitor","SGLT2 inhibitor","Tablet","Oral","Once daily (before first meal)",JNJ,"2013",T2,"Available",
  "The first SGLT2 inhibitor; removes extra glucose through the urine.",""),
 ("Farxiga","dapagliflozin","Oral: SGLT2 inhibitor","SGLT2 inhibitor","Tablet","Oral","Once daily",AZ,"2014",T2,"Available",
  "SGLT2 inhibitor also approved for heart failure and chronic kidney disease.",""),
 ("Jardiance","empagliflozin","Oral: SGLT2 inhibitor","SGLT2 inhibitor","Tablet","Oral","Once daily (morning)",BI,"2014",T2,"Available",
  "SGLT2 inhibitor shown to lower the risk of cardiovascular death in type 2 diabetes.","Also approved for heart failure and chronic kidney disease."),
 ("Steglatro","ertugliflozin","Oral: SGLT2 inhibitor","SGLT2 inhibitor","Tablet","Oral","Once daily (morning)",MERCK,"2017",T2,"Available",
  "SGLT2 inhibitor taken once daily.",""),
 ("Brenzavvy","bexagliflozin","Oral: SGLT2 inhibitor","SGLT2 inhibitor","Tablet","Oral","Once daily (morning)","TheracosBio","2023",T2,"Available",
  "Lower-cost SGLT2 inhibitor approved in 2023.",""),
 ("Victoza","liraglutide","GLP-1 and GIP/GLP-1 agonists","GLP-1 receptor agonist","Injection (pen)","Subcutaneous","Once daily",NOVO,"2010",T2,"Available",
  "Daily GLP-1 injection that lowers blood sugar and reduces cardiovascular risk.","Approved for children 10 and older."),
 ("Trulicity","dulaglutide","GLP-1 and GIP/GLP-1 agonists","GLP-1 receptor agonist","Injection (single-dose pen)","Subcutaneous","Once weekly",LILLY,"2014",T2,"Available",
  "Once-weekly GLP-1 injection.",""),
 ("Ozempic","semaglutide","GLP-1 and GIP/GLP-1 agonists","GLP-1 receptor agonist","Injection (pen)","Subcutaneous","Once weekly",NOVO,"2017",T2,"Available",
  "Once-weekly GLP-1 injection that lowers blood sugar and supports weight loss.","Also approved to reduce cardiovascular and kidney risk in certain adults."),
 ("Rybelsus (Ozempic pill)","semaglutide (oral)","GLP-1 and GIP/GLP-1 agonists","GLP-1 receptor agonist","Tablet","Oral","Once daily, 30 minutes before first food",NOVO,"2019",T2,"Available",
  "The first GLP-1 medicine in pill form.","Being renamed Ozempic pill in the US during 2026."),
 ("Mounjaro","tirzepatide","GLP-1 and GIP/GLP-1 agonists","Dual GIP and GLP-1 receptor agonist","Injection (single-dose pen, vial)","Subcutaneous","Once weekly",LILLY,"2022",T2,"Available",
  "First dual GIP/GLP-1 agonist; strong effects on blood sugar and weight.","In August 2026 the FDA added a use to lower heart attack and stroke risk in high-risk adults with type 2 diabetes."),
 ("Symlin","pramlintide","Other","Amylin analog","Injection (pen)","Subcutaneous","Before major meals",AZ,"2005",BOTH,"Available",
  "Amylin analog used with mealtime insulin to smooth blood sugar after meals.",""),
 ("Janumet","sitagliptin and metformin","Combination pills","DPP-4 inhibitor + biguanide","Tablet; extended-release tablet (Janumet XR)","Oral","Twice daily with meals (XR once daily)",MERCK,"2007",T2,"Available",
  "Combines Januvia with metformin in one tablet.",""),
 ("Xigduo XR","dapagliflozin and metformin","Combination pills","SGLT2 inhibitor + biguanide","Extended-release tablet","Oral","Once daily (morning, with food)",AZ,"2014",T2,"Available",
  "Combines Farxiga with extended-release metformin.",""),
 ("Synjardy","empagliflozin and metformin","Combination pills","SGLT2 inhibitor + biguanide","Tablet; extended-release tablet (Synjardy XR)","Oral","Twice daily with meals (XR once daily)",BI,"2015",T2,"Available",
  "Combines Jardiance with metformin.",""),
 ("Glyxambi","empagliflozin and linagliptin","Combination pills","SGLT2 inhibitor + DPP-4 inhibitor","Tablet","Oral","Once daily (morning)",BI,"2015",T2,"Available",
  "Combines Jardiance with Tradjenta.",""),
 ("Soliqua 100/33","insulin glargine and lixisenatide","Combination pills","Basal insulin + GLP-1 receptor agonist","Injection (pen)","Subcutaneous","Once daily, within an hour before the first meal",SANOFI,"2016",T2,"Available",
  "Basal insulin and a GLP-1 agonist in one daily injection.",""),
 ("Tzield","teplizumab-mzwv","Other","Anti-CD3 monoclonal antibody","IV infusion","Intravenous","Once daily for 14 days (one course)",SANOFI,"2022",T1,"Available",
  "The first medicine that delays the onset of stage 3 type 1 diabetes.","For people 8 and older with stage 2 type 1 diabetes."),
 ("Baqsimi","glucagon (nasal)","Other","Glucagon (hypoglycemia rescue)","Nasal powder","Nasal","One dose as needed for severe low blood sugar","Amphastar","2019",BOTH,"Available",
  "The first needle-free emergency treatment for severe low blood sugar.",""),
]
for (b,g,grp,cls,form,route,dose,mfr,yr,typ,status,desc,notes) in DM:
    drugs.append(dict(slug=slugify(b.split(" (")[0]), brand=b, generic=g, condition="diabetes", group=grp, cls=cls,
        form=form, route=route, dosing=dose, mfr=mfr, approved=yr, status=status, desc=desc, notes=notes,
        extra=[["Diabetes type", typ]], source=FDA, sourceName="Drugs@FDA (U.S. Food and Drug Administration)"))

order = list(HIV_GROUPS.values())
drugs.sort(key=lambda d: (order.index(d["group"]) if d["condition"] == "hiv" else 0))
slugs = [d["slug"] for d in drugs]
dupes = {s for s in slugs if slugs.count(s) > 1}
assert not dupes, dupes
json.dump(drugs, open(f"{OUT}/drugs.json", "w"), ensure_ascii=False)

# Framer-friendly CSVs for the two new conditions
for cond in ("adhd", "diabetes"):
    rows = [d for d in drugs if d["condition"] == cond]
    keys = ["slug","brand","generic","group","cls","form","route","dosing","mfr","approved","status","desc","notes"]
    hdr = ["slug","brandName","genericName","category","drugClass","formulation","route","dosingFrequency","manufacturer","approvalYear","status","description","notes"]
    xh = [e[0] for e in rows[0]["extra"]]
    camel = lambda s: re.sub(r"\s+(\w)", lambda m: m.group(1).upper(), s.lower())
    with open(f"{OUT}/{cond}-medicines.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(hdr + [camel(h) for h in xh] + ["sourceUrl"])
        for d in rows: w.writerow([d[k] for k in keys] + [e[1] for e in d["extra"]] + [d["source"]])
from collections import Counter
print(len(drugs), Counter(d["condition"] for d in drugs))
