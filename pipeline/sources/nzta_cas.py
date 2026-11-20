"""H24 – NZTA Crash Analysis System (CAS), aggregated server-side by year.

The public CAS layer has crash year (and financial year) but no month field, so the
dashboard series is annual. CAS is "live": past years can change, and non-injury
crashes can be reported up to seven months late.
"""
from __future__ import annotations

import datetime as dt
import json

from ..core import fetch, land_raw, obs

SOURCE_ID = "nzta_cas"
LICENCE = "CC BY 4.0"
LAYER = "https://services.arcgis.com/CXBb7LAjgIIdcsPt/arcgis/rest/services/CAS_Data_Public/FeatureServer/0/query"
WHERE = "region='Gisborne Region'"


def _stats(group: str, stats: list[tuple[str, str, str]]) -> list[dict]:
    params = {
        "where": WHERE, "groupByFieldsForStatistics": group, "f": "json",
        "outStatistics": json.dumps([
            {"statisticType": t, "onStatisticField": f, "outStatisticFieldName": n} for t, f, n in stats]),
    }
    r = fetch(LAYER, params=params)
    data = r.json()
    if "error" in data:
        raise RuntimeError(data["error"])
    land_raw(SOURCE_ID, f"stats-{group.replace(',', '-')}.json", r.content)
    return [f["attributes"] for f in data["features"]]


def run() -> tuple[list[dict], list[str]]:
    by_sev = _stats("crashYear,crashSeverity", [("count", "OBJECTID", "n")])
    by_year = _stats("crashYear", [("sum", "fatalCount", "deaths"),
                                   ("sum", "seriousInjuryCount", "serious"),
                                   ("sum", "minorInjuryCount", "minor"),
                                   ("count", "OBJECTID", "crashes")])
    this_year = dt.date.today().year
    rows = []

    def add(ind, year, value, unit):
        partial = year >= this_year
        rows.append(obs(
            indicator_id=ind, period_start=f"{year}-01-01", period_end=f"{year}-12-31",
            period_type="year", value=value, unit=unit, source_id=SOURCE_ID, licence=LICENCE,
            quality_flag="partial year; CAS is live and late reports are added" if partial else "",
        ))

    sev = {}
    for a in by_sev:
        sev.setdefault(a["crashYear"], {})[a["crashSeverity"]] = a["n"]
    for y, d in sev.items():
        if y is None:
            continue
        add("cas_fatal_serious_crashes", y, d.get("Fatal Crash", 0) + d.get("Serious Crash", 0), "crashes")
        add("cas_injury_crashes", y, d.get("Fatal Crash", 0) + d.get("Serious Crash", 0) + d.get("Minor Crash", 0), "crashes")
    for a in by_year:
        y = a["crashYear"]
        if y is None:
            continue
        add("cas_deaths", y, a["deaths"] or 0, "people")
        add("cas_dsi", y, (a["deaths"] or 0) + (a["serious"] or 0), "people")
    return rows, []
