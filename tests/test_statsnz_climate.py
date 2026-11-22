import io
import unittest
import zipfile

from pipeline.sources import statsnz_climate as climate


def archive(member: str, text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(member, "﻿" + text)
    return buf.getvalue()


RAIN = """"site","season","precipitation","precipitation_units","period_start","period_end","lat","lon","anomaly_1961","anomaly_1991"
"Gisborne (Gisborne)","Annual",1376.5,"mm","1960-01-01","1960-12-31",-38.6586,177.9851,354.9,356.3
"Gisborne (Gisborne)","Winter",379.3,"mm","1960-06-01","1960-08-31",-38.6586,177.9851,30.9,61.8
"Napier (Hawke's Bay)","Annual",800,"mm","1960-01-01","1960-12-31",-39.47,176.86,1,1
"Gisborne (Gisborne)","Annual",NA,"mm","1961-01-01","1961-12-31",-38.6586,177.9851,NA,NA
"""
TEMP = """"site","statistic","season","year","prop_missing","temperature","period_start","period_end","lat","lon","anomaly","reference_period"
"Gisborne (Gisborne)","Average","Annual",1941,0.0026881720430107525,13.441666666666666,"1941-01-01","1941-12-31",-38.6586,177.9851,-0.57,"1961-1990"
"Gisborne (Gisborne)","Average","Annual",1941,0.0026881720430107525,13.441666666666666,"1941-01-01","1941-12-31",-38.6586,177.9851,-0.9,"1991-2020"
"Gisborne (Gisborne)","Maximum","Annual",1941,0,19.1,"1941-01-01","1941-12-31",-38.6586,177.9851,0.1,"1961-1990"
"Gisborne (Gisborne)","Average","Annual",1957,0.013888888888888888,NA,"1957-01-01","1957-12-31",-38.6586,177.9851,NA,"1961-1990"
"Gisborne (Gisborne)","Average","Summer",2022,0,19.8,"2021-12-01","2022-02-28",-38.6586,177.9851,1.5,"1961-1990"
"""


class ClimateTests(unittest.TestCase):
    def test_rainfall_keeps_annual_gisborne_rows_and_unavailable_values(self):
        rows = climate.rainfall(archive(climate.RAIN_CSV, RAIN))
        self.assertEqual([(r["period_end"], r["value"], r["suppression_flag"]) for r in rows],
                         [("1960-12-31", 1376.5, ""), ("1961-12-31", None, "publisher_unavailable")])
        self.assertEqual({(r["geo_type"], r["geo_code"], r["unit"]) for r in rows},
                         {("site", climate.SITE_CODE, "mm")})

    def test_temperature_dedupes_baselines_and_flags_missing_days(self):
        rows = climate.temperature(archive(climate.TEMP_CSV, TEMP))
        self.assertEqual([(r["period_end"], r["value"], r["suppression_flag"], r["quality_flag"]) for r in rows],
                         [("1941-12-31", 13.441666666666666, "", "0.3% of days missing"),
                          ("1957-12-31", None, "publisher_unavailable", "")])

    def test_conflicting_baseline_rows_fail(self):
        bad = TEMP.replace('13.441666666666666,"1941-01-01","1941-12-31",-38.6586,177.9851,-0.9',
                           '13.5,"1941-01-01","1941-12-31",-38.6586,177.9851,-0.9')
        with self.assertRaises(ValueError):
            climate.temperature(archive(climate.TEMP_CSV, bad))


if __name__ == "__main__":
    unittest.main()
