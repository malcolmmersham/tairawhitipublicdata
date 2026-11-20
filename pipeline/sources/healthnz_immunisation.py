"""H13 – Health NZ childhood immunisation coverage, rolling 12-month files by district.

Uses the "annual" (rolling 12-month) workbooks, which are less noisy for a district
of ~600 births a year than the single-quarter files. Tairāwhiti district = former
Tairāwhiti DHB = Gisborne region, so no apportioning is needed.
"""
from __future__ import annotations

import datetime as dt
import io
import re

import pandas as pd

from ..core import fetch, fetch_file, log, obs

SOURCE_ID = "healthnz_immunisation"
LICENCE = "CC BY 4.0"
PAGE = ("https://www.healthnz.govt.nz/about-us/health-data/data-sets-and-collections/"
        "immunisation-data-and-statistics/immunisation-coverage")
MILESTONES = {"6 months": "imms_6m", "12 months": "imms_12m", "24 months": "imms_24m", "5 years": "imms_5y"}
GEOS = {"tairāwhiti": ("district", "TRW", "Tairāwhiti district"),
        "national total": ("national", "NZ", "Aotearoa New Zealand")}
ETHNICITIES = {"Total": "Total", "Māori": "Māori"}


def _period(title: str) -> tuple[dt.date, dt.date]:
    m = re.search(r"\((\d{1,2} \w+ \d{4}) - (\d{1,2} \w+ \d{4})\)", title)
    if not m:
        raise ValueError(f"no period in title: {title!r}")
    f = lambda s: dt.datetime.strptime(s, "%d %B %Y").date()
    start, end = f(m.group(1)), f(m.group(2))
    if (end - start).days > 370:  # publisher typo seen in titles, e.g. "1 Jan 2025 - 31 Dec 2026"
        end = dt.date(start.year + 1, start.month, 1) - dt.timedelta(days=1)
    return start, end


def parse(content: bytes) -> list[dict]:
    df = pd.read_excel(io.BytesIO(content), sheet_name="Ethnicity", header=None)
    start, end = _period(str(df.iloc[0, 0]))
    hdr_i = df.index[df[1].astype(str).eq("District of residence")][0]
    groups = df.iloc[hdr_i - 1].ffill()
    metrics = df.iloc[hdr_i]
    rows = []
    for _, r in df.iloc[hdr_i + 1:].iterrows():
        ms, geo = str(r[0]).strip(), str(r[1]).strip().lower()
        if ms not in MILESTONES or geo not in GEOS:
            continue
        for col in df.columns[3:]:
            eth = str(groups[col]).strip()
            if eth not in ETHNICITIES or str(metrics[col]).strip() != "% Fully immunised":
                continue
            v = r[col]
            gt, gc, gn = GEOS[geo]
            suppressed = str(v).strip().lower() == "n/s"
            rows.append(obs(
                indicator_id=MILESTONES[ms], geo_type=gt, geo_code=gc, geo_name=gn,
                period_start=start.isoformat(), period_end=end.isoformat(),
                period_type="rolling_12m", year_basis="rolling",
                value=None if suppressed else float(v) * 100, unit="%", measure="rate",
                ethnicity=ETHNICITIES[eth], suppression_flag="n/s" if suppressed else "",
                source_id=SOURCE_ID, licence=LICENCE,
            ))
    return rows


def run() -> tuple[list[dict], list[str]]:
    html = fetch(PAGE).text
    links = sorted(set(re.findall(r'href="(https://static\.info\.content\.health\.nz/[^"]*annual-childhood-imm[^"]*\.xlsx)"', html)))
    if not links:
        raise RuntimeError("no annual immunisation files linked")
    rows, files = [], []
    for url in links:
        try:
            content, path = fetch_file(SOURCE_ID, url)
            rows += parse(content)
            files.append(str(path))
        except Exception as e:
            log.warning("immunisation: %s: %s", url, e)
    # Several files can cover the same 12-month window (re-extracts): keep the last.
    seen, out = set(), []
    for r in reversed(rows):
        k = (r["indicator_id"], r["geo_code"], r["ethnicity"], r["period_end"])
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out[::-1], files
