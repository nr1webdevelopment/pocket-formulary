# NomadCeuticals

*Formerly Pocket Formulary. The GitHub repository and download URLs still use the `pocket-formulary` name.*

An open dataset of **HIV, ADHD and diabetes medicines** and **care providers in 10 cities** for the same three conditions. Free to download and reuse, with a source for every record and a verification status on every provider. The website is available in English, 简体中文, 繁體中文, Español, Português and ไทย.

| Dataset | Records | What's in it |
|---|---|---|
| Medicines | 124 | FDA-approved HIV (58), ADHD (25) and diabetes (41) medicines: brand and generic name, class, form, dosing, manufacturer, approval date |
| Providers | 166 | HIV (131), ADHD (19) and diabetes (19) providers. Local and English names, address, phone, hours, services, cost, sources and verification |
| Cities | 10 | Country, jurisdiction, dialling code, time zone, currency, local languages, and per-condition notes on local rules (e.g. which ADHD medicines are legal) |

| City | Code | HIV | ADHD | Diabetes | Total |
|---|---|---|---|---|---|
| Bangkok, Thailand | `bkk` | 38 | 6 | 5 | 49 |
| Shanghai, Mainland China | `sha` | 8 | 1 | 2 | 11 |
| Hong Kong SAR | `hkg` | 21 | 2 | 1 | 24 |
| Macau SAR | `mfm` | 2 | 2 | 2 | 3 |
| Taipei, Taiwan | `tpe` | 4 | 1 | 1 | 6 |
| Singapore | `sin` | 5 | 3 | 1 | 9 |
| San Francisco, USA | `sfo` | 15 | 1 | 3 | 19 |
| Los Angeles, USA | `lax` | 21 | 1 | 2 | 24 |
| Guadalajara, Mexico | `gdl` | 7 | 1 | 1 | 9 |
| Lisbon, Portugal | `lis` | 10 | 1 | 1 | 12 |

Some providers cover more than one condition, so condition counts add up to more than the total.

> **Mainland China, Hong Kong, Macau and Taiwan are four separate jurisdictions.** Each has its own laws, medicine regulator, approved and controlled medicine lists, prescription rules and health insurance. A medicine or service available in one may not be available, or legal, in another. Check the rules for the place you are in. (This note is in `data/cities.json` as `jurisdictionNotes` and shows on the website for those four cities.)

> **Provider data is not yet phone-verified.** Every provider record starts as `unverified`, meaning it comes from the provider's own website or an official government source but nobody has confirmed it directly yet. Check `verification.status` before relying on a record, and call ahead before visiting. This is not medical advice. If you need PEP, go to a clinic or hospital emergency department as soon as possible; PEP has to start within 72 hours.

## Download the latest data

Always-current files (they track the `main` branch):

| File | URL |
|---|---|
| Providers (JSON) | https://raw.githubusercontent.com/nr1webdevelopment/pocket-formulary/main/dist/v1/providers.json |
| Providers (CSV) | https://raw.githubusercontent.com/nr1webdevelopment/pocket-formulary/main/dist/v1/providers.csv |
| Medicines (JSON) | https://raw.githubusercontent.com/nr1webdevelopment/pocket-formulary/main/dist/v1/medicines.json |
| Medicines (CSV) | https://raw.githubusercontent.com/nr1webdevelopment/pocket-formulary/main/dist/v1/medicines.csv |
| Cities (JSON) | https://raw.githubusercontent.com/nr1webdevelopment/pocket-formulary/main/dist/v1/cities.json |
| Cities (CSV) | https://raw.githubusercontent.com/nr1webdevelopment/pocket-formulary/main/dist/v1/cities.csv |
| Translations | `https://raw.githubusercontent.com/nr1webdevelopment/pocket-formulary/main/dist/v1/i18n/ui.json` and `content.<lang>.json` |
| Manifest | https://raw.githubusercontent.com/nr1webdevelopment/pocket-formulary/main/dist/v1/manifest.json |

