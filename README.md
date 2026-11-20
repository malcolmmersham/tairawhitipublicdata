# Tairāwhiti Regional Public Data Dashboard

A self-updating dashboard of public, regularly updated data for Te Tairāwhiti, organised by HRHTO domain
(Ōhanga, Hapori, Mātauranga, Taiao, Tūhono, Tūtangata). It implements Phase 1 of the
*Tairāwhiti Longitudinal Open Data Library and Connector Plan* (November 2026).

[Open the dashboard](https://malcolmmersham.github.io/tairawhitipublicdata/).

GitHub Actions is scheduled daily at 18:17 UTC (6:17 am NZST or 7:17 am NZDT the next day).
It refreshes the sources, validates the processed observations, commits the processed data and
publishes the static dashboard. Git records the revisions to processed data. Raw downloads are
copied to `data/raw/` during a run. That folder is ignored by Git and is temporary on hosted runners.

## What's live

| Plan ID | Dataset | Publisher | Tairāwhiti history | Cadence | Status |
|---|---|---|---|---|---|
| H5 | Benefit Fact Sheets (regional council) | MSD | Sept 2013 → | Quarterly | Automated |
| H7 | Government Housing Dashboard | HUD | June 2017 → | Monthly | Automated |
| H13 | Childhood immunisation coverage (rolling 12 months, by ethnicity) | Health NZ | Oct 2022 → | Quarterly | Automated |
| H24 | Crash Analysis System | NZTA | 2006 → | Annual (public layer has no month) | Automated |
| H1, E3 | Population estimates and median age; business locations and employees | Stats NZ ADE | 1996 → / 2000 → | Annual | Automated (needs `STATSNZ_API_KEY` secret in GitHub) |
| H11 | Rental bonds | MBIE Tenancy Services | Feb 1993 → | Monthly | Automated with manual fallback |
| T6 | Gross regional greenhouse gas emissions | Stats NZ | 2007 → | Annual | Automated |
| M1 | Regular school attendance by term | Ministry of Education | 2019 → | Termly | Automated with manual fallback |
| R5 | Gisborne mayoral turnout | Department of Internal Affairs | 2022 and 2025 | Triennial | Reviewed snapshots |
| R4 | People who can speak te reo Māori | Stats NZ | 2023 Census | Five-yearly | Reviewed snapshot |

The dataset catalogue and coverage are available on the dashboard's **Data library** tab,
along with downloads for the observations and indicator definitions.

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

1. **Stats NZ key.** Register for a free key at the [Stats NZ API Portal](https://portal.apis.stats.govt.nz/how-to-subscribe). In GitHub, go to
   *Settings → Secrets and variables → Actions* and add a repository secret named `STATSNZ_API_KEY`.
2. **GitHub Pages.** Select *Settings → Pages → Source → GitHub Actions*. Open
   *Actions → Refresh data → Run workflow* on `main` and leave the sources field empty for the
   first refresh. The workflow publishes after each validated refresh.
3. **MBIE rental bonds (optional override).** The connector discovers the monthly territorial
   authority CSV on the Tenancy Services website. Set `MBIE_BOND_CSV_URL` to try a direct CSV URL
   first, or save the file to `data/manual/mbie_bonds/` as a fallback (see `data/manual/README.md`).

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

## Operating the dashboard

- The repository maintainer, `@malcolmmersham`, should enable failed Actions notifications in
  GitHub. Verify delivery using a failed run triggered by the maintainer. For scheduled workflows,
  GitHub routes notifications to the account associated with the schedule.
- If a connector fails, check its refresh log and the dashboard's **Data status** tab for the last
  successful check. Successful sources still publish, and the workflow reports the failure after
  deployment. Rerun **Refresh data** on `main` with the affected source ID after resolving it.
- If validation fails, the workflow stops before publishing. For a published bad revision, revert
  the offending data commit on `main` and run **Refresh data** with **Rebuild and publish from the
  committed data** selected. Run a normal refresh after correcting the underlying issue.

## Adding a connector

1. Add `pipeline/sources/<name>.py` with a `run()` that returns `(rows, files)`. Build each row
   with `core.obs(...)` and fetch with `core.fetch` / `core.fetch_file`, which land the raw copy
   and raise `SourceBlocked` on bot walls.
2. Register it in `SOURCES` / `MODULES` in `pipeline/run.py` and add its attribution to
   `registry.yaml` under `sources:`.
3. Add its indicators to `registry.yaml` and set its status to `live` in `catalogue.yaml`.

## Zoho Analytics

The **Data library** CSVs can feed Zoho Analytics alongside the Tairāwhiti Wellbeing Survey.
The public dashboard contains public datasets only. Survey results require an agreed release scope
before they can be added here.

## Known limits

- **Stats NZ Infoshare** series (GDP, ECT, building consents, HLFS) are not automated. Infoshare
  is being replaced by ADE (target April 2027); add them as ADE dataflows once they move.
- **Health NZ** immunisation history before October 2022 is in older quarterly files with a
  different layout, not yet parsed.
- **NZTA CAS** is live data: past years can change, and the current year is year-to-date. The
  public layer has `region = "Gisborne Region"` from 2006.
- **Local election turnout (R5).** The published snapshots use the overall turnout from the mayoral
  section of each official CSV. Check earlier contested elections before charting a longer series.
  [Official 2022 and 2025 election data](https://www.mcert.govt.nz/our-work/local-government/local-elections-and-voting/local-authority-election-statistics/)
- **Census te reo Māori (R4).** The snapshot uses the Stats NZ Gisborne Region estimate. Check
  denominators, geography and the effects of imputation
  across census years before publishing a trend.
  [Stats NZ Gisborne Region summary](https://tools.summaries.stats.govt.nz/places/rc/gisborne-region)
  [2018 Census variable quality assessment](https://www.stats.govt.nz/assets/Uploads/Reports/2018-Census-External-Data-Quality-Panel-Assessment-of-Variables/Download-data/2018-census-external-data-quality-panel-assessment-of-variables.pdf)
- **Labour market:** there is no Tairāwhiti-only unemployment rate (HLFS combines Gisborne and
  Hawke's Bay). Jobseeker Support counts are the regional signal.

## Data governance

- Publisher licences are kept per row and attribution is shown under every chart (most sources
  are CC BY 4.0; MBIE tenancy data is CC BY 3.0 NZ).
- Publisher suppression and rounding are inherited and never undone (for example, by
  differencing region minus TA). Suppressed cells stay empty with a `suppression_flag`.
- Māori-disaggregated indicators follow Te Mana Raraunga and CARE principles. Agree with iwi
  entities how iwi-level views are shown before adding them, and avoid deficit-only framing.
