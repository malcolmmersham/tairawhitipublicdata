# Tairāwhiti Public Data Dashboard master plan

Build a regularly refreshed public data library that helps people find, compare, and reuse data about Tairāwhiti. The audience includes residents, local organisations, iwi and hapū, analysts, and people making decisions about the region. Use free GitHub Pages hosting, GitHub Actions, and the existing Python pipeline.

Start with **data discovery and syncing**, then improve **provenance and reuse**, then expand into **new collections and decision-support views**. Publish verified source groups as they are ready. [Dashboard](https://malcolmmersham.github.io/tairawhitipublicdata/) · [Data library](https://malcolmmersham.github.io/tairawhitipublicdata/#library) · [Workstream issues](https://github.com/malcolmmersham/tairawhitipublicdata/issues)

## 1. Discover, publish and keep the data current

Review every existing catalogue entry and sweep the official publishers relevant to each domain. Include reusable Tairāwhiti data and wider regional or national benchmarks that answer a stated comparison question. Label the real geography for every value. Pair measures only when their definitions, units, denominators and periods align.

| Workstream | First assignments |
| --- | --- |
| [Ōhanga · Economy](https://github.com/malcolmmersham/tairawhitipublicdata/issues/1) | Verify the agriculture and LEED connectors on the live site. Investigate retail and tourism spend, modelled district GDP, and usable economic benchmarks. |
| [Hapori · Communities](https://github.com/malcolmmersham/tairawhitipublicdata/issues/2) | Review housing, transport, Health NZ enrolment and vaccination, health survey, and the remaining health and justice catalogue entries. |
| [Mātauranga · Learning](https://github.com/malcolmmersham/tairawhitipublicdata/issues/3) | Verify the NZQA attainment connector on the live site. Check tertiary participation and the reviewed Education Counts releases. |
| [Taiao · Environment](https://github.com/malcolmmersham/tairawhitipublicdata/issues/4) | Check LAWA groundwater and lakes, Council hydrology, and climate observations. Verify licensed monitoring exports, sites, dates, units, and reporting limits. |
| [Tūhono · Connection](https://github.com/malcolmmersham/tairawhitipublicdata/issues/5) | Check earlier comparable turnout and other public civic measures. Require a Trust-approved aggregate release for survey data. |
| [Tūtangata · Identity and culture](https://github.com/malcolmmersham/tairawhitipublicdata/issues/6) | Assess census te reo Māori comparability, find public culture indicators, and route iwi-level proposals through the appropriate stewardship review. |
| [Places and refresh operations](https://github.com/malcolmmersham/tairawhitipublicdata/issues/7) | Assess annual SA2 population, business counts, and deprivation against each series' boundary vintage. Audit expected publication cadence and latest data for each active source. |

For each candidate, capture the official release and download links, licence, geography and vintage, population, period, units, denominator, quality and suppression rules, available history, and expected publication cadence. Record one outcome and its evidence in the [dataset catalogue](../pipeline/catalogue.yaml).

- **Automated** when a repeatable publisher feed works on the hosted runner. Reuse the existing connector and validation patterns where possible.
- **Reviewed release** when a reusable official file needs a manual step. Record the steward, next review date, release or file identifier, and replacement instructions. Publish eligible releases through the existing manual drop process.
- **Reference or deferred** when only a link is useful or the source needs a specific trigger to reopen. Record the exact blocker, evidence, and what would change the decision. Keep blank values, publisher rounding, and suppression intact.

Use the six domain sweeps and inventory of live and reviewed sources to define the first-pass scope. Open a separate implementation issue for each verified publisher group. The first stage is complete when each candidate in that inventory has a recorded decision, every eligible series is published with a tested refresh route, and all reviewed releases have a steward and next check. Track the latest data period separately from the latest successful refresh.

## 2. Make the published data easier to reuse

- Give every published series searchable metadata covering its definition, publisher, licence, geography and boundary vintage, dates, refresh status, and relevant caveats. Add a direct route from each chart to the metadata.
- Add indicator- and place-filtered observations CSV downloads. Keep the existing observations and definitions CSV URLs and identifiers stable. Document units, denominators, revisions, and the meaning of missing and suppressed values.
- Test the exports with an external consumer such as Zoho Analytics. Reproduce a regional indicator, an SA2 profile value, and a water sample from exports and metadata. Confirm the import can be refreshed without manual reshaping and preserves dates, geographies, revisions and flags.

## 3. Expand coverage and decision support

Use gaps from the first sweep and feedback from dashboard users to prioritise new collections, deeper historical coverage, and comparison views. Each proposal should name its audience, decision, source, geographic fit, and acceptance check. Review any additional infrastructure against a documented requirement that the static site and scheduled pipeline cannot meet.

## Collaboration and ownership

The roadmap sets priorities. The catalogue records publication status. GitHub Issues hold workstream owners, source evidence, dependencies, and PRs. Contributors can claim an issue through an issue comment before editing. The maintainer nominates one release coordinator for each production release. Review open blockers and upcoming publisher releases weekly.

Research contributors verify sources and record outcomes. Implementation contributors use a current branch and open focused PRs. Reviewers independently check publisher values, geography, suppression and UI behaviour where possible. The coordinator resolves overlapping changes, rebuilds from the integrated branch, merges, publishes, and records the deployed commit and Actions run. The [agent instructions](../AGENTS.md) contain the handoff checklist.

## Release and data governance

Use the repo's [operator instructions](../README.md#operating-the-dashboard) and [Refresh data workflow](https://github.com/malcolmmersham/tairawhitipublicdata/actions/workflows/refresh.yml). The workflow validates the build, retains last-good data for a failing source, and reports connector failures after publication. Keep all publisher attribution and flags. Follow Te Mana Raraunga and CARE principles, agree iwi-level uses with the relevant stewards, and keep Trust survey inputs and unapproved extracts outside the repository.
