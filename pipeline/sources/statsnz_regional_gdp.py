"""E1 – Stats NZ regional GDP release, year ended March."""
from __future__ import annotations

import csv
import io
import re
from html import unescape
from urllib.parse import urljoin

from ..core import fetch, fetch_file, obs

SOURCE_ID = "statsnz_regional_gdp"
PAGE = "https://www.stats.govt.nz/large-datasets/csv-files-for-download/"
ASSET = re.compile(r'(/assets/[^\s"<>]+/regional-gross-domestic-product-year-ended-march-(\d{4})\.csv)', re.I)
SERIES = {
    "RNAA.SG01NAC34B0105ZZB": ("gisborne_nominal_gdp", 6, "NZD million"),
    "RNAA.SG09NAC34B0105": ("gisborne_nominal_gdp_per_person", 0, "NZD per person"),
}


def run() -> tuple[list[dict], list[str]]:
    page = unescape(fetch(PAGE, timeout=30).text).replace(r"\/", "/")
    downloads = ASSET.findall(page)
    if not downloads:
        raise RuntimeError("Stats NZ did not list a regional GDP CSV")
    asset, latest_year = max(downloads, key=lambda item: item[1])
    content, path = fetch_file(SOURCE_ID, urljoin(PAGE, asset), timeout=60)
    rows = _parse(content)
    latest = {row["indicator_id"] for row in rows if row["period_end"] == f"{latest_year}-03-31"}
    if latest != {row[0] for row in SERIES.values()}:
        raise RuntimeError(f"Incomplete Gisborne GDP data for {latest_year}")
    return rows, [str(path)]


def _parse(content: bytes) -> list[dict]:
    rows = []
    for r in csv.DictReader(io.StringIO(content.decode("utf-8-sig"))):
        if r["Series_reference"] not in SERIES:
            continue
        indicator, magnitude, unit = SERIES[r["Series_reference"]]
        if (r["Series_title_2"], r["UNITS"], int(r["MAGNTUDE"])) != ("Gisborne", "Dollars", magnitude):
            raise ValueError("Gisborne GDP series scope or units changed")
        year, month = r["Period"].split(".")
        if month != "03":
            raise ValueError(f"Unexpected regional GDP period {r['Period']}")
        value = r["Data_value"].strip()
        suppressed = r["STATUS"].upper() in {"SUPPRESSED", "CONFIDENTIAL"}
        rows.append(obs(
            source_id=SOURCE_ID, indicator_id=indicator, geo_name="Gisborne Region",
            period_start=f"{int(year)-1}-04-01", period_end=f"{year}-03-31", period_type="year",
            year_basis="march", value=None if suppressed or not value else float(value), unit=unit,
            measure="current prices", suppression_flag="publisher suppression" if suppressed else "",
            quality_flag=r["STATUS"].lower() if r["STATUS"] != "FINAL" and not suppressed else "",
            licence="CC BY 4.0",
        ))
    return rows
