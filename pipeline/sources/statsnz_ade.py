"""Stats NZ Aotearoa Data Explorer (ADE) SDMX API – H1 population, E3 business demography.

Needs a free subscription key from the Stats NZ API Portal, sent as the
Ocp-Apim-Subscription-Key header. In GitHub Actions it comes from the STATSNZ_API_KEY
secret; in a cloud dev session a network proxy adds it, so the variable stays unset.

Each query filters on the Stats NZ server with an SDMX key (dimension codes joined by
dots, `+` for several codes, empty for all). Unfiltered, business demography is
over 500 MB for all of New Zealand. If Stats NZ renumbers a code, the query returns
no Gisborne rows and the run fails loudly rather than silently changing the series.
"""
from __future__ import annotations

import io

import pandas as pd

from ..core import env, fetch, land_raw, log, obs

SOURCE_ID = "statsnz_ade"
LICENCE = "CC BY 4.0"
API = "https://api.data.stats.govt.nz/rest/data/STATSNZ,{flow},1.0/{key}"

QUERIES = [
    {   # Dimensions: YEAR . SEX . AGE . AREA. Sex 3 = total; age 999999 = total, 888 = median age; area 028 = Gisborne district.
        "flow": "POPES_SUB_011", "key": ".3.999999+888.028",
        "split_col": "Age", "geo_name": "Gisborne District", "year_basis": "june", "ref": ("01-01", "06-30"),
        "indicators": {"Total people, age": ("pop_estimate", "people", "count"),
                       "Median age": ("pop_median_age", "years", "median")},
    },
    {   # Dimensions: ANZSIC06 . AREA . YEAR . MEASURE. TOTAL = all industries; T028 = Gisborne District.
        "flow": "BDS_BDS_001", "key": "TOTAL.T028..",
        "split_col": "Measure", "geo_name": "Gisborne District", "year_basis": "february", "ref": ("02-01", "02-28"),
        "indicators": {"Geographic Units": ("bds_geographic_units", "business locations", "count"),
                       "Employee Count": ("bds_employee_count", "employees", "count")},
    },
]


def _download(flow: str, key: str) -> pd.DataFrame:
    headers = {"Accept": "application/vnd.sdmx.data+csv"}
    api_key = env("STATSNZ_API_KEY")
    if api_key:
        headers["Ocp-Apim-Subscription-Key"] = api_key
    r = fetch(API.format(flow=flow, key=key), headers=headers,
              params={"format": "csvfilewithlabels", "dimensionAtObservation": "AllDimensions"},
              timeout=300)
    land_raw(SOURCE_ID, f"{flow}.csv", r.content)
    return pd.read_csv(io.BytesIO(r.content), dtype=str)


def _query(q: dict) -> list[dict]:
    df = _download(q["flow"], q["key"])
    year_col = next(c for c in df.columns if c.startswith("Year"))
    rows = []
    for _, r in df.iterrows():
        hit = q["indicators"].get(r[q["split_col"]])
        if not hit or pd.isna(r["OBS_VALUE"]):
            continue
        ind, unit, measure = hit
        y = str(r[year_col])[:4]
        rows.append(obs(
            indicator_id=ind, geo_type="ta", geo_code="028", geo_name=q["geo_name"],
            period_start=f"{y}-{q['ref'][0]}", period_end=f"{y}-{q['ref'][1]}", period_type="year",
            year_basis=q["year_basis"], value=r["OBS_VALUE"], unit=unit, measure=measure,
            source_id=SOURCE_ID, licence=LICENCE,
            quality_flag="" if measure == "median" else "random rounding",
        ))
    if not rows:
        raise RuntimeError(f"{q['flow']}: no Gisborne rows – check the SDMX key {q['key']!r}")
    return rows


def run() -> tuple[list[dict], list[str]]:
    rows, errors = [], []
    for q in QUERIES:
        try:
            rows += _query(q)
        except Exception as e:
            log.warning("ADE %s: %s", q["flow"], e)
            errors.append(f"{q['flow']}: {e}")
    if errors:  # partial success would silently drop a series from the silver file
        raise RuntimeError("; ".join(errors))
    return rows, []
