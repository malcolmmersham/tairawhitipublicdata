"""T1 – measured river E. coli state for Gisborne monitoring sites, 2020–2024."""
from __future__ import annotations

import json

from ..core import fetch_file, obs

SOURCE_ID = "statsnz_river_quality"
LAYER = "https://services2.arcgis.com/vKb0s8tBIA3bdocZ/arcgis/rest/services/rwq_state/FeatureServer/0/query"


def run() -> tuple[list[dict], list[str]]:
    content, path = fetch_file(SOURCE_ID, LAYER, timeout=45, params={
        "f": "json", "where": "region = 'Gisborne Region' AND median_ECOLI IS NOT NULL",
        "outFields": "custom_site_identifier,region,median_ECOLI", "returnGeometry": "false",
        "orderByFields": "custom_site_identifier",
    })
    response = json.loads(content)
    if response.get("error") or response.get("exceededTransferLimit") or not response.get("features"):
        raise RuntimeError("Incomplete Stats NZ Gisborne monitored river results")
    rows = []
    for feature in response["features"]:
        site = feature["attributes"]
        if site["region"] != "Gisborne Region" or not site["custom_site_identifier"]:
            raise ValueError("Unexpected geography or site identifier in monitored river results")
        rows.append(obs(
            source_id=SOURCE_ID, indicator_id="river_ecoli_median", geo_type="site",
            geo_code=site["custom_site_identifier"], geo_name=site["custom_site_identifier"],
            period_start="2020-01-01", period_end="2024-12-31", period_type="multi_year",
            value=site["median_ECOLI"], unit="E. coli per 100 mL", measure="median", licence="CC BY 4.0",
        ))
    return rows, [str(path)]
