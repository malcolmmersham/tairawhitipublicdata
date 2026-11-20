"""Shared plumbing: HTTP fetch, raw landing, the tidy observation schema."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"          # bronze: gitignored, immutable downloads
SILVER_DIR = ROOT / "data" / "silver"    # one tidy CSV per dataset (committed)
GOLD_DIR = ROOT / "data" / "gold"        # curated, registry-joined outputs (committed)
MANUAL_DIR = ROOT / "data" / "manual"    # hand-dropped files for sources that block bots
SITE_DATA = ROOT / "site" / "data"

# Override with PIPELINE_USER_AGENT (e.g. to add a contact address) if a publisher asks.
USER_AGENT = os.environ.get(
    "PIPELINE_USER_AGENT",
    "Mozilla/5.0 (compatible; TairawhitiPublicDataPipeline/1.0)",
)

log = logging.getLogger("pipeline")

# Long-format schema used by every connector (the "silver" layer).
COLUMNS = [
    "indicator_id", "geo_type", "geo_code", "geo_name",
    "period_start", "period_end", "period_type", "year_basis",
    "value", "unit", "measure", "ethnicity", "age", "sex",
    "suppression_flag", "quality_flag", "source_id", "vintage_date", "licence",
]

TODAY = dt.date.today().isoformat()


class SourceBlocked(RuntimeError):
    """The publisher refused an automated request (bot protection, 401/403)."""


_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})


def fetch(url: str, *, headers: dict | None = None, params: dict | None = None,
          retries: int = 3, timeout: int = 120) -> requests.Response:
    """GET with retries and polite backoff. Raises SourceBlocked on bot walls."""
    last: Exception | None = None
    for attempt in range(retries):
        try:
            r = _session.get(url, headers=headers, params=params, timeout=timeout)
            if r.status_code in (401, 403):
                raise SourceBlocked(f"{r.status_code} from {url}: {r.text[:200]}")
            r.raise_for_status()
            # Imperva/Incapsula returns a 200 HTML stub instead of the file.
            if b"_Incapsula_Resource" in r.content[:2000]:
                raise SourceBlocked(f"bot protection (Incapsula) on {url}")
            return r
        except SourceBlocked:
            raise
        except Exception as e:  # network / 5xx
            last = e
            time.sleep(2 ** attempt * 3)
    raise RuntimeError(f"failed to fetch {url}: {last}")


def land_raw(source_id: str, name: str, content: bytes) -> Path:
    """Write an immutable raw copy: data/raw/<source>/<date>/<sha12>-<name>."""
    sha = hashlib.sha256(content).hexdigest()[:12]
    d = RAW_DIR / source_id / TODAY
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{sha}-{name}"
    if not p.exists():
        p.write_bytes(content)
    return p


def fetch_file(source_id: str, url: str, **kw) -> tuple[bytes, Path]:
    r = fetch(url, **kw)
    name = url.split("?")[0].rstrip("/").split("/")[-1] or "download"
    return r.content, land_raw(source_id, name, r.content)


def obs(**kw) -> dict:
    """Build one observation row with schema defaults."""
    row = {
        "geo_type": "region", "geo_code": "05", "geo_name": "Gisborne / Tairāwhiti",
        "year_basis": "calendar", "measure": "count", "ethnicity": "Total",
        "age": "Total", "sex": "Total", "suppression_flag": "", "quality_flag": "",
        "vintage_date": TODAY,
    }
    row.update(kw)
    missing = set(COLUMNS) - set(row)
    if missing:
        raise ValueError(f"observation missing {missing}")
    return row


def to_frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=COLUMNS)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df


def quarter_bounds(end: dt.date) -> tuple[str, str]:
    """Given any date in a quarter's last month, return (start, end) ISO strings."""
    q_end_month = end.month
    start = dt.date(end.year, q_end_month - 2, 1)
    nxt = dt.date(end.year + (q_end_month == 12), q_end_month % 12 + 1, 1)
    return start.isoformat(), (nxt - dt.timedelta(days=1)).isoformat()


def month_bounds(d: dt.date) -> tuple[str, str]:
    start = d.replace(day=1)
    nxt = dt.date(start.year + (start.month == 12), start.month % 12 + 1, 1)
    return start.isoformat(), (nxt - dt.timedelta(days=1)).isoformat()


@dataclass
class RunResult:
    source_id: str
    ok: bool
    rows: int = 0
    latest_period: str | None = None
    message: str = ""
    files: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return self.__dict__ | {"checked": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def env(name: str) -> str | None:
    v = os.environ.get(name)
    return v or None
