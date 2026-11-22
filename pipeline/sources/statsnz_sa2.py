"""Stats NZ Census profiles for Gisborne District's populated 2023 SA2s."""
from __future__ import annotations

import json
import math
import re

from ..core import SITE_DATA, fetch_file, obs

SOURCE_ID = "statsnz_sa2"
BASE = "https://services2.arcgis.com/vKb0s8tBIA3bdocZ/arcgis/rest/services"
CODE = "SA22023_V1_00"
NAME = "SA22023_V1_00_NAME"
DATES = {2013: "2013-03-05", 2018: "2018-03-06", 2023: "2023-03-07"}
# Field numbers come from the Stats NZ lookup tables. Numerator groups and
# denominators are ordered by Census year, with a single group for 2023-only measures.
SUBJECTS = {
    "individuals": {
        "sa2_population": ([(1,), (2,), (3,)], ()),
        "sa2_under_15": ([(70,), (75,), (80,)], (1, 2, 3)),
        "sa2_age_65_plus": ([(73,), (78,), (83,)], (1, 2, 3)),
        "sa2_maori_ethnicity": ([(159,)], (168,)),
        "sa2_te_reo_maori": ([(206,)], (213,)),
    },
    "households": {
        "sa2_median_household_income": ([(225,)], ()),
        "sa2_home_ownership": ([(184, 186)], (189,)),
        "sa2_household_crowding": ([(48,)], (57,)),
        "sa2_internet_access": ([(24,)], (27,)),
    },
    "dwellings": {
        "sa2_dwelling_dampness": ([(29, 30)], (34,)),
    },
}
PREFIX = {"individuals": "VAR_1_", "households": "VAR_4_", "dwellings": "VAR_3_"}


def district_names() -> dict[str, str]:
    boundaries = json.loads((SITE_DATA / "sa2-boundaries.geojson").read_text(encoding="utf-8"))
    areas = boundaries["features"]
    names = {feature["properties"]["code"]: feature["properties"]["name"] for feature in areas}
    if not names or len(names) != len(areas) or any(not re.fullmatch(r"\d{6}", code) for code in names):
        raise ValueError("SA2 boundary file has missing or duplicate area codes")
    return names


def observations(indicator, prefix, fields, denominators, record):
    if denominators:
        measure, unit = "percentage", "%"
    elif indicator == "sa2_median_household_income":
        measure, unit = "median", "NZD"
    else:
        measure, unit = "count", "people"
    years = tuple(DATES)[-len(fields):]
    for index, (year, indices) in enumerate(zip(years, fields)):
        parts = [record[prefix + str(field)] for field in indices]
        denom = record[prefix + str(denominators[index])] if denominators else None
        inputs = parts + ([denom] if denominators else [])
        suppressed = any(value is None or value == -999 for value in inputs)
        quality = ""
        value = None
        if not suppressed:
            if any(not isinstance(n, (int, float)) or not math.isfinite(n) or n < 0 for n in inputs):
                raise ValueError(f"Unexpected Stats NZ value for {indicator}, {record[CODE]}, {year}: {inputs}")
            value = sum(parts)
            if denominators:
                if denom == 0 or value > denom:
                    quality = "zero_denominator" if denom == 0 else "inconsistent_rounded_counts"
                    value = None
                else:
                    value = round(100 * value / denom, 2)
        yield obs(
            source_id=SOURCE_ID, indicator_id=indicator, geo_type="sa2", geo_code=record[CODE],
            geo_name=record[NAME], period_start=DATES[year], period_end=DATES[year],
            period_type="year", year_basis="census", value=value, unit=unit, measure=measure,
            suppression_flag="publisher_unavailable" if suppressed else "", quality_flag=quality,
            licence="CC BY 4.0",
        )


def run() -> tuple[list[dict], list[str]]:
    areas = district_names()
    where = f"{CODE} IN (" + ",".join(f"'{code}'" for code in sorted(areas)) + ")"
    rows, files = [], []
    for subject, metrics in SUBJECTS.items():
        prefix = PREFIX[subject]
        fields = sorted({field for groups, totals in metrics.values()
                         for indices in [*groups, totals] for field in indices})
        url = f"{BASE}/2023_Census_totals_by_topic_for_{subject}_by_SA2/FeatureServer/1/query"
        content, path = fetch_file(SOURCE_ID, url, params={
            "where": where, "outFields": ",".join([CODE, NAME, *(prefix + str(field) for field in fields)]),
            "returnGeometry": "false", "f": "json",
        }, timeout=25)
        files.append(str(path))
        response = json.loads(content)
        if "error" in response or response.get("exceededTransferLimit"):
            raise ValueError(f"Incomplete Stats NZ {subject} extract: {response.get('error', 'transfer limit')}")
        records = [feature["attributes"] for feature in response["features"]]
        if len(records) != len(areas) or {record[CODE]: record[NAME] for record in records} != areas:
            raise ValueError(f"Stats NZ {subject} Census codes or names differ from the district boundaries")
        for record in records:
            for indicator, (field_groups, denominators) in metrics.items():
                rows.extend(observations(indicator, prefix, field_groups, denominators, record))
    return rows, files
