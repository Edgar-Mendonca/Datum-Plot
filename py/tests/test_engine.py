"""Engine tests: statistics against values from R, graphs render and report their geometry.
Run: python -m unittest discover -s py/tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from datum import graph, stats  # noqa: E402


def table(cols, sets, excluded=()):
    return {"rows": max(len(c) for c in cols), "xTitle": "Time", "xUnits": "h", "yTitle": "Response", "yUnits": "", "sets": sets, "cols": cols, "excluded": [list(e) for e in excluded]}


REP3 = {"title": "Control", "entry": "rep", "reps": 3}


class Stats(unittest.TestCase):
    def test_describe_matches_r(self):
        # R: x <- c(2.1, 2.5, 2.9); mean(x); sd(x); sd(x)/sqrt(3); qt(.975, 2) * sd(x)/sqrt(3)
        d = stats.describe([2.1, 2.5, 2.9])
        self.assertAlmostEqual(d["mean"], 2.5, places=12)
        self.assertAlmostEqual(d["sd"], 0.4, places=12)
        self.assertAlmostEqual(d["sem"], 0.2309401077, places=9)
        self.assertAlmostEqual(d["ci"], 0.9936551, places=6)

    def test_ci_large_n(self):
        # R: x <- 1:20; qt(.975, 19) * sd(x) / sqrt(20)  -> 2.768811
        self.assertAlmostEqual(stats.describe(list(range(1, 21)))["ci"], 2.768811, places=5)

    def test_single_value_has_no_spread(self):
        d = stats.describe([4.0, None])
        self.assertEqual((d["n"], d["sd"], d["sem"], d["ci"]), (1, 0.0, 0.0, 0.0))
        self.assertIsNone(stats.describe([None]))

    def test_excluded_and_empty_cells_are_skipped(self):
        t = table([[1, 2, None], [10, 20, 30], [12, 99, 30], [None, 22, 30]], [REP3], excluded=[(1, 2)])
        s = stats.summarize(t)[0]
        self.assertEqual([p["x"] for p in s], [1, 2])  # row 3 has no X
        self.assertEqual(s[0]["values"], [10, 12])
        self.assertEqual(s[1]["values"], [20, 22])  # 99 is excluded
        self.assertAlmostEqual(s[1]["mean"], 21)

    def test_entered_mean_sd_n(self):
        t = table([[1], [5.0], [2.0], [4]], [{"title": "A", "entry": "msn", "reps": 1}])
        p = stats.summarize(t)[0][0]
        self.assertAlmostEqual(p["sem"], 1.0)
        self.assertAlmostEqual(p["ci"], 3.182446 * 1.0, places=5)  # R: qt(.975, 3)
        t["sets"][0]["entry"] = "mesn"
        p = stats.summarize(t)[0][0]
        self.assertAlmostEqual(p["sd"], 4.0)

    def test_set_columns(self):
        t = table([[0]] * 6, [REP3, {"entry": "msn", "reps": 1}])
        self.assertEqual(stats.set_columns(t), [(1, 3), (4, 3)])


class Graphs(unittest.TestCase):
    T = table([[1, 2, 4, 8], [1, 2, 3, 4], [1.2, 2.2, 3.1, 4.4], [0.9, 1.8, 2.7, 4.1], [2, 3, 4, 5], [2.1, 3.3, 4.2, 5.1], [None] * 4],
              [REP3, {"title": "Treated", "entry": "rep", "reps": 3}])

    def test_render_svg_and_geometry(self):
        r = graph.render(self.T, {"width": 80, "height": 60, "error": "sem"})
        self.assertTrue(r["svg"].lstrip().startswith("<?xml"))
        self.assertIn("<svg", r["svg"])
        self.assertAlmostEqual(r["w"], 80 / 25.4 * 72, places=3)
        x0, y0, x1, y1 = r["plot"]
        self.assertTrue(0 < x0 < x1 < r["w"] and 0 < y0 < y1 < r["h"])
        self.assertIsNotNone(r["legend"])  # two data sets
        self.assertEqual(len(r["points"]), 8)
        self.assertEqual(r["ylim"][0], 0)  # positive data: Y starts at zero
        self.assertIn("Time (h)", r["svg"])  # text stays text (editable in Illustrator)

    def test_log_axis_and_fixed_range(self):
        r = graph.render(self.T, {"x": {"scale": "log"}, "y": {"auto": False, "min": 0, "max": 10, "step": 2}})
        self.assertTrue(r["xlog"])
        self.assertEqual(r["ylim"], [0, 10])

    def test_each_replicate_frame_style_and_hidden_set(self):
        r = graph.render(self.T, {"points": "each", "style": "frame", "line": True, "sets": [{}, {"show": False}]})
        self.assertIsNone(r["legend"])
        self.assertEqual(len(r["points"]), 4)

    def test_empty_table(self):
        r = graph.render(table([[]], [REP3]), {})
        self.assertIn("Enter X and Y values", r["svg"])

    def test_export_formats(self):
        with tempfile.TemporaryDirectory() as d:
            for fmt in ("png", "svg", "pdf", "tiff", "eps"):
                p = os.path.join(d, f"g.{fmt}")
                graph.export(self.T, {}, fmt, p, dpi=150)
                self.assertGreater(os.path.getsize(p), 500, fmt)
            with open(os.path.join(d, "g.png"), "rb") as f:
                self.assertEqual(f.read(8), b"\x89PNG\r\n\x1a\n")
        self.assertTrue(graph.export(self.T, {}, "png", dpi=72)["data"].startswith("iVBOR"))


class Worker(unittest.TestCase):
    def test_protocol(self):
        p = subprocess.Popen([sys.executable, os.path.join(os.path.dirname(HERE), "worker.py")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.assertTrue(json.loads(p.stdout.readline())["ready"])
        for q in ({"cmd": "ping"}, {"cmd": "nope"}, {"cmd": "render", "table": Graphs.T, "graph": {}}):
            p.stdin.write(json.dumps(q) + "\n")
            p.stdin.flush()
        a, b, c = (json.loads(p.stdout.readline()) for _ in range(3))
        p.stdin.close()
        p.wait(10)
        self.assertTrue(a["ok"] and "matplotlib" in a)
        self.assertFalse(b["ok"])
        self.assertIn("Unknown request", b["error"])
        self.assertTrue(c["ok"] and "<svg" in c["svg"])


if __name__ == "__main__":
    unittest.main()


class Import(unittest.TestCase):
    def test_csv_and_semicolon_decimal_comma(self):
        from datum import io as dio
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "a.csv")
            open(p, "w", encoding="utf-8").write("Strain,Sample 1,Sample 2\n0,0,0\n0.01,70.5,68\n\n")
            s = dio.read_file(p)["sheets"][0]
            self.assertEqual(s["rows"], [["Strain", "Sample 1", "Sample 2"], ["0", "0", "0"], ["0.01", "70.5", "68"]])
            p = os.path.join(d, "b.txt")
            open(p, "w", encoding="cp1252").write("Temp;Résistance\n20;1,5\n30;2,25\n")
            s = dio.read_file(p)["sheets"][0]
            self.assertEqual(s["rows"][0][1], "Résistance")
            self.assertEqual(s["rows"][2], ["30", "2.25"])

    def test_excel_every_sheet(self):
        from openpyxl import Workbook
        from datum import io as dio
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "w.xlsx")
            wb = Workbook()
            wb.active.title = "Run 1"
            for r in (["T", "R"], [1, 2.5], [2.0, None]):
                wb.active.append(r)
            wb.create_sheet("Empty")
            wb.save(p)
            s = dio.read_file(p)["sheets"]
            self.assertEqual([x["name"] for x in s], ["Run 1", "Empty"])
            self.assertEqual(s[0]["rows"], [["T", "R"], ["1", "2.5"], ["2", ""]])
            self.assertEqual(s[1]["rows"], [])
        with self.assertRaises(ValueError):
            dio.read_file("x.ods")
