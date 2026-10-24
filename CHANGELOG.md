# Changelog

## Unreleased

- **Renamed to NomadCeuticals** (formerly Pocket Formulary). New logo: compass with a medical cross (vector files in `assets/`). Repository URLs and dataset IDs are unchanged.
- Website redesign: black top bar, square cards, serif headings, red accent, icon squares on condition tabs. No gradients.
- Header slideshow of three Pexels photos (`images/`, configured in `images/slides.json`), beside the title or above it on phones.
- Release zip renamed to `nomadceuticals-data-<version>.zip`.

## v2.0.0 — 2026-10-23

- **Nine new cities, 117 new providers (166 total).** Shanghai (11), Hong Kong (24), Macau (3), Taipei (6), Singapore (9), San Francisco (19), Los Angeles (24), Guadalajara (9), Lisbon (12), plus Bangkok (49). All new records are `unverified`.
- **New `cities` dataset** (`dist/v1/cities.json` / `.csv`): jurisdiction, dialling code, time zone, currency, local languages, and per-condition notes on local rules, with sources.
- **Jurisdiction note:** Mainland China, Hong Kong, Macau and Taiwan are four separate jurisdictions with different laws, regulators, approved medicines and prescription rules. Recorded in `cities.json` (`jurisdictionNotes`) and shown on the website for those cities.
- **Breaking schema changes:** every provider now requires `city`. `name` and `location.address` are objects keyed by language. IDs use `<country>-<city>-<slug>`. New provider type `public_clinic` and operators `government_regional` / `government_local`.
- **Website in six languages:** English, Simplified Chinese, Traditional Chinese, Spanish, Portuguese, Thai. City picker, city-aware phone links and notes, routes of the form `#providers/<city>/<condition>`. Translations are machine-produced and need native review.
- Translation files published in `dist/v1/i18n/`. Manifest counts providers by city.
- Known gaps: see `docs/leads.md`.

## v1.1.0 — 2026-10-23

- **Providers now cover ADHD and diabetes.** New `conditions` field on every provider, plus condition-specific service keys (see README).
  - ADHD (6): MedConsult Clinic (Thonglor, Silom), Bangkok Hospital (Psychiatry; Child Development Neuropsychiatric Clinic), Rajanagarindra Institute of Child and Adolescent Mental Health, Somdet Chaopraya Institute of Psychiatry
  - Diabetes (5): Bangkok Hospital Diabetes Center, Bumrungrad Endocrinology & Diabetes Center, MedPark Endocrinology Center, Samitivej Children's Growth, Endocrine and Diabetes Center, Siriraj Paediatric DM Clinic
  - All new records are `unverified`
- Schema: `conditions` (required), ADHD/diabetes service keys, `children` population focus.
- Website: HIV / ADHD / Diabetes tabs on the providers section. Medicine pages link to matching providers, and ADHD medicine pages flag Thai legal status.
- Manifest now counts providers by condition.

## v1.0.0 — 2026-10-23

First data release.

- **Medicines:** 124 records (58 HIV, 25 ADHD, 41 diabetes) in one normalised format (`dist/v1/medicines.json` / `.csv`).
- **Providers (new):** 38 HIV service providers in Bangkok:
  - 7 individual clinics and hospitals: Thai Red Cross Anonymous Clinic, Pribta, Tangerine, SWING, RSAT Ramkhamhaeng, Bumrungrad Pride Clinic, Bangkok Hospital Gay Men's Health
  - all 31 sites in the BMA's BKK Pride Clinic network
  - Every provider is `unverified` (source-checked 2026-10-23, not yet confirmed by phone)
- JSON Schemas, a validator, a manifest with checksums, CI on every push, and release packaging on tags.
