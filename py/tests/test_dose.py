"""IC50 / EC50 (B38, 0.4.11) and comparing them (B39, 0.4.12). Checked against R's drc package: its ryegrass data
(root length against herbicide concentration, data(ryegrass)) fitted with LL.4 give b = 2.98222, c = 0.48141,
d = 7.79296, e = 3.05795 and a residual standard error of 0.5196 on 20 degrees of freedom (drc documentation;
Ritz et al. 2015, PLOS ONE). drc's b is our Hill slope with the opposite sign. The other data are made up.
Run: python -m unittest discover -s py/tests"""
import math
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datum import analysis as A, dose  # noqa: E402

CONC = [0] * 6 + [0.94] * 3 + [1.88] * 3 + [3.75] * 3 + [7.5] * 3 + [15] * 3 + [30] * 3
ROOTL = [7.58, 8.0, 8.328571, 7.25, 7.375, 7.9625, 8.355556, 6.914286, 7.75, 6.871429, 6.45, 5.922222,
         1.925, 2.885714, 4.233333, 1.1875, 0.857143, 1.057143, 0.6875, 0.525, 0.825, 0.25, 0.22, 0.44]


def xy(x, *ys, reps=1):
    """An XY table: X, then each data set with `reps` replicates side by side."""
    n = len(x)
    cols = [list(map(float, x))]
    for y in ys:
        for r in range(reps):
            cols.append([float(v[r]) if isinstance(v, (list, tuple)) else float(v) for v in y] if reps > 1 else list(map(float, y)))
    return {"name": "D", "kind": "xy", "rows": n, "xTitle": "Concentration", "xUnits": "", "yTitle": "Response", "excluded": [],
            "sets": [{"title": f"Compound {chr(65 + i)}", "entry": "rep", "reps": reps} for i in range(len(ys))], "cols": cols}


def value(res, label, col=1, table=0):
    for row in res["tabs"][0]["tables"][table]["rows"]:
        if row[0] == label:
            return row[col]
    raise KeyError(label)


class Ic50(unittest.TestCase):
    def test_matches_drc_on_ryegrass(self):
        p, cov, sy, df, _ = dose.fit(np.array(CONC, float), np.array(ROOTL), falling=True)
        b, t, lx, h = p
        self.assertAlmostEqual(-h, 2.98222, places=4)
        self.assertAlmostEqual(b, 0.48141, places=4)
        self.assertAlmostEqual(t, 7.79296, places=4)
        self.assertAlmostEqual(10 ** lx, 3.05795, places=4)
        self.assertAlmostEqual(sy, 0.5196256, places=6)
        self.assertEqual(df, 20)
        r = A.run("ic50", xy(CONC, ROOTL), [], {})
        self.assertTrue(r["answer"].startswith("Compound A: IC50 = 3.058"), r["answer"])
        lo, hi = map(float, value(r, "IC50", 2).split(" to "))
        self.assertTrue(lo < 3.058 < hi and abs(math.log10(3.058) - math.log10(lo) - (math.log10(hi) - math.log10(3.058))) < 1e-3, "even on the log scale (to the 4 digits shown)")
        self.assertTrue(r["curves"] and len(r["curves"][0]["x"]) == 200)

    def test_three_parameters_log_x_and_pic50(self):
        c = np.array([1, 3, 10, 30, 100, 300, 1000], float)  # nM, made up: IC50 = 40 nM, Hill −1
        y = 5 + 90 / (1 + (c / 40))
        r = A.run("ic50", xy(np.log10(c), y), [], {"xlog": True, "model": "3", "unit": "nM"})
        self.assertAlmostEqual(float(value(r, "IC50").split()[0]), 40, places=3)
        self.assertAlmostEqual(float(value(r, "pIC50 (−log10 molar)")), -math.log10(40e-9), places=3)
        self.assertEqual(value(r, "Hill slope", 2), "fixed (3-parameter model)")

    def test_stimulation_normalised_and_fixed(self):
        c = np.array([0, 0.1, 0.3, 1, 3, 10, 30], float)  # made up: EC50 = 2, rising from 200 to 1200
        y = np.array([200.0] + [200 + 1000 / (1 + (2 / v) ** 1.5) for v in c[1:]])
        r = A.run("ic50", xy(c, y), [], {"normalize": "values", "zero": 200, "hundred": 1200, "fix": True})
        self.assertIn("EC50", r["answer"])
        self.assertAlmostEqual(float(value(r, "EC50").split()[0]), 2, places=3)
        self.assertEqual(value(r, "Top", 2), "fixed at 100 %")
        with self.assertRaises(ValueError):
            A.run("ic50", xy(c, y), [], {"normalize": "values", "zero": 5, "hundred": 5})

    def test_says_why_it_cannot_fit(self):
        with self.assertRaises(ValueError) as e:
            A.run("ic50", xy([1, 2, 3], [9, 5, 1]), [], {})
        self.assertIn("four concentrations", str(e.exception))

    def test_compare_two_compounds(self):
        # 0.4.12 (B39): made up, IC50 10 and 75 (7.5-fold), triplicates with a little noise; and two the same
        rng = np.random.default_rng(4)
        c = np.array([1, 3, 10, 30, 100, 300, 1000], float)
        a = [tuple(100 / (1 + (v / 10)) + rng.normal(0, 2, 3)) for v in c]
        b = [tuple(100 / (1 + (v / 75)) + rng.normal(0, 2, 3)) for v in c]
        r = A.run("ic50", xy(c, a, b, reps=3), [], {"compare": True})
        comp = r["tabs"][1]["tables"][0]["rows"]
        self.assertEqual(comp[0][2], "Yes")
        self.assertAlmostEqual(float(comp[1][1]), 7.5, delta=1.0)
        self.assertIn("less potent", comp[1][2])
        same = [tuple(100 / (1 + (v / 10)) + rng.normal(0, 2, 3)) for v in c]
        r = A.run("ic50", xy(c, a, same, reps=3), [], {"compare": True})
        self.assertEqual(r["tabs"][1]["tables"][0]["rows"][0][2], "No")


if __name__ == "__main__":
    unittest.main()
