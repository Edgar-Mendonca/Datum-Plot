"""3D and surface fits (A10, B26, D11) against surfaces known by construction: an exact quadratic
(coefficients and its maximum), a 2D Gaussian peak (centre and widths), and the matrix, polar and
broken column graphs drawing. Run: python -m unittest discover -s py/tests"""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datum import analysis as A, graph  # noqa: E402

XS, YS = np.linspace(0, 10, 11), np.array([0, 2, 4, 6, 8])


def matrix(f):
    """X down the rows, Y values as the data sets' titles, Z in the cells."""
    return {"name": "M", "kind": "matrix", "rows": len(XS), "xTitle": "X", "yTitle": "Hardness", "yUnits": "HV", "excluded": [],
            "sets": [{"title": f"{y:g}", "entry": "rep", "reps": 1} for y in YS], "cols": [list(XS)] + [[float(f(x, y)) for x in XS] for y in YS]}


class Surfaces(unittest.TestCase):
    def test_quadratic_coefficients_and_maximum(self):
        f = lambda x, y: 50 + 4 * x + 6 * y - 0.4 * x * x + 0.1 * x * y - 0.5 * y * y
        r = A.run("surface", matrix(f), [], {"model": "quad"})
        p = [float(row[1]) for row in r["tabs"][0]["tables"][0]["rows"]]
        self.assertTrue(np.allclose(p, [50, 4, 6, -0.4, 0.1, -0.5], atol=1e-6))
        sp = {row[0]: row[1] for row in r["tabs"][0]["tables"][2]["rows"]}
        H = np.array([[-0.8, 0.1], [0.1, -1.0]])
        xs, ys = np.linalg.solve(H, [-4, -6])
        self.assertEqual(sp["Kind"], "maximum")
        self.assertAlmostEqual(float(sp["x"]), xs, 3)
        self.assertAlmostEqual(float(sp["y"]), ys, 3)
        self.assertEqual(len(r["surface"]["z"]), 40)

    def test_gaussian_peak(self):
        f = lambda x, y: 200 + 80 * np.exp(-((x - 4.5) ** 2 / (2 * 1.5 ** 2) + (y - 3.0) ** 2 / (2 * 2.0 ** 2)))
        r = A.run("surface", matrix(f), [], {"model": "gauss"})
        p = {row[0]: float(row[1]) for row in r["tabs"][0]["tables"][0]["rows"]}
        self.assertAlmostEqual(p["Centre x0"], 4.5, 3)
        self.assertAlmostEqual(p["Centre y0"], 3.0, 3)
        self.assertAlmostEqual(abs(p["Width σx"]), 1.5, 3)
        self.assertAlmostEqual(p["Height A"], 80, 2)

    def test_three_columns_of_a_table_of_many_variables(self):
        rng = np.random.default_rng(2)
        x, y = rng.uniform(0, 5, 30), rng.uniform(0, 5, 30)
        z = 3 + 2 * x - y
        t = {"name": "T", "kind": "multi", "rows": 30, "excluded": [], "sets": [{"title": n, "entry": "rep", "reps": 1} for n in "xyz"], "cols": [[None] * 30, list(x), list(y), list(z)]}
        r = A.run("surface", t, [], {"model": "plane"})
        self.assertEqual([row[1] for row in r["tabs"][0]["tables"][0]["rows"]], ["3", "2", "-1"])
        self.assertNotIn("surface", r)


class Graphs3D(unittest.TestCase):
    def test_matrix_kinds_and_fit_overlay(self):
        t = matrix(lambda x, y: x * y)
        for kind in ("contour", "heatmap", "surface", "wireframe"):
            out = graph.render(t, {"column": kind, "palette": "magma"}, [{"kind": "surface", "options": {"model": "quad"}}])
            self.assertIn("<svg", out["svg"], kind)
            self.assertIn("HV", out["svg"], kind)  # the colour bar or Z axis title

    def test_polar_and_broken_column_graph(self):
        from test_analysis import xy
        out = graph.render(xy([0, 90, 180, 270], [1, 2, 1, 2]), {"polar": True})
        self.assertIn("<svg", out["svg"])
        from test_groups import col
        out = graph.render(col([1, 2, 3], [2, 3, 4], [100, 110, 120]), {"column": "bars", "y": {"breakFrom": 10, "breakTo": 90}})
        self.assertEqual(len([p for p in out["points"] if p]), 3)
        self.assertIn("<svg", out["svg"])
