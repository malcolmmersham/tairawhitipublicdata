"""E14 – EMI average residential electricity consumption for Gisborne Region."""
from __future__ import annotations

import csv
import io
from datetime import date, datetime

from ..core import fetch_file, obs

SOURCE_ID = "ea_residential"
CSV_URL = "https://www.emi.ea.govt.nz/Retail/Download/DataReport/CSV/ZSZG4D"


def run() -> tuple[list[dict], list[str]]:
    rows, paths = [], []
    last_year = date.today().year - 1
    for year in range(2016, last_year + 1):
        content, path = fetch_file(SOURCE_ID, CSV_URL, timeout=25,
                                   params={"DateTo": f"{year}1231", "RegionType": "REG_COUNCIL", "Show": "Avg", "_si": "v|4"})
        row = _parse(content)
        if row["period_end"] != f"{year}-12-31":
            if year == last_year and row["period_end"] == f"{year-1}-12-31":
                continue  # EMI repeats the previous year before the latest becomes available.
            raise ValueError(f"EMI did not return the requested Gisborne year {year}")
        rows.append(row)
        paths.append(str(path))
    return rows, paths


def _parse(content: bytes) -> dict:
    text = io.StringIO(content.decode("utf-8-sig"))
    for line in text:
        if line.startswith("Region,Year ended,"):
            records = csv.DictReader(text, fieldnames=next(csv.reader([line])))
            record = next(row for row in records if row["Region"] == "Gisborne")
            end = datetime.strptime(record["Year ended"], "%d/%m/%Y").date()
            value = record["Average consumption (kWh)"].strip()
            return obs(
                source_id=SOURCE_ID, indicator_id="gisborne_residential_electricity",
                geo_name="Gisborne Region", period_start=f"{end.year}-01-01", period_end=end.isoformat(),
                period_type="year", value=float(value) if value else None, unit="kWh per residential connection",
                measure="average", licence="CC BY 4.0",
            )
    raise RuntimeError("EMI residential report is missing the regional table")
