"""H25 – Ministry of Justice: people with finalised and convicted charges at Tairāwhiti courts.

Table 2b of the "People with finalised charges (including convicted charges)" workbook gives
people by court location and charge outcome for years ended June. A person is counted once
per year, at the court of their most serious finalised charge. Court location is where the
final hearing was held, not where the person lives. The workbook counts people of all ages.
Courts use geo_type "site" so the dashboard lists them as locations, not as areas.
"""
from __future__ import annotations

import io
import re

import openpyxl

from ..core import fetch, fetch_file, obs

SOURCE_ID = "moj_courts"
LICENCE = "CC BY 4.0"
BASE = "https://www.justice.govt.nz"
PAGE = BASE + "/justice-sector-policy/research-data/justice-statistics/data-tables/"
LINK = re.compile(r'href="([^"]*People-with-finalised-charges-including-convicted-charges[^"]*\.xlsx)"', re.I)
COURTS = {"Gisborne": ("court-gisborne", "Gisborne court"), "Ruatōria": ("court-ruatoria", "Ruatōria court")}
OUTCOMES = {"Total": "court_people_finalised", "Convicted": "court_people_convicted"}


def _carry(value, previous):
    """Merged-looking cells are stored as formulas pointing at the cell above."""
    return previous if value is None or (isinstance(value, str) and value.startswith("=")) else value


def run() -> tuple[list[dict], list[str]]:
    links = LINK.findall(fetch(PAGE).text)
    if not links:
        raise RuntimeError("people with finalised charges workbook link not found")
    content, path = fetch_file(SOURCE_ID, links[0] if links[0].startswith("http") else BASE + links[0])
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
    sheet = next((ws for ws in wb.worksheets if "by court and outcome" in ws.title), None)
    if sheet is None:
        raise RuntimeError("court and outcome table not found")
    table = list(sheet.iter_rows(values_only=True))
    if "by court and charge outcome" not in str(table[0][0]):
        raise RuntimeError(f"unexpected court table title: {table[0][0]}")
    header = next(i for i, r in enumerate(table) if r[0] == "Justice service area")
    years = {j: str(v) for j, v in enumerate(table[header]) if isinstance(v, str) and re.fullmatch(r"\d{4}/\d{4}", v)}
    if len(years) < 5:
        raise RuntimeError("year columns not found in court table")

    rows, area, court = [], None, None
    for r in table[header + 1:]:
        area, court = _carry(r[0], area), _carry(r[1], court)
        if area != "East Coast" or court not in COURTS or r[2] not in OUTCOMES:
            continue
        code, name = COURTS[court]
        for j, label in years.items():
            value = r[j]
            if value in (None, "-"):
                continue
            if not isinstance(value, (int, float)):
                raise ValueError(f"unexpected value {value!r} for {court} {label}")
            end = int(label[-4:])
            rows.append(obs(
                indicator_id=OUTCOMES[r[2]], geo_type="site", geo_code=code, geo_name=name,
                period_start=f"{end - 1}-07-01", period_end=f"{end}-06-30", period_type="year",
                year_basis="june", value=value, unit="people", source_id=SOURCE_ID, licence=LICENCE,
            ))
    found = {(row["indicator_id"], row["geo_code"]) for row in rows}
    if len(found) != len(COURTS) * len(OUTCOMES):
        raise RuntimeError(f"missing court series: found {sorted(found)}")
    return rows, [str(path)]
