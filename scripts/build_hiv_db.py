import csv, re, sys

SRC = "https://hivinfo.nih.gov/understanding-hiv/fact-sheets/fda-approved-hiv-medicines"
VERIFIED = "2026-10-20"
VIIV, GILEAD, MERCK, JNJ = "ViiV Healthcare", "Gilead Sciences", "Merck", "Johnson & Johnson (Janssen)"
BMS, BI, ABBVIE, VIATRIS = "Bristol Myers Squibb", "Boehringer Ingelheim", "AbbVie", "Viatris (Mylan)"

# brand, generic, abbr, class, componentClasses, use, route, formulation, dosing,
# longActing, pediatric, completeRegimen, manufacturer, date, status, description, notes
R = [
 # ---- NRTIs
 ("Ziagen","abacavir","ABC","NRTI","NRTI","Treatment","Oral","Tablet; oral solution","Once or twice daily",0,0,0,VIIV,"1998-12-17","Available",
  "Nucleoside reverse transcriptase inhibitor used as part of a combination regimen.","HLA-B*5701 screening required before starting (hypersensitivity risk)."),
 ("Emtriva","emtricitabine","FTC","NRTI","NRTI","Treatment","Oral","Capsule; oral solution","Once daily",0,0,0,GILEAD,"2003-07-02","Available",
  "Nucleoside reverse transcriptase inhibitor; also a component of many combination pills.",""),
 ("Epivir","lamivudine","3TC","NRTI","NRTI","Treatment","Oral","Tablet; oral solution","Once or twice daily",0,0,0,VIIV,"1995-11-17","Available",
  "Nucleoside reverse transcriptase inhibitor widely used in combination regimens.",""),
 ("Viread","tenofovir disoproxil fumarate","TDF","NRTI","NRTI","Treatment","Oral","Tablet; oral powder","Once daily",0,0,0,GILEAD,"2001-10-26","Available",
  "Nucleotide reverse transcriptase inhibitor; also approved for chronic hepatitis B.",""),
 ("Vemlidy","tenofovir alafenamide","TAF","NRTI","NRTI","Hepatitis B","Oral","Tablet","Once daily",0,0,0,GILEAD,"2016-11-10","Available",
  "Tenofovir alafenamide as a standalone tablet.","Standalone Vemlidy is FDA-approved for chronic hepatitis B, not HIV; TAF is used for HIV inside combination products (e.g. Biktarvy, Descovy)."),
 ("Retrovir","zidovudine","ZDV (AZT)","NRTI","NRTI","Treatment","Oral / IV","Tablet; capsule; syrup; IV infusion","Twice daily (oral)",0,0,0,VIIV,"1987-03-19","Available",
  "The first FDA-approved HIV medicine (1987).","Also used to reduce perinatal (mother-to-child) transmission."),
 # ---- NNRTIs
 ("Pifeltro","doravirine","DOR","NNRTI","NNRTI","Treatment","Oral","Tablet","Once daily",0,0,0,MERCK,"2018-08-30","Available",
  "Non-nucleoside reverse transcriptase inhibitor used in combination regimens.",""),
 ("Sustiva","efavirenz","EFV","NNRTI","NNRTI","Treatment","Oral","Tablet; capsule","Once daily (at bedtime)",0,0,0,BMS,"1998-09-17","Discontinued",
  "Non-nucleoside reverse transcriptase inhibitor.","Brand discontinued; generic efavirenz may still be available."),
 ("Intelence","etravirine","ETR","NNRTI","NNRTI","Treatment","Oral","Tablet","Twice daily (after a meal)",0,0,0,JNJ,"2008-01-18","Available",
  "Second-generation NNRTI, mainly for treatment-experienced patients.",""),
 ("Viramune","nevirapine","NVP","NNRTI","NNRTI","Treatment","Oral","Tablet; oral suspension","Twice daily (after 14-day lead-in)",0,0,0,BI,"1996-06-21","Discontinued",
  "First-generation non-nucleoside reverse transcriptase inhibitor.","Brand discontinued; generic nevirapine may still be available."),
 ("Viramune XR","nevirapine (extended-release)","NVP","NNRTI","NNRTI","Treatment","Oral","Extended-release tablet","Once daily",0,0,0,BI,"2011-03-25","Discontinued",
  "Extended-release, once-daily version of nevirapine.","Brand discontinued; generics may still be available."),
 ("Edurant","rilpivirine","RPV","NNRTI","NNRTI","Treatment","Oral","Tablet","Once daily (with a meal)",0,0,0,JNJ,"2011-05-20","Available",
  "Non-nucleoside reverse transcriptase inhibitor; also used as oral lead-in for Cabenuva.",""),
 ("Edurant PED","rilpivirine","RPV","NNRTI","NNRTI","Treatment","Oral","Tablet for oral suspension","Once daily (with a meal)",0,1,0,JNJ,"2024-03-15","Available",
  "Pediatric dispersible formulation of rilpivirine.","Listed as available by NIH HIVinfo (Sep 2026) but as discontinued by NYSDOH hivguidelines.org — verify before publishing."),
 # ---- INSTIs
 ("Vocabria","cabotegravir","CAB","INSTI","INSTI","Treatment & PrEP","Oral","Tablet","Once daily (short oral lead-in)",0,0,0,VIIV,"2021-01-22","Available",
  "Oral cabotegravir used as an optional lead-in before Cabenuva or Apretude injections.",""),
 ("Apretude","cabotegravir (extended-release injection)","CAB-LA","INSTI","INSTI","PrEP","Injection","Intramuscular injection","Every 2 months (after 2 monthly starter injections)",1,0,0,VIIV,"2021-12-20","Available",
  "First long-acting injectable for HIV prevention (PrEP).",""),
 ("Tivicay","dolutegravir","DTG","INSTI","INSTI","Treatment","Oral","Tablet","Once daily (twice daily in some cases)",0,0,0,VIIV,"2013-08-12","Available",
  "Integrase inhibitor with a high barrier to resistance; a core of many first-line regimens.",""),
 ("Tivicay PD","dolutegravir","DTG","INSTI","INSTI","Treatment","Oral","Tablet for oral suspension","Once daily",0,1,0,VIIV,"2020-06-12","Available",
  "Pediatric dispersible formulation of dolutegravir.",""),
 ("Isentress","raltegravir","RAL","INSTI","INSTI","Treatment","Oral","Tablet; chewable tablet; oral suspension","Twice daily",0,0,0,MERCK,"2007-10-12","Available",
  "The first FDA-approved integrase inhibitor.",""),
 ("Isentress HD","raltegravir","RAL","INSTI","INSTI","Treatment","Oral","Tablet (600 mg)","Once daily (two tablets)",0,0,0,MERCK,"2017-05-26","Available",
  "High-dose raltegravir allowing once-daily dosing.",""),
 # ---- PIs
 ("Reyataz","atazanavir","ATV","PI","PI","Treatment","Oral","Capsule; oral powder","Once daily (with food)",0,0,0,BMS,"2003-06-20","Available",
  "Protease inhibitor, usually given with a booster (ritonavir or cobicistat).",""),
 ("Prezista","darunavir","DRV","PI","PI","Treatment","Oral","Tablet; oral suspension","Once or twice daily (with food and a booster)",0,0,0,JNJ,"2006-06-23","Available",
  "Protease inhibitor with a high barrier to resistance; must be boosted.",""),
 ("Lexiva","fosamprenavir","FPV","PI","PI","Treatment","Oral","Tablet; oral suspension","Once or twice daily",0,0,0,VIIV,"2003-10-20","Discontinued",
  "Prodrug of the protease inhibitor amprenavir.","Brand discontinued."),
 ("Norvir","ritonavir","RTV","PI","PI","Booster","Oral","Tablet; oral powder; oral solution","Once or twice daily (as booster)",0,0,0,ABBVIE,"1996-03-01","Available",
  "Protease inhibitor now used almost only as a pharmacokinetic booster for other PIs.","Per HHS guidelines, used as a PK enhancer rather than as an active antiretroviral."),
 ("Aptivus","tipranavir","TPV","PI","PI","Treatment","Oral","Capsule; oral solution","Twice daily (with ritonavir)",0,0,0,BI,"2005-06-22","Available",
  "Protease inhibitor for treatment-experienced patients with PI resistance.",""),
 # ---- Other classes
 ("Fuzeon","enfuvirtide","T-20","Fusion Inhibitor","Fusion Inhibitor","Treatment","Injection","Subcutaneous injection","Twice daily",0,0,0,"Genentech (Roche)","2003-03-13","Discontinued",
  "The first fusion inhibitor; blocks HIV from fusing with the CD4 cell membrane.","Brand discontinued."),
 ("Selzentry","maraviroc","MVC","CCR5 Antagonist","CCR5 Antagonist","Treatment","Oral","Tablet; oral solution","Twice daily",0,0,0,VIIV,"2007-08-06","Available",
  "Blocks the CCR5 co-receptor HIV uses to enter cells.","Requires a tropism test to confirm CCR5-tropic virus."),
 ("Rukobia","fostemsavir","FTR","Attachment Inhibitor","Attachment Inhibitor","Treatment","Oral","Extended-release tablet","Twice daily",0,0,0,VIIV,"2020-07-02","Available",
  "First-in-class attachment inhibitor for heavily treatment-experienced adults with multidrug-resistant HIV.",""),
 ("Trogarzo","ibalizumab-uiyk","IBA","Post-Attachment Inhibitor","Post-Attachment Inhibitor","Treatment","Injection","Intravenous infusion or IV push","Every 2 weeks (after loading dose)",0,0,0,"Theratechnologies (TaiMed Biologics)","2018-03-06","Available",
  "Monoclonal antibody for heavily treatment-experienced adults with multidrug-resistant HIV.",""),
 ("Sunlenca","lenacapavir","LEN","Capsid Inhibitor","Capsid Inhibitor","Treatment","Oral + Injection","Tablet; subcutaneous injection","Every 6 months (after oral/injection initiation)",1,0,0,GILEAD,"2022-12-22","Available",
  "First-in-class capsid inhibitor for heavily treatment-experienced adults with multidrug-resistant HIV.",""),
 ("Yeztugo","lenacapavir","LEN","Capsid Inhibitor","Capsid Inhibitor","PrEP","Injection","Subcutaneous injection (with oral initiation)","Every 6 months",1,0,0,GILEAD,"2025-06-18","Available",
  "Twice-yearly injectable for HIV prevention (PrEP).",""),
 ("Tybost","cobicistat","COBI","Pharmacokinetic Enhancer","Pharmacokinetic Enhancer","Booster","Oral","Tablet","Once daily",0,0,0,GILEAD,"2014-09-24","Discontinued",
  "Booster that raises blood levels of atazanavir or darunavir.","Brand discontinued; cobicistat remains inside combination products."),
 # ---- Combination medicines
 ("Epzicom","abacavir and lamivudine","ABC/3TC","Combination","NRTI","Treatment","Oral","Tablet","Once daily",0,0,0,VIIV,"2004-08-02","Discontinued",
  "Two-NRTI backbone pill, taken with a third drug.","Brand discontinued; generics may still be available."),
 ("Triumeq","abacavir, dolutegravir, and lamivudine","ABC/DTG/3TC","Combination","INSTI, NRTI","Treatment","Oral","Tablet","Once daily",0,0,1,VIIV,"2014-08-22","Available",
  "Complete single-tablet regimen built on dolutegravir.","HLA-B*5701 screening required (contains abacavir)."),
 ("Triumeq PD","abacavir, dolutegravir, and lamivudine","ABC/DTG/3TC","Combination","INSTI, NRTI","Treatment","Oral","Tablet for oral suspension","Once daily",0,1,1,VIIV,"2022-03-30","Available",
  "Pediatric dispersible version of Triumeq.",""),
 ("Trizivir","abacavir, lamivudine, and zidovudine","ABC/3TC/ZDV","Combination","NRTI","Treatment","Oral","Tablet","Twice daily",0,0,1,VIIV,"2000-11-14","Discontinued",
  "Triple-NRTI pill.","Brand discontinued; triple-NRTI regimens are no longer recommended."),
 ("Evotaz","atazanavir and cobicistat","ATV/COBI","Combination","PI, Pharmacokinetic Enhancer","Treatment","Oral","Tablet","Once daily (with food)",0,0,0,BMS,"2015-01-29","Available",
  "Atazanavir pre-boosted with cobicistat; taken with other HIV medicines.",""),
 ("Bixlenvo","bictegravir and lenacapavir","BIC/LEN","Combination","INSTI, Capsid Inhibitor","Treatment","Oral","Tablet","Once daily",0,0,1,GILEAD,"2026-08-27","Available",
  "Two-drug single-tablet regimen for virologically suppressed adults, including those switching from complex regimens.","New in 2026. Starts with a 2-day initiation that adds Sunlenca tablets."),
 ("Biktarvy","bictegravir, emtricitabine, and tenofovir alafenamide","BIC/FTC/TAF","Combination","INSTI, NRTI","Treatment","Oral","Tablet","Once daily",0,0,1,GILEAD,"2018-02-07","Available",
  "Complete once-daily single-tablet regimen; among the most prescribed HIV medicines in the US.",""),
 ("Cabenuva","cabotegravir and rilpivirine (extended-release injections)","CAB/RPV","Combination","INSTI, NNRTI","Treatment","Injection","Intramuscular injections","Monthly or every 2 months",1,0,1,VIIV,"2021-01-22","Available",
  "First complete long-acting injectable HIV treatment regimen.",""),
 ("Prezcobix","darunavir and cobicistat","DRV/COBI","Combination","PI, Pharmacokinetic Enhancer","Treatment","Oral","Tablet","Once daily (with food)",0,0,0,JNJ,"2015-01-29","Available",
  "Darunavir pre-boosted with cobicistat; taken with other HIV medicines.",""),
 ("Prezcobix PED","darunavir and cobicistat","DRV/COBI","Combination","PI, Pharmacokinetic Enhancer","Treatment","Oral","Tablet","Once daily (with food)",0,1,0,JNJ,"2026-02-27","Available",
  "Pediatric-dose version of Prezcobix.","New in 2026."),
 ("Symtuza","darunavir, cobicistat, emtricitabine, and tenofovir alafenamide","DRV/COBI/FTC/TAF","Combination","PI, Pharmacokinetic Enhancer, NRTI","Treatment","Oral","Tablet","Once daily (with food)",0,0,1,JNJ,"2018-07-17","Available",
  "First darunavir-based complete single-tablet regimen.",""),
 ("Dovato","dolutegravir and lamivudine","DTG/3TC","Combination","INSTI, NRTI","Treatment","Oral","Tablet","Once daily",0,0,1,VIIV,"2019-04-08","Available",
  "Two-drug complete single-tablet regimen.",""),
 ("Juluca","dolutegravir and rilpivirine","DTG/RPV","Combination","INSTI, NNRTI","Treatment","Oral","Tablet","Once daily (with a meal)",0,0,1,VIIV,"2017-11-21","Available",
  "First two-drug complete regimen; for virologically suppressed adults switching therapy.",""),
 ("Idvynso","doravirine and islatravir","DOR/ISL","Combination","NNRTI, NRTI","Treatment","Oral","Tablet","Once daily",0,0,1,MERCK,"2026-04-20","Available",
  "Two-drug single-tablet regimen for virologically suppressed adults switching therapy.","New in 2026. Islatravir is a next-generation nucleoside reverse transcriptase translocation inhibitor (NRTTI)."),
 ("Delstrigo","doravirine, lamivudine, and tenofovir disoproxil fumarate","DOR/3TC/TDF","Combination","NNRTI, NRTI","Treatment","Oral","Tablet","Once daily",0,0,1,MERCK,"2018-08-30","Available",
  "Complete doravirine-based single-tablet regimen.",""),
 ("Atripla","efavirenz, emtricitabine, and tenofovir disoproxil fumarate","EFV/FTC/TDF","Combination","NNRTI, NRTI","Treatment","Oral","Tablet","Once daily (empty stomach, at bedtime)",0,0,1,"Gilead Sciences & Bristol Myers Squibb","2006-07-12","Discontinued",
  "The first complete once-daily single-tablet HIV regimen (2006).","Brand discontinued; generics may still be available."),
 ("Symfi","efavirenz, lamivudine, and tenofovir disoproxil fumarate","EFV/3TC/TDF","Combination","NNRTI, NRTI","Treatment","Oral","Tablet","Once daily (empty stomach, at bedtime)",0,0,1,VIATRIS,"2018-03-22","Available",
  "Complete efavirenz-based single-tablet regimen (efavirenz 600 mg).",""),
 ("Symfi Lo","efavirenz, lamivudine, and tenofovir disoproxil fumarate","EFV/3TC/TDF","Combination","NNRTI, NRTI","Treatment","Oral","Tablet","Once daily (empty stomach, at bedtime)",0,0,1,VIATRIS,"2018-02-05","Discontinued",
  "Lower-dose (efavirenz 400 mg) version of Symfi.","Brand discontinued."),
 ("Genvoya","elvitegravir, cobicistat, emtricitabine, and tenofovir alafenamide","EVG/COBI/FTC/TAF","Combination","INSTI, Pharmacokinetic Enhancer, NRTI","Treatment","Oral","Tablet","Once daily (with food)",0,0,1,GILEAD,"2015-11-05","Available",
  "Complete single-tablet regimen; the first approved with tenofovir alafenamide (TAF).",""),
 ("Stribild","elvitegravir, cobicistat, emtricitabine, and tenofovir disoproxil fumarate","EVG/COBI/FTC/TDF","Combination","INSTI, Pharmacokinetic Enhancer, NRTI","Treatment","Oral","Tablet","Once daily (with food)",0,0,1,GILEAD,"2012-08-27","Available",
  "First integrase-inhibitor-based complete single-tablet regimen.",""),
 ("Odefsey","emtricitabine, rilpivirine, and tenofovir alafenamide","FTC/RPV/TAF","Combination","NNRTI, NRTI","Treatment","Oral","Tablet","Once daily (with a meal)",0,0,1,GILEAD,"2016-03-01","Available",
  "Complete rilpivirine-based single-tablet regimen; one of the smallest HIV pills.",""),
 ("Complera","emtricitabine, rilpivirine, and tenofovir disoproxil fumarate","FTC/RPV/TDF","Combination","NNRTI, NRTI","Treatment","Oral","Tablet","Once daily (with a meal)",0,0,1,GILEAD,"2011-08-10","Available",
  "Complete rilpivirine-based single-tablet regimen (TDF version).",""),
 ("Descovy","emtricitabine and tenofovir alafenamide","FTC/TAF","Combination","NRTI","Treatment & PrEP","Oral","Tablet","Once daily",0,0,0,GILEAD,"2016-04-04","Available",
  "Two-NRTI backbone for treatment; also approved as daily oral PrEP.","PrEP indication excludes people at risk through receptive vaginal sex."),
 ("Truvada","emtricitabine and tenofovir disoproxil fumarate","FTC/TDF","Combination","NRTI","Treatment & PrEP","Oral","Tablet","Once daily",0,0,0,GILEAD,"2004-08-02","Available",
  "Two-NRTI backbone; in 2012 became the first medicine approved for HIV PrEP.","Generic versions available."),
 ("Cimduo","lamivudine and tenofovir disoproxil fumarate","3TC/TDF","Combination","NRTI","Treatment","Oral","Tablet","Once daily",0,0,0,VIATRIS,"2018-02-28","Available",
  "Two-NRTI backbone pill, taken with a third drug.",""),
 ("Combivir","lamivudine and zidovudine","3TC/ZDV","Combination","NRTI","Treatment","Oral","Tablet","Twice daily",0,0,0,VIIV,"1997-09-27","Discontinued",
  "One of the first fixed-dose HIV combination pills.","Brand discontinued; generics may still be available."),
 ("Kaletra","lopinavir and ritonavir","LPV/r","Combination","PI","Treatment","Oral","Tablet; oral solution","Once or twice daily",0,0,0,ABBVIE,"2000-09-15","Available",
  "Co-formulated, pre-boosted protease inhibitor; taken with other HIV medicines.",""),
]

