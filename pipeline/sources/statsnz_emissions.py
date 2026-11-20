"""T6 – Stats NZ annual regional greenhouse gas emissions."""
from __future__ import annotations

import csv
import io
import re
from html import unescape
from urllib.parse import urljoin

from ..core import fetch, fetch_file, obs

SOURCE_ID = "statsnz_emissions"
PAGE = "https://www.stats.govt.nz/large-datasets/csv-files-for-download/"
ASSET = re.compile(
    r'(/assets/[^\s"<>]+/greenhouse-gas-emissions-by-region-industry-and-household-year-ended-(\d{4})\.csv)',
    re.IGNORECASE,
)


def run() -> tuple[list[dict], list[str]]:
    page = unescape(fetch(PAGE, timeout=30).text).replace(r"\/", "/")
    downloads = ASSET.findall(page)
    if not downloads:
        raise RuntimeError("Stats NZ did not list a regional emissions CSV")
    url, release_year = max(downloads, key=lambda download: download[1])
    content, path = fetch_file(SOURCE_ID, urljoin(PAGE, url), timeout=60)
    rows = _parse(content)
    if not any(row["period_end"] == f"{release_year}-12-31" and row["value"] is not None for row in rows):
        raise RuntimeError(f"No Gisborne total emissions value for release year {release_year}")
    return rows, [str(path)]


def _parse(content: bytes) -> list[dict]:
    rows = []
    for row in csv.DictReader(io.StringIO(content.decode("utf-8-sig"))):
        if (row["region"], row["anzsic_descriptor"], row["anzsic_descriptor2"], row["category"],
                row["gas"], row["units"], row["magnitude"]) != (
                "Gisborne", "Total", "Total", "Total", "Carbon dioxide equivalents", "Kilotonnes",
                "Carbon dioxide equivalents"):
            continue
        year = int(row["year"])
        value = row["data_val"].strip()
        suppressed = value in {"C", "S", ".."}
        rows.append(obs(
            source_id=SOURCE_ID, indicator_id="regional_ghg_emissions", geo_name="Gisborne Region",
            period_start=f"{year}-01-01", period_end=f"{year}-12-31", period_type="year",
            value=None if suppressed or not value else float(value), unit="kt CO₂-e", measure="total",
            suppression_flag="publisher suppression" if suppressed else "", licence="CC BY 4.0",
        ))
    return rows
