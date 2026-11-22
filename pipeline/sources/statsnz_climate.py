"""T5 – annual rainfall and mean temperature at the Gisborne climate site.

Stats NZ and Ministry for the Environment atmosphere and climate indicators, using
NIWA (now Earth Sciences New Zealand) National Climate Database records. The
September 2023 release is the latest with downloadable data. The October 2026
"Data to 2025" pages publish charts only, so check them for data files each review.
"""
from __future__ import annotations

import csv
import io
import zipfile

from ..core import fetch_file, obs

SOURCE_ID = "statsnz_climate"
BASE = "https://www.stats.govt.nz/assets/Uploads/Environment-indicators-2023"
RAIN_ZIP = f"{BASE}/Rainfall/Download-data/rainfall-data-to-2022.zip"
TEMP_ZIP = f"{BASE}/Temperature-indicator/Download-data/temperature-data-to-2022.zip"
RAIN_CSV = "annual-and-seasonal-rainfall-at-30-sites-1960-to-2022.csv"
TEMP_CSV = "annual-and-seasonal-temperature-at-30-sites-to-2022.csv"
SITE = "Gisborne (Gisborne)"
SITE_CODE, SITE_NAME = "gisborne_climate_site", "Gisborne climate site"
LICENCE = "CC BY 4.0"


def _rows(archive: bytes, member: str) -> list[dict]:
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        text = z.read(member).decode("utf-8-sig")
    return [r for r in csv.DictReader(io.StringIO(text)) if r["site"] == SITE and r["season"] == "Annual"]


def _site_obs(indicator: str, start: str, end: str, value: float | None, unit: str, measure: str,
              suppression: str = "", quality: str = "") -> dict:
    return obs(source_id=SOURCE_ID, indicator_id=indicator, geo_type="site", geo_code=SITE_CODE,
               geo_name=SITE_NAME, period_start=start, period_end=end, period_type="year",
               value=value, unit=unit, measure=measure, licence=LICENCE,
               suppression_flag=suppression, quality_flag=quality)


def rainfall(archive: bytes) -> list[dict]:
    out = []
    for r in _rows(archive, RAIN_CSV):
        if r["precipitation_units"] != "mm":
            raise ValueError(f"Unexpected rainfall unit {r['precipitation_units']!r}")
        missing = r["precipitation"] in ("", "NA")
        out.append(_site_obs("climate_annual_rainfall", r["period_start"], r["period_end"],
                             None if missing else float(r["precipitation"]), "mm", "total",
                             "publisher_unavailable" if missing else ""))
    return out


def temperature(archive: bytes) -> list[dict]:
    """Annual mean of daily average temperature. Each year appears once per anomaly baseline."""
    years: dict[str, dict] = {}
    for r in _rows(archive, TEMP_CSV):
        if r["statistic"] != "Average":
            continue
        prev = years.setdefault(r["year"], r)
        if (prev["temperature"], prev["prop_missing"]) != (r["temperature"], r["prop_missing"]):
            raise ValueError(f"Conflicting Gisborne temperature rows for {r['year']}")
    out = []
    for r in years.values():
        missing = r["temperature"] in ("", "NA")
        share = float(r["prop_missing"] or 0)
        quality = f"{share:.1%} of days missing" if share and not missing else ""
        out.append(_site_obs("climate_annual_mean_temperature", r["period_start"], r["period_end"],
                             None if missing else float(r["temperature"]), "°C", "mean",
                             "publisher_unavailable" if missing else "", quality))
    return out


def run() -> tuple[list[dict], list[str]]:
    rain, rain_path = fetch_file(SOURCE_ID, RAIN_ZIP, timeout=120)
    temp, temp_path = fetch_file(SOURCE_ID, TEMP_ZIP, timeout=180)
    rows = rainfall(rain) + temperature(temp)
    for ind in ("climate_annual_rainfall", "climate_annual_mean_temperature"):
        if sum(r["indicator_id"] == ind and r["value"] is not None for r in rows) < 30:
            raise RuntimeError(f"Incomplete Gisborne climate site series for {ind}")
    return rows, [str(rain_path), str(temp_path)]
