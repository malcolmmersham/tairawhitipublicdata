"""July Māori-medium school rolls from the public Education Counts pivot workbook."""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from xml.etree.ElementTree import iterparse, parse
from zipfile import ZipFile

from ..core import MANUAL_DIR, SourceBlocked, obs

SOURCE_ID = "moe_maori_medium"
PATTERN = re.compile(r"Maori-Language-Learning-Student-Numbers-Pivot-(\d{4})-(\d{4})(?:-v(\d+))?\.xlsx", re.I)
XML = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def run() -> tuple[list[dict], list[str]]:
    candidates = []
    for path in (MANUAL_DIR / SOURCE_ID).glob("*.xlsx"):
        match = PATTERN.fullmatch(path.name)
        if match:
            first, last, revision = (int(value or 0) for value in match.groups())
            candidates.append((last, revision, first, path))
    if not candidates:
        raise SourceBlocked(f"Save the reviewed Education Counts Māori language workbook in data/manual/{SOURCE_ID}/")
    last, _, first, path = max(candidates)
    counts = read_counts(path)
    if set(counts) != set(range(first, last + 1)):
        raise ValueError("Māori-medium Gisborne enrolment years do not match the release filename")
    return [obs(
        source_id=SOURCE_ID, indicator_id="gisborne_maori_medium_roll", geo_type="ta", geo_code="028",
        geo_name="Gisborne District", period_start=f"{year}-07-01", period_end=f"{year}-07-01",
        period_type="year", year_basis="july", value=count, unit="students", measure="count", licence="CC BY 4.0",
    ) for year, count in sorted(counts.items())], [str(path)]


def read_counts(path: Path) -> Counter:
    # The visible pivot is preselected for New Zealand. Apply the publisher's
    # territorial authority and immersion filters to the workbook's public pivot records.
    with ZipFile(path) as archive:
        with archive.open("xl/pivotCache/pivotCacheDefinition1.xml") as definition:
            fields = parse(definition).getroot().findall(f"{XML}cacheFields/{XML}cacheField")
        indexes = {field.attrib["name"]: i for i, field in enumerate(fields)}
        count = indexes["Students (∑ Values)"]
        year = indexes["Year: As at 1 July"]
        immersion = indexes["Student: Māori Language Immersion Level"]
        district = indexes["Region: Territorial Authority"]
        shared = [[item.get("v") for item in field.findall(f"{XML}sharedItems/*")] for field in fields]
        levels = {i for i, label in enumerate(shared[immersion])
                  if label and label.startswith(("Level 1:", "Level 2:"))}
        if len(levels) != 2:
            raise ValueError("Workbook does not identify immersion levels 1 and 2")

        totals = Counter()
        with archive.open("xl/pivotCache/pivotCacheRecords1.xml") as raw:
            reader = iterparse(raw, events=("start", "end"))
            _, root = next(reader)
            for event, record in reader:
                if event != "end" or record.tag != f"{XML}r":
                    continue
                area = record[district].get("v")
                if record[district].tag == f"{XML}x":
                    area = shared[district][int(area)]
                if area == "Gisborne District":
                    level = record[immersion]
                    if level.tag != f"{XML}x":
                        raise ValueError("Unexpected immersion category encoding for Gisborne District")
                    if int(level.attrib["v"]) in levels:
                        if record[count].tag != f"{XML}n" or record[year].tag != f"{XML}x":
                            raise ValueError("Missing published count or year for Māori-medium Gisborne enrolments")
                        size = int(record[count].attrib["v"])
                        if size < 0:
                            raise ValueError("Negative Māori-medium enrolment count")
                        totals[int(shared[year][int(record[year].attrib["v"])])] += size
                root.remove(record)
    return totals
