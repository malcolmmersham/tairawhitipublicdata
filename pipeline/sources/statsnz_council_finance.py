"""G2 – Stats NZ annual financial statistics for Gisborne District Council."""
from __future__ import annotations

import csv
import io
import re
from html import unescape
from urllib.parse import urljoin
from zipfile import ZipFile

from ..core import fetch, fetch_file, obs

SOURCE_ID = "statsnz_council_finance"
PAGE = "https://www.stats.govt.nz/large-datasets/csv-files-for-download/"
ASSET = re.compile(r'(/assets/[^\s"<>]+/local-authority-financial-statistics-year-ended-june-(20\d{2})\.zip)', re.I)
SERIES = {"LAFA.S020C07": ("gisborne_council_operating_income", "Total operating income"),
          "LAFA.S020C21": ("gisborne_council_operating_expenditure", "Total operating expenditure")}


def run() -> tuple[list[dict], list[str]]:
    page = unescape(fetch(PAGE, timeout=30).text).replace(r"\/", "/")
    downloads = ASSET.findall(page)
    if not downloads:
        raise RuntimeError("Stats NZ did not list a local authority finance CSV archive")
    asset, latest_year = max(downloads, key=lambda item: item[1])
    content, path = fetch_file(SOURCE_ID, urljoin(PAGE, asset), timeout=60)
    with ZipFile(io.BytesIO(content)) as archive:
        member = next(filename for filename in archive.namelist() if filename.endswith("-tables-csv.csv"))
        with archive.open(member) as raw:
            rows = _parse(io.TextIOWrapper(raw, encoding="utf-8-sig"))
    latest = {r["indicator_id"] for r in rows if r["period_end"] == f"{latest_year}-06-30" and r["value"] is not None}
    if latest != {indicator for indicator, _ in SERIES.values()}:
        raise RuntimeError(f"Incomplete council finances for June {latest_year}")
    return rows, [str(path)]


def _parse(raw) -> list[dict]:
    rows = []
    for r in csv.DictReader(raw):
        if r["Series_reference"] not in SERIES:
            continue
        indicator, label = SERIES[r["Series_reference"]]
        if (r["Series_title_1"], r["Series_title_2"], r["UNITS"].lower(), r["MAGNTUDE"]) != (
                "Gisborne District Council", label, "dollars", "3"):
            raise ValueError("Council finance series scope or unit changed")
        year, month = r["Period"].split(".")
        if month != "06":
            raise ValueError(f"Unexpected council finance period {r['Period']}")
        raw_value = r["Data_value"].strip()
        suppressed = raw_value.lower() in {"s", "c", "..", "suppressed"}
        rows.append(obs(
            source_id=SOURCE_ID, indicator_id=indicator, geo_type="ta", geo_code="028", geo_name="Gisborne District Council",
            period_start=f"{int(year)-1}-07-01", period_end=f"{year}-06-30", period_type="year", year_basis="june",
            value=None if suppressed or not raw_value else float(raw_value) * 1000, unit="NZD", measure="current prices",
            suppression_flag="publisher suppression" if suppressed else "", licence="CC BY 4.0",
        ))
    return rows
