"""H17 – NZ Health Survey regional estimates for Tairāwhiti (former DHB = Gisborne region).

Source: the Ministry of Health's 2017–20 Regional Data Explorer, whose "Download datasets"
page publishes static CSVs. The DHB prevalence file holds three-year pooled estimates for
2011–14, 2014–17 and 2017–20. Pooled periods are reported as published and never combined.

Unadjusted (CRUDE) prevalences for all ages, sexes and deprivation levels are used, for the
total population and Māori. The file carries 95% confidence intervals but no RSE, so
precision is flagged from the interval: an approximate RSE of (upper − lower) / 3.92 / estimate
of 30% or more marks the estimate as low precision (NZHS practice for RSE 30–100%).

The newer three-year rolling regional release by health district is published on health.govt.nz,
which refuses automated requests (Cloudflare challenge, reviewed November 2026); it needs a reviewed
manual file before it can be added, with its pooled periods kept separate from this series. The
2025/26 Annual Data Explorer CSV has national and health-region estimates only, so it has no
Tairāwhiti cells.
"""
from __future__ import annotations

import io

import pandas as pd

from ..core import fetch_file, obs

SOURCE_ID = "moh_nzhs_regional"
LICENCE = "CC BY 4.0"
APP = "https://minhealthnz.shinyapps.io/nz-health-survey-2017-20-regional-update/"
URL = APP + "data/nz-health-survey-2017-20-regional-update-dhb-prevalences.csv"
INDICATORS = {  # (population, short.description) -> indicator_id
    ("adults", "Current smokers"): "nzhs_smoking",
    ("adults", "Hazardous drinkers (total population)"): "nzhs_hazardous_drinking",
    ("adults", "Obese"): "nzhs_obesity",
    ("adults", "Unmet need for GP due to cost"): "nzhs_unmet_gp_cost",
    ("adults", "Psychological distress"): "nzhs_psych_distress",
}
POOLS = {"2011-14": ("2011-07-01", "2014-06-30"), "2014-17": ("2014-07-01", "2017-06-30"),
         "2017-20": ("2017-07-01", "2020-06-30")}
GEOS = {"Tairāwhiti": ("district", "TRW", "Tairāwhiti district"),
        "New Zealand": ("national", "NZ", "Aotearoa New Zealand")}
ETHNICITIES = {"All": "Total", "Māori": "Māori"}
LOW_PRECISION = "low precision: RSE ≈30% or more (from 95% CI)"


def parse(content: bytes) -> list[dict]:
    df = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig", dtype=str, keep_default_na=False)
    df = df[(df["type"] == "CRUDE") & (df["agegroup"] == "All") & (df["sex"] == "All")
            & (df["nzdep_quin"] == "All") & df["year"].isin(POOLS) & df["region"].isin(GEOS)
            & df["Ethnicity"].isin(ETHNICITIES)]
    rows = []
    for r in df.to_dict("records"):
        ind = INDICATORS.get((r["population"], r["short.description"]))
        if not ind:
            continue
        gt, gc, gn = GEOS[r["region"]]
        start, end = POOLS[r["year"]]
        est = pd.to_numeric(r["Prevalence"], errors="coerce")
        lo, hi = pd.to_numeric(r["CL.Lower.Bound"], errors="coerce"), pd.to_numeric(r["CL.Upper.Bound"], errors="coerce")
        suppressed = pd.isna(est)
        rse = (hi - lo) / 3.92 / est if not suppressed and est > 0 else None
        rows.append(obs(
            indicator_id=ind, geo_type=gt, geo_code=gc, geo_name=gn,
            period_start=start, period_end=end, period_type="multi_year", year_basis="july",
            value=None if suppressed else float(est), unit="%", measure="prevalence",
            ethnicity=ETHNICITIES[r["Ethnicity"]], age="15+",
            suppression_flag="not published" if suppressed else "",
            quality_flag=LOW_PRECISION if rse is not None and rse >= 0.3 else "",
            source_id=SOURCE_ID, licence=LICENCE,
        ))
    found = {r["indicator_id"] for r in rows if r["geo_code"] == "TRW"}
    if found != set(INDICATORS.values()):
        raise ValueError(f"missing Tairāwhiti indicators: {set(INDICATORS.values()) - found}")
    return rows


def run() -> tuple[list[dict], list[str]]:
    content, path = fetch_file(SOURCE_ID, URL, timeout=300)
    return parse(content), [str(path)]
