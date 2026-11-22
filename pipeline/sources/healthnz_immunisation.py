"""H13 – Health NZ childhood immunisation coverage by district.

Two series, kept as separate indicators because they measure different cohorts:

* Rolling 12-month files (Oct 2022 onward), less noisy for a district of ~600 births a year.
* Three-month (quarterly) files, back to April–June 2009. The 2009–2020 workbooks have one
  sheet per milestone ("DHB Area" rows); the 2021+ workbooks have one long "Ethnicity" sheet.

Tairāwhiti district = former Tairāwhiti DHB = Gisborne region, so no apportioning is needed.
"""
from __future__ import annotations

import datetime as dt
import io
import re
import unicodedata

import pandas as pd

from ..core import fetch, fetch_file, log, obs, quarter_bounds

SOURCE_ID = "healthnz_immunisation"
LICENCE = "CC BY 4.0"
SITE = "https://www.healthnz.govt.nz"
PAGE = (f"{SITE}/about-us/health-data/data-sets-and-collections/"
        "immunisation-data-and-statistics/immunisation-coverage")
MILESTONES = {"6 months": "imms_6m", "12 months": "imms_12m", "24 months": "imms_24m", "5 years": "imms_5y"}
GEOS = {"tairāwhiti": ("district", "TRW", "Tairāwhiti district"),
        "national total": ("national", "NZ", "Aotearoa New Zealand")}
ETHNICITIES = {"Total": "Total", "Māori": "Māori"}
# Quarterly layouts: geography label variants, normalised (no macrons, lower case).
Q_GEOS = {"tairawhiti": GEOS["tairāwhiti"], "national": GEOS["national total"],
          "national total": GEOS["national total"]}
Q_ETHNICITIES = {"total": "Total", "maori": "Māori"}
GEO_HEADERS = {"dhb", "dhb area", "dhb of residence", "district of residence"}
SUPPRESSED = {"n/s", "-", "s"}