COLS = ["slug","brandName","genericName","abbreviation","drugClass","componentClasses","isCombination",
        "componentCount","completeRegimen","use","route","formulation","dosingFrequency","longActing",
        "pediatricVersion","manufacturer","fdaApprovalDate","approvalYear","status","description",
        "notes","sourceUrl","lastVerified"]

def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

rows = []
for (brand, generic, abbr, cls, comp, use, route, form, dose, la, ped, full, mfr, date, status, desc, notes) in R:
    is_combo = cls == "Combination"
    rows.append({
        "slug": slugify(brand), "brandName": brand, "genericName": generic, "abbreviation": abbr,
        "drugClass": cls, "componentClasses": comp, "isCombination": str(is_combo).lower(),
        "componentCount": abbr.count("/") + 1 if is_combo else 1,
        "completeRegimen": str(bool(full)).lower(), "use": use, "route": route, "formulation": form,
        "dosingFrequency": dose, "longActing": str(bool(la)).lower(), "pediatricVersion": str(bool(ped)).lower(),
        "manufacturer": mfr, "fdaApprovalDate": date, "approvalYear": int(date[:4]), "status": status,
        "description": desc, "notes": notes, "sourceUrl": SRC, "lastVerified": VERIFIED,
    })

rows.sort(key=lambda r: r["fdaApprovalDate"])
out = sys.argv[1]
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=COLS, quoting=csv.QUOTE_MINIMAL)
    w.writeheader(); w.writerows(rows)
print(len(rows), "rows ->", out)
