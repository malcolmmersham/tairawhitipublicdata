import datetime as dt
import io
import unittest

from openpyxl import Workbook

from pipeline.sources.mbie_tect import HEADER, _check_summary, _parse


def _series(cells):
    wb = Workbook()
    wb.active.title = "Pivot table"
    ws = wb.create_sheet("Data base")
    ws.append(HEADER)
    for row in cells:
        ws.append(row)
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def _summary(domestic, international):
    wb = Workbook()
    ws = wb.active
    ws.title = "REGION table"
    ws.append(["December-2025  Region Summary Table"])
    ws.append(["REGION", "December-2025 domestic spend", "December-2025 International spend"])
    ws.append(["Gisborne", domestic, international])
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


NOV, DEC = dt.datetime(2025, 11, 30), dt.datetime(2025, 12, 31)
CELLS = [
    (DEC, "Gisborne", "Accommodation services", "New Zealand", "Auckland", 5.0, 1.5),
    (DEC, "Gisborne", "Retail sales - other", "New Zealand", "Waikato", 4.0, 2.25),
    (DEC, "Gisborne", "Retail sales - other", "International", "Australia", 2.0, 0.5),
    (DEC, "Hawke's Bay", "Retail sales - other", "International", "Australia", 9.0, 9.0),
    (NOV, "Gisborne", "Retail sales - other", "New Zealand", "Waikato", 3.0, 1.0),
    (NOV, "Gisborne", "Retail sales - other", "International", "Australia", 1.0, None),
    (None, None, None, None, None, None, None),
]


class TectTests(unittest.TestCase):
    def test_sums_gisborne_cells_and_leaves_incomplete_month_empty(self):
        rows = {(r["indicator_id"], r["period_end"]): r for r in _parse(_series(CELLS))}
        self.assertEqual(rows[("tect_gisborne_domestic_spend", "2025-12-31")]["value"], 3.75)
        self.assertEqual(rows[("tect_gisborne_international_spend", "2025-12-31")]["value"], 0.5)
        self.assertEqual(rows[("tect_gisborne_domestic_spend", "2025-11-30")]["period_start"], "2025-11-01")
        incomplete = rows[("tect_gisborne_international_spend", "2025-11-30")]
        self.assertIsNone(incomplete["value"])
        self.assertEqual(incomplete["suppression_flag"], "publisher unavailable")

    def test_latest_month_must_match_publisher_summary(self):
        rows = _parse(_series(CELLS))
        _check_summary(rows, _summary(3.75, 0.5))
        with self.assertRaises(RuntimeError):
            _check_summary(rows, _summary(3.9, 0.5))


if __name__ == "__main__":
    unittest.main()
