"""H18 – Health NZ PHO enrolment ("Access to primary care") by district, quarterly from April 2019.

Each quarterly workbook's "Ethnicity" sheet gives, per district of domicile, the number enrolled
in a PHO, Health NZ's estimated population (Stats NZ projections) and the percentage enrolled.
Values are a snapshot at the start of the month named in the title, e.g. "(Oct 2026)".
The population base is updated about once a year, so the percentage can step when it is;
it can exceed 100% for some groups because the two figures come from different sources.
"""
from __future__ import annotations

import datetime as dt
import io
import re

import pandas as pd

from ..core import fetch, fetch_file, log, obs
from .healthnz_immunisation import Q_ETHNICITIES, Q_GEOS, _norm

SOURCE_ID = "healthnz_pho_enrolment"
LICENCE = "CC BY 4.0"
PAGE = ("https://www.healthnz.govt.nz/about-us/health-data/data-sets-and-collections/"
        "primary-care-data-and-statistics/enrolment-with-a-general-practice-and-primary-health-organisation")
METRICS = {"total enrolled": ("pho_enrolled", "people", "count"), "%": ("pho_enrolled_pct", "%", "rate")}


def _snapshot(title: str) -> str:
    m = re.search(r"\(([A-Za-z]{3})[a-z]* (\d{4})\)", title)
    if not m:
        raise ValueError(f"no month in title: {title!r}")
    return dt.datetime.strptime(f"1 {m.group(1)} {m.group(2)}", "%d %b %Y").date().isoformat()


def parse(content: bytes) -> list[dict]:
    df = pd.read_excel(io.BytesIO(content), sheet_name="Ethnicity", header=None)
    day = _snapshot(str(df.iloc[0, 0]))
    hdr = next(i for i in range(15) if _norm(df.iat[i, 0]) in ("dhb of domicile", "district of domicile"))
    groups, metrics = df.iloc[hdr - 1].ffill(), df.iloc[hdr]
    cols = {c: (Q_ETHNICITIES[_norm(groups[c])], METRICS[_norm(metrics[c])]) for c in df.columns[1:]
            if _norm(groups[c]) in Q_ETHNICITIES and _norm(metrics[c]) in METRICS}
    if len(cols) != 4:
        raise ValueError(f"unexpected columns: {cols}")
    rows = []
    for i in range(hdr + 1, len(df)):
        geo = Q_GEOS.get(_norm(df.iat[i, 0]))
        if not geo:
            continue
        for c, (eth, (ind, unit, measure)) in cols.items():
            v = float(df.iat[i, c])
            rows.append(obs(
                indicator_id=ind, geo_type=geo[0], geo_code=geo[1], geo_name=geo[2],
                period_start=day, period_end=day, period_type="point",
                value=round(v * 100, 1) if unit == "%" else v, unit=unit, measure=measure,
                ethnicity=eth, source_id=SOURCE_ID, licence=LICENCE,
            ))
    if {(r["geo_code"], r["ethnicity"]) for r in rows} != {("TRW", "Total"), ("TRW", "Māori"), ("NZ", "Total"), ("NZ", "Māori")}:
        raise ValueError("unexpected PHO enrolment layout")
    return rows


def run() -> tuple[list[dict], list[str]]:
    html = fetch(PAGE).text
    links = sorted(set(re.findall(
        r'href="(https://static\.info\.content\.health\.nz/[^"]*Primary%20care/[^"]*primary[_-]care[_-]stats[^"]*\.xlsx)"',
        html, re.I)))
    if not links:
        raise RuntimeError("no PHO enrolment workbooks linked")
    rows, files = [], []
    for url in links:
        try:
            content, path = fetch_file(SOURCE_ID, url)
            rows += parse(content)
            files.append(str(path))
        except Exception as e:
            log.warning("pho enrolment: %s: %s", url, e)
    seen, out = set(), []
    for r in rows:
        k = (r["indicator_id"], r["geo_code"], r["ethnicity"], r["period_end"])
        if k in seen:
            raise ValueError(f"two workbooks for {k}")
        seen.add(k)
        out.append(r)
    return out, files
