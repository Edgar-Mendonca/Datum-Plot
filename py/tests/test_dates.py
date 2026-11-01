"""Dates (0.3.11): an X column flagged as dates (days since 1970, matplotlib's epoch) draws a date axis in every
export, fits on dates report per day, and workbooks write real dates. Run: python -m unittest discover -s py/tests"""
import os
import re
import sys
import tempfile
import unittest
import warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datum import analysis as A, graph, io as dio  # noqa: E402

# Datum Plan's hand-off: 20738 is 12 Oct 2026.
PLAN = {"id": 1, "name": "Project S-curve", "kind": "xy", "xTitle": "Date", "xUnits": "", "xFormat": "date", "yTitle": "Cumulative progress", "yUnits": "%",
        "rows": 3, "rowTitles": ["2026-10-12", "2026-10-19", "2026-10-26"], "excluded": [],
        "sets": [{"title": "Planned (baseline)", "entry": "rep", "reps": 1}, {"title": "Actual", "entry": "rep", "reps": 1}],
        "cols": [[20738, 20745, 20752], [0, 12.5, 31.0], [0, 10.0, None]]}
SETTINGS = {"line": True, "error": "none", "width": 160, "height": 100}


def ticks(svg):
    return re.findall(r">([^<>]+)</text>", svg)


class Dates(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore")

    def test_the_plan_sample_draws_a_date_axis_in_every_format(self):
        labels = " ".join(ticks(graph.render(PLAN, SETTINGS)["svg"]))
        self.assertTrue("Oct" in labels or "2026" in labels, labels[:300])
        self.assertNotIn("20740", labels, "no day numbers on the axis")
        iso = " ".join(ticks(graph.render(PLAN, dict(SETTINGS, x={"dates": "iso"}))["svg"]))
        self.assertIn("2026-10-", iso)
        week = " ".join(ticks(graph.render(PLAN, dict(SETTINGS, x={"dates": "week"}))["svg"]))
        self.assertRegex(week, r"W4[1-4]")
        for fmt in ("png", "tiff", "svg", "pdf", "eps"):
            self.assertTrue(graph.export(PLAN, SETTINGS, fmt, None)["data"], fmt)
        self.assertNotIn("Oct", " ".join(ticks(graph.render(dict(PLAN, xFormat=""), SETTINGS)["svg"])), "without the flag, numbers as before")

    def test_fits_on_dates_are_per_day_and_workbooks_write_dates(self):
        t = dict(PLAN, cols=[[20738 + i for i in range(5)], [1, 1.5, 2, 2.6, 3], [None] * 5], sets=PLAN["sets"][:1], rows=5)
        self.assertIn("per day", A.run("linear", t, [], {})["answer"])
        from openpyxl import load_workbook
        with tempfile.TemporaryDirectory() as d:
            dio.write_excel(os.path.join(d, "p.xlsx"), {"name": "P", "tables": [PLAN]}, [])
            cell = load_workbook(os.path.join(d, "p.xlsx")).worksheets[0]["A2"].value
            self.assertEqual((cell.year, cell.month, cell.day), (2026, 10, 12))


if __name__ == "__main__":
    unittest.main()
