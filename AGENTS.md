# Agent contributor guide

Read the [master plan](docs/MASTER_PLAN.md), [README](README.md), and the relevant [GitHub issue](https://github.com/malcolmmersham/tairawhitipublicdata/issues) before starting. The [catalogue](pipeline/catalogue.yaml) is the source of truth for dataset publication status.

## Pick up work

1. Check the latest `main`, open issues and PRs for overlapping efforts. Claim a scoped issue and state the intended deliverable, catalogue or indicator IDs, and dependencies. Use one branch or worktree per publisher group or feature.
2. Verify an official release or download before building a connector. Capture the licence, geography and boundary vintage, dates, unit, denominator, rounding, suppression, and next release or review date. For a benchmark, record its actual geography and the question it helps answer.
3. Use the existing connector and observation contracts in `pipeline/`. Keep source attribution, flags, and period semantics through the CSV and chart. Leave publisher-suppressed values empty. Use reviewed public exports where required and record replacement steps in [the manual drop guide](data/manual/README.md). Credentials, raw sensitive material, and unapproved Trust survey extracts stay outside the repo.
4. Keep the PR small. Use the existing public identifiers and CSV URLs. When source files overlap with another issue, coordinate edits before working on them. The release coordinator rebuilds shared generated outputs after integration.

## Verify and hand off

- Run `python -m unittest discover -s tests`, `python -m pipeline.run <source_id>` for a connector change, and `python -m pipeline.run --build-only` as applicable. Check the first and latest periods and a local value against the publisher. Exercise unavailable values, suppression, and last-good retention as applicable.
- For site changes, serve `site/` locally, check affected views at desktop and mobile widths, and verify both CSV downloads. Record skipped checks and the reason.
- Open a PR linked to the issue and include the base commit, scope and files changed, publisher evidence, checks and results, pending decisions, and rollback or recovery steps if needed. For research-only work, put the same evidence and a proposed catalogue outcome in the issue.
- The nominated release coordinator handles production merges and the Pages workflow. Record the deployed commit, workflow URL, and public verification in the issue.

### Issue body

Use the headings **Question**, **Scope and IDs**, **Publisher evidence**, **Deliverable**, **Dependencies**, and **Acceptance checks**. For a reviewed release, include its steward and next review date. When a candidate is held, record the condition that would reopen it.
