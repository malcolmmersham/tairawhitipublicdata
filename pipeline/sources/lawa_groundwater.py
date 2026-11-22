"""Groundwater quality samples from the reviewed LAWA and GDC release."""
from __future__ import annotations

import csv
import datetime as dt
import math
import re

from ..core import MANUAL_DIR, SourceBlocked, obs

SOURCE_ID = "lawa_groundwater"
PATTERN = re.compile(r"gisborne-groundwater-samples-(\d{4}-\d{2}-\d{2})\.csv")
# LAWA indicator -> (indicator ID, LAWA standardised unit)
INDICATORS = {
    "Chloride": ("groundwater_chloride", "g/m3"),
    "Electrical conductivity/salinity": ("groundwater_conductivity", "µS/cm"),
    "Dissolved reactive phosphorus": ("groundwater_drp", "g/m3"),
    "Nitrate nitrogen": ("groundwater_nitrate_n", "g/m3"),
    "E.coli": ("groundwater_ecoli", "#/100 mL"),
}
LIMITS = {"NA": "", "<": "less_than", ">": "greater_than"}


def run() -> tuple[list[dict], list[str]]:
    files = [
        path for path in (MANUAL_DIR / SOURCE_ID).glob("*.csv")
        if PATTERN.fullmatch(path.name)
    ]
    if not files:
        raise SourceBlocked(f"Save the reviewed LAWA groundwater extract in data/manual/{SOURCE_ID}/")
    path = max(files)
    rows = []
    keys = set()
    with path.open(encoding="utf-8-sig", newline="") as contents:
        for sample in csv.DictReader(contents):
            indicator, unit = INDICATORS[sample["Indicator"]]
            site_id = sample["LAWASiteID"]
            bore = sample["BoreID"]
            # Agency timestamps may be NZST, NZDT or UTC, so keep them as published.
            when = dt.datetime.fromisoformat(sample["SampleDateTime"]).isoformat(timespec="minutes")
            key = (indicator, site_id, when)
            if key in keys:
                raise ValueError(f"Multiple samples with the same site, indicator and time: {key}")
            keys.add(key)
            if (sample["Region"], sample["Agency"]) != ("Gisborne", "Gisborne District Council") \
                    or not site_id or not bore:
                raise ValueError(f"Unexpected sampling scope or missing site for {key}")
            if sample["DataLicensing"] != "CC BY 4.0":
                raise ValueError(f"Row is not licensed under CC BY 4.0: {key}")
            if sample["Units"] != unit:
                raise ValueError(f"Unexpected unit {sample['Units']!r} for {key}")
            symbol = sample["Censor_Symbol"]
            text = sample["Value"].strip()
            prefix = text[:1] if text[:1] in ("<", ">") else "NA"
            if symbol not in LIMITS or symbol != prefix:
                raise ValueError(f"Censor symbol does not match the result for {key}")
            value = float(text if symbol == "NA" else text[1:])
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"Invalid sample result for {key}")
            zone = sample["GroundwaterQualityZone"]
            rows.append(obs(
                source_id=SOURCE_ID, indicator_id=indicator, geo_type="site", geo_code=site_id,
                geo_name=f"{bore} · {zone}" if zone not in ("", "Unstated") else bore,
                period_start=when, period_end=when, period_type="sample",
                value=value, unit=unit, measure="concentration",
                quality_flag=LIMITS[symbol], licence=sample["DataLicensing"],
            ))
    found = {row["indicator_id"] for row in rows}
    expected = {indicator for indicator, _ in INDICATORS.values()}
    if found != expected:
        raise ValueError(f"The reviewed extract is missing indicators: {sorted(expected - found)}")
    return rows, [str(path)]
