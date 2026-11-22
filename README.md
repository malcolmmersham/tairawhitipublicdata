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
| M1 | Regular school attendance by term | Ministry of Education | 2019 → | Termly | Reviewed workbook fallback |
| M3 | NCEA Level 2 or above | Ministry of Education | 2015 → | Annual | Reviewed workbook fallback |
| E1 | Regional GDP and GDP per person at current prices | Stats NZ | 2000 → | Annual | Automated |
| H8, H9 | House price to income ratio and changes in housing affordability | HUD | 2001 → | Quarterly | Automated |
| E5, E13 | Filled jobs and building consents | Stats NZ | May 2019 / Apr 1990 → | Monthly | Automated |
| E10 | Commercial guest nights and active accommodation establishments | MBIE | June 2020 → | Monthly | Automated |
| E14 | Average residential electricity off-take | Electricity Authority | 2016 → | Annual | Automated |
| G2 | Council operating income and expenditure | Stats NZ | Annual coverage | Annual | Automated |
| H2 | 2023-base population projections | Stats NZ | 2028–2053 | Irregular | Reviewed scenarios |
| H3, H4 | Registered births and deaths, and census household counts | Stats NZ | 2012 / 2013 → | Annual / Five-yearly | Automated |
| M5, M8 | Prior early learning participation and July school rolls | Ministry of Education | 2018 / 1996 → | Quarterly / Annual | Reviewed workbook fallback |
| M8 | Māori-medium enrolment at schools in Gisborne District, immersion levels 1–2 | Ministry of Education | 2000–2025 | Annual | Reviewed workbook |
| T1 | Median river E. coli by monitoring site | Stats NZ and Ministry for the Environment | 2020–2024 | Irregular | Published monitoring window |
| T2 | Routine river E. coli and coastal enterococci samples by site and date | LAWA and Gisborne District Council | 2020–2026 | Annual | Reviewed monitoring release |
| R5 | Gisborne mayoral turnout | Department of Internal Affairs | 2022 and 2025 | Triennial | Reviewed snapshots |
| R4 | People who can speak te reo Māori | Stats NZ | 2023 Census | Five-yearly | Reviewed snapshot |
| SA2 | Gisborne District place profiles | Stats NZ | 2013–2023 population and age, 2023 other measures | Five-yearly | Automated |

The dataset catalogue and coverage are available on the dashboard's **Data library** tab,
along with downloads for the observations and indicator definitions.

The [Places (SA2) tab](https://malcolmmersham.github.io/tairawhitipublicdata/#places)
joins Census records and generalised 2023 boundaries by six-digit SA2 code. The bundled
boundary extract covers 27 populated areas. It uses the published territorial authority profile
list and was checked spatially against the official 2023 boundary for Gisborne District (028).
[Profile list](https://www.ehinz.ac.nz/assets/Social-Vulnerability-Indicators/2025-SVI-update/Heatmap_SVI2023_SA2.pdf) · [SA2 boundaries](https://datafinder.stats.govt.nz/layer/111227-statistical-area-2-2023-generalised/) · [District boundaries](https://services2.arcgis.com/vKb0s8tBIA3bdocZ/arcgis/rest/services/Territorial_Authority_2023/FeatureServer/0)

## Catalogue and release review

- The catalogue records the rollout release for each planned connector. A reference entry links
  to the publisher. A deferred entry records what evidence or permission would reopen it.
- The repository maintainer, `@malcolmmersham`, coordinates reviewed manual releases. Compare the
  first and latest periods and a local value to the publisher, record the licence, confirm source
  geography and suppression, then rebuild. Verify the chart and both CSVs after the workflow deploys.
- PHO enrolment (H18) needs a reviewed district workbook with the release date and district definition. [Health NZ quarterly releases](https://www.healthnz.govt.nz/about-us/health-data/data-sets-and-collections/primary-care-data-and-statistics/enrolment-with-a-general-practice-and-primary-health-organisation)
- Victimisations (H22) needs a repeatable monthly Gisborne District export. The public geographic reports exclude most dwelling offences. [Police statistics](https://www.police.govt.nz/stats-data-category/victimisations-rcvs) · [Geographic reporting coverage](https://data.govt.nz/datasetrequest/show/1078)
- Finalised charges (H25) links to the court-location tables as a reference. [Ministry of Justice tables](https://www.justice.govt.nz/justice-sector-policy/research-data/justice-statistics/adults-with-finalised-charges-in-court/) · [Stats NZ methodology](https://datainfoplus.stats.govt.nz/item/nz.govt.stats/c4adb79f-4d9c-4109-914e-bf2973f79102/6)
- For the Trust survey, start from the [public Trust dashboard](https://trusttairawhiti.nz/what-we-do/wellbeing-data).
  A Trust-approved aggregate export must identify the survey years, weighting method, permitted
  breakdowns, and suppression rules. Keep response data and working files outside this repository.

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
- Scheduled runs skip recently successful sources with a longer check interval. A manual run always
  checks the selected sources. A failed source stays eligible for the next scheduled retry.
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

- **Stats NZ Infoshare.** Regional GDP and building consents use the official release downloads.
  Check the availability and geographic scope of remaining series as Stats NZ moves them to ADE.
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
