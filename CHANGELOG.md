# Changelog

## v1.0.0 — 2026-10-23

First data release.

- **Medicines:** 124 records (58 HIV, 25 ADHD, 41 diabetes) in one normalised format (`dist/v1/medicines.json` / `.csv`).
- **Providers (new):** 38 HIV service providers in Bangkok:
  - 7 individual clinics and hospitals: Thai Red Cross Anonymous Clinic, Pribta, Tangerine, SWING, RSAT Ramkhamhaeng, Bumrungrad Pride Clinic, Bangkok Hospital Gay Men's Health
  - all 31 sites in the BMA's BKK Pride Clinic network
  - Every provider is `unverified` (source-checked 2026-10-23, not yet confirmed by phone)
- JSON Schemas, a validator, a manifest with checksums, CI on every push, and release packaging on tags.
