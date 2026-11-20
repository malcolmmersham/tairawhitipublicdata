"""M8 and M5 – published July school rolls and participation before starting school."""
from __future__ import annotations

import io
import re
from datetime import date, datetime, timedelta
from html import unescape
from urllib.parse import urljoin

from openpyxl import load_workbook

from ..core import MANUAL_DIR, SourceBlocked, fetch, fetch_file, log, month_bounds, obs

SOURCE_ID = "moe_rolls_ece"
ROLLS = "https://www.educationcounts.govt.nz/statistics/school-rolls"
ECE = "https://www.educationcounts.govt.nz/statistics/participation"
ROLL_FILE = r'1-Time-series-for-trend-analysis-\d{4}-\d{4}(?:-v\d+)?\.xlsx'
ECE_FILE = r'Prior-participation-YE-[a-z]+-20\d{2}\.xlsx'


def _release_key(path):
    parts = path.stem.rsplit("-", 2)
    if path.name.lower().startswith("prior-participation"):
        stamp = datetime.strptime("-".join(parts[-2:]), "%B-%Y")
        return stamp.year, stamp.month
    if parts[-1].startswith("v"):
        return int(parts[-2]), int(parts[-1][1:])
    return int(parts[-1]), 0


def _load(url: str, filename: str) -> tuple[bytes, str]:
    try:
        page = fetch(url, timeout=30, retries=1)
        match = re.search(rf'\bhref=["\']([^"\']*/{filename})["\']', page.text, re.I)
        if not match:
            raise RuntimeError("Publisher workbook is missing")
        content, path = fetch_file(SOURCE_ID, urljoin(page.url, unescape(match[1])), timeout=60, retries=1)
        return content, str(path)
    except RuntimeError as error:
        paths = [path for path in (MANUAL_DIR / SOURCE_ID).glob("*.xlsx") if re.fullmatch(filename, path.name, re.I)]
        if not paths:
            raise SourceBlocked(f"No reviewed workbook in data/manual/{SOURCE_ID}/ for {url}") from error
        path = max(paths, key=_release_key)
        log.warning("Using reviewed workbook %s: %s", path.name, error)
        return path.read_bytes(), str(path)


def run() -> tuple[list[dict], list[str]]:
    rolls, roll_path = _load(ROLLS, ROLL_FILE)
    ece, ece_path = _load(ECE, ECE_FILE)
    return _rolls(rolls) + _ece(ece), [roll_path, ece_path]


def _observation(indicator: str, start: str, end: str, value, **fields) -> dict:
    suppressed = str(value).strip().lower() in {"s", "c", "x", "..", "suppressed"}
    return obs(
        source_id=SOURCE_ID, indicator_id=indicator, geo_type="ta", geo_code="028", geo_name="Gisborne District",
        period_start=start, period_end=end, value=None if suppressed or value in (None, "") else float(value),
        suppression_flag="publisher suppression" if suppressed else "", licence="CC BY 4.0", **fields,
    )


def _rolls(content: bytes) -> list[dict]:
    workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    try:
        cells = workbook["Territorial Authority - Board"].values
        years = next(r for r in cells if r[0] == "Territorial Authority")
        local = next(r for r in cells if r[0] == "Gisborne District")
        return [_observation("gisborne_july_school_roll", f"{year}-07-01", f"{year}-07-01", value,
                             unit="students", period_type="year", year_basis="july")
                for year, value in zip(years, local) if isinstance(year, int)]
    finally:
        workbook.close()


def _ece(content: bytes) -> list[dict]:
    workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    try:
        cells = workbook["PPN6"].values
        periods = next(r for r in cells if r[:3] == ("Participation Type", "Territorial authority and Auckland boards", "Gender"))
        local = next(r for r in cells if r[:3] == ("Prior participation rate", "Gisborne District", "Total"))
        rows = []
        for label, value in zip(periods[3:], local[3:]):
            if not re.fullmatch(r"[A-Za-z]{3} 20\d{2}", str(label)):
                continue
            month = datetime.strptime(label, "%b %Y").date()
            start = date(month.year-1, month.month, 1)
            start = month_bounds(start)[1]
            start = (date.fromisoformat(start) + timedelta(days=1)).isoformat()
            rows.append(_observation("gisborne_prior_ece_participation", start, month_bounds(month)[1], value,
                                     unit="percent", period_type="rolling_12m", measure="share"))
        return rows
    finally:
        workbook.close()
