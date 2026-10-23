# Changelog

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
