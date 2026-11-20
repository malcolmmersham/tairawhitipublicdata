"""H11 – MBIE Tenancy Services rental bond data (monthly, Feb 1993 →).

mbie.govt.nz sits behind Imperva/Incapsula bot protection, which refuses requests
from cloud servers (including GitHub Actions). The connector tries the download and,
if blocked, falls back to the newest CSV a data steward has saved to
data/manual/mbie_bonds/ (download "Territorial authority – monthly" from the
Rental bond data page in a normal browser).
"""
from __future__ import annotations

import io
import re

import pandas as pd

from ..core import MANUAL_DIR, SourceBlocked, env, fetch, fetch_file, log, month_bounds, obs

SOURCE_ID = "mbie_bonds"
LICENCE = "CC BY 3.0 NZ"
PAGE = "https://www.mbie.govt.nz/building-and-energy/tenancy-and-housing/rental-bond-data/"
COLUMNS = {  # source column (lower-case) -> (indicator_id, unit, measure)
    "lodged bonds": ("bonds_lodged", "bonds", "count"),
    "active bonds": ("bonds_active", "bonds", "count"),
    "geometric mean rent": ("rent_geomean", "NZD/week", "geometric mean"),
    "median rent": ("rent_median", "NZD/week", "median"),
}


def _candidate_urls() -> list[str]:
    urls = [u for u in [env("MBIE_BOND_CSV_URL")] if u]
    try:
        html = fetch(PAGE, retries=1).text
        links = re.findall(r'href="([^"]+\.csv)"', html, re.I)
        tla = [l for l in links if re.search(r"tla|territorial", l, re.I) and "detailed" not in l.lower()]
        urls += ["https://www.mbie.govt.nz" + l if l.startswith("/") else l for l in tla]
    except SourceBlocked as e:
        log.warning("mbie bond page blocked: %s", e)
    return urls


def _load() -> tuple[bytes, str]:
    for url in _candidate_urls():
        try:
            content, path = fetch_file(SOURCE_ID, url, retries=1)
            return content, str(path)
        except Exception as e:
            log.warning("mbie bonds %s: %s", url, e)
    manual = sorted((MANUAL_DIR / "mbie_bonds").glob("*.csv"))
    if not manual:
        raise SourceBlocked("MBIE blocks automated downloads and no manual file is in "
                            "data/manual/mbie_bonds/")
    return manual[-1].read_bytes(), str(manual[-1])


def run() -> tuple[list[dict], list[str]]:
    content, path = _load()
    df = pd.read_csv(io.BytesIO(content))
    cols = {c.lower().strip(): c for c in df.columns}
    loc = next(cols[c] for c in cols if c in ("location", "territorial authority", "tla"))
    time = next(cols[c] for c in cols if "time" in c or c in ("month", "date"))
    df = df[df[loc].astype(str).str.contains("Gisborne", case=False)]
    rows = []
    for _, r in df.iterrows():
        d = pd.to_datetime(r[time]).date()
        start, end = month_bounds(d)
        for src, (ind, unit, measure) in COLUMNS.items():
            if src not in cols or pd.isna(r[cols[src]]):
                continue
            rows.append(obs(
                indicator_id=ind, geo_type="ta", geo_code="028", geo_name="Gisborne District",
                period_start=start, period_end=end, period_type="month", value=r[cols[src]],
                unit=unit, measure=measure, source_id=SOURCE_ID, licence=LICENCE,
                quality_flag="fixed random rounding (base 3); cells <5 bonds suppressed",
            ))
    if not rows:
        raise RuntimeError("no Gisborne rows in bond file")
    return rows, [path]
