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
MEASURES = {
    "FILLED_JOBS": ("leed_filled_jobs", "jobs", "count"),
    "MEDIAN_EARN": ("leed_median_quarterly_earnings", "NZD", "median"),
    "WORKER_TURNOVER_RATE": ("leed_worker_turnover_rate", "percent", "rate"),
}


def run() -> tuple[list[dict], list[str]]:
    df = _download(FLOW, f".{REGION}.{'+'.join(MEASURES)}", SOURCE_ID)
    rows = []
    for _, r in df.iterrows():
        if r[f"REGION_{FLOW}"] != REGION or r["Region"] != "Gisborne" or r[f"MEASURE_{FLOW}"] not in MEASURES:
            raise ValueError(f"{FLOW}: unexpected row {r[f'REGION_{FLOW}']}/{r[f'MEASURE_{FLOW}']}")
        if pd.isna(r["OBS_VALUE"]):
            continue
        indicator, unit, measure = MEASURES[r[f"MEASURE_{FLOW}"]]
        code = str(r[f"QUARTER_{FLOW}"])
        start, end = quarter_bounds(dt.date(int(code[:4]), int(code[4:]), 1))
        rows.append(obs(
            indicator_id=indicator, geo_name="Gisborne Region",
            period_start=start, period_end=end, period_type="quarter",
            value=float(r["OBS_VALUE"]), unit=unit, measure=measure,
            quality_flag="" if measure == "rate" else "rounded by Stats NZ",
            source_id=SOURCE_ID, licence=LICENCE,
        ))
    missing = {m[0] for m in MEASURES.values()} - {r["indicator_id"] for r in rows}
    if missing:
        raise RuntimeError(f"{FLOW}: no Gisborne rows for {sorted(missing)} – check the SDMX key")
    return rows, []
