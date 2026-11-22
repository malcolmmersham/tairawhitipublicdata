import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pipeline.core import SourceBlocked
from pipeline.sources import moe_tertiary

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_moe_tertiary" / "tertiary-participation-region-2099-01-01.csv"


class MoeTertiaryTest(unittest.TestCase):
    """Uses a synthetic extract: the values are invented, not publisher data."""

    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.manual = Path(tmp.name)
        self.folder = self.manual / "moe_tertiary"
        self.folder.mkdir()
        self.enterContext(patch.object(moe_tertiary, "MANUAL_DIR", self.manual))

    def drop(self, name="tertiary-participation-region-2099-01-01.csv", text=None):
        target = self.folder / name
        if text is None:
            shutil.copyfile(FIXTURE, target)
        else:
            target.write_text(text, encoding="utf-8")
        return target

    def test_missing_extract_is_blocked(self):
        with self.assertRaises(SourceBlocked):
            moe_tertiary.run()

    def test_reads_gisborne_rows_and_keeps_suppression(self):
        path = self.drop()
        rows, files = moe_tertiary.run()
        self.assertEqual(files, [str(path)])
        got = {(r["indicator_id"], r["period_end"]): (r["value"], r["suppression_flag"]) for r in rows}
        self.assertEqual(got, {
            ("gisborne_tertiary_participation_rate", "2097-12-31"): (11.1, ""),
            ("gisborne_tertiary_domestic_students", "2097-12-31"): (1111.0, ""),
            ("gisborne_tertiary_participation_rate", "2098-12-31"): (None, "publisher suppression"),
            ("gisborne_tertiary_domestic_students", "2098-12-31"): (None, "publisher suppression"),
            ("gisborne_tertiary_participation_rate", "2099-12-31"): (22.2, ""),
        })
        self.assertEqual({r["age"] for r in rows}, {"15 years and over"})
        self.assertEqual({r["geo_name"] for r in rows}, {"Gisborne Region"})

    def test_latest_release_is_used(self):
        self.drop("tertiary-participation-region-2001-01-01.csv", "not,a,valid,extract\n")
        self.drop()
        _, files = moe_tertiary.run()
        self.assertTrue(files[0].endswith("2099-01-01.csv"))

    def test_rejects_wrong_columns_and_mixed_age_groups(self):
        source = FIXTURE.read_text(encoding="utf-8")
        self.drop(text=source.replace("Age group", "Ages"))
        with self.assertRaises(ValueError):
            moe_tertiary.run()
        self.drop(text=source.replace("2099,Gisborne Region,15 years", "2099,Gisborne Region,18 years"))
        with self.assertRaises(ValueError):
            moe_tertiary.run()

    def test_rejects_rate_above_100(self):
        self.drop(text=FIXTURE.read_text(encoding="utf-8").replace(",22.2,", ",122.2,"))
        with self.assertRaises(ValueError):
            moe_tertiary.run()


if __name__ == "__main__":
    unittest.main()
