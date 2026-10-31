"""Ternary, bubble, waterfall and radar graphs (D19): each draws, places its data where it belongs, and
says why when the table cannot make it. Run: python -m unittest discover -s py/tests"""
import math
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datum import graph  # noqa: E402
from datum.graph import Figure, FigureCanvasAgg, MM  # noqa: E402
from datum import special  # noqa: E402


def multi(rows, names):
    n = len(rows)
    return {"kind": "multi", "rows": n, "rowTitles": [], "excluded": [], "sets": [{"title": t, "entry": "rep", "reps": 1} for t in names],
            "cols": [[None] * n] + [[r[k] for r in rows] for k in range(len(names))]}


def fig():
    f = Figure(figsize=(80 * MM, 60 * MM), dpi=72, layout="constrained")
    FigureCanvasAgg(f)
    return f, f.add_subplot()


class SpecialGraphs(unittest.TestCase):
    def test_ternary_puts_each_row_by_its_shares(self):
        t = multi([[100, 0, 0], [0, 50, 0], [0, 0, 7], [1, 1, 1]], ["A", "B", "C"])
        f, ax = fig()
        f, ax, _, _ = special.ternary_figure(f, ax, t, {}, ["#000"], 10)
        pts = ax.collections[0].get_offsets()
        self.assertTrue(np.allclose(pts[0], [0.5, math.sqrt(3) / 2]) and np.allclose(pts[1], [0, 0]) and np.allclose(pts[2], [1, 0]))
        self.assertTrue(np.allclose(pts[3], [0.5, math.sqrt(3) / 6]), "equal shares sit at the centre")
        with self.assertRaises(ValueError):
            special.ternary_figure(*fig(), multi([[1, 2]], ["A", "B"]), {}, ["#000"], 10)

    def test_waterfall_lifts_each_curve_by_the_chosen_step(self):
        t = {"kind": "xy", "rows": 3, "xTitle": "X", "yTitle": "Y", "excluded": [], "sets": [{"title": s, "entry": "rep", "reps": 1} for s in "PQR"],
             "cols": [[1, 2, 3], [0, 1, 0], [0, 1, 0], [0, 1, 0]]}
        f, ax, _, _ = graph.figure(t, {"column": "waterfall", "offset": 5})
        ys = [line.get_ydata() for line in ax.get_lines()]
        self.assertEqual([float(y[1]) for y in ys], [1.0, 6.0, 11.0])

    def test_radar_and_bubble_draw_and_render(self):
        rng = np.random.default_rng(1)
        g = {"kind": "grouped", "rows": 4, "rowTitles": list("abcd"), "excluded": [], "sets": [{"title": s, "entry": "rep", "reps": 2} for s in "XY"],
             "cols": [[None] * 4] + [list(rng.uniform(1, 5, 4)) for _ in range(4)]}
        r = graph.render(g, {"column": "radar"})
        self.assertIn("<svg", r["svg"])
        self.assertEqual(len(r["colors"]), 2)
        with self.assertRaises(ValueError):
            graph.render(dict(g, rows=2), {"column": "radar"})
        for names in (["X", "Y", "Size"], ["X", "Y", "Size", "Colour"]):
            m = multi([list(rng.uniform(1, 9, len(names))) for _ in range(12)], names)
            self.assertIn("<svg", graph.render(m, {"column": "bubble"})["svg"])
            self.assertTrue(graph.export(m, {"column": "ternary"}, "pdf", None)["data"])


if __name__ == "__main__":
    unittest.main()
