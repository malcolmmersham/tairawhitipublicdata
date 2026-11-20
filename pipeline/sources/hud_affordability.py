"""H8 and H9 – local house price-to-income ratio and housing affordability indices."""
from __future__ import annotations

import io
import re
from html import unescape
from urllib.parse import urljoin

from openpyxl import load_workbook

from ..core import fetch, fetch_file, obs, quarter_bounds

SOURCE_ID = "hud_affordability"
CHAI = "https://www.hud.govt.nz/stats-and-insights/change-in-housing-affordability-indicators/about-the-indicators"
LHS = "https://www.hud.govt.nz/stats-and-insights/local-housing-statistics/about-the-local-housing-statistics-dashboard"
INDICES = {
    "Deposit affordability index": "hud_deposit_affordability",
    "Mortgage affordability index": "hud_mortgage_affordability",
    "Rent affordability index": "hud_rent_affordability",
}
PRICE_TO_INCOME = "hud_house_price_to_income"


def run() -> tuple[list[dict], list[str]]:
    rows, paths = [], []
    for page_url, prefix in ((CHAI, "CHAI"), (LHS, "LHS")):
        page = fetch(page_url, timeout=30)
        match = re.search(rf'\bhref=["\']([^"\']*/{prefix}-data-download-[^"\']+?\.xlsx(?:\?[^"\']*)?)["\']', page.text, re.I)
        if not match:
            raise RuntimeError(f"HUD did not list a {prefix} workbook")
        content, path = fetch_file(SOURCE_ID, urljoin(page.url, unescape(match[1])), timeout=60)
        rows.extend(_parse(content, prefix))
        paths.append(str(path))
    return rows, paths


def _parse(content: bytes, prefix: str) -> list[dict]:
    workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    rows = []
    try:
        sheet = workbook["Indices" if prefix == "CHAI" else "Metrics"]
        sheet.reset_dimensions()
        values = sheet.values
        headers = next(values)
        labels = INDICES if prefix == "CHAI" else {"Timeseries Median-Median ratio": PRICE_TO_INCOME}
        for cells in values:
            r = dict(zip(headers, cells))
            if r.get("area_type") != "TA" or r.get("area_name") != "Gisborne District":
                continue
            label = r["index_name"] if prefix == "CHAI" else r["series"]
            if label not in labels:
                continue
            date = r["quarter"] if prefix == "CHAI" else r["date"]
            value = r["index_value"] if prefix == "CHAI" else r["value"]
            start, end = quarter_bounds(date.date())
            suppressed = str(value).strip().lower() in {"s", "c", "suppressed", ".."}
            rows.append(obs(
                source_id=SOURCE_ID, indicator_id=labels[label], geo_type="ta", geo_code="028",
                geo_name="Gisborne District", period_start=start, period_end=end, period_type="quarter",
                value=None if suppressed or value in (None, "") else float(value),
                unit="index" if prefix == "CHAI" else "ratio", measure="affordability",
                suppression_flag="publisher suppression" if suppressed else "", licence="CC BY 4.0",
            ))
        if {r["indicator_id"] for r in rows} != set(labels.values()):
            raise RuntimeError(f"Incomplete Gisborne District {prefix} series")
        return rows
    finally:
        workbook.close()
