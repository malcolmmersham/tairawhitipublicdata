"""E10 – MBIE Accommodation Data Programme regional council results."""
from __future__ import annotations

import csv
import io
from datetime import datetime

from ..core import fetch_file, month_bounds, obs

SOURCE_ID = "mbie_accommodation"
DATA = "https://teic.mbie.govt.nz/assets/adp/ADP_All_Measures.csv"
MEASURES = {"Total guest nights": ("gisborne_guest_nights", "guest nights"),
            "Number of active establishments": ("gisborne_active_accommodation", "establishments")}


def run() -> tuple[list[dict], list[str]]:
    content, path = fetch_file(SOURCE_ID, DATA, timeout=90)
    return _parse(content), [str(path)]


def _parse(content: bytes) -> list[dict]:
    rows = []
    for r in csv.DictReader(io.StringIO(content.decode("utf-8-sig"))):
        if (r["Area type"], r["Area"], r["Property"]) != ("RC", "Gisborne Region", "Total") or r["Measure"] not in MEASURES:
            continue
        indicator, unit = MEASURES[r["Measure"]]
        start, end = month_bounds(datetime.strptime(r["Month"], "%b-%y").date())
        value = r["Value"].strip()
        suppressed = value.lower() in {"s", "c", "..", "suppressed"}
        rows.append(obs(
            source_id=SOURCE_ID, indicator_id=indicator, geo_name="Gisborne Region",
            period_start=start, period_end=end, period_type="month", unit=unit,
            value=None if suppressed or not value else float(value),
            suppression_flag="publisher suppression" if suppressed else "", licence="CC BY 4.0",
        ))
    if {row["indicator_id"] for row in rows} != {indicator for indicator, _ in MEASURES.values()}:
        raise RuntimeError("Incomplete Gisborne accommodation measures")
    return rows
