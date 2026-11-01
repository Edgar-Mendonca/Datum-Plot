"""More statistics (B34), each against an independent result: kappa by its formula, McNemar's exact test by
the binomial, three-way ANOVA by the balanced closed-form sums of squares, ANCOVA by nested models, the
bootstrap repeatable with a fixed seed, and the smoothing spline by SciPy. Run: python -m unittest discover -s py/tests"""
import os
import sys
import unittest
import warnings

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datum import analysis as A  # noqa: E402


def counts(M, names, sets=None):
    k = len(M[0])
    return {"kind": "contingency", "rows": len(M), "rowTitles": names, "excluded": [], "sets": [{"title": n, "entry": "rep", "reps": 1} for n in (sets or names)],
            "cols": [[None] * len(M)] + [[float(M[r][c]) for r in range(len(M))] for c in range(k)]}


class MoreStatistics(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore")

    def test_kappa_by_its_formula_and_mcnemar_by_the_binomial(self):
        M = np.array([[20, 5], [10, 15]], float)
        r = A.run("agreement", counts(M, ["Yes", "No"]), [], {})
        n = M.sum()
        po, pe = np.trace(M) / n, (M.sum(0) * M.sum(1)).sum() / n ** 2
        self.assertIn(f"kappa = {round((po - pe) / (1 - pe), 3):g}", r["answer"])
        exact = 2 * stats.binom.cdf(5, 15, 0.5)
        rows = r["tabs"][0]["tables"][1]["rows"][0]
        self.assertTrue(rows[0].startswith("McNemar's test (exact"))
        self.assertAlmostEqual(float(rows[2]), exact, places=3)
        big = A.run("agreement", counts([[10, 2, 1], [3, 12, 2], [1, 2, 9]], ["Low", "Mid", "High"]), [], {"weights": "quadratic"})
        self.assertIn("Bowker", big["tabs"][0]["tables"][1]["rows"][0][0])
        with self.assertRaises(ValueError):
            A.run("agreement", counts([[1, 2, 3], [4, 5, 6]], ["a", "b"], ["a", "b", "c"]), [], {})

    def test_three_way_anova_matches_the_balanced_sums_of_squares(self):
        rng = np.random.default_rng(3)
        n, rows, sets = 3, 2, [("Young / Drug"), ("Young / Placebo"), ("Old / Drug"), ("Old / Placebo")]
        cols = [[None] * rows]
        for k in range(4):
            for j in range(n):
                cols.append([10 + r + (k % 2) * 2 + (k // 2) + rng.normal(0, 1) for r in range(rows)])
        t = {"kind": "grouped", "rows": rows, "rowTitles": ["Male", "Female"], "excluded": [], "sets": [{"title": s, "entry": "rep", "reps": n} for s in sets], "cols": cols}
        r = A.run("threeway", t, [], {"rowname": "Sex", "bname": "Age", "cname": "Treatment"})
        y = np.array([[[cols[1 + k * n + j][rr] for j in range(n)] for k in range(4)] for rr in range(rows)])  # rows × sets × reps
        ssA = 4 * n * ((y.mean((1, 2)) - y.mean()) ** 2).sum()
        tab = {row[0]: row for row in r["tabs"][0]["tables"][0]["rows"]}
        self.assertAlmostEqual(float(tab["Sex"][1]), ssA, delta=1e-3 * max(ssA, 1))
        self.assertIn("Sex × Age × Treatment", tab)
        with self.assertRaises(ValueError):
            A.run("threeway", dict(t, sets=[{"title": "no slash", "entry": "rep", "reps": n}] * 4), [], {})

    def test_ancova_against_nested_models(self):
        import pandas as pd
        import statsmodels.formula.api as smf
        rng = np.random.default_rng(1)
        x = np.linspace(0, 10, 12)
        ys = [2 + 0.5 * x + rng.normal(0, 0.4, 12), 4 + 0.5 * x + rng.normal(0, 0.4, 12)]
        t = {"kind": "xy", "rows": 12, "xTitle": "Age", "excluded": [], "sets": [{"title": s, "entry": "rep", "reps": 1} for s in "AB"], "cols": [list(x), list(ys[0]), list(ys[1])]}
        r = A.run("ancova", t, [], {})
        df = pd.DataFrame({"G": ["A"] * 12 + ["B"] * 12, "x": np.r_[x, x], "y": np.r_[ys[0], ys[1]]})
        small, big = smf.ols("y ~ x", df).fit(), smf.ols("y ~ C(G) + x", df).fit()
        F = ((small.ssr - big.ssr) / 1) / (big.ssr / big.df_resid)
        self.assertIn(f"F = {float(f'{F:.4g}'):g}", r["answer"])
        self.assertEqual(len(r["curves"]), 2)

    def test_bootstrap_is_repeatable_and_brackets_the_estimate(self):
        rng = np.random.default_rng(2)
        t = {"kind": "column", "rows": 20, "excluded": [], "sets": [{"title": s, "entry": "rep", "reps": 1} for s in "AB"], "cols": [[None] * 20, list(rng.normal(10, 2, 20)), list(rng.normal(13, 2, 20))]}
        a, b = A.run("bootstrap", t, [], {"stat": "mean", "n": 2000}), A.run("bootstrap", t, [], {"stat": "mean", "n": 2000})
        self.assertEqual(a["answer"], b["answer"])
        lo, hi = (float(v) for v in a["tabs"][0]["tables"][0]["rows"][0][3].split(" to "))
        self.assertTrue(lo < np.mean(t["cols"][1]) < hi)
        self.assertIn("excludes 0", a["answer"])

    def test_smoothing_spline_matches_scipy(self):
        from scipy.interpolate import make_smoothing_spline
        x = np.linspace(0, 6, 30)
        y = np.sin(x) + np.random.default_rng(4).normal(0, 0.1, 30)
        t = {"kind": "xy", "rows": 30, "xTitle": "X", "excluded": [], "sets": [{"title": "S", "entry": "rep", "reps": 1}], "cols": [list(x), list(y)]}
        r = A.run("smooth", t, [], {"method": "spline"})
        self.assertTrue(np.allclose(r["table"]["cols"][1], make_smoothing_spline(x, y)(x)))
        self.assertEqual(len(r["curves"][0]["x"]), 200)


if __name__ == "__main__":
    unittest.main()