def _norm(v) -> str:
    s = unicodedata.normalize("NFKD", str(v)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip(" *").lower()


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


# ---- three-month (quarterly) files -------------------------------------------------------

def _quarter(title: str) -> tuple[str, str]:
    """Quarter from a title: 'period ending 30-Jun-2016' / '(1 Jan- 31 Mar 2022)' etc."""
    m = (re.search(r"ending (?:\d{1,2}[ -])?([A-Za-z]{3})[a-z]*[ -](\d{4})", title)
         or re.search(r"\d{1,2} ?[A-Za-z]+\.?\s*(?:\d{4})?\s*(?:-|to)\s*\d{1,2} ?([A-Za-z]{3})[a-z]*\.? (\d{4})", title))
    if not m:
        raise ValueError(f"no quarter in title: {title!r}")
    end = dt.datetime.strptime(f"1 {m.group(1)} {m.group(2)}", "%d %b %Y").date()
    if end.month % 3:
        raise ValueError(f"quarter does not end in Mar/Jun/Sep/Dec: {title!r}")
    return quarter_bounds(end)


def _parse_sheet(df: pd.DataFrame, start: str, end: str, milestone: str | None) -> list[dict]:
    """One coverage table. `milestone` is the sheet's milestone (old layout) or None (long layout)."""
    hits = [(i, j) for i in range(min(len(df), 40)) for j in range(min(df.shape[1], 4))
            if _norm(df.iat[i, j]) in GEO_HEADERS]
    if not hits:
        raise ValueError("no geography header")
    hi, gcol = hits[0]
    # Metric labels ("%"/"% Fully immunised") are on the header row or the row below it;
    # the ethnicity group labels are on the row above the metric labels.
    mrow = next(i for i in (hi, hi + 1) if any(_norm(v) in ("%", "% fully immunised") for v in df.iloc[i]))
    groups = df.iloc[mrow - 1].ffill()
    cols = {c: Q_ETHNICITIES[_norm(groups[c])] for c in df.columns
            if _norm(df.iat[mrow, c]) in ("%", "% fully immunised") and _norm(groups[c]) in Q_ETHNICITIES}
    if set(cols.values()) != {"Total", "Māori"}:
        raise ValueError(f"expected Total and Māori columns, got {cols}")
    rows = []
    ms_col = df[0].where(df[0].astype(str).str.contains(r"months|years", case=False)).ffill()
    for i in range(mrow + 1, len(df)):
        if _norm(df.iat[i, gcol]) in GEO_HEADERS:  # old sheets repeat the table by deprivation below
            break
        geo = Q_GEOS.get(_norm(df.iat[i, gcol]))
        ms = milestone or _norm(ms_col.iat[i])
        if not geo or ms not in MILESTONES:
            continue
        for c, eth in cols.items():
            v = df.iat[i, c]
            if pd.isna(v):  # not reported (e.g. 2010 5-year milestone not yet available for all DHBs)
                continue
            suppressed = _norm(v) in SUPPRESSED
            rows.append(obs(
                indicator_id=MILESTONES[ms] + "_qtr", geo_type=geo[0], geo_code=geo[1], geo_name=geo[2],
                period_start=start, period_end=end, period_type="quarter", year_basis="calendar",
                value=None if suppressed else round(float(v) * 100, 1), unit="%", measure="rate",
                ethnicity=eth, suppression_flag=str(v).strip() if suppressed else "",
                source_id=SOURCE_ID, licence=LICENCE,
            ))
    return rows


def parse_quarterly(content: bytes) -> list[dict]:
    book = pd.ExcelFile(io.BytesIO(content))
    if "Ethnicity" in book.sheet_names:
        df = pd.read_excel(book, sheet_name="Ethnicity", header=None)
        start, end = _quarter(str(df.iloc[0, 0]))
        rows = _parse_sheet(df, start, end, None)
    else:
        rows = []
        for name in book.sheet_names:
            ms = re.sub(r"\s*\(\d\)$", "", _norm(name))
            if ms not in MILESTONES:
                continue
            df = pd.read_excel(book, sheet_name=name, header=None)
            title = " ".join(str(v) for v in df.iloc[:3, :3].values.ravel() if pd.notna(v))
            start, end = _quarter(title)
            rows += _parse_sheet(df, start, end, ms)
    # Each geography × milestone × ethnicity must appear once per file.
    keys = [(r["indicator_id"], r["geo_code"], r["ethnicity"]) for r in rows]
    if len(keys) != len(set(keys)) or not rows:
        raise ValueError("unexpected quarterly layout")
    return rows


def _dedupe(rows: list[dict]) -> list[dict]:
    # Several files can cover the same period (re-extracts): keep the last.
    seen, out = set(), []
    for r in reversed(rows):
        k = (r["indicator_id"], r["geo_code"], r["ethnicity"], r["period_end"])
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out[::-1]


def run() -> tuple[list[dict], list[str]]:
    html = fetch(PAGE).text
    links = sorted(set(re.findall(r'href="(https://static\.info\.content\.health\.nz/[^"]*annual-childhood-imm[^"]*\.xlsx)"', html)))
    if not links:
        raise RuntimeError("no annual immunisation files linked")
    quarterly = sorted(set(
        re.findall(r'href="(https://static\.info\.content\.health\.nz/[^"]*quarterly-childhood-imm[^"]*\.xlsx)"', html)
        + [SITE + p for p in re.findall(r'href="(/assets/About-us/Health-data/Immunisation-coverage/[^"]+\.xlsx?)"', html)]))
    if not quarterly:
        raise RuntimeError("no quarterly immunisation files linked")
    rows, qrows, files = [], [], []
    for url, parser, out in [(u, parse, rows) for u in links] + [(u, parse_quarterly, qrows) for u in quarterly]:
        try:
            content, path = fetch_file(SOURCE_ID, url)
            out += parser(content)
            files.append(str(path))
        except Exception as e:
            log.warning("immunisation: %s: %s", url, e)
    if not qrows:
        raise RuntimeError("no quarterly immunisation files parsed")
    qrows.sort(key=lambda r: r["period_end"])
    return _dedupe(rows) + _dedupe(qrows), files
