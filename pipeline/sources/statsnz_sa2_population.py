"""Stats NZ ADE annual population estimates for Gisborne District's populated SA2s (Places).

POPES_SUB_006 holds estimates at 30 June for TALB, SA3 and SA2 areas. Its dimensions are
SEX . AGE . YEAR . AREA; sex 3 = total, age 999999 = total people and 888 = median age.
The flow uses 2025 boundaries. The 27 Places SA2 codes and names are unchanged from the
2023 boundaries used by the Census profiles, and every area must be returned or the run fails
and the last good file is kept. Estimates after the 2023 census base are provisional.
"""
from __future__ import annotations

import pandas as pd

from .statsnz_ade import _download
from .statsnz_sa2 import district_names
from ..core import obs

SOURCE_ID = "statsnz_sa2_population"
FLOW = "POPES_SUB_006"
BASE_YEAR = 2023  # latest census base; later years are provisional
INDICATORS = {"999999": ("sa2_pop_estimate", "people", "count"),
              "888": ("sa2_pop_median_age", "years", "median")}


def observations(df: pd.DataFrame, areas: dict[str, str]) -> list[dict]:
    df = df[df["AREA_POPES_SUB_006"].isin(areas) & df["AGE_POPES_SUB_006"].isin(INDICATORS)]
    returned = {code: set(group["AGE_POPES_SUB_006"]) for code, group in df.groupby("AREA_POPES_SUB_006")}
    missing = sorted(code for code in areas if returned.get(code) != set(INDICATORS))
    if missing:
        raise ValueError(f"{FLOW}: no estimates for SA2 {', '.join(missing)} – check the area codes")
    rows = []
    for r in df.itertuples(index=False):
        ind, unit, measure = INDICATORS[r.AGE_POPES_SUB_006]
        year = str(r.YEAR_POPES_SUB_006)[:4]
        rows.append(obs(
            indicator_id=ind, geo_type="sa2", geo_code=r.AREA_POPES_SUB_006, geo_name=areas[r.AREA_POPES_SUB_006],
            period_start=f"{year}-01-01", period_end=f"{year}-06-30", period_type="year", year_basis="june",
            value=None if pd.isna(r.OBS_VALUE) else r.OBS_VALUE, unit=unit, measure=measure,
            suppression_flag="publisher_unavailable" if pd.isna(r.OBS_VALUE) else "",
            quality_flag="provisional" if int(year) > BASE_YEAR else "",
            source_id=SOURCE_ID, licence="CC BY 4.0",
        ))
    return rows


def run() -> tuple[list[dict], list[str]]:
    areas = district_names()
    df = _download(FLOW, f"3.{'+'.join(INDICATORS)}..{'+'.join(sorted(areas))}", SOURCE_ID)
    return observations(df, areas), []
