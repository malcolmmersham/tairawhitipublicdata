"""M3 – Education Counts regional school leavers attaining NCEA Level 2 or above."""
from __future__ import annotations

import io
import re
from html import unescape
from urllib.parse import urljoin

from openpyxl import load_workbook

from ..core import MANUAL_DIR, SourceBlocked, fetch, fetch_file, log, obs

SOURCE_ID = "moe_leavers"
PAGE = "https://www.educationcounts.govt.nz/statistics/school-leavers"


def run() -> tuple[list[dict], list[str]]:
    try:
        page = fetch(PAGE, timeout=30, retries=1)
        match = re.search(r'\bhref=["\']([^"\']*/Time-series-School-leavers-NCEA-Level-2-\d{4}\.xlsx)["\']', page.text, re.I)
        if not match:
            raise RuntimeError("Education Counts did not list the Level 2 time-series workbook")
        content, path = fetch_file(SOURCE_ID, urljoin(page.url, unescape(match[1])), timeout=60, retries=1)
    except RuntimeError as error:
        files = sorted((MANUAL_DIR / SOURCE_ID).glob("Time-series-School-leavers-NCEA-Level-2-*.xlsx"))
        if not files:
            raise SourceBlocked(f"No leaver workbook available. Save it in data/manual/{SOURCE_ID}/.") from error
        log.warning("Using the reviewed school leaver workbook: %s", error)
        path = files[-1]
        content = path.read_bytes()
    return _parse(content), [str(path)]


def _parse(content: bytes) -> list[dict]:
    workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    try:
        sheet = next(s for s in workbook if s.title.endswith("Regional Council"))
        data = sheet.values
        years = next(r for r in data if r[1] == "Regional Council")
        fields = next(data)
        regional = next(r for r in data if r[1] == "Gisborne Region")
        rows = []
        for index, year in enumerate(years[:-1]):
            if not isinstance(year, int) or fields[index+1] != "Percent":
                continue
            value = regional[index+1]
            suppressed = str(value).strip().lower() in {"s", "c", "x", "suppressed", ".."}
            rows.append(obs(
                source_id=SOURCE_ID, indicator_id="school_leavers_level_2", geo_name="Gisborne Region",
                period_start=f"{year}-01-01", period_end=f"{year}-12-31", period_type="year",
                value=None if suppressed or value in (None, "") else float(value), unit="percent",
                measure="share", suppression_flag="publisher suppression" if suppressed else "",
                licence="CC BY 4.0",
            ))
        if not rows:
            raise RuntimeError("No Gisborne school leaver percentages in the workbook")
        return rows
    finally:
        workbook.close()
