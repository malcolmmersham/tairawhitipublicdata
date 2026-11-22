"""E9 – MBIE Tourism Electronic Card Transactions (TECTs) for Gisborne Region.

The TEIC "Monthly and annual spending by region" workbook has one row per month, regional
council area, product, visitor type and origin, with spend in NZD million. Domestic visitors
are cardholders from another region ("New Zealand"); international visitors use overseas
cards. Local residents' spending, cash and non-card spending are out of scope. The connector
adds the publisher's product and origin cells for Gisborne and checks the latest month
against the publisher's own region summary table.
"""
from __future__ import annotations

import collections
import datetime as dt
import io
import math

from openpyxl import load_workbook

from ..core import fetch_file, month_bounds, obs

SOURCE_ID = "mbie_tect"
LICENCE = "CC BY 4.0"
BASE = "https://teic.mbie.govt.nz/assets/tect/"
REGION_SERIES, SUMMARY = BASE + "Region-series.xlsx", BASE + "Summary.xlsx"
REGION = "Gisborne"
HEADER = ("Date", "Region", "Product", "Visitor Type", "Origin", "Annual Spend", "Monthly Spend")
VISITORS = {"New Zealand": "tect_gisborne_domestic_spend",
            "International": "tect_gisborne_international_spend"}


def run() -> tuple[list[dict], list[str]]:
    series, series_path = fetch_file(SOURCE_ID, REGION_SERIES, timeout=180)
    summary, summary_path = fetch_file(SOURCE_ID, SUMMARY, timeout=60)
    rows = _parse(series)
    _check_summary(rows, summary)
    return rows, [str(series_path), str(summary_path)]


def _monthly_totals(content: bytes) -> dict:
    wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    it = wb["Data base"].iter_rows(values_only=True)
    if tuple(next(it)[:7]) != HEADER:
        raise ValueError("TECT region workbook columns changed")
    totals = collections.defaultdict(lambda: [0.0, 0, 0])  # sum, cells, blank cells
    for date, region, product, visitor, _origin, _annual, monthly in (r[:7] for r in it):
        if region != REGION:
            continue
        if visitor not in VISITORS or not product:
            raise ValueError(f"Unexpected TECT visitor type or product: {visitor!r}/{product!r}")
        cell = totals[(date.date(), visitor)]
        cell[1] += 1
        if monthly is None or (isinstance(monthly, float) and math.isnan(monthly)):
            cell[2] += 1
        else:
            cell[0] += float(monthly)
    return totals


def _parse(content: bytes) -> list[dict]:
    rows = []
    for (date, visitor), (value, cells, blank) in sorted(_monthly_totals(content).items()):
        start, end = month_bounds(date)
        if end != date.isoformat():
            raise ValueError(f"TECT date is not a month end: {date}")
        rows.append(obs(
            source_id=SOURCE_ID, indicator_id=VISITORS[visitor], geo_name="Gisborne Region",
            period_start=start, period_end=end, period_type="month",
            value=None if blank else round(value, 4), unit="NZD million", measure="sum",
            # A month with any blank publisher cell is left empty rather than partly summed.
            suppression_flag="publisher unavailable" if blank else "", licence=LICENCE,
        ))
    if {r["indicator_id"] for r in rows} != set(VISITORS.values()):
        raise RuntimeError("TECT workbook has no Gisborne domestic or international rows")
    return rows


def _check_summary(rows: list[dict], content: bytes) -> None:
    """Match the latest Gisborne month to the publisher's REGION summary table."""
    wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    table = [r for r in wb["REGION table"].iter_rows(values_only=True) if any(c is not None for c in r)]
    header = next(r for r in table if r and r[0] == "REGION")
    gisborne = next(r for r in table if r and r[0] == REGION)
    latest = max(r["period_end"] for r in rows)
    values = {r["indicator_id"]: r["value"] for r in rows if r["period_end"] == latest}
    label = f"{_month_label(latest)} "
    for column, indicator in ((f"{label}domestic spend", "tect_gisborne_domestic_spend"),
                              (f"{label}International spend", "tect_gisborne_international_spend")):
        if column not in header:
            raise RuntimeError(f"TECT summary does not cover the latest month ({column})")
        expected = gisborne[header.index(column)]
        if values[indicator] is None or abs(values[indicator] - float(expected)) > 0.01:
            raise RuntimeError(f"TECT {indicator} {latest} does not match the summary table")


def _month_label(period_end: str) -> str:
    return dt.date.fromisoformat(period_end).strftime("%B-%Y")
