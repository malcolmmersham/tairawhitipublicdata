"""H27 – NZTA Motor Vehicle Register: Gisborne District light fleet, aggregated server-side.

The register is a point-in-time snapshot of currently registered vehicles, updated monthly
and accurate to the end of the previous month. Vehicles are placed in the territorial
authority of the registered owner's physical address. Each run stores the snapshot month as
the period. Earlier snapshots are kept from the committed silver file, so the history grows
one month at a time. Past fleets cannot be rebuilt from a current snapshot.
"""
from __future__ import annotations

import json

import pandas as pd

from ..core import SILVER_DIR, fetch, land_raw, month_bounds, obs

SOURCE_ID = "nzta_mvr"
LICENCE = "CC BY 4.0"
ITEM = "https://opendata-nzta.opendata.arcgis.com/api/search/v1/collections/all/items/7b4df667d5014f1a93e6050b31d18407"
FALLBACK = "https://services.arcgis.com/CXBb7LAjgIIdcsPt/arcgis/rest/services/MVR_Mar26/FeatureServer"
TLA = "GISBORNE DISTRICT"
# NZTA light fleet: light passenger (MA, MB, MC) and light goods (NA) vehicle classes.
LIGHT = f"TLA='{TLA}' AND CLASS IN ('MA','MB','MC','NA')"


def _layer() -> str:
    """The service is renamed with each vintage, so resolve it from the stable hub item."""
    try:
        url = fetch(ITEM, retries=2).json()["properties"]["url"]
    except Exception:
        url = FALLBACK
    return url.rstrip("/") + "/0/query"


def _stats(layer: str, where: str, group: str, stats: list[tuple[str, str, str]], name: str) -> list[dict]:
    params = {"where": where, "f": "json", "outStatistics": json.dumps([
        {"statisticType": t, "onStatisticField": f, "outStatisticFieldName": n} for t, f, n in stats])}
    if group:
        params["groupByFieldsForStatistics"] = group
    r = fetch(layer, params=params, timeout=300)
    data = r.json()
    if "error" in data or data.get("exceededTransferLimit"):
        raise RuntimeError(f"incomplete Motor Vehicle Register response: {data.get('error')}")
    land_raw(SOURCE_ID, f"{name}.json", r.content)
    return [f["attributes"] for f in data["features"]]


def _snapshot_month(layer: str) -> tuple[int, int]:
    """Latest first-registration month on the whole register = the month the snapshot covers."""
    year = _stats(layer, "1=1", "", [("max", "FIRST_NZ_REGISTRATION_YEAR", "y")], "max-year")[0]["y"]
    month = _stats(layer, f"FIRST_NZ_REGISTRATION_YEAR={int(year)}", "",
                   [("max", "FIRST_NZ_REGISTRATION_MONTH", "m")], "max-month")[0]["m"]
    return int(year), int(month)


def keep_earlier(source_id: str, rows: list[dict]) -> list[dict]:
    """Return rows plus committed silver rows for periods this run did not publish."""
    path = SILVER_DIR / f"{source_id}.csv"
    if not path.exists():
        return rows
    old = pd.read_csv(path, dtype=str, keep_default_na=False)
    seen = {(r["indicator_id"], r["geo_code"], r["period_end"]) for r in rows}
    kept = [r for r in old.to_dict("records") if (r["indicator_id"], r["geo_code"], r["period_end"]) not in seen]
    return rows + kept


def run() -> tuple[list[dict], list[str]]:
    layer = _layer()
    year, month = _snapshot_month(layer)
    start, end = month_bounds(pd.Timestamp(year=year, month=month, day=1).date())

    power = _stats(layer, LIGHT, "MOTIVE_POWER", [("count", "OBJECTID", "n")], "light-motive-power")
    total = sum(a["n"] for a in power)
    plugin = sum(a["n"] for a in power if (a["MOTIVE_POWER"] or "").startswith(("ELECTRIC", "PLUGIN")))
    hybrid = sum(a["n"] for a in power if "HYBRID" in (a["MOTIVE_POWER"] or "")
                 and not (a["MOTIVE_POWER"] or "").startswith("PLUGIN"))
    age = _stats(layer, LIGHT + " AND VEHICLE_YEAR > 1800", "", [("avg", "VEHICLE_YEAR", "y"),
                                                                 ("count", "OBJECTID", "n")], "light-vehicle-year")[0]
    if total < 1000 or not age["n"]:
        raise RuntimeError(f"implausible Gisborne District light fleet: {total}")

    def add(ind, value, unit, measure):
        return obs(indicator_id=ind, geo_type="ta", geo_code="028", geo_name="Gisborne District",
                   period_start=start, period_end=end, period_type="month", value=value, unit=unit,
                   measure=measure, source_id=SOURCE_ID, licence=LICENCE)

    rows = [
        add("mvr_light_fleet", total, "vehicles", "count"),
        add("mvr_light_fleet_age", round(year - age["y"], 1), "years", "mean"),
        add("mvr_light_plugin_share", round(plugin / total * 100, 2), "percent", "share"),
        add("mvr_light_hybrid_share", round(hybrid / total * 100, 2), "percent", "share"),
    ]
    return keep_earlier(SOURCE_ID, rows), []
