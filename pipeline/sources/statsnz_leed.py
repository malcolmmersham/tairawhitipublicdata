"""E4 – Stats NZ Linked Employer-Employee Data, quarterly measures by region (ADE LEED_Q1W_005).

Dimensions are QUARTER . REGION . MEASURE. Region R1E is Gisborne in the regional council
classification (R2E repeats it in a grouped list with independent rounding; R3E merges it with
Hawke's Bay). Quarter codes are YYYYMM for the quarter's last month. Stats NZ rounds the counts
and earnings in this table.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

from ..core import obs, quarter_bounds
from .statsnz_ade import _download

SOURCE_ID = "statsnz_leed"
LICENCE = "CC BY 4.0"
FLOW, REGION = "LEED_Q1W_005", "R1E"
# R3Z ("Total Region") is the New Zealand total in the same table, used as a dashed national
# benchmark for the median and rate measures only.
NATIONAL, NATIONAL_MEASURES = "R3Z", {"MEDIAN_EARN", "WORKER_TURNOVER_RATE"}
GEOS = {REGION: ("Gisborne", "region", "05", "Gisborne Region"),
        NATIONAL: ("Total Region", "national", "NZ", "Aotearoa New Zealand")}
MEASURES = {
    "FILLED_JOBS": ("leed_filled_jobs", "jobs", "count"),
    "MEDIAN_EARN": ("leed_median_quarterly_earnings", "NZD", "median"),
    "WORKER_TURNOVER_RATE": ("leed_worker_turnover_rate", "percent", "rate"),
}


def run() -> tuple[list[dict], list[str]]:
    df = _download(FLOW, f".{REGION}+{NATIONAL}.{'+'.join(MEASURES)}", SOURCE_ID)
    rows = []
    for _, r in df.iterrows():
        code, measure_code = r[f"REGION_{FLOW}"], r[f"MEASURE_{FLOW}"]
        if code not in GEOS or r["Region"] != GEOS[code][0] or measure_code not in MEASURES:
            raise ValueError(f"{FLOW}: unexpected row {code}/{measure_code}")
        if code == NATIONAL and measure_code not in NATIONAL_MEASURES:
            continue
        _, geo_type, geo_code, geo_name = GEOS[code]
        if pd.isna(r["OBS_VALUE"]):
            continue
        indicator, unit, measure = MEASURES[measure_code]
        quarter = str(r[f"QUARTER_{FLOW}"])
        start, end = quarter_bounds(dt.date(int(quarter[:4]), int(quarter[4:]), 1))
        rows.append(obs(
            indicator_id=indicator, geo_type=geo_type, geo_code=geo_code, geo_name=geo_name,
            period_start=start, period_end=end, period_type="quarter",
            value=float(r["OBS_VALUE"]), unit=unit, measure=measure,
            quality_flag="" if measure == "rate" else "rounded by Stats NZ",
            source_id=SOURCE_ID, licence=LICENCE,
        ))
    expected = {(MEASURES[m][0], "05") for m in MEASURES} | {(MEASURES[m][0], "NZ") for m in NATIONAL_MEASURES}
    missing = expected - {(r["indicator_id"], r["geo_code"]) for r in rows}
    if missing:
        raise RuntimeError(f"{FLOW}: no rows for {sorted(missing)} – check the SDMX key")
    return rows, []
