"""
Smoke tests: build a database from SYNTHETIC data, check the cleaning rules,
make sure every SQL statement in sql/queries.sql runs and every plot renders.

    python -m unittest discover -s tests -v
"""
import os
import sqlite3
import tempfile
import unittest

import matplotlib

matplotlib.use("Agg")
import pandas as pd  # noqa: E402

from src import plots  # noqa: E402
from src.build_database import build  # noqa: E402
from tests.make_sample_data import make_sample  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        csv_dir = make_sample(os.path.join(cls.tmp.name, "csv"), n_trips=20_000, n_stations=40)
        cls.db_path = build(csv_dir, os.path.join(cls.tmp.name, "test.db"), rebuild=True)
        cls.db = sqlite3.connect(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        cls.tmp.cleanup()

    def q(self, sql):
        return pd.read_sql_query(sql, self.db)

    def test_cleaning_rules(self):
        r = self.q("SELECT MIN(duration_min) AS lo, MAX(duration_min) AS hi, COUNT(*) AS n FROM trips_clean").iloc[0]
        self.assertGreaterEqual(r["lo"], 1)
        self.assertLessEqual(r["hi"], 1440)
        raw = self.q("SELECT COUNT(*) AS n FROM daily_rent_detail").iloc[0]["n"]
        self.assertLess(r["n"], raw)  # the sample data contains bad rows

    def test_derived_columns(self):
        r = self.q("SELECT MIN(hour) AS h0, MAX(hour) AS h1, MIN(dow) AS d0, MAX(dow) AS d1, "
                   "MIN(month) AS m0, MAX(month) AS m1 FROM trips_clean").iloc[0]
        self.assertEqual((r["h0"], r["h1"]), (0, 23))
        self.assertEqual((r["d0"], r["d1"]), (0, 6))
        self.assertEqual((r["m0"], r["m1"]), (1, 12))

    def test_sql_file_runs(self):
        with open(os.path.join(ROOT, "sql", "queries.sql"), encoding="utf-8") as fh:
            self.db.executescript(fh.read())

    def test_plots_render(self):
        out = tempfile.mkdtemp()
        fleet = self.q("SELECT rideable_type, member_casual, COUNT(*) AS number_of_rides, "
                       "AVG(duration_min) AS avg_duration_min FROM trips_clean GROUP BY 1, 2")
        dh = self.q("SELECT dow, hour AS hour_of_day, member_casual, COUNT(*) AS number_of_trips "
                    "FROM trips_clean GROUP BY 1, 2, 3")
        dh["Day"] = dh["dow"].map(dict(enumerate(["Sunday", "Monday", "Tuesday", "Wednesday",
                                                  "Thursday", "Friday", "Saturday"])))
        hourly = dh.groupby("hour_of_day", as_index=False)["number_of_trips"].sum()
        weekday = (dh.groupby("Day", as_index=False)["number_of_trips"].sum()
                   .rename(columns={"number_of_trips": "Number_of_Trips"}))
        monthly = self.q("SELECT year, month, COUNT(*) AS trips FROM trips_clean GROUP BY 1, 2")
        top = pd.DataFrame({"station_name": list("abcdefghij"), "trip_count": range(10, 0, -1)})
        weather = pd.DataFrame({"category": ["Clear", "Rain"], "avg_trips_per_day": [100.0, 60.0]})

        figs = [
            plots.plot_fleet_mix(fleet, f"{out}/a.png"),
            plots.plot_avg_duration(fleet, f"{out}/b.png"),
            plots.plot_hourly_overall(hourly, f"{out}/c.png"),
            plots.plot_weekday(weekday, f"{out}/d.png"),
            plots.plot_monthly_trend(monthly, f"{out}/e.png"),
            plots.plot_station_bars(top, "trip_count", "t", save_path=f"{out}/f.png"),
            plots.plot_dashboard(hourly, weekday, monthly, fleet, top, weather, f"{out}/g.png"),
        ]
        for f in figs:
            plots.plt.close(f)
        self.assertEqual(len([x for x in os.listdir(out) if x.endswith(".png")]), 7)


if __name__ == "__main__":
    unittest.main()
