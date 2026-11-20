"""M1 – Education Counts regular attendance for Gisborne Region by school term."""
from __future__ import annotations

import io
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from openpyxl import load_workbook

from ..core import MANUAL_DIR, SourceBlocked, fetch, fetch_file, land_raw, log, obs, quarter_bounds

SOURCE_ID = "moe_attendance"
PAGE = "https://www.educationcounts.govt.nz/statistics/attendance"
WORKBOOK = re.compile(r"^regular-attendance-data-(\d{4})-(\d{4})(?:-term(\d)(?:-\d)?)?\.xlsx$", re.I)


def _select_workbooks(locations: list[str]) -> list[str]:
    latest = {}
    for location in locations:
        filename = urlsplit(location).path.rsplit("/", 1)[-1]
        match = WORKBOOK.fullmatch(filename)
        if match:
            first, last, term = (int(part or 0) for part in match.groups())
            candidate = (last, term, location)
            latest[first] = max(candidate, latest.get(first, candidate))
    workbooks = []
    for first, (last, _, location) in sorted(latest.items()):
        if first in (2019, 2022):
            workbooks.append(location)
        if first == 2019 and last >= 2022:
            return workbooks
    if len(workbooks) != 2:
        raise SourceBlocked("The 2019–2021 and 2022 onward attendance workbooks are required")
    return workbooks


def _load() -> list[tuple[bytes, str]]:
    try:
        page = fetch(PAGE, timeout=30, retries=1)
        hrefs = re.findall(r'''\bhref\s*=\s*["']([^"']+)["']''', page.text, re.I)
        urls = _select_workbooks([urljoin(page.url, unescape(href)) for href in hrefs])
        result = []
        for url in urls:
            content, path = fetch_file(SOURCE_ID, url, timeout=60, retries=1)
            result.append((content, str(path)))
        return result
    except RuntimeError as error:
        log.warning("Education Counts downloads unavailable: %s", error)
        directory = MANUAL_DIR / SOURCE_ID
        try:
            local_files = _select_workbooks([str(path) for path in directory.glob("*.xlsx")])
        except SourceBlocked as missing:
            raise SourceBlocked(f"{missing}. Save both in data/manual/{SOURCE_ID}/.") from error
        result = []
        for local_file in local_files:
            path = Path(local_file)
            content = path.read_bytes()
            result.append((content, str(land_raw(SOURCE_ID, path.name, content))))
        return result


def run() -> tuple[list[dict], list[str]]:
    rows, paths = [], []
    for content, path in _load():
        rows.extend(_parse(content))
        paths.append(path)
    return rows, paths


def _parse(content: bytes) -> list[dict]:
    workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    rows = []
    try:
        sheet = workbook["Regional Council"].values
        for row in sheet:
            headers = [" ".join(str(cell).lower().split()) for cell in row]
            if "regional council" in headers:
                break
        else:
            raise ValueError("Missing regional council headers in attendance workbook")
        year_col = headers.index("year")
        term_col = headers.index("term")
        geo_col = headers.index("regional council")
        value_col = headers.index("students attending more than 90% (%)")
        for row in sheet:
            if str(row[geo_col]).strip() != "Gisborne Region":
                continue
            year, term = int(row[year_col]), int(row[term_col])
            if not 1 <= term <= 4:
                raise ValueError(f"Unexpected school term {term}")
            # The workbooks identify terms by number. Use their corresponding quarters for sorting.
            start, end = quarter_bounds(date(year, term * 3, 1))
            value = row[value_col]
            suppressed = isinstance(value, str) and value.strip().lower() in {"s", "c", "suppressed", ".."}
            rate = None if suppressed or value in (None, "") else float(value)
            if rate is not None and not 0 <= rate <= 100:
                raise ValueError(f"Invalid attendance rate for {year} term {term}")
            rows.append(obs(
                source_id=SOURCE_ID, indicator_id="regular_school_attendance", geo_name="Gisborne Region",
                period_start=start, period_end=end, period_type="term", year_basis="school_term",
                value=rate, unit="percent", measure="rate",
                suppression_flag="publisher suppression" if suppressed else "", licence="CC BY 4.0",
                quality_flag="COVID-19 affected comparability" if year in (2020, 2021) else "",
            ))
    finally:
        workbook.close()
    if not rows:
        raise ValueError("Attendance workbook has no Gisborne Region observations")
    return rows
