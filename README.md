# Pocket Formulary

An open dataset of **HIV, ADHD and diabetes medicines** and **HIV service providers in Bangkok** (testing, PrEP, PEP and treatment). Free to download and reuse, with a source for every record and a verification status on every provider.

| Dataset | Records | What's in it |
|---|---|---|
| Medicines | 124 | FDA-approved HIV (58), ADHD (25) and diabetes (41) medicines: brand and generic name, class, form, dosing, manufacturer, approval date |
| Providers | 38 (Bangkok) | Clinics and hospitals offering HIV testing, PrEP, PEP or ART: Thai and English names, address, phone/LINE, hours, services, cost, sources, verification |

> **Provider data is not yet phone-verified.** Every provider record starts as `unverified`, meaning it comes from the provider's own website or an official BMA announcement but nobody has confirmed it directly yet. Check `verification.status` before relying on a record, and call ahead before visiting. This is not medical advice. If you need PEP, go to a clinic or hospital emergency department as soon as possible; PEP has to start within 72 hours.

## Download the latest data

Always-current files (they track the `main` branch):

| File | URL |
|---|---|
| Providers (JSON) | https://raw.githubusercontent.com/nr1webdevelopment/pocket-formulary/main/dist/v1/providers.json |
| Providers (CSV) | https://raw.githubusercontent.com/nr1webdevelopment/pocket-formulary/main/dist/v1/providers.csv |
| Medicines (JSON) | https://raw.githubusercontent.com/nr1webdevelopment/pocket-formulary/main/dist/v1/medicines.json |
| Medicines (CSV) | https://raw.githubusercontent.com/nr1webdevelopment/pocket-formulary/main/dist/v1/medicines.csv |
| Manifest | https://raw.githubusercontent.com/nr1webdevelopment/pocket-formulary/main/dist/v1/manifest.json |

- **Pinned versions:** each tagged release (e.g. `v1.0.0`) has a zip on the [Releases page](https://github.com/nr1webdevelopment/pocket-formulary/releases). Use these if you need data that won't change under you.
- **CDN:** the same files through jsDelivr, e.g. `https://cdn.jsdelivr.net/gh/nr1webdevelopment/pocket-formulary@main/dist/v1/providers.json`, or `@v1.0.0` for a pinned version.
- **Checking for updates:** fetch `manifest.json` and compare `version` or the `sha256` of each file.

```js
const res = await fetch("https://raw.githubusercontent.com/nr1webdevelopment/pocket-formulary/main/dist/v1/providers.json");
const { version, data } = await res.json();
const prep = data.filter(p => p.services.prep === true && p.verification.status !== "closed");
```

## Data format

Each JSON file looks like `{ dataset, version, released, license, schema, count, data: [...] }`. Records follow the JSON Schemas in [`schema/`](schema/). The CSV files are the same records flattened (`location.district`, `services.prep`, …) for spreadsheets and the Framer CMS.

**Provider services** are `true` (offered), `false` (not offered) or `null` (not confirmed). `services.basis` says where that claim comes from:

- `site`: stated for this location
- `network`: stated for the whole network (e.g. all 31 BKK Pride Clinic sites), not for this site specifically
- `third_party`: taken from a directory or news report

**Verification status:**

| Status | Meaning |
|---|---|
| `unverified` | From an official or provider source, checked on `sourceChecked`, but not confirmed directly |
| `verified` | Confirmed with the provider by phone, email or visit on `lastVerified`. Due for re-check on `nextReviewDue` (every 90 days) |
| `needs_review` | Something may have changed; treat with caution |
| `closed` | No longer offers HIV services. Kept so IDs never get reused |

IDs (`th-bkk-…`, medicine slugs) are stable and never reused.

## Repository layout

```
data/                     SOURCE DATA: edit these
  hiv-medicines.csv  adhd-medicines.csv  diabetes-medicines.csv
  providers/bangkok.json
  release.json            version + release date
schema/                   JSON Schemas for medicine and provider records
dist/v1/                  PUBLISHED DATA: generated, don't edit by hand
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

`index.html` is a self-contained reference site for the medicines (no server needed). Rebuild it with `python3 scripts/site_data.py && python3 scripts/build_site.py`. The medicine CSVs in `data/` can also be imported straight into the Framer CMS.

## Sources

- **HIV medicines:** [NIH HIVinfo, FDA-Approved HIV Medicines](https://hivinfo.nih.gov/understanding-hiv/fact-sheets/fda-approved-hiv-medicines)
- **ADHD and diabetes medicines:** compiled list. Check entries against [Drugs@FDA](https://www.accessdata.fda.gov/scripts/cder/daf/).
- **Providers:** each record lists its own sources: the provider's website, BMA announcements (BKK Pride Clinic network) and, where noted, news reports.

## License

Data: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Code: MIT. See [LICENSE.md](LICENSE.md).
