"""HUD's annual price-to-cost ratio for Gisborne District."""

import datetime as dt
import io
import math
import re
from html import unescape
from urllib.parse import urljoin

from openpyxl import load_workbook

from ..core import fetch, fetch_file, obs

SOURCE_ID = "hud_urban_land"
PAGE = "https://www.hud.govt.nz/stats-and-insights/urban-land-dashboard/data-download"
INDICATOR = "hud_urban_land_price_to_cost"


def run() -> tuple[list[dict], list[str]]:
    response = fetch(PAGE, timeout=30)
    match = re.search(r'\bhref=["\']([^"\']*/Urban-land-dashboard-data-download-[^"\']+?\.xlsx(?:\?[^"\']*)?)["\']',
                      response.text, re.I)
    if not match:
        raise ValueError("HUD did not list the Urban Land Dashboard workbook")
    content, path = fetch_file(SOURCE_ID, urljoin(response.url, unescape(match[1])), timeout=60)
    return parse_workbook(content), [str(path)]


def parse_workbook(content: bytes) -> list[dict]:
    workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    try:
        records = workbook["Urban land efficiency indicator"].values
        headers = next(records)
        rows = []
        for record in records:
            row = dict(zip(headers, record))
            if (row["territorial_authority"], row["indicator_name"], row["typology"]) != (
                "Gisborne District", "Price-Cost Ratio", "Total residential"
            ):
                continue
            date = row["period"]
            if not isinstance(date, dt.date) or (date.month, date.day) != (6, 30) or row["value_type"] != "Ratio":
                raise ValueError(f"Unexpected HUD annual period or unit: {date!r}, {row['value_type']!r}")
            raw = row["indicator_value"]
            suppressed = str(raw).strip().lower() in {"s", "c", "suppressed"}
            value = None if suppressed or raw in (None, "") else float(raw)
            if value is not None and (not math.isfinite(value) or value <= 0):
                raise ValueError(f"Invalid HUD price-to-cost ratio for {date}: {value}")
            rows.append(obs(
                source_id=SOURCE_ID, indicator_id=INDICATOR, geo_type="ta", geo_code="028",
                geo_name="Gisborne District", period_start=f"{date.year - 1}-07-01",
                period_end=f"{date.year}-06-30", period_type="year", year_basis="june",
                value=value, unit="ratio", measure="ratio",
                suppression_flag="publisher suppression" if suppressed else "", licence="CC BY 4.0",
            ))
        if len(rows) != len({row["period_end"] for row in rows}) or not any(row["value"] is not None for row in rows):
            raise ValueError("HUD workbook has duplicate or missing Gisborne District price-to-cost ratios")
        return rows
    finally:
        workbook.close()
