"""M7 – Education Counts tertiary participation for residents of Gisborne Region.

Education Counts refuses automated downloads, so a data steward transcribes the Gisborne
Region row of the publisher's tertiary participation workbook into a reviewed extract
(see data/manual/README.md). Geography is the student's region of residence, not the
location of the provider. School-leaver progression to tertiary study is a separate measure.
"""
from __future__ import annotations

import csv
import math
import re

from ..core import MANUAL_DIR, SourceBlocked, obs

SOURCE_ID = "moe_tertiary"
PATTERN = re.compile(r"tertiary-participation-region-(\d{4}-\d{2}-\d{2})\.csv")
COLUMNS = ("Year", "Region of residence", "Age group", "Domestic students", "Participation rate (%)",
           "Publisher file", "Publisher table")
REGIONS = {"gisborne", "gisborne region"}
SUPPRESSED = {"s", "c", "x", "..", "suppressed"}
MEASURES = (
    ("Participation rate (%)", "gisborne_tertiary_participation_rate", "percent", "share"),
    ("Domestic students", "gisborne_tertiary_domestic_students", "students", "count"),
)


def run() -> tuple[list[dict], list[str]]:
    files = [path for path in (MANUAL_DIR / SOURCE_ID).glob("*.csv") if PATTERN.fullmatch(path.name)]
    if not files:
        raise SourceBlocked(f"Save the reviewed tertiary participation extract in data/manual/{SOURCE_ID}/")
    path = max(files)
    with path.open(encoding="utf-8-sig", newline="") as contents:
        reader = csv.DictReader(contents)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise ValueError(f"{path.name} must have the columns {', '.join(COLUMNS)}")
        records = [r for r in reader if r["Region of residence"].strip().lower() in REGIONS]
    return _parse(records, path.name), [str(path)]


def _parse(records: list[dict], name: str) -> list[dict]:
    if not records:
        raise ValueError(f"{name} has no Gisborne Region rows")
    for field in ("Age group", "Publisher file", "Publisher table"):
        values = {r[field].strip() for r in records}
        if len(values) != 1 or "" in values:
            raise ValueError(f"{name} must name one {field.lower()} for every row")
    age = records[0]["Age group"].strip()
    rows, years = [], set()
    for record in records:
        year = int(record["Year"])
        if year in years:
            raise ValueError(f"{name} repeats Gisborne Region for {year}")
        years.add(year)
        for column, indicator, unit, measure in MEASURES:
            raw = record[column].strip()
            if not raw:  # not published for this year
                continue
            suppressed = raw.lower() in SUPPRESSED
            value = None if suppressed else float(raw.replace(",", ""))
            if value is not None and (not math.isfinite(value) or value < 0 or (unit == "percent" and value > 100)):
                raise ValueError(f"{name} has an invalid {column.lower()} for {year}")
            rows.append(obs(
                source_id=SOURCE_ID, indicator_id=indicator, geo_name="Gisborne Region",
                period_start=f"{year}-01-01", period_end=f"{year}-12-31", period_type="year",
                value=value, unit=unit, measure=measure, age=age,
                suppression_flag="publisher suppression" if suppressed else "", licence="CC BY 4.0",
            ))
    if not any(r["indicator_id"] == "gisborne_tertiary_participation_rate" for r in rows):
        raise ValueError(f"{name} has no Gisborne Region participation rates")
    return rows
