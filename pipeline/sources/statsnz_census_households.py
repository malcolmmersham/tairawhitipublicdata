"""H4 – published census counts for families and households in Gisborne Region."""
from __future__ import annotations

import json
import re

from ..core import fetch_file, obs

SOURCE_ID = "statsnz_census_households"
PAGE = "https://tools.summaries.stats.govt.nz/places/rc/gisborne-region"
SERIES = {"F": ("gisborne_census_families", "families"), "H": ("gisborne_census_households", "households")}


def run() -> tuple[list[dict], list[str]]:
    content, path = fetch_file(SOURCE_ID, PAGE, timeout=30)
    rows = _parse(content)
    return rows, [str(path)]


def _parse(content: bytes) -> list[dict]:
    matched = re.search(rb'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', content, re.S)
    if not matched:
        raise RuntimeError("No data in the Stats NZ place summary")
    topics = json.loads(matched[1])["props"]["pageProps"]["place"]
    published = next(section["numbers_data"]["numbers"]
                     for topic in topics if topic["classification_descriptor"] == "Gisborne Region"
                     for concept in topic["concepts"] for section in concept["sections"]
                     if section["section_title"] == "Number of families and households")
    rows = []
    for record in published:
        if record["variable1_code"] not in SERIES:
            continue
        indicator, unit = SERIES[record["variable1_code"]]
        year = int(record["period"])
        suppressed = bool(record["confidentiality_indicator"])
        rows.append(obs(
            source_id=SOURCE_ID, indicator_id=indicator, geo_name="Gisborne Region",
            period_start=f"{year}-01-01", period_end=f"{year}-12-31", period_type="year",
            value=None if suppressed else record["value"], unit=unit,
            suppression_flag="publisher suppression" if suppressed else "", licence="CC BY 4.0",
        ))
    if {row["indicator_id"] for row in rows} != {indicator for indicator, _ in SERIES.values()}:
        raise RuntimeError("Incomplete Gisborne census household counts")
    return rows
