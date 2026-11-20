"""H5 – MSD Benefit Fact Sheets, regional council tables (quarterly, Sept 2013 →).

Each quarterly workbook holds the last five years per regional council. We take the
current file plus one archived file per year and keep the newest vintage of every
quarter, which rebuilds the series back to September 2013.
"""
from __future__ import annotations

import datetime as dt
import io
import re

import pandas as pd

from ..core import fetch, fetch_file, log, obs, quarter_bounds

SOURCE_ID = "msd_benefits"
LICENCE = "CC BY 4.0"
BASE = "https://www.msd.govt.nz"
INDEX = BASE + "/about-msd-and-our-work/publications-resources/statistics/benefit/index.html"
ARCHIVE = BASE + "/about-msd-and-our-work/publications-resources/statistics/benefit/archive-{year}.html"
FIRST_ARCHIVE_YEAR = 2013

BLOCKS = {  # block title keyword -> indicator id
    "jobseeker": "msd_jobseeker",
    "sole parent": "msd_sole_parent",
    "supported living": "msd_supported_living",
}
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _links(html: str) -> list[str]:
    return re.findall(r'href="([^"]*regional-council-tables[^"]*\.xlsx)"', html, re.I)


def _rank(url: str) -> tuple[int, int]:
    """Sort key (year, month) guessed from a file URL."""
    u = url.lower()
    y = re.search(r"/(20\d\d)/", u) or re.search(r"(20\d\d)", u)
    m = max((i for k, i in MONTHS.items() if re.search(rf"[-/]{k}[a-z]*[-./]", u)), default=0)
    return (int(y.group(1)) if y else 0, m)


def _period(v) -> dt.date | None:
    if isinstance(v, (dt.datetime, pd.Timestamp)):
        return v.date()
    s = str(v).strip()
    m = re.fullmatch(r"([A-Za-z]{3})[a-z]*[- ](\d{2,4})", s)
    if m and m.group(1).lower() in MONTHS:
        y = int(m.group(2))
        return dt.date(y + 2000 if y < 100 else y, MONTHS[m.group(1).lower()], 1)
    return None


def parse_gisborne(content: bytes) -> pd.DataFrame:
    """Return rows (indicator_id, ethnicity, period, value) from one workbook."""
    xl = pd.ExcelFile(io.BytesIO(content))
    sheet = next((s for s in xl.sheet_names if "gisborne" in s.lower()), None)
    if not sheet:
        raise ValueError("no Gisborne sheet")
    df = pd.read_excel(xl, sheet_name=sheet, header=None)
    out, indicator, periods = [], None, {}
    for _, row in df.iterrows():
        cells = [c for c in row.tolist()]
        text = " ".join(str(c) for c in cells if isinstance(c, str)).strip()
        low = text.lower()
        # Block titles (current layout: "Characteristics ... for Jobseeker Support - last 5 years";
        # 2013 layout: a bare "Jobseeker Support" row).
        if periods == {} or not any(isinstance(c, (int, float)) and not pd.isna(c) for c in cells):
            is_title = low.startswith("characteristics") or low in (
                "jobseeker support", "sole parent support", "supported living payment")
            hit = next((ind for k, ind in BLOCKS.items() if k in low), None) if is_title else None
            if hit:
                indicator, periods = hit, {}
                continue
            if "other main benefit" in low:
                indicator, periods = None, {}
                continue
            if indicator is None and ("main benefit" in low or "gisborne" in low):
                indicator = "msd_main_benefits_total"
        # Header row with period columns
        found = {i: p for i, c in enumerate(cells) if (p := _period(c))}
        if len(found) >= 2:
            periods = found
            if indicator is None:
                indicator = "msd_main_benefits_total"
            continue
        if not periods or indicator is None:
            continue
        labels = [str(c).strip() for i, c in enumerate(cells)
                  if i < min(periods) and isinstance(c, str) and str(c).strip()]
        if not labels:
            continue
        lab = labels[-1].lower()
        if lab == "total" or (lab.startswith("total ") and not lab.startswith(
                ("total recipients", "total other"))):
            eth = "Total"
        elif lab in ("māori", "mäori", "maori"):
            eth = "Māori"
        else:
            continue
        for i, p in periods.items():
            v = cells[i]
            if isinstance(v, (int, float)) and not pd.isna(v):
                out.append((indicator, eth, p, float(v)))
        if eth == "Total":  # a block's Total row ends it
            periods = {}
            indicator = None if indicator == "msd_main_benefits_total" else indicator
    return pd.DataFrame(out, columns=["indicator_id", "ethnicity", "period", "value"])


def run() -> tuple[list[dict], list[str]]:
    html = fetch(INDEX).text
    urls = _links(html)
    for year in range(FIRST_ARCHIVE_YEAR, dt.date.today().year + 1):
        try:
            year_links = _links(fetch(ARCHIVE.format(year=year), retries=1).text)
        except Exception as e:  # archive page missing for that year
            log.info("msd archive %s: %s", year, e)
            continue
        if year_links:  # newest quarter of each archive year is enough (5-year window)
            urls.append(max(year_links, key=_rank))
    urls = sorted({BASE + u if u.startswith("/") else u for u in urls}, key=_rank)

    frames, files = [], []
    for url in urls:
        try:
            content, path = fetch_file("msd_benefits", url)
            f = parse_gisborne(content)
            f["vintage_rank"] = _rank(url)[0] * 100 + _rank(url)[1]
            frames.append(f)
            files.append(str(path))
        except Exception as e:
            log.warning("msd: could not parse %s: %s", url, e)
    if not frames:
        raise RuntimeError("no MSD workbooks parsed")
    all_ = pd.concat(frames)
    all_ = (all_.sort_values("vintage_rank")
            .drop_duplicates(["indicator_id", "ethnicity", "period"], keep="last"))

    rows = []
    for r in all_.itertuples():
        start, end = quarter_bounds(r.period)
        rows.append(obs(
            indicator_id=r.indicator_id, period_start=start, period_end=end,
            period_type="quarter", value=r.value, unit="people", ethnicity=r.ethnicity,
            source_id=SOURCE_ID, licence=LICENCE,
            quality_flag="MSD random-rounds counts to base 3",
        ))
    return rows, files
