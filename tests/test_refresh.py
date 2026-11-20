import csv
import datetime as dt
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd

from pipeline import run
from pipeline.core import COLUMNS, SourceBlocked, obs


class RefreshTest(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.silver = self.root / "silver"
        self.silver.mkdir()
        self.site = self.root / "site"
        self.status = self.root / "status.json"
        self.gold = self.root / "gold"
        self.enterContext(patch.multiple(run, SILVER_DIR=self.silver, SITE_DATA=self.site,
                                        STATUS_FILE=self.status, GOLD_DIR=self.gold))

    def seed(self, source="mbie_bonds", indicator="bonds_active", **changes):
        row = obs(source_id=source, indicator_id=indicator, period_start="2026-01-01",
                  period_end="2026-01-31", period_type="month", value=100, unit="bonds",
                  licence="CC BY 3.0 NZ", vintage_date="2026-02-01")
        row.update(changes)
        with (self.silver / f"{source}.csv").open("w", newline="", encoding="utf-8") as out:
            writer = csv.DictWriter(out, COLUMNS)
            writer.writeheader()
            writer.writerow(row)
        return row

    def test_failed_connector_keeps_data_and_other_update_is_published(self):
        self.seed()
        prior = (self.silver / "mbie_bonds.csv").read_bytes()
        run.write_json(self.status, {"mbie_bonds": {"ok": True, "rows": 1,
                       "latest_period": "2026-01-31", "last_success": "2026-02-01",
                       "schema_hash": "original"}})
        update = self.seed("statsnz_ade", "pop_estimate", value=200)
        with patch("pipeline.sources.mbie_bonds.run", side_effect=SourceBlocked("test outage")), \
             patch("pipeline.sources.statsnz_ade.run", return_value=([update | {"value": 201}], [])):
            self.assertEqual(run.main(["mbie_bonds", "statsnz_ade"]), 0)

        self.assertEqual((self.silver / "mbie_bonds.csv").read_bytes(), prior)
        payload = json.loads((self.site / "dashboard.json").read_text())
        failed = payload["status"]["mbie_bonds"]
        self.assertFalse(failed["ok"])
        self.assertEqual(failed["last_success"], "2026-02-01")
        self.assertEqual(failed["schema_hash"], "original")
        series = {series["indicator"]: series["points"][0][1] for series in payload["series"]}
        self.assertEqual(series, {"bonds_active": 100, "pop_estimate": 201})
        for filename in run.DOWNLOADS:
            self.assertEqual((self.site / filename).read_bytes(), (self.gold / filename).read_bytes())

    def test_invalid_data_cannot_replace_dashboard(self):
        row = self.seed()
        run.build()
        dashboard = self.site / "dashboard.json"
        prior = dashboard.read_bytes()
        invalid_cases = [
            ([row, row], "Duplicate observation key"),
            ([row | {"indicator_id": "unknown"}], "Unregistered indicator_id"),
            ([row | {"suppression_flag": "suppressed"}], "Suppressed observations"),
        ]
        for rows, error in invalid_cases:
            with self.subTest(error=error):
                pd.DataFrame(rows).to_csv(self.silver / "mbie_bonds.csv", index=False)
                with self.assertRaisesRegex(ValueError, error):
                    run.build()
                self.assertEqual(dashboard.read_bytes(), prior)

    def test_scheduled_refresh_skips_recent_source_but_manual_run_checks_it(self):
        self.seed("statsnz_regional_gdp", "gisborne_nominal_gdp")
        checked = dt.datetime.now(dt.timezone.utc).isoformat()
        run.write_json(self.status, {"statsnz_regional_gdp": {"ok": True, "checked": checked}})
        with patch.object(run, "run_source", return_value=run.RunResult("statsnz_regional_gdp", False)) as refresh:
            run.main(["--scheduled", "statsnz_regional_gdp"])
            refresh.assert_not_called()
            run.main(["statsnz_regional_gdp"])
            refresh.assert_called_once_with("statsnz_regional_gdp")


if __name__ == "__main__":
    unittest.main()
