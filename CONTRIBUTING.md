# Contributing

The provider data is only useful if it's right. A wrong entry can send someone who needs PEP, which has to start within 72 hours, to a clinic that's closed or doesn't stock it. These rules exist for that reason.

## What counts as "verified"

A provider is `verified` only when **someone has confirmed it directly with the provider**, by phone, email or visit, within the last 90 days. Being listed on a website, in a government announcement or in a directory makes a record a source, not a verification. Those records stay `unverified`.

When you verify a record, confirm:

1. The provider is open and at this address
2. Each service for the provider's condition(s):
   - HIV: testing, PrEP, PEP (and whether PEP is available same day or out of hours), ART
   - ADHD: assessment for children and for adults, and whether they prescribe medication (and which: methylphenidate, atomoxetine, …)
   - Diabetes: adult and child care, endocrinologist, insulin pumps, CGM, education, foot care
3. Opening hours, and whether walk-ins are OK or an appointment is needed
4. Whether foreigners and people who don't speak the local language are served, and which languages
5. Cost: free, low cost (e.g. covered by public health insurance), or fee

Then record it:

```bash
python3 scripts/mark_verified.py <id> --by "<your name>" --method phone \
  --set hivTesting=true prep=true pep=true art=false walkIn=true foreignersAccepted=true \
  --hours "Mon–Fri 08:30–16:00" --languages Thai English --note "Confirmed with reception"
python3 scripts/build_dist.py && python3 scripts/validate.py
```

If the provider has closed or stopped offering the listed services, use `--closed`. Don't delete the record, so its ID is never reused.

### Phone script (Thai / English)

> สวัสดีครับ/ค่ะ ขอสอบถามข้อมูลบริการเกี่ยวกับ HIV หน่อยครับ/ค่ะ
> ที่นี่มีบริการตรวจ HIV, ยา PrEP, ยา PEP และยาต้านไวรัส (ART) ไหมครับ/คะ
> เปิดวันไหน เวลาไหนบ้าง ต้องนัดล่วงหน้าหรือ walk-in ได้ไหม
> รับคนต่างชาติไหม และมีค่าใช้จ่ายประมาณเท่าไหร่ครับ/คะ

> Hello, I'd like to ask about your HIV services. Do you offer HIV testing, PrEP, PEP and HIV treatment (ART)? What days and hours are you open? Do I need an appointment, or can I walk in? Do you see foreigners, and roughly how much does it cost?

## Adding a provider

1. Add a record to the city's file in `data/providers/` (e.g. `hong-kong.json`). Follow `schema/provider.schema.json`.
2. Use an ID of the form `<country>-<city code>-<short-name>`, e.g. `th-bkk-…`, `hk-hkg-…`, `us-lax-…`. Set `"city"` to the same city code.
3. Put the provider's own names in `name` (and `location.address`) under the right language keys: `en`, plus `th`, `zh-Hans`, `zh-Hant`, `es` or `pt` where the provider publishes one. Don't translate official names yourself.
4. Cite at least one source. Prefer the provider's own website or an official government page. Directories and news reports are fine as leads, but say so (`"type": "third_party_directory"` or `"news"`).
5. Set `services.*` to `null` for anything the source doesn't state. Don't guess.
6. Start at `"status": "unverified"`.
7. Run the build and validator (below) and open a pull request.

## Adding a city

1. Add the city to `data/cities.json`: a three-letter code, country, jurisdiction, dialling code, time zone, currency, local languages, and `notes` for `hiv`, `adhd` and `diabetes` covering local rules people need to know (e.g. which ADHD medicines are banned or controlled). Cite each note's source in `noteSources`.
2. Create `data/providers/<city-name>.json` and add providers as above.
3. If the city is in a place with its own legal system (like Hong Kong or Macau), set `jurisdiction` accordingly. Don't group it with a neighbouring jurisdiction.

## Translations

The website is in English, Simplified Chinese (`zh-Hans`), Traditional Chinese (`zh-Hant`), Spanish (`es`), Portuguese (`pt`) and Thai (`th`).

- Interface text is in `i18n/ui.json`: one key per string, one value per language.
- Everything else written in English (city notes, service descriptions, provider notes) is translated in `i18n/content.<lang>.json`, keyed by the exact English text. If you change an English string in `data/`, update the matching key in each content file, or that string will show in English.
- Leave generic medicine names, brand names and official provider names untranslated.
- The current translations were machine-produced. Fixes from native speakers, especially for medical wording, are the most useful contribution you can make.

Rebuild after any change:

```bash
python3 scripts/build_dist.py && python3 scripts/build_site.py && python3 scripts/validate.py
```

Store organisation information only. Never add anything about patients or individuals.

## Re-checks

`validate.py` warns when a verified record is more than 90 days old. Run `python3 scripts/validate.py --strict` to treat those warnings as errors.
