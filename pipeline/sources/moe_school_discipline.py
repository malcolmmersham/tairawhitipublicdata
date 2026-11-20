"""M6 – reviewed Education Counts workbooks with school disciplinary case counts."""
from __future__ import annotations

import re

from openpyxl import load_workbook

from ..core import MANUAL_DIR, SourceBlocked, obs

SOURCE_ID = "moe_school_discipline"
MEASURES = {"Stand-downs": "gisborne_stand_down_cases", "Suspension": "gisborne_suspension_cases",
            "Exclusion": "gisborne_exclusion_cases", "Expulsion": "gisborne_expulsion_cases"}


def run() -> tuple[list[dict], list[str]]:
    rows, files = [], []
    for prefix, indicator in MEASURES.items():
        paths = sorted((MANUAL_DIR / SOURCE_ID).glob(f"{prefix}-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9].xlsx"))
        if not paths:
            raise SourceBlocked(f"Save the reviewed {prefix} workbook in data/manual/{SOURCE_ID}/")
        path = max(paths, key=lambda candidate: int(candidate.stem.rsplit("-", 1)[-1]))
        batch = _parse(path, indicator)
        expected_year = path.stem.rsplit("-", 1)[-1]
        if not any(row["period_end"] == f"{expected_year}-12-31" for row in batch):
            raise RuntimeError(f"Missing Gisborne District {prefix} case count for {expected_year}")
        rows.extend(batch)
        files.append(str(path))
    return rows, files


def _parse(path, indicator: str) -> list[dict]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = next(sheet for sheet in workbook if sheet.title.startswith("6b. Territorial Authority"))
        data = sheet.values
        years = next(row for row in data if any(re.fullmatch(r"20\d{2}", str(v)) for v in row))
        local = next(row for row in data if row[0] == "Gisborne District")
        rows = []
        for year, value in zip(years, local):
            if not re.fullmatch(r"20\d{2}", str(year)):
                continue
            suppressed = str(value).strip().lower() in {"x", "s", "c", "..", "suppressed"}
            rows.append(obs(
                source_id=SOURCE_ID, indicator_id=indicator, geo_type="ta", geo_code="028", geo_name="Gisborne District",
                period_start=f"{year}-01-01", period_end=f"{year}-12-31", period_type="year", unit="cases",
                value=None if suppressed or value in (None, "") else int(value),
                suppression_flag="publisher suppression" if suppressed else "", licence="CC BY 4.0",
            ))
        return rows
    finally:
        workbook.close()
