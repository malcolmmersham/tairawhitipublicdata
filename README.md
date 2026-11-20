# Tairāwhiti Regional Public Data Dashboard

A self-updating dashboard of public, regularly updated data for Te Tairāwhiti, organised by HRHTO domain
(Ōhanga, Hapori, Mātauranga, Taiao, Tūhono, Tūtangata). It implements Phase 1 of the
*Tairāwhiti Longitudinal Open Data Library and Connector Plan* (November 2026).

A GitHub Actions job runs every day at about 6:17 am NZST. It downloads each source, keeps an
immutable raw copy, rewrites a tidy long-format table, rebuilds the dashboard data and commits
any changes. Git history is the revision history: every vintage of every series is recoverable.

## What's live

| Plan ID | Dataset | Publisher | Tairāwhiti history | Cadence | Status |
|---|---|---|---|---|---|
| H5 | Benefit Fact Sheets (regional council) | MSD | Sept 2013 → | Quarterly | Automated |
| H7 | Government Housing Dashboard | HUD | June 2017 → | Monthly | Automated |
| H13 | Childhood immunisation coverage (rolling 12 months, by ethnicity) | Health NZ | Oct 2022 → | Quarterly | Automated |
| H24 | Crash Analysis System | NZTA | 2006 → | Annual (public layer has no month) | Automated |
| H1, E3 | Population estimates and median age; business locations and employees | Stats NZ ADE | 1996 → / 2000 → | Annual | Automated (needs `STATSNZ_API_KEY` secret in GitHub) |
| H11 | Rental bonds | MBIE | 1993 → | Monthly | Manual drop: mbie.govt.nz blocks cloud servers |

The full 70-dataset library, with the status of each, is in `pipeline/catalogue.yaml` and on the
dashboard's **Data library** tab.

## How it fits together

```
pipeline/sources/*.py   one connector per publisher → list of observations
        │
data/raw/               bronze: every downloaded file, by source/date/sha (not committed)
data/silver/<src>.csv   silver: tidy long table per source (committed)
data/gold/              gold: all observations + indicator registry (committed)
site/data/dashboard.json  what the web page reads
site/index.html         the dashboard (static, no build step)
```

Every observation uses one schema:
`indicator_id, geo_type, geo_code, geo_name, period_start, period_end, period_type, year_basis,
value, unit, measure, ethnicity, age, sex, suppression_flag, quality_flag, source_id, vintage_date, licence`.

`vintage_date` is the date a value was first seen. It only changes when the publisher revises
that value, so revisions are visible.

`pipeline/registry.yaml` maps each indicator to its domain and topic, says which direction is
"good", sets headline tiles, and holds the caveat and attribution text shown under each chart.
Add a `muka:` field to each indicator to map it to the HRHTO muka/outcomes.

A connector that fails never wipes data. Its last good CSV stays in place, `data/status.json`
records the failure, and the **Data status** tab shows it. A schema hash per source flags when a
publisher's file starts producing a different set of indicators.

## Setup

1. **Stats NZ key.** Register for a free key at the Stats NZ API Portal. In GitHub, go to
   *Settings → Secrets and variables → Actions* and add a repository secret named `STATSNZ_API_KEY`.
2. **Hosting the dashboard (optional).** GitHub Pages on a private repository needs a paid GitHub
   plan, or make the repository public. Then enable *Settings → Pages → Source: GitHub Actions*
   and add a repository variable `ENABLE_PAGES` = `true`. Without Pages, open `site/index.html`
   through any static web server (see below), or point Zoho Analytics at `data/gold/`.
3. **MBIE rental bonds.** Save the territorial-authority monthly CSV from the MBIE rental bond
   page into `data/manual/mbie_bonds/` (see `data/manual/README.md`). If you find a direct CSV
   URL that works, set it as repository variable `MBIE_BOND_CSV_URL` instead.

Run it locally:

```bash
pip install -r requirements.txt
```

```bash
python -m pipeline.run
```

```bash
python -m http.server --directory site 8000
```

Run one source with `python -m pipeline.run msd_benefits`. Rebuild the dashboard from existing
data without downloading with `python -m pipeline.run --build-only`. You can also run the
workflow by hand from the **Actions** tab, optionally naming sources.

## Adding a connector

1. Add `pipeline/sources/<name>.py` with a `run()` that returns `(rows, files)`. Build each row
   with `core.obs(...)` and fetch with `core.fetch` / `core.fetch_file`, which land the raw copy
   and raise `SourceBlocked` on bot walls.
2. Register it in `SOURCES` / `MODULES` in `pipeline/run.py` and add its attribution to
   `registry.yaml` under `sources:`.
3. Add its indicators to `registry.yaml` and set its status to `live` in `catalogue.yaml`.

## Zoho Analytics

`data/gold/observations.csv` and `data/gold/indicators.csv` are designed to load straight into
Zoho Analytics next to the Tairāwhiti Wellbeing Survey, using the same long format (put TWS rows
in with `geo_type = "TWS area"`). Because this repository is private, Zoho's "Import from URL"
cannot read the files directly. Either make the gold folder reachable (public repo or Pages), or
add a step to the workflow that pushes the CSVs with the Zoho Analytics Import API.

## Known limits

- **Stats NZ Infoshare** series (GDP, ECT, building consents, HLFS) are not automated. Infoshare
  is being replaced by ADE (target April 2027); add them as ADE dataflows once they move.
- **Health NZ** immunisation history before October 2022 is in older quarterly files with a
  different layout, not yet parsed.
- **NZTA CAS** is live data: past years can change, and the current year is year-to-date. The
  public layer has `region = "Gisborne Region"` from 2006.
- **Education Counts** returned HTTP 403 to automated requests during setup, so school
  attendance (M1) is not yet automated.
- **Labour market:** there is no Tairāwhiti-only unemployment rate (HLFS combines Gisborne and
  Hawke's Bay). Jobseeker Support counts are the regional signal.

## Data governance

- Publisher licences are kept per row and attribution is shown under every chart (most sources
  are CC BY 4.0; MBIE tenancy data is CC BY 3.0 NZ).
- Publisher suppression and rounding are inherited and never undone (for example, by
  differencing region minus TA). Suppressed cells stay empty with a `suppression_flag`.
- Māori-disaggregated indicators follow Te Mana Raraunga and CARE principles. Agree with iwi
  entities how iwi-level views are shown before adding them, and avoid deficit-only framing.
