"""H11 – MBIE Tenancy Services rental bond data (monthly, Feb 1993 →)."""
from __future__ import annotations

import io
import re
from collections.abc import Iterator
from html import unescape
from urllib.parse import urljoin, urlsplit

import pandas as pd

from ..core import MANUAL_DIR, SourceBlocked, env, fetch, fetch_file, log, month_bounds, obs

SOURCE_ID = "mbie_bonds"
LICENCE = "CC BY 3.0 NZ"
PAGE = "https://www.tenancy.govt.nz/about-tenancy-services/data-and-statistics/rental-bond-data/"
COLUMNS = {  # source column (lower-case) -> (indicator_id, unit, measure)
    "lodged bonds": ("bonds_lodged", "bonds", "count"),
    "active bonds": ("bonds_active", "bonds", "count"),
    "geometric mean rent": ("rent_geomean", "NZD/week", "geometric mean"),
    "median rent": ("rent_median", "NZD/week", "median"),
}


def _candidate_urls() -> Iterator[str]:
    override = env("MBIE_BOND_CSV_URL")
    if override:
        yield override
    try:
        page = fetch(PAGE, retries=1, timeout=30)
    except RuntimeError as e:
        log.warning("tenancy rental bond page unavailable: %s", e)
        return
    for href in re.findall(r'''\bhref\s*=\s*["']([^"']+)["']''', page.text, re.I):
        url = urljoin(page.url, unescape(href))
        filename = urlsplit(url).path.rsplit("/", 1)[-1].lower()
        if filename.startswith("detailed-monthly-tla-") and filename.endswith(".csv") and url != override:
            yield url


def run() -> tuple[list[dict], list[str]]:
    for url in _candidate_urls():
        try:
            content, path = fetch_file(SOURCE_ID, url, retries=1, timeout=60)
            return _parse(content), [str(path)]
        except (RuntimeError, ValueError) as e:
            log.warning("mbie bonds %s: %s", url, e)
    manual = sorted((MANUAL_DIR / "mbie_bonds").glob("*.csv"))
    if not manual:
        raise SourceBlocked("No usable Tenancy Services territorial authority CSV and no manual file in "
                            "data/manual/mbie_bonds/")
    path = manual[-1]
    return _parse(path.read_bytes()), [str(path)]


def _parse(content: bytes) -> list[dict]:
    df = pd.read_csv(io.BytesIO(content), dtype=str)
    cols = {c.lower().strip(): c for c in df.columns}
    loc = next((cols[c] for c in cols if c in ("location", "territorial authority", "tla")), None)
    time = next((cols[c] for c in cols if "time" in c or c in ("month", "date")), None)
    if loc is None or time is None:
        raise ValueError("missing location or date column in rental bond CSV")
    df = df[df[loc].str.contains("Gisborne", case=False, na=False)].copy()
    for src in COLUMNS.keys() & cols.keys():
        column = cols[src]
        df[column] = pd.to_numeric(df[column].str.strip().str.replace(",", "", regex=False))
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
    return rows