- **Pinned versions:** each tagged release (e.g. `v1.0.0`) has a zip on the [Releases page](https://github.com/nr1webdevelopment/pocket-formulary/releases). Use these if you need data that won't change under you.
- **CDN:** the same files through jsDelivr, e.g. `https://cdn.jsdelivr.net/gh/nr1webdevelopment/pocket-formulary@main/dist/v1/providers.json`, or `@v1.0.0` for a pinned version.
- **Checking for updates:** fetch `manifest.json` and compare `version` or the `sha256` of each file.

```js
const res = await fetch("https://raw.githubusercontent.com/nr1webdevelopment/pocket-formulary/main/dist/v1/providers.json");
const { version, data } = await res.json();
const prep = data.filter(p => p.conditions.includes("hiv") && p.services.prep === true && p.verification.status !== "closed");
const adhdAdults = data.filter(p => p.conditions.includes("adhd") && p.services.adhdAssessmentAdults === true);
const hongKongHiv = data.filter(p => p.city === "hkg" && p.conditions.includes("hiv"));
```

## Data format

Each JSON file looks like `{ dataset, version, released, license, schema, count, data: [...] }`. Records follow the JSON Schemas in [`schema/`](schema/). The CSV files are the same records flattened (`location.district`, `services.prep`, …) for spreadsheets and the Framer CMS.

**Cities and IDs:** every provider has a `city` code (see the table above and `cities.json`). IDs are `<country>-<city>-<short-name>`, e.g. `th-bkk-pribta-clinic`, `hk-hkg-shc-chai-wan`, `us-sfo-city-clinic`. `name` and `location.address` are objects keyed by language (`en`, `th`, `zh-Hans`, `zh-Hant`, `es`, `pt`), holding the provider's own names only. We don't invent translations of official names.

**Provider conditions:** `conditions` lists what the provider is in the dataset for (`hiv`, `adhd`, `diabetes`), matching the medicines' `condition`. Which `services` keys a record has depends on it:

| Condition | Service keys |
|---|---|
| `hiv` | `hivTesting`, `prep`, `pep`, `art`, `stiTesting`, `genderAffirmingHormones` |
| `adhd` | `adhdAssessmentChildren`, `adhdAssessmentAdults`, `adhdMedication` |
| `diabetes` | `diabetesCare` (adults), `diabetesCareChildren`, `endocrinologist`, `insulinPump`, `cgm`, `diabetesEducation`, `diabeticFootCare` |

**Provider services** are `true` (offered), `false` (not offered) or `null` (not confirmed). `services.basis` says where that claim comes from:

- `site`: stated for this location
- `network`: stated for the whole network (e.g. all 31 BKK Pride Clinic sites, or every Hong Kong Social Hygiene Clinic), not for this site specifically
- `third_party`: taken from a directory or news report

**Verification status:**

| Status | Meaning |
|---|---|
| `unverified` | From an official or provider source, checked on `sourceChecked`, but not confirmed directly |
| `verified` | Confirmed with the provider by phone, email or visit on `lastVerified`. Due for re-check on `nextReviewDue` (every 90 days) |
| `needs_review` | Something may have changed; treat with caution |
| `closed` | No longer offers the listed services. Kept so IDs never get reused |

IDs (`th-bkk-…`, `us-lax-…`, medicine slugs) are stable and never reused.

## Repository layout

```
data/                     SOURCE DATA: edit these
  hiv-medicines.csv  adhd-medicines.csv  diabetes-medicines.csv
  providers/<city>.json   one file per city (bangkok, shanghai, hong-kong, macau, taipei,
                          singapore, san-francisco, los-angeles, guadalajara, lisbon)
  cities.json             city metadata, local-rule notes, jurisdiction notes
  release.json            version + release date
i18n/
  ui.json                 website interface text, 6 languages
  content.<lang>.json     translations of notes, descriptions and other English content
schema/                   JSON Schemas for medicine, provider and city records
dist/v1/                  PUBLISHED DATA: generated, don't edit by hand
assets/                   logo (SVG)
images/                   header slideshow photos + slides.json
scripts/
  build_dist.py           data/ -> dist/v1/ (JSON, CSV, manifest)
  validate.py             checks sources + dist/ (CI runs this)
  mark_verified.py        record a phone/email verification
  build_hiv_db.py  site_data.py  build_site.py  template.html   website build
docs/                     verification protocol notes, leads
index.html                the reference website (open in a browser)
```

## Updating the data

```bash
python3 scripts/mark_verified.py th-bkk-swing-silom --by "Gary" --method phone --set pep=true walkIn=true
python3 scripts/build_dist.py
python3 scripts/validate.py
git commit -am "Verify SWING Silom" && git push
```

To publish a numbered release, bump `version` and `released` in `data/release.json`, add a `CHANGELOG.md` entry, rebuild, commit, then `git tag v1.1.0 && git push --tags`. GitHub Actions validates every push and attaches the files to the release.

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to verify a provider and how to add one.

## Website

`index.html` is a self-contained reference site (no server needed), in six languages: English, Simplified Chinese, Traditional Chinese, Spanish, Portuguese and Thai. The language follows the browser, can be changed from the menu at the top, and can be set in the link with `?lang=zh-Hant` (also `en`, `zh-Hans`, `es`, `pt`, `th`).

- **Medicines** (`index.html#biktarvy`): a profile for each medicine, linking to matching providers in the selected city. ADHD medicine pages flag Thai legal status when Bangkok is selected.
- **Providers** (`index.html#providers/hkg/hiv`, `#providers/lis/adhd`, `#providers/sfo/diabetes`): a city picker, condition tabs, service filters and search. Each city shows its local notes; Shanghai, Hong Kong, Macau and Taipei also show the four-jurisdictions note. HIV has a PEP shortcut. Each provider page (`index.html#provider/th-bkk-pribta-clinic`) has tap-to-call with the right country code, LINE where available, directions, a service checklist, verification status, sources and a "report a problem" link.

**Logo and header slideshow:** the logo is in `assets/`: `logo.svg` (full lockup with tagline), `logo-mark.svg` (compass mark with N/E/S/W), `logo-icon.svg` (mark without letters, used as the favicon) and `logo-bar.svg` (icon + wordmark, used in the top bar). All are vector, with text converted to outlines, redrawn from `logo_nomadceuticals.jpg`. The header photos are in `images/`. `images/slides.json` sets their order, focal point, photographer credit (shown in the footer), and which text goes with each photo: `text` picks the `hero_<text>_title`, `_text` and `_cta` strings in `i18n/ui.json`, and `link` is where the button goes (`#providers`, `#medicines` or `repo`). Add or swap photos, update `slides.json`, then run `python3 scripts/build_site.py`. The build resizes each photo to a small WebP and embeds it in `index.html`, so the page stays a single file. The slideshow crossfades every 6 seconds, has indicator and pause buttons, and doesn't auto-play for people who have "reduce motion" turned on. Current photos are from Pexels (free to use, credit given).

Generic medicine names, brand names and providers' official names are left untranslated. All other translations were machine-produced and still need review by native speakers. Corrections to `i18n/` are welcome.

Rebuild after any data change:

```bash
python3 scripts/site_data.py     # medicines -> data/drugs.json
python3 scripts/build_dist.py    # providers + medicines -> dist/v1/
python3 scripts/build_site.py    # -> index.html
```

The medicine CSVs in `data/` can also be imported straight into the Framer CMS.

## Sources

- **HIV medicines:** [NIH HIVinfo, FDA-Approved HIV Medicines](https://hivinfo.nih.gov/understanding-hiv/fact-sheets/fda-approved-hiv-medicines)
- **ADHD and diabetes medicines:** compiled list. Check entries against [Drugs@FDA](https://www.accessdata.fda.gov/scripts/cder/daf/).
- **Providers:** each record lists its own sources: the provider's website, government health department pages (e.g. BMA, Hong Kong Department of Health, SF and LA County public health, Singapore HPB, Portugal SNS, Jalisco and Mexico health services) and, where noted, directories or news reports.
- **City notes:** each city in `data/cities.json` lists the sources for its notes in `noteSources`.

## License

Data: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Code: MIT. See [LICENSE.md](LICENSE.md).
