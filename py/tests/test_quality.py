"""Control charts and factorial designs (B35): the limits equal the textbook constants (A2, D4, A3, B4,
2.66 and 3.267 for individuals, the binomial for p), and factorial effects recover known ones, with Lenth's
method when the design has no residual. Run: python -m unittest discover -s py/tests"""
import itertools
import os
import sys
import unittest
import warnings

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datum import analysis as A  # noqa: E402


def lims(r, i=0):
    row = r["tabs"][0]["tables"][0]["rows"][i]
    return [float(v) for v in row[1:4]]


class ControlCharts(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore")
        rng = np.random.default_rng(3)
        self.v = rng.normal(10, 0.5, (20, 5))
        self.t = {"kind": "grouped", "rows": 20, "rowTitles": [], "excluded": [], "sets": [{"title": "D", "entry": "rep", "reps": 5}],
                  "cols": [[None] * 20] + [list(self.v[:, j]) for j in range(5)]}

    def test_limits_match_the_table_constants(self):
        xbb, rbar = self.v.mean(), np.ptp(self.v, axis=1).mean()
        c, lo, hi = lims(A.run("control", self.t, [], {"chart": "xbar"}))
        self.assertAlmostEqual(hi - c, 0.577 * rbar, delta=2e-3)          # A2(5) = 0.577
        self.assertAlmostEqual(lims(A.run("control", self.t, [], {"chart": "xbar"}), 1)[2], 2.114 * rbar, delta=3e-3)  # D4(5)
        sbar = self.v.std(axis=1, ddof=1).mean()
        c, lo, hi = lims(A.run("control", self.t, [], {"chart": "xbar_s"}))
        self.assertAlmostEqual(hi - c, 1.427 * sbar, delta=2e-3)          # A3(5) = 1.427
        self.assertAlmostEqual(lims(A.run("control", self.t, [], {"chart": "xbar_s"}), 1)[2], 2.089 * sbar, delta=3e-3)  # B4(5)
        x = self.v.ravel()
        mr = np.abs(np.diff(x)).mean()
        c, lo, hi = lims(A.run("control", self.t, [], {"chart": "imr"}))
        self.assertAlmostEqual(hi - c, 2.66 * mr, delta=2e-3)
        self.assertAlmostEqual(c, x.mean(), delta=1e-3)

    def test_p_chart_capability_and_signals(self):
        d = [3, 5, 2, 4, 6, 3, 15, 4, 2, 5, 3, 4]
        pt = {"kind": "grouped", "rows": 12, "rowTitles": [], "excluded": [], "sets": [{"title": "Defective", "entry": "rep", "reps": 1}, {"title": "Inspected", "entry": "rep", "reps": 1}],
              "cols": [[None] * 12, d, [100] * 12]}
        r = A.run("control", pt, [], {"chart": "p"})
        pbar = sum(d) / 1200
        self.assertAlmostEqual(lims(r)[2], pbar + 3 * np.sqrt(pbar * (1 - pbar) / 100), delta=1e-4)
        self.assertIn("1 point beyond the limits", r["answer"])
        cap = A.run("control", self.t, [], {"chart": "xbar", "lsl": 8, "usl": 12})
        self.assertIn("Cpk", cap["answer"])
        # Ten subgroups centred at 9.9, then ten at 10.1 (the same spread in each): no point beyond the limits, but a run.
        spread = [-0.5, -0.25, 0, 0.25, 0.5]
        shifted = dict(self.t, cols=[[None] * 20] + [[(9.9 if i < 10 else 10.1) + spread[j] for i in range(20)] for j in range(5)])
        r = A.run("control", shifted, [], {"chart": "xbar"})
        self.assertIn("run on one side", r["answer"])
        self.assertTrue(any("8 points on one side" in c[1] for c in r["checks"]))


class Factorial(unittest.TestCase):
    def test_effects_are_recovered_with_and_without_replicates(self):
        rng = np.random.default_rng(1)
        runs = [(a, b, c) for _ in range(2) for a, b, c in itertools.product([-1, 1], repeat=3)]
        y = [50 + 5 * a - 3 * b + 2 * a * b + rng.normal(0, 0.3) for a, b, c in runs]
        d = {"kind": "multi", "rows": 16, "rowTitles": [], "excluded": [], "sets": [{"title": t, "entry": "rep", "reps": 1} for t in ["T", "P", "C", "Yield"]],
             "cols": [[None] * 16, [150 + 25 * a for a, _, _ in runs], [1 + 0.5 * b for _, b, _ in runs], [c for *_, c in runs], y]}
        rows = {r[0]: float(r[1]) for r in A.run("doe", d, [], {})["tabs"][0]["tables"][0]["rows"]}
        self.assertAlmostEqual(rows["T"], 10, delta=0.5)
        self.assertAlmostEqual(rows["P"], -6, delta=0.5)
        self.assertAlmostEqual(rows["T × P"], 4, delta=0.5)
        sat = dict(d, rows=4, sets=[d["sets"][0], d["sets"][1], d["sets"][3]], cols=[[None] * 4, [-1, 1, -1, 1], [-1, -1, 1, 1], [40, 60, 34, 66]])
        r = A.run("doe", sat, [], {})
        self.assertIn("Lenth", r["tabs"][0]["tables"][0]["title"])
        with self.assertRaises(ValueError):
            A.run("doe", dict(sat, cols=[[None] * 4, [1, 2, 3, 4], [-1, -1, 1, 1], [1, 2, 3, 4]]), [], {})


if __name__ == "__main__":
    unittest.main()
