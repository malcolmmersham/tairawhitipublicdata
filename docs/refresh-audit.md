# Refresh coverage audit

Audit for [issue #7](https://github.com/malcolmmersham/tairawhitipublicdata/issues/7), checked on
22 November 2026 against base commit `6fe3c8d`. The latest period is the most recent `period_end`
in `data/silver/<source>.csv`. The last check comes from `data/status.json` in that commit. Each
automated connector succeeded within the last three days, so its latest period matches the
publisher feed at that check. The status column compares the latest period with the published
cadence and usual lag.

A next release is marked *verified* only when a publisher page confirms the release. Other dates
are inferred from the cadence and need checking. The catalogue and `data/manual/README.md` do
not record a named steward or next review date for any reviewed release. The README names the
maintainer, `@malcolmmersham`, as coordinator for all of them.

## Automated sources

| Catalogue ID | Source ID | Latest period | Cadence | Last success | Next expected publisher release | Status |
|---|---|---|---|---|---|---|
| H1 | `statsnz_ade` (population) | 30 June 2026, provisional (TALB, 2026 boundaries) | Annual | 2026-11-21 | 30 June 2027 TALB estimates, about October 2027 (inferred). The 2026 TALB release was published on [29 October 2026](https://www.stats.govt.nz/information-releases/subnational-population-estimates-at-30-june-2026/). | Current |
| E3 | `statsnz_ade` (business demography) | February 2026 | Annual | 2026-11-21 | February 2027, about October 2027 (inferred) | Current |
| SA2E (new) | `statsnz_sa2_population` | 30 June 2025, provisional (SA2, 2025 boundaries) | Annual | Not yet run on `main` | **25 November 2026** (verified). SA2 and other geographies for 30 June 2026 are scheduled for ADE in the [release callout](https://www.stats.govt.nz/information-releases/subnational-population-estimates-at-30-june-2026/) and the [Stats NZ release calendar](https://www.stats.govt.nz/release-calendar/) | Due in 3 days |
| E1 | `statsnz_regional_gdp` | Year ended March 2025, provisional | Annual | 2026-11-20 | Year ended March 2026, about March 2027 (inferred) | Current |
| E4 | `statsnz_leed` | June 2025 quarter | Quarterly, about 14 months' lag | 2026-11-22 | September 2025 quarter. The June 2025 quarter release was published on [25 August 2026](https://www.stats.govt.nz/information-releases/linked-employer-employee-data-june-2025-quarter/), and no September 2025 quarter page was published on 22 November 2026 | Current, release due |
| E5, E13 | `statsnz_monthly` | September 2026 | Monthly | 2026-11-20 | October 2026. No October release page was found on 22 November 2026 | Current |
| E10 | `mbie_accommodation` | September 2026 | Monthly | 2026-11-20 | October 2026 (not verified, TEIC page has no schedule) | Watch for October |
| E12 | `statsnz_agriculture` | Livestock June 2025. Horticulture June 2024. Timber year ended March 2018 | Annual | 2026-11-22 | June 2026 provisional livestock, about May 2027 (inferred) | Current. The ADE flows have no later Gisborne horticulture or timber values |
| E14 | `ea_residential` | 2025 | Annual | 2026-11-20 | 2026, early 2027 (inferred) | Current |
| G2 | `statsnz_council_finance` | Year ended June 2025 | Annual | 2026-11-20 | Year ended June 2026, about early 2027 (inferred) | Current |
| H3 | `statsnz_vital_statistics` | 2025 | Annual | 2026-11-20 | 2026, about February 2027 (inferred) | Current |
| H4 | `statsnz_census_households` | 2023 Census | Five-yearly | 2026-11-20 | Next census (2028) | Current |
| H5 | `msd_benefits` | September 2026 quarter | Quarterly | 2026-11-21 | December 2026 quarter, about February 2027 (inferred) | Current |
| H7 | `hud_housing` | September 2026 | Monthly | 2026-11-21 | October 2026 (not verified) | Current |
| H8, H9 | `hud_affordability` | June 2026 quarter | Quarterly | 2026-11-20 | September 2026 quarter (not verified) | Watch for September quarter |
| H11 | `mbie_bonds` | September 2026 | Monthly | 2026-11-21 | October 2026 (not verified because tenancy.govt.nz is not reachable from this session) | Watch for October |
| H13 | `healthnz_immunisation` | June 2026 quarter | Quarterly | 2026-11-22 | September 2026 quarter (not verified) | Watch for September quarter |
| H14 | `healthnz_hpv` | June 2026 quarter | Quarterly | 2026-11-22 | September 2026 quarter (not verified) | Watch for September quarter |
| H17 | `moh_nzhs_regional` | Pooled 2017–20 | Irregular | 2026-11-22 | The 2011/12–2023/24 regional release is already published but refuses automated requests | **Stale.** Needs a reviewed manual file (catalogue note) |
| H18 | `healthnz_pho_enrolment` | 1 October 2026 | Quarterly | 2026-11-22 | 1 January 2027 quarter (inferred) | Current |
| H24 | `nzta_cas` | 2026 year to date | Live layer, annual periods | 2026-11-21 | Continuous | Current. 2026 is a partial year |
| H25 | `moj_courts` | Year ended June 2026 | Annual | 2026-11-22 | Year ended June 2027, late 2027 (inferred) | Current |
| H27 | `nzta_mvr` | October 2026 snapshot | Monthly snapshot | 2026-11-22 | November 2026 snapshot | Current. History accumulates only from October 2026 |
| H27 | `nzta_traffic` | 2025 | Annual | 2026-11-22 | 2026, in 2027 (inferred) | Current |
| H28 | `hud_urban_land` | Year ended June 2025 | Annual | 2026-11-22 | Year ended June 2026 (not verified) | Current |
| M4 | `nzqa_secondary` | 2025 | Annual | 2026-11-22 | 2026 results, about April 2027 (inferred) | Current |
| SA2 | `statsnz_sa2` | 2023 Census | Five-yearly | 2026-11-22 | Next census (2028) | Current |
| T1 | `statsnz_river_quality` | 2020–2024 | Irregular | 2026-11-20 | Next Stats NZ indicator update (not scheduled) | Current |
| T6 | `statsnz_emissions` | 2025 | Annual | 2026-11-21 | 2026, in 2027 (inferred) | Current |

## Reviewed releases and snapshots

| Catalogue ID | Source ID | Latest period | Cadence | Last success | Steward / next review | Status |
|---|---|---|---|---|---|---|
| M1 | `moe_attendance` (manual workbook) | Term 3 2026 | Termly | 2026-11-21 | Maintainer. Next review on the Term 4 2026 release, about February 2027 (inferred). No date recorded | Current |
| M3 | `moe_leavers` (manual workbook) | 2025 leavers | Annual | 2026-11-20 | Maintainer. No date recorded | Current |
| M5 | `moe_rolls_ece` (prior participation) | Year ended June 2026 | Quarterly | 2026-11-20 | Maintainer. No date recorded | Current |
| M8 | `moe_rolls_ece` (school rolls) | 1 July 2025 roll | Annual | 2026-11-20 | Maintainer. No date recorded | **Check** whether the July 2026 roll is published (Education Counts blocks automated checks) |
| M8 | `moe_maori_medium` (manual workbook) | 1 July 2025 roll | Annual | 2026-11-22 | Maintainer. No date recorded | **Check** for the July 2026 roll |
| M6 | `moe_school_discipline` (manual workbooks) | 2025 | Annual | 2026-11-20 | Maintainer. No date recorded | Current |
| T2 | `lawa_swimming` (manual extract) | Coastal 22 July 2026. River 26 May 2026 | Annual | 2026-11-22 | Maintainer. LAWA workbook dated 3 November 2026. No next date recorded | Current. Review when LAWA publishes the next workbook |
| H2 | `statsnz_population_projections` (reviewed snapshot) | 2023 base, to 2053 | About every 3 years | No connector | Maintainer. Review on the next base release (not scheduled) | Current |
| R4 | `statsnz_census_language` (reviewed snapshot) | 2023 Census | Five-yearly | No connector | Maintainer. Next census (2028) | Current |
| R5 | `mcert_local_elections` (reviewed snapshot) | 2025 election | Triennial | No connector | Maintainer. Next election (2028) | Current |
| E2, H15, H16, H19, H20, H21, R1, G1 | None | No published data | Various | None | No steward or review date recorded | **Gap.** Each needs a steward, a reviewed file or a reopening condition |

## Findings

- Only H17 is stale against a release that has already been published. Its newer regional release needs a reviewed manual file.
- The 25 November 2026 Stats NZ release adds SA2 estimates for 30 June 2026. Check SA2E then. H1 already holds 30 June 2026 from the 29 October release and needs no code change.
- Until SA2E is refreshed, its provisional 2024 and 2025 values come from the 2025 release. H1 holds the revised 2026 release. The SA2 sum for 2025 is 52,710, compared with 52,300 for the district in H1. Keep both series labelled provisional, and do not mix them in one chart.
- No reviewed release has a recorded next review date. Add a steward and date to each manual catalogue entry, or to `data/manual/README.md`.
- The check intervals (`check_every_days`) allow a scheduled run to pick up each release within seven days, or 30 days for five-yearly and irregular sources.
