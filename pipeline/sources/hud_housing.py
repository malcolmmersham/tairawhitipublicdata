"""H7 – HUD Government Housing Dashboard data download (monthly, June 2017 →)."""
from __future__ import annotations

import io
import re

import pandas as pd

from ..core import fetch, fetch_file, month_bounds, obs

SOURCE_ID = "hud_housing"
LICENCE = "CC BY 4.0"
PAGE = "https://www.hud.govt.nz/stats-and-insights/the-government-housing-dashboard/further-information"
TA_NAME = "Gisborne District"

# (programme, series, category_1_name, category_1_value) -> (indicator_id, unit)
SERIES = {
    ("Social Housing", "Stock", "Total", "Total"): ("hud_social_housing_stock", "places"),
    ("Social Housing", "Stock", "Provider CHP/KO", "Kainga Ora"): ("hud_social_housing_kainga_ora", "places"),
    ("Social Housing", "Stock", "Provider CHP/KO", "Community Housing Provider"): ("hud_social_housing_chp", "places"),
    ("Social Housing Register", "Applicants", "Total", "Total"): ("hud_register_applicants", "applicants"),
    ("Social Housing Register", "Applicants", "Type of Register", "Housing Register"): ("hud_housing_register", "applicants"),
    ("Social Housing Register", "Applicants", "Type of Register", "Transfer Register"): ("hud_transfer_register", "applicants"),
    ("Emergency Housing Grants", "Grants Approved", "Total", "Total"): ("hud_eh_grants", "grants"),
    ("Emergency Housing Grants", "Distinct Clients", "Total", "Total"): ("hud_eh_clients", "households"),
    ("Emergency Housing Grants", "Amount Granted", "Total", "Total"): ("hud_eh_amount", "NZD"),
    ("Transitional Housing", "Contracted Places", "Total", "Total"): ("hud_transitional_places", "places"),
}


def run() -> tuple[list[dict], list[str]]:
    html = fetch(PAGE).text
    links = re.findall(r'href="([^"]*Housing-dashboard-data-download[^"]*\.xlsx[^"]*)"', html, re.I)
    if not links:
        raise RuntimeError("HUD data-download link not found on page")
    url = links[0]
    url = "https://www.hud.govt.nz" + url if url.startswith("/") else url
    content, path = fetch_file(SOURCE_ID, url)
    df = pd.read_excel(io.BytesIO(content), sheet_name="Key stats by TA")
    df = df[(df.area_name == TA_NAME) & (df.area_type == "Territorial Authority")]
    # Only rows without a second breakdown (category_2 empty or "Total").
    df = df[df.category_2_value.isna() | (df.category_2_value == "Total")]

    rows = []
    for r in df.itertuples():
        key = (r.programme, r.series, r.category_1_name, r.category_1_value)
        if key not in SERIES:
            continue
        ind, unit = SERIES[key]
        start, end = month_bounds(pd.Timestamp(r.reporting_month).date())
        rows.append(obs(
            indicator_id=ind, geo_type="ta", geo_code="028", geo_name="Gisborne District",
            period_start=start, period_end=end, period_type="month",
            value=r.value, unit=unit, measure="amount" if unit == "NZD" else "count",
            source_id=SOURCE_ID, licence=LICENCE,
        ))
    return rows, [str(path)]
