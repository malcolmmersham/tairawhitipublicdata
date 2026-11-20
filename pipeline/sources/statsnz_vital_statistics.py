"""H3 – annual registered births and deaths for Gisborne Region."""
from __future__ import annotations

import io
import re
from html import unescape
from urllib.parse import urljoin

from openpyxl import load_workbook

from ..core import fetch, fetch_file, obs

SOURCE_ID = "statsnz_vital_statistics"
PAGE = "https://www.stats.govt.nz/topics/births-and-deaths/"


def _page(url: str) -> str:
    return unescape(fetch(url, timeout=30).text).replace(r"\/", "/")


def run() -> tuple[list[dict], list[str]]:
    releases = re.findall(r'(/information-releases/births-and-deaths-year-ended-december-(20\d{2})(?:-[a-z0-9-]+)?/)', _page(PAGE))
    if not releases:
        raise RuntimeError("No annual regional vital statistics release found")
    release, year = max(releases, key=lambda item: item[1])
    match = re.search(rf'(/assets/[^\s"<>]+/births-and-deaths-year-ended-december-{year}\.xlsx)',
                      _page(urljoin(PAGE, release)), re.I)
    if not match:
        raise RuntimeError(f"No December {year} vital statistics workbook found")
    content, path = fetch_file(SOURCE_ID, urljoin(PAGE, match[1]), timeout=60)
    rows = _parse(content)
    if sum(row["period_end"] == f"{year}-12-31" and row["value"] is not None for row in rows) != 2:
        raise RuntimeError(f"Incomplete Gisborne annual vital statistics for {year}")
    return rows, [str(path)]


def _parse(content: bytes) -> list[dict]:
    books = {"Table 2": ("gisborne_live_births", "births"), "Table 3": ("gisborne_registered_deaths", "deaths")}
    workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    rows = []
    try:
        for sheet, (indicator, unit) in books.items():
            cells = workbook[sheet].values
            next(r for r in cells if r[0] == "Regional council area" and "December year" in r)
            years = next(cells)
            regional = next(r for r in cells if str(r[0]).lower() == "gisborne region")
            for year, value in zip(years, regional):
                if not re.fullmatch(r"20\d{2}", str(year)):
                    continue
                suppressed = str(value).strip().lower() in {"s", "c", "..", "suppressed"}
                rows.append(obs(
                    source_id=SOURCE_ID, indicator_id=indicator, geo_name="Gisborne Region",
                    period_start=f"{year}-01-01", period_end=f"{year}-12-31", period_type="year", unit=unit,
                    value=None if suppressed or value in (None, "") else int(value),
                    suppression_flag="publisher suppression" if suppressed else "", licence="CC BY 4.0",
                ))
    finally:
        workbook.close()
    return rows
