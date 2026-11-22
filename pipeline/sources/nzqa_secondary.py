"""M4 – NZQA secondary school statistics: NCEA and University Entrance attainment, Gisborne region.

NZQA's consolidated files report NCEA Level 1 on a participation basis and NCEA Levels 2
and 3 and University Entrance on an enrolment basis, by the region of the student's school.
These are distinct from the Ministry of Education school-leaver measure (moe_leavers).
"""
from __future__ import annotations

import csv
import io
import re
from html import unescape
from urllib.parse import urljoin

from ..core import fetch, fetch_file, obs

SOURCE_ID = "nzqa_secondary"
INDEX = "https://www2.nzqa.govt.nz/ncea/understanding-secondary-quals/secondary-school-stats/"
REGION = "Gisborne"
# (file prefix, year level, qualification) -> indicator. Typical-level rows only.
SERIES = {
    ("Participation", 11, "NCEA Level 1"): "nzqa_ncea_level_1_year_11",
    ("Enrolment", 12, "NCEA Level 2"): "nzqa_ncea_level_2_year_12",
    ("Enrolment", 13, "NCEA Level 3"): "nzqa_ncea_level_3_year_13",
    ("Enrolment", 13, "University Entrance"): "nzqa_university_entrance_year_13",
}


def run() -> tuple[list[dict], list[str]]:
    index = fetch(INDEX, timeout=60)
    years = [int(y) for y in re.findall(r'href=["\'][^"\']*/secondary-school-stats/(\d{4})/["\']', index.text)]
    if not years:
        raise RuntimeError("NZQA did not list a secondary statistics year page")
    page = fetch(urljoin(index.url, f"{max(years)}/"), timeout=60)
    rows, files = [], []
    for prefix in ("Participation", "Enrolment"):
        match = re.search(rf'href=["\']([^"\']*/{prefix}-Qualification-Attainment-Statistics-National-Region-\d{{4}}-\d{{8}}\.csv)["\']',
                          page.text, re.I)
        if not match:
            raise RuntimeError(f"NZQA did not list the {prefix.lower()}-based region CSV")
        content, path = fetch_file(SOURCE_ID, urljoin(page.url, unescape(match[1])), timeout=60)
        rows += _parse(content, prefix)
        files.append(str(path))
    found = {r["indicator_id"] for r in rows}
    missing = set(SERIES.values()) - found
    if missing:
        raise RuntimeError(f"NZQA region files lack Gisborne series: {sorted(missing)}")
    return rows, files


def _parse(content: bytes, prefix: str) -> list[dict]:
    rows = []
    for rec in csv.DictReader(io.StringIO(content.decode("utf-8-sig"))):
        if rec["Region"] != REGION or rec["Typical Level Flag"] != "1":
            continue
        indicator = SERIES.get((prefix, int(rec["Year Level"]), rec["Qualification"]))
        if not indicator:
            continue
        year = int(rec["Academic Year"])
        rate = rec["Cumulative Year Attainment Rate"].strip()
        small = rec.get("Cohort Warning", "").strip()
        rows.append(obs(
            source_id=SOURCE_ID, indicator_id=indicator, geo_name="Gisborne Region",
            period_start=f"{year}-01-01", period_end=f"{year}-12-31", period_type="year",
            # CSV rates are proportions to three decimals; NZQA's XLSX shows the same as a percentage.
            value=round(float(rate) * 100, 1) if rate else None, unit="percent", measure="share",
            # NZQA blanks all attainment figures where the cohort is under five students.
            suppression_flag="" if rate else "publisher suppression",
            quality_flag="small cohort (under 30)" if small else "",
            licence="CC BY 4.0",
        ))
    return rows
