"""H14 – Health NZ quarterly HPV immunisation coverage by district (July 2024 onward).

Each quarterly workbook's "Ethnicity" sheet reports young people who turned a milestone
age (14, 15, 17, 25) during the quarter. Only the age-14 rows are used: they are labelled
consistently in every file (some files mislabel later age blocks as "8 months"/"12 months").
Earlier cohort-based files (2009–2011 birth cohorts) use a different measure and are not mixed in.
"""
from __future__ import annotations

import io
import re

import pandas as pd

from ..core import fetch, fetch_file, log, obs
from .healthnz_immunisation import Q_ETHNICITIES, Q_GEOS, SUPPRESSED, _norm, _quarter

SOURCE_ID = "healthnz_hpv"
LICENCE = "CC BY 4.0"
PAGE = ("https://www.healthnz.govt.nz/about-us/health-data/data-sets-and-collections/"
        "immunisation-data-and-statistics/hpv-immunisation-coverage-data")
AGE = "14"


def parse(content: bytes) -> list[dict]:
    df = pd.read_excel(io.BytesIO(content), sheet_name="Ethnicity", header=None)
    start, end = _quarter(str(df.iloc[0, 0]))
    hdr = df.index[df[1].map(_norm).eq("district of residence")][0]
    groups, metrics = df.iloc[hdr - 1].ffill(), df.iloc[hdr]
    cols = {c: Q_ETHNICITIES[_norm(groups[c])] for c in df.columns
            if _norm(metrics[c]) == "% fully immunised" and _norm(groups[c]) in Q_ETHNICITIES}
    if set(cols.values()) != {"Total", "Māori"}:
        raise ValueError(f"expected Total and Māori columns, got {cols}")
    rows = []
    for i in range(hdr + 1, len(df)):
        geo = Q_GEOS.get(_norm(df.iat[i, 1]))
        if not geo or _norm(df.iat[i, 0]).removesuffix(".0") != AGE:
            continue
        for c, eth in cols.items():
            v = df.iat[i, c]
            suppressed = pd.isna(v) or _norm(v) in SUPPRESSED
            rows.append(obs(
                indicator_id="hpv_14", geo_type=geo[0], geo_code=geo[1], geo_name=geo[2],
                period_start=start, period_end=end, period_type="quarter",
                value=None if suppressed else round(float(v) * 100, 1), unit="%", measure="rate",
                ethnicity=eth, suppression_flag=(str(v).strip() if pd.notna(v) else "n/s") if suppressed else "",
                source_id=SOURCE_ID, licence=LICENCE,
            ))
    keys = [(r["geo_code"], r["ethnicity"]) for r in rows]
    if len(keys) != len(set(keys)) or ("TRW", "Total") not in keys:
        raise ValueError("unexpected HPV layout")
    return rows


def run() -> tuple[list[dict], list[str]]:
    html = fetch(PAGE).text
    links = sorted(set(u for u in re.findall(r'href="(https://static\.info\.content\.health\.nz/[^"]+\.xlsx)"', html)
                       if "hpv" in u.lower() and "cohort" not in u.lower()))
    if not links:
        raise RuntimeError("no quarterly HPV files linked")
    rows, files = [], []
    for url in links:
        try:
            content, path = fetch_file(SOURCE_ID, url)
            rows += parse(content)
            files.append(str(path))
        except Exception as e:
            log.warning("hpv: %s: %s", url, e)
    seen, out = set(), []
    for r in sorted(rows, key=lambda r: r["period_end"], reverse=True):
        k = (r["geo_code"], r["ethnicity"], r["period_end"])
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out[::-1], files
