# Pocket Formulary

A single-page reference site for FDA-approved medicines used in **HIV**, **ADHD** and **diabetes** — 124 medicines, each with its own profile page (brand and generic name, drug class, form, dosing, manufacturer, FDA approval date, brand status, notes).

Open `index.html` in a browser. No build step or server needed; the data is embedded in the page. Profiles are linkable by slug, e.g. `index.html#biktarvy`.

## Structure

```
index.html              The site (generated, self-contained)
data/
  hiv-medicines.csv      58 HIV medicines (Framer CMS-ready)
  adhd-medicines.csv     25 ADHD medicines (Framer CMS-ready)
  diabetes-medicines.csv 41 diabetes medicines (Framer CMS-ready)
  drugs.json             Combined dataset used by the site
scripts/
  build_hiv_db.py        Source data for the HIV CSV
  site_data.py           ADHD + diabetes data; builds drugs.json and the two CSVs
  template.html          Site template (HTML/CSS/JS)
  build_site.py          Injects drugs.json into the template -> index.html
```

## Rebuilding

```bash
python3 scripts/build_hiv_db.py data/hiv-medicines.csv   # only if you edit HIV data
python3 scripts/site_data.py                             # rebuilds drugs.json + ADHD/diabetes CSVs
python3 scripts/build_site.py                            # rebuilds index.html
```

## Importing into Framer

In the Framer CMS, import a CSV from `data/`. Suggested field types: dates/years as Date or Number, `true`/`false` columns as Toggle, and class/status/use columns as Option for filtering. Multi-value fields (e.g. `componentClasses`) are comma-separated text.

## Sources and accuracy

- HIV: [NIH HIVinfo — FDA-Approved HIV Medicines](https://hivinfo.nih.gov/understanding-hiv/fact-sheets/fda-approved-hiv-medicines) (reviewed Sept 2026).
- ADHD and diabetes: compiled list with approval years; verify each entry against [Drugs@FDA](https://www.accessdata.fda.gov/scripts/cder/daf/) before publishing. 2026 updates included: Simtriyo (centanafadine), Awiqli (insulin icodec), Rybelsus → "Ozempic pill" rename, Mounjaro cardiovascular indication.

For general reference only — not medical advice.
