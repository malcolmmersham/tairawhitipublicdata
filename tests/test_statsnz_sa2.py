import unittest

from pipeline.sources.statsnz_sa2 import CODE, NAME, observations


class SA2CensusTests(unittest.TestCase):
    def test_2023_tenure_handles_zero_and_unavailable_inputs(self):
        metrics = [(462, 75, 729, 73.66, "", ""),
                   (0, 0, 729, 0, "", ""),
                   (None, 75, 729, None, "publisher_unavailable", ""),
                   (462, -999, 729, None, "publisher_unavailable", ""),
                   (0, 0, 0, None, "", "zero_denominator"),
                   (3, 3, 3, None, "", "inconsistent_rounded_counts")]
        for owned, trust, stated, result, suppression, quality in metrics:
            with self.subTest(owned=owned, trust=trust, stated=stated):
                record = {CODE: "206900", NAME: "Kaiti North", "VAR_4_184": owned,
                          "VAR_4_186": trust, "VAR_4_189": stated}
                row, = observations("sa2_home_ownership", "VAR_4_", [(184, 186)], (189,), record)
                self.assertEqual(row["period_end"], "2023-03-07")
                self.assertEqual(row["value"], result)
                self.assertEqual(row["suppression_flag"], suppression)
                self.assertEqual(row["quality_flag"], quality)
