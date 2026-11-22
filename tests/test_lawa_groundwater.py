import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd

from pipeline import run
from pipeline.core import MANUAL_DIR, SourceBlocked, to_frame
from pipeline.sources import lawa_groundwater

FIELDS = ["Region", "Agency", "GroundwaterQualityZone", "LAWASiteID", "BoreID", "Indicator",
          "SampleDateTime", "Value", "Units", "Censor_Symbol", "DataLicensing"]
UNITS = {"Chloride": "g/m3", "Electrical conductivity/salinity": "µS/cm",
         "Dissolved reactive phosphorus": "g/m3", "Nitrate nitrogen": "g/m3", "E.coli": "#/100 mL"}


def sample(indicator="Chloride", when="2004-12-08T07:15:00", value="109", symbol="NA", **changes):
    row = {"Region": "Gisborne", "Agency": "Gisborne District Council",
           "GroundwaterQualityZone": "Makauri Gravel Aquifer", "LAWASiteID": "GDC-00035",
           "BoreID": "GPB102", "Indicator": indicator, "SampleDateTime": when, "Value": value,
           "Units": UNITS[indicator], "Censor_Symbol": symbol, "DataLicensing": "CC BY 4.0"}
    return row | changes


def complete(*extra):
    """One sample per indicator plus any extra rows."""
    return [sample(indicator) for indicator in UNITS if indicator != "Chloride"] + [sample(), *extra]


class LawaGroundwaterTest(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.manual = Path(tmp.name)
        (self.manual / "lawa_groundwater").mkdir()
        self.enterContext(patch.object(lawa_groundwater, "MANUAL_DIR", self.manual))

    def write(self, rows, name="gisborne-groundwater-samples-2026-10-27.csv"):
        with (self.manual / "lawa_groundwater" / name).open("w", newline="", encoding="utf-8") as out:
            writer = csv.DictWriter(out, FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    def test_same_day_samples_and_lab_limits_are_kept(self):
        self.write(complete(
            sample(when="2004-12-08T10:35:00", value="47"),
            sample("Nitrate nitrogen", when="2005-03-01T09:00:00", value="<0.002", symbol="<"),
        ))
        rows, _ = lawa_groundwater.run()
        chloride = [r for r in rows if r["indicator_id"] == "groundwater_chloride"]
        self.assertEqual([(r["period_end"], r["value"]) for r in chloride],
                         [("2004-12-08T07:15", 109.0), ("2004-12-08T10:35", 47.0)])
        limit = next(r for r in rows if r["period_end"] == "2005-03-01T09:00")
        self.assertEqual((limit["value"], limit["quality_flag"], limit["unit"]), (0.002, "less_than", "g/m3"))
        self.assertEqual(chloride[0]["geo_code"], "GDC-00035")
        self.assertEqual(chloride[0]["geo_name"], "GPB102 · Makauri Gravel Aquifer")
        self.assertEqual(chloride[0]["quality_flag"], "")
        conductivity = next(r for r in rows if r["indicator_id"] == "groundwater_conductivity")
        self.assertEqual(conductivity["unit"], "µS/cm")
        frame = to_frame(rows)
        self.assertFalse(frame.duplicated(run.OBSERVATION_KEY).any())

    def test_rows_without_cc_by_licence_are_rejected(self):
        self.write(complete(sample(when="2019-11-21T10:00:00", DataLicensing="Unstated")))
        with self.assertRaisesRegex(ValueError, "CC BY 4.0"):
            lawa_groundwater.run()

    def test_duplicate_timestamp_is_rejected(self):
        self.write(complete(sample(value="110")))
        with self.assertRaisesRegex(ValueError, "same site, indicator and time"):
            lawa_groundwater.run()

    def test_censor_symbol_must_match_result(self):
        self.write(complete(sample(when="2006-01-01T09:00:00", value="<1", symbol="NA")))
        with self.assertRaisesRegex(ValueError, "Censor symbol"):
            lawa_groundwater.run()

    def test_unexpected_unit_is_rejected(self):
        self.write(complete(sample(when="2006-01-01T09:00:00", Units="mg/L")))
        with self.assertRaisesRegex(ValueError, "Unexpected unit"):
            lawa_groundwater.run()

    def test_missing_extract_is_blocked(self):
        with self.assertRaises(SourceBlocked):
            lawa_groundwater.run()


class BundledExtractTest(unittest.TestCase):
    def test_reviewed_extract(self):
        if not any((MANUAL_DIR / "lawa_groundwater").glob("*.csv")):
            self.skipTest("no reviewed extract bundled")
        frame = to_frame(lawa_groundwater.run()[0])
        self.assertFalse(frame.duplicated(run.OBSERVATION_KEY).any())
        self.assertEqual(set(frame.licence), {"CC BY 4.0"})
        self.assertTrue(frame.value.notna().all())
        self.assertTrue(set(frame.quality_flag) <= {"", "less_than", "greater_than"})


if __name__ == "__main__":
    unittest.main()
