"""Stats NZ Aotearoa Data Explorer (ADE) SDMX API – H1 population, E3 business demography.

Needs a free subscription key (Stats NZ API Portal), read from STATSNZ_API_KEY and
sent as the Ocp-Apim-Subscription-Key header. Queries ask for the whole dataflow in
`csvfilewithlabels` form and filter locally, so they do not depend on dimension
codes that Stats NZ may renumber.
"""
from __future__ import annotations

import io
import re

import pandas as pd

from ..core import env, fetch, land_raw, log, obs

SOURCE_ID = "statsnz_ade"
LICENCE = "CC BY 4.0"
API = "https://api.data.stats.govt.nz/rest/data/STATSNZ,{flow},1.0/all"

# Each query: dataflow, geography match, and how to pick other dimensions.
#  pick: {dimension-label regex: value regex}; any dimension not named must resolve
#  to a single "total"-like value, otherwise its values become separate indicators via
#  `split` (dimension-label regex -> {value regex: indicator_id}).
QUERIES = [
    {
        "flow": "POPES_SUB_011", "geo": r"Gisborne", "start": "1996",
        "split": {r"measure|indicator|variable|^$": {r".*": "pop_estimate"}},
        "unit": "people", "year_basis": "june", "geo_type": "ta",
    },
    {
        "flow": "BDS_BDS_001", "geo": r"Gisborne", "start": "2000",
        "split": {r"measure|variable|indicator": {
            r"geographic unit": "bds_geographic_units",
            r"employee": "bds_employee_count"}},
        "unit": None, "year_basis": "february", "geo_type": "ta",
    },
]


def _label(v) -> str:
    s = str(v)
    return s.split(": ", 1)[1] if ": " in s else s


def _download(flow: str, start: str) -> pd.DataFrame:
    key = env("STATSNZ_API_KEY") or "proxy-injected"
    r = fetch(API.format(flow=flow), headers={"Ocp-Apim-Subscription-Key": key,
                                             "Accept": "application/vnd.sdmx.data+csv"},
              params={"format": "csvfilewithlabels", "dimensionAtObservation": "AllDimensions",
                      "startPeriod": start}, timeout=300)
    land_raw(SOURCE_ID, f"{flow}.csv", r.content)
    return pd.read_csv(io.BytesIO(r.content), dtype=str)


def _is_total(label: str) -> bool:
    return bool(re.search(r"\btotal\b|all industries|all ages|both sexes", label, re.I))


def _query(q: dict) -> list[dict]:
    df = _download(q["flow"], q["start"])
    skip = re.compile(r"^(STRUCTURE|STRUCTURE_ID|STRUCTURE_NAME|ACTION|TIME_PERIOD|OBS_VALUE|OBS_STATUS|"
                      r"UNIT_MEASURE|UNIT_MULT|OBS_COMMENT|DECIMALS|Time|Observation.*|Unit.*|Status.*)$", re.I)
    dims = [c for c in df.columns if not skip.match(c.split(":")[0].strip())
            and df[c].nunique() > 0 and c not in ("Value",)]
    time_col = next(c for c in df.columns if c.split(":")[0].strip().upper() == "TIME_PERIOD")
    val_col = next(c for c in df.columns if c.split(":")[0].strip().upper() == "OBS_VALUE")

    geo_col = next((c for c in dims if df[c].astype(str).str.contains(q["geo"]).any()), None)
    if geo_col is None:
        raise RuntimeError(f"{q['flow']}: no geography column matching {q['geo']}")
    df = df[df[geo_col].astype(str).str.contains(q["geo"])]
    # Keep only the TA/region row for Gisborne (not wards/SA2s) – shortest label wins.
    geo_label = min(df[geo_col].map(_label).unique(), key=len)
    df = df[df[geo_col].map(_label) == geo_label]

    split_col, split_map = None, None
    for c in dims:
        if c == geo_col:
            continue
        vals = df[c].map(_label).unique()
        for pat, mapping in q["split"].items():
            if re.search(pat, c, re.I) and split_col is None and len(vals) > 1:
                split_col, split_map = c, mapping
                break
        if c == split_col or len(vals) == 1:
            continue
        totals = [v for v in vals if _is_total(v)]
        if not totals:
            raise RuntimeError(f"{q['flow']}: dimension {c!r} has no total among {list(vals)[:6]}")
        df = df[df[c].map(_label) == min(totals, key=len)]

    rows = []
    for _, r in df.iterrows():
        if split_col:
            lab = _label(r[split_col])
            ind = next((i for pat, i in split_map.items() if re.search(pat, lab, re.I)), None)
            if ind is None:
                continue
        else:
            ind = next(iter(next(iter(q["split"].values())).values()))
        period = str(r[time_col])[:4]
        rows.append(obs(
            indicator_id=ind, geo_type=q["geo_type"], geo_code="028", geo_name=geo_label,
            period_start=f"{period}-01-01", period_end=f"{period}-12-31", period_type="year",
            year_basis=q["year_basis"], value=r[val_col],
            unit=q["unit"] or ("units" if "unit" in ind else "employees"),
            source_id=SOURCE_ID, licence=LICENCE, quality_flag="random rounding",
        ))
    return rows


def run() -> tuple[list[dict], list[str]]:
    rows, errors = [], []
    for q in QUERIES:
        try:
            rows += _query(q)
        except Exception as e:
            log.warning("ADE %s: %s", q["flow"], e)
            errors.append(f"{q['flow']}: {e}")
    if not rows:
        raise RuntimeError("; ".join(errors))
    return rows, []
