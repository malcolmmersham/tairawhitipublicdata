"""E12 – Stats NZ Agricultural Production Statistics by regional council (ADE AGR_AGR_001–003).

Each query filters on the Stats NZ server: dimensions are ITEM . AREA . YEAR, and area 5 is
the Gisborne regional council. Livestock and horticulture are stocks "as at 30 June"; the
forestry table covers years ended 31 March (31 December before 2005), read from the year label.
Stats NZ suppresses some cells (OBS_STATUS s = suppressed, c = confidential); those rows are
kept with an empty value and a suppression flag.
"""
from __future__ import annotations

import re
from datetime import datetime

import pandas as pd

from ..core import obs
from .statsnz_ade import _download

SOURCE_ID = "statsnz_agriculture"
LICENCE = "CC BY 4.0"
GISBORNE = "5"
QUERIES = [
    ("AGR_AGR_003", "Livestock", {
        "6731": ("agr_sheep", "sheep"),
        "7077": ("agr_beef_cattle", "beef cattle"),
    }),
    ("AGR_AGR_002", "Horticulture", {
        "8555": ("agr_kiwifruit_area", "hectares"),
        "8500": ("agr_apples_area", "hectares"),
        "8600": ("agr_wine_grapes_area", "hectares"),
        "9170": ("agr_squash_area", "hectares"),
    }),
    ("AGR_AGR_001", "Forestry", {
        "6052": ("agr_timber_harvested", "cubic metres"),
    }),
]
SUPPRESSED = {"s": "publisher suppression", "c": "publisher suppression (confidential)"}


def _period(label: str) -> tuple[str, str, str]:
    """Map an ADE year label to (period_start, period_end, year_basis)."""
    m = re.fullmatch(r"As at June 30 (\d{4})", label)
    if m:
        return f"{m[1]}-06-30", f"{m[1]}-06-30", "june"
    m = re.fullmatch(r"For year ended 31 (March|December) (\d{4})", label)
    if m:
        end = datetime.strptime(f"31 {m[1]} {m[2]}", "%d %B %Y").date()
        if m[1] == "March":
            return f"{end.year - 1}-04-01", end.isoformat(), "march"
        return f"{end.year}-01-01", end.isoformat(), "calendar"
    raise ValueError(f"Unrecognised agricultural year label {label!r}")


def _query(flow: str, item_label: str, items: dict) -> list[dict]:
    df = _download(flow, f"{'+'.join(items)}.{GISBORNE}.", SOURCE_ID)
    item_col, area_col, year_col = (f"{d}_{flow}" for d in (item_label.upper(), "AREA", "YEAR"))
    rows = []
    for _, r in df.iterrows():
        if r[area_col] != GISBORNE or r[item_col] not in items:
            raise ValueError(f"{flow}: unexpected row {r[item_col]}/{r[area_col]} – check the SDMX key")
        indicator, unit = items[r[item_col]]
        start, end, basis = _period(r["Year"])
        status = str(r.get("OBS_STATUS", "") if pd.notna(r.get("OBS_STATUS")) else "").strip().lower()
        if status and status not in SUPPRESSED:
            raise ValueError(f"{flow}: unknown observation status {status!r}")
        value = None if status or pd.isna(r["OBS_VALUE"]) else float(r["OBS_VALUE"])
        if value is None and not status:
            continue
        rows.append(obs(
            indicator_id=indicator, geo_name="Gisborne Region",
            period_start=start, period_end=end, period_type="year", year_basis=basis,
            value=value, unit=unit, measure="count" if unit != "hectares" else "area",
            suppression_flag=SUPPRESSED.get(status, ""), source_id=SOURCE_ID, licence=LICENCE,
        ))
    missing = {i for i, _ in items.values()} - {r["indicator_id"] for r in rows if r["value"] is not None}
    if missing:
        raise RuntimeError(f"{flow}: no Gisborne values for {sorted(missing)}")
    return rows


def run() -> tuple[list[dict], list[str]]:
    rows = []
    for flow, item_label, items in QUERIES:
        rows += _query(flow, item_label, items)
    return rows, []
