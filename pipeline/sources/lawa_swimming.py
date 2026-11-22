"""Routine recreational water samples from the reviewed LAWA and GDC release."""
from __future__ import annotations

import csv
import datetime as dt
import math
import re

from ..core import MANUAL_DIR, SourceBlocked, obs

SOURCE_ID = "lawa_swimming"
PATTERN = re.compile(r"gisborne-swimming-samples-(\d{4}-\d{2}-\d{2})\.csv")
INDICATORS = {
    ("River", "E. coli"): "swimming_freshwater_ecoli",
    ("Coastal", "Enterococci"): "swimming_coastal_enterococci",
}
LIMITS = {"": "", "<": "less_than", ">": "greater_than"}


def run() -> tuple[list[dict], list[str]]:
    files = [
        path for path in (MANUAL_DIR / SOURCE_ID).glob("*.csv")
        if PATTERN.fullmatch(path.name)
    ]
    if not files:
        raise SourceBlocked(f"Save the reviewed LAWA sampling extract in data/manual/{SOURCE_ID}/")
    path = max(files)
    rows = []
    keys = set()
    with path.open(encoding="utf-8-sig", newline="") as contents:
        for sample in csv.DictReader(contents):
            indicator = INDICATORS[(sample["Site Type"], sample["Indicator"])]
            site_id = sample["LAWASiteID"]
            site_name = sample["SiteID"]
            date = dt.date.fromisoformat(sample["SampleDate"]).isoformat()
            key = (indicator, site_id, date)
            if key in keys:
                raise ValueError(f"Multiple routine samples without separate identifiers: {key}")
            keys.add(key)
            if (sample["Region"], sample["Agency"], sample["SampleType"]) != (
                "Gisborne", "Gisborne District Council", "Routine"
            ) or not site_id or not site_name:
                raise ValueError(f"Unexpected sampling scope or missing site for {key}")
            if sample["IndicatorUnit"] != "#/100 mL" or sample["Data Licensing"] != "CC BY 4.0":
                raise ValueError(f"Unexpected unit or reuse licence for {key}")
            value = float(sample["Value"])
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"Invalid sample result for {key}")
            rows.append(obs(
                source_id=SOURCE_ID, indicator_id=indicator, geo_type="site", geo_code=site_id,
                geo_name=site_name, period_start=date, period_end=date, period_type="sample",
                value=value, unit=sample["IndicatorUnit"], measure="concentration",
                quality_flag=LIMITS[sample["Censor_Symbol"]], licence=sample["Data Licensing"],
            ))
    if {row["indicator_id"] for row in rows} != set(INDICATORS.values()):
        raise ValueError("The reviewed extract must contain both river and coastal results")
    return rows, [str(path)]
