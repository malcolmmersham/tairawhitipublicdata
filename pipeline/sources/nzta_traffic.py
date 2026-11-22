"""H27 – NZTA state highway traffic: published AADT at monitoring sites in NZTA's Gisborne region.

The State highway traffic monitoring sites layer gives each site's annual average daily
traffic (AADT) for the five most recent years, labelled relative to the release
("1 year ago" ... "5 years ago"). The layer keeps earlier releases as extra rows, so the
connector uses the newest row per site. The calendar year of "1 year ago" is not stated
in the layer, so it is anchored to NZTA's TMS daily counts: for continuous sites the
published AADT equals the mean daily count for that year. Earlier years are kept from the
committed silver file once they fall out of the five-year window.
"""
from __future__ import annotations

import datetime as dt
import json
from collections import Counter

from ..core import fetch, land_raw, obs
from .nzta_mvr import keep_earlier

SOURCE_ID = "nzta_traffic"
LICENCE = "CC BY 4.0"
BASE = "https://services.arcgis.com/CXBb7LAjgIIdcsPt/arcgis/rest/services/"
SITES = BASE + "Assets_SHTrafficMonitoringSites/FeatureServer/0"
TMS = BASE + "TMS_Telemetry_Sites/FeatureServer/0/query"
REGION = "05 - Gisborne"
OFFSETS = {"aadt1yearago": 1, "aadt2yearsago": 2, "aadt3yearsago": 3, "aadt4yearsago": 4, "aadt5yearsago": 5}


def _json(url: str, params: dict, name: str | None = None) -> dict:
    r = fetch(url, params=params | {"f": "json"}, timeout=300)
    data = r.json()
    if "error" in data or data.get("exceededTransferLimit"):
        raise RuntimeError(f"incomplete NZTA traffic response: {data.get('error')}")
    if name:
        land_raw(SOURCE_ID, name, r.content)
    return data


def _site_ref(a: dict) -> str:
    """TMS site reference: 3-digit state highway + 5-digit reference station code."""
    return f"{int(a['sh']):03d}{str(a['siteref'])[-5:]}"


def _tms_mean(ref: str, year: int) -> float | None:
    data = _json(TMS, {
        "where": f"SiteRef='{ref}' AND startDate >= DATE '{year}-01-01' AND startDate < DATE '{year + 1}-01-01'",
        "groupByFieldsForStatistics": "startDate",
        "outStatistics": json.dumps([{"statisticType": "sum", "onStatisticField": "trafficCount",
                                      "outStatisticFieldName": "v"}])})
    days = [f["attributes"]["v"] for f in data["features"]]
    return sum(days) / len(days) if days else None


def _anchor_year(sites: list[dict], edited: int) -> int:
    """Calendar year of 'aadt1yearago': the year whose TMS daily mean reproduces it."""
    best = sorted((s for s in sites if s["aadt1yearago"] and (s["accepteddays"] or 0) >= 300),
                  key=lambda s: -s["accepteddays"])[:5]
    votes = Counter()
    for s in best:
        for year in (edited - 1, edited - 2):
            mean = _tms_mean(_site_ref(s), year)
            if mean and abs(mean - s["aadt1yearago"]) <= 0.005 * s["aadt1yearago"]:
                votes[year] += 1
    if not votes or votes.most_common(1)[0][1] < 2:
        raise RuntimeError(f"could not anchor the AADT release year with TMS counts: {dict(votes)}")
    return votes.most_common(1)[0][0]


def run() -> tuple[list[dict], list[str]]:
    meta = _json(SITES, {})
    edited = dt.datetime.fromtimestamp(meta["editingInfo"]["dataLastEditDate"] / 1000, dt.timezone.utc).year
    data = _json(SITES + "/query", {"where": f"region='{REGION}'", "outFields": "*", "returnGeometry": "false"},
                 "sh-traffic-sites.json")
    newest: dict[str, dict] = {}
    for f in data["features"]:
        a = f["attributes"]
        if a["region"] != REGION:
            raise ValueError("unexpected region in traffic monitoring sites")
        ref = _site_ref(a)
        if ref not in newest or a["OBJECTID"] > newest[ref]["OBJECTID"]:
            newest[ref] = a
    if len(newest) < 10:
        raise RuntimeError(f"only {len(newest)} Gisborne traffic monitoring sites returned")
    base = _anchor_year(list(newest.values()), edited) + 1

    rows = []
    for ref, a in newest.items():
        name = f"SH{int(a['sh'])} {' '.join(a['description'].split())}"
        for field, back in OFFSETS.items():
            if a[field] is None:
                continue
            year = base - back
            rows.append(obs(
                indicator_id="sh_traffic_aadt", geo_type="site", geo_code=ref, geo_name=name,
                period_start=f"{year}-01-01", period_end=f"{year}-12-31", period_type="year",
                value=a[field], unit="vehicles per day", measure="mean", source_id=SOURCE_ID, licence=LICENCE,
            ))
    return keep_earlier(SOURCE_ID, rows), []
