import unittest

import pandas as pd

from pipeline.sources.statsnz_sa2_population import observations

AREAS = {"206900": "Kaiti North", "204700": "East Cape"}


def frame(rows):
    return pd.DataFrame(rows, columns=["AGE_POPES_SUB_006", "YEAR_POPES_SUB_006", "AREA_POPES_SUB_006", "OBS_VALUE"])


class SA2PopulationTests(unittest.TestCase):
    def test_estimates_keep_places_areas_and_flag_provisional_years(self):
        df = frame([("999999", "2023", "206900", "4890"), ("888", "2023", "206900", "29.4"),
                    ("999999", "2025", "206900", None), ("999999", "2025", "204700", "1540"),
                    ("888", "2025", "204700", "36.1"), ("999999", "2025", "206802", "0")])
        rows = {(r["indicator_id"], r["geo_code"], r["period_end"]): r for r in observations(df, AREAS)}
        self.assertEqual(len(rows), 5)  # the unpopulated inlet SA2 is not a Places area
        base = rows["sa2_pop_estimate", "206900", "2023-06-30"]
        self.assertEqual((base["value"], base["geo_type"], base["geo_name"], base["quality_flag"]),
                         ("4890", "sa2", "Kaiti North", ""))
        latest = rows["sa2_pop_median_age", "204700", "2025-06-30"]
        self.assertEqual((latest["measure"], latest["unit"], latest["quality_flag"]), ("median", "years", "provisional"))
        unavailable = rows["sa2_pop_estimate", "206900", "2025-06-30"]
        self.assertIsNone(unavailable["value"])
        self.assertEqual(unavailable["suppression_flag"], "publisher_unavailable")

    def test_missing_area_or_measure_fails_so_last_good_data_is_kept(self):
        df = frame([("999999", "2025", "206900", "4900"), ("888", "2025", "206900", "29.5"),
                    ("999999", "2025", "204700", "1540")])
        with self.assertRaisesRegex(ValueError, "204700"):
            observations(df, AREAS)


if __name__ == "__main__":
    unittest.main()
