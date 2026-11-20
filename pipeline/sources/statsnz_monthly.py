"""E5 and E13 – Stats NZ monthly filled jobs and building consents releases."""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from html import unescape
from urllib.parse import urljoin
from zipfile import ZipFile

from ..core import fetch, fetch_file, month_bounds, obs

SOURCE_ID = "statsnz_monthly"
HOME = "https://www.stats.govt.nz"
REPORTS = (
    ("employment-and-unemployment", "employment-indicators", None),
    ("building", "building-consents-issued", "Building consents by territorial authority (Monthly).csv"),
)
SERIES = {
    "MEIM.SB1REA": ("gisborne_filled_jobs", "region", "05", "Gisborne", "jobs", "Number"),
    "BLDM.SY0281100A1": ("gisborne_new_dwellings_consented", "ta", "028", "Gisborne District", "dwellings", "Number"),
    "BLDM.SY0280001C2": ("gisborne_building_consent_value", "ta", "028", "Gisborne District", "NZD", "Dollars"),
}


def _page(url: str) -> str:
    return unescape(fetch(url, timeout=30).text).replace(r"\/", "/")


def run() -> tuple[list[dict], list[str]]:
    rows, paths = [], []
    for topic, slug, member in REPORTS:
        releases = set(re.findall(rf'/information-releases/{slug}-([a-z]+-20\d{{2}})/',
                                 _page(f"{HOME}/topics/{topic}/"), re.I))
        if not releases:
            raise RuntimeError(f"Stats NZ listed no monthly {slug} releases")
        release = max(releases, key=lambda stamp: datetime.strptime(stamp, "%B-%Y"))
        page = _page(f"{HOME}/information-releases/{slug}-{release}/")
        asset = re.search(rf'(/assets/[^\s"<>]+/{slug}-{release}\.zip)', page, re.I)
        if not asset:
            raise RuntimeError(f"Stats NZ did not list the {slug} CSV archive for {release}")
        content, path = fetch_file(SOURCE_ID, urljoin(HOME, asset[1]), timeout=90)
        with ZipFile(io.BytesIO(content)) as archive:
            filename = member or f"{slug}-{release}-csv-tables.csv"
            paths.append(str(path))
            with archive.open(filename) as raw:
                parsed = _parse(io.TextIOWrapper(raw, encoding="utf-8-sig"))
        latest = month_bounds(datetime.strptime(release, "%B-%Y").date())[1]
        ids = {row["indicator_id"] for row in parsed if row["period_end"] == latest and row["value"] is not None}
        expected = {SERIES["MEIM.SB1REA"][0]} if member is None else {s[0] for k, s in SERIES.items() if k.startswith("BLDM")}
        if ids != expected:
            raise RuntimeError(f"Incomplete Gisborne {slug} data for {release}")
        rows.extend(parsed)
    return rows, paths


def _parse(raw) -> list[dict]:
    rows = []
    for r in csv.DictReader(raw):
        if r["Series_reference"] not in SERIES:
            continue
        indicator, geo_type, geo_code, label, unit, units = SERIES[r["Series_reference"]]
        geography = r["Series_title_2"] if geo_type == "region" else r["Series_title_1"]
        if (geography, r.get("UNITS", r.get("Units")), r["Magnitude"]) != (label, units, "0"):
            raise ValueError(f"Geography or units changed for {r['Series_reference']}")
        start, end = month_bounds(datetime.strptime(r["Period"], "%Y.%m").date())
        value = r["Data_value"].strip()
        suppressed = r["Suppressed"].strip().lower() in {"y", "yes", "s", "c"}
        rows.append(obs(
            source_id=SOURCE_ID, indicator_id=indicator, geo_type=geo_type, geo_code=geo_code,
            geo_name="Gisborne Region" if geo_type == "region" else label,
            period_start=start, period_end=end, period_type="month", unit=unit,
            value=None if suppressed or not value else float(value),
            suppression_flag="publisher suppression" if suppressed else "",
            quality_flag="provisional" if r.get("STATUS", r.get("Status")) == "P" else "", licence="CC BY 4.0",
        ))
    return rows
