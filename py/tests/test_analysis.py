"""Analyses against published values: R's lm() on Anscombe's data, NIST StRD Misra1a, R's
shapiro.test(), and hand-checkable cases. Run: python -m unittest discover -s py/tests"""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datum import analysis as A  # noqa: E402


def xy(x, *ys, reps=1):
    """An XY table: X and data sets of `reps` columns each."""
    cols = [list(x)] + [list(c) for c in ys]
    n = len(ys) // reps
    return {"rows": len(x), "sets": [{"title": f"S{k}", "entry": "rep", "reps": reps} for k in range(n)], "cols": cols, "excluded": [], "xTitle": "X", "yTitle": "Y"}


def num(s):
    return float(str(s).split()[0])


def cell(res, title, row, col=1, tab=0, t=0):
    tbl = res["tabs"][tab]["tables"][t]
    return next(r for r in tbl["rows"] if r[0] == title)[col] if row is None else tbl["rows"][row][col]


AX = [10, 8, 13, 9, 11, 14, 6, 4, 12, 7, 5]
AY = [8.04, 6.95, 7.58, 8.81, 8.33, 9.96, 7.24, 4.26, 10.84, 4.82, 5.68]


class Linear(unittest.TestCase):
    def test_anscombe_matches_r_lm(self):
        # R: summary(lm(y1 ~ x1, anscombe)): slope 0.5001 (SE 0.1179), intercept 3.0001 (SE 1.1247),
        # R² 0.6665, adj 0.6295, residual SE 1.237, F 17.99, p 0.00217
        r = A.run("linear", xy(AX, AY), [], {})
        self.assertAlmostEqual(num(cell(r, "Slope", None)), 0.5001, places=4)
        self.assertAlmostEqual(num(cell(r, "Slope", None, 2)), 0.1179, places=4)
        self.assertAlmostEqual(num(cell(r, "Y-intercept", None)), 3.0001, places=3)
        self.assertAlmostEqual(num(cell(r, "Y-intercept", None, 2)), 1.1247, places=4)
        self.assertAlmostEqual(num(cell(r, "R squared", None)), 0.6665, places=4)
        self.assertAlmostEqual(num(cell(r, "Adjusted R squared", None)), 0.6295, places=4)
        self.assertAlmostEqual(num(cell(r, "Sy.x", None)), 1.237, places=3)
        self.assertIn("0.0022", cell(r, "Is the slope different from zero?", None))
        c = r["curves"][0]
        self.assertTrue(all(lo <= m <= hi for lo, m, hi in zip(c["lo"], c["y"], c["hi"])))
        self.assertTrue(all(plo <= lo for plo, lo in zip(c["plo"], c["lo"])))
        self.assertIn("Y = 0.5001·X + 3", c["label"])
        self.assertTrue(r["plots"][0]["svg"].lstrip().startswith("<?xml"))

    def test_fit_range_through_origin_and_poly(self):
        x = np.arange(1, 11.0)
        y = 2 * x
        y[-3:] += [5, 9, 14]  # curves away after X = 7
        r = A.run("linear", xy(x, y), [], {"xmax": 7})
        self.assertAlmostEqual(num(cell(r, "Slope", None)), 2.0, places=8)
        r = A.run("linear", xy(x, 3 * x), [], {"model": "origin"})
        self.assertAlmostEqual(num(cell(r, "Slope", None)), 3.0, places=8)
        r = A.run("linear", xy(x, 1 + 2 * x + 0.5 * x * x), [], {"model": "poly", "order": 2})
        self.assertAlmostEqual(num(cell(r, "B2", None)), 0.5, places=6)

    def test_compare_lines_and_interpolate(self):
        x = np.arange(0, 10.0)
        noise = np.array([0.1, -0.1, 0.05, -0.05, 0.1, -0.1, 0.02, -0.02, 0.05, -0.05])
        r = A.run("linear", xy(x, 2 * x + noise, 3 * x - noise), [], {"unknowns": "10, 400"})
        q = next(t for t in r["tabs"][0]["tables"] if t["title"] == "Comparing the lines")
        self.assertIn("differ", q["rows"][0][4])
        rows = next(t for t in r["tabs"] if t["name"] == "Interpolated")["tables"][0]["rows"]
        self.assertAlmostEqual(num(rows[0][2]), 5.0, delta=0.05)
        self.assertEqual(rows[1][2], "outside the curve")

    def test_deming_equals_ols_for_exact_line(self):
        x = np.arange(1, 9.0)
        r = A.run("linear", xy(x, 4 - 1.5 * x), [], {"model": "deming"})
        self.assertAlmostEqual(num(cell(r, "Slope", None)), -1.5, places=6)

    def test_replicates_each_or_mean(self):
        t = xy([1, 2, 3, 4], [1, 2, 3, 4], [1.2, 2.2, 3.2, 4.2], reps=2)
        self.assertEqual(cell(A.run("linear", t, [], {}), "Number of points", None), "8")
        self.assertEqual(cell(A.run("linear", t, [], {"points": "mean"}), "Number of points", None), "4")


class Nonlinear(unittest.TestCase):
    def test_nist_misra1a(self):
        # NIST StRD Misra1a: y = b1*(1 - exp(-b2*x)); certified b1 = 238.94212918, b2 = 5.5015643181E-04
        x = [77.6, 114.9, 141.1, 190.8, 239.9, 289.0, 332.8, 378.4, 434.8, 477.3, 536.8, 593.1, 689.1, 760.0]
        y = [10.07, 14.73, 17.94, 23.93, 29.61, 35.18, 40.02, 44.82, 50.76, 55.05, 61.01, 66.40, 75.47, 81.78]
        r = A.run("fit", xy(x, y), [], {"model": "custom", "equation": "Y = b1*(1 - exp(-b2*X))", "init": {"b1": 500, "b2": 1e-4}})
        self.assertAlmostEqual(num(cell(r, "b1", None)) / 238.94212918, 1, places=4)
        self.assertAlmostEqual(num(cell(r, "b2", None)) / 5.5015643181e-4, 1, places=4)
        self.assertEqual(cell(r, "Converged", None), "Yes")

    def test_library_models_recover_parameters(self):
        x = np.linspace(0.1, 10, 25)
        cases = {"exp_decay": (lambda x: (10 - 2) * np.exp(-0.7 * x) + 2, {"K": 0.7, "Plateau": 2}),
                 "power": (lambda x: 3 * x ** 1.7, {"B": 1.7}),
                 "logistic": (lambda x: 1 + 9 / (1 + np.exp(-1.5 * (x - 5))), {"X50": 5, "Slope": 1.5}),
                 "gauss": (lambda x: 0.5 + 4 * np.exp(-0.5 * ((x - 6) / 0.8) ** 2), {"Center": 6, "Width": 0.8}),
                 "mm": (lambda x: 8 * x / (2 + x), {"Ymax": 8, "K": 2}),
                 "avrami": (lambda x: 1 - np.exp(-0.02 * x ** 2.5), {"n": 2.5})}
        for m, (f, want) in cases.items():
            r = A.run("fit", xy(x, f(x)), [], {"model": m})
            for p, v in want.items():
                self.assertAlmostEqual(num(cell(r, p, None)), v, places=3, msg=m)
        r = A.run("fit", xy(x, 2 * np.exp(-0.5 * x)), [], {"model": "custom", "equation": "Y = A*exp(-k*X)", "fixed": {"A": 2}})
        self.assertEqual(cell(r, "A", None, 2), "fixed")
        self.assertAlmostEqual(num(cell(r, "k", None)), 0.5, places=6)
        self.assertTrue(r["curves"][0]["lo"])

    def test_bad_equation_is_reported(self):
        with self.assertRaises(Exception):
            A.run("fit", xy([1, 2, 3], [1, 2, 3]), [], {"model": "custom", "equation": ""})


class Arrhenius(unittest.TestCase):
    def test_activation_energy(self):
        Ea, A0 = 75000.0, 1e9
        T = np.array([300.0, 320, 340, 360, 380, 400])
        k = A0 * np.exp(-Ea / (8.314462618 * T))
        r = A.run("arrhenius", xy(T - 273.15, k), [], {"tunit": "C", "eunit": "kJ/mol"})
        self.assertAlmostEqual(num(cell(r, None, 0)), 75.0, places=6)
        self.assertAlmostEqual(num(cell(r, None, 1)) / A0, 1, places=5)
        self.assertIn("Ea = 75 kJ/mol", r["answer"])
        r = A.run("arrhenius", xy(T, k), [], {"tunit": "K", "eunit": "eV"})
        self.assertAlmostEqual(num(cell(r, None, 0)), 0.7773, places=3)


class Statistics(unittest.TestCase):
    def test_describe(self):
        r = A.run("describe", xy([1, 2, 3], [2.1, 2.5, 2.9]), [], {})
        rows = {row[0]: row[1] for row in r["tabs"][0]["tables"][0]["rows"]}
        self.assertEqual(rows["Number of values"], "3")
        self.assertAlmostEqual(num(rows["Std. deviation"]), 0.4, places=6)
        self.assertAlmostEqual(num(rows["Upper 95% CI of mean"]), 2.5 + 0.9936551, places=4)

    def test_shapiro_matches_r(self):
        # R: shapiro.test(1:10) -> W = 0.97016, p-value = 0.8924
        r = A.run("normality", xy(list(range(10)), list(range(1, 11))), [], {})
        rows = r["tabs"][0]["tables"][0]["rows"]
        self.assertAlmostEqual(num(rows[0][1]), 0.97016, places=4)
        self.assertAlmostEqual(num(rows[1][1]), 0.8924, places=3)
        self.assertTrue(r["plots"])

    def test_grubbs_finds_the_outlier_and_its_cell(self):
        v = [9.8, 10.1, 10.0, 9.9, 10.2, 10.0, 9.7, 10.3, 14.5]
        r = A.run("outliers", xy(list(range(9)), v), [], {})
        self.assertEqual(r["cells"], [[8, 1]])
        self.assertIn("1 outlier", r["answer"])
        self.assertEqual(A.run("outliers", xy(list(range(8)), v[:8]), [], {})["cells"], [])



def cols(*groups, kind="column"):
    n = max(len(g) for g in groups)
    return {"kind": kind, "rows": n, "sets": [{"title": f"G{k}", "entry": "rep", "reps": 1} for k in range(len(groups))], "rowTitles": [f"R{r}" for r in range(n)],
            "cols": [[None] * n] + [list(g) + [None] * (n - len(g)) for g in groups], "excluded": [], "xTitle": "", "yTitle": "Y"}


class NotYetChecked(unittest.TestCase):
    """0.4.32: the analyses that had no check against an independent reference, now against R 4.x
    (friedman.test, lm/nls with weights = 1/y^2 and predict(weights=), anova of nested fits, lowess)."""

    @classmethod
    def setUpClass(cls):
        A.more_kinds()

    def test_friedman_with_ties(self):
        fr = [[9, 11, 12, 9], [10, 10, 13, 8], [8, 12, 11, 9], [11, 11, 14, 10], [9, 13, 12, 9], [10, 12, 12, 11]]
        r = A.run("nonparam", cols(*np.array(fr).T.tolist()), [0, 1, 2, 3], {"test": "friedman"})
        self.assertAlmostEqual(num(cell(r, "Friedman statistic", None)), 13.47, places=2)
        self.assertEqual(cell(r, "P value", None), "0.0037")

    def test_diagnostic_table(self):
        t = cols([41, 7], [9, 63], kind="grouped")
        rows = {x[0]: x[1] for x in A.run("contingency", t, [0, 1], {"diagnostic": True})["tabs"][0]["tables"][1]["rows"]}
        self.assertEqual([rows[k] for k in ("Sensitivity", "Specificity", "Positive predictive value", "Negative predictive value")], ["85.42%", "87.5%", "82%", "90%"])

    def test_bland_altman_ratios_from_logs(self):
        a, b = [10.2, 15.1, 22.3, 30.8, 41.0, 55.5, 63.2, 78.9], [11.0, 15.8, 23.9, 32.1, 43.9, 57.0, 68.1, 82.2]
        r = A.run("blandaltman", cols(a, b), [0, 1], {"diff": "logratio"})
        rows = r["tabs"][0]["tables"][0]["rows"]
        self.assertEqual([x[1] for x in rows[:1]] + [x[1] for x in rows[2:4]], ["1.0568", "1.0186", "1.0964"])
        self.assertIn("logarithms", r["methods"])
        plain = A.run("blandaltman", cols(a, b), [0, 1], {"diff": "ratio"})["tabs"][0]["tables"][0]["rows"][0]
        self.assertEqual(plain[0], "Mean ratio")

    def test_weighted_line_prediction_band_and_comparison(self):
        x, y, y2 = list(range(1, 9)), [41.8, 37.5, 31.2, 30.1, 24.6, 22.9, 17.8, 16.1], [44.0, 41.9, 37.0, 37.2, 33.1, 32.0, 28.4, 27.5]
        r = A.run("linear", xy(x, y), [0], {"weight": "1/y2"})
        c = r["curves"][0]
        self.assertAlmostEqual(c["plo"][0], 34.2835, places=3); self.assertAlmostEqual(c["phi"][0], 45.5163, places=3)  # was the confidence band
        cmp = A.run("linear", xy(x, y, y2), [0, 1], {"weight": "1/y2"})["tabs"][0]["tables"][2]["rows"][0]
        self.assertEqual((cmp[1], cmp[3]), ("F = 16.85", "P = 0.0015"))  # was the unweighted F

    def test_weighted_curve_reports_weighted_sums(self):
        xe, ye = list(range(1, 11)), [68.0, 52.1, 41.9, 33.0, 28.2, 23.9, 20.5, 19.1, 17.2, 16.3]
        r = A.run("fit", xy(xe, ye), [0], {"model": "exp_decay", "weight": "1/y2"})
        self.assertAlmostEqual(num(cell(r, "K", None)), 0.33432, places=4)
        self.assertAlmostEqual(num(cell(r, "Sum of squares (weighted)", None)), 0.0012462, places=6)
        self.assertAlmostEqual(num(cell(r, "Sy.x (weighted)", None)), 0.013343, places=5)

    def test_own_equation_that_overflows_while_searching(self):
        xe, ye = list(range(1, 11)), [68.0, 52.1, 41.9, 33.0, 28.2, 23.9, 20.5, 19.1, 17.2, 16.3]
        r = A.run("fit", xy(xe, ye), [0], {"model": "custom", "equation": "Y = A*exp(-B*X) + C"})
        self.assertAlmostEqual(num(cell(r, "B", None)), 0.33461, places=4)  # was "the fit failed"
        two = A.run("fit", xy(xe, ye), [0], {"model": "exp_decay", "model2": "custom", "equation2": "Y = Y0*exp(-K*X)"})
        self.assertNotIn("did not fit", str(two["tabs"][1]["tables"][0]["rows"]))

    def test_lowess(self):
        ys = [0.2, 0.9, 1.7, 2.1, 2.6, 2.4, 2.9, 2.5, 2.1, 1.4, 1.1, 0.3]
        out = A.run("smooth", xy(list(range(1, 13)), ys), [0], {"method": "lowess", "frac": 0.5})["curves"][0]["y"]
        np.testing.assert_allclose(out, [0.2454099, 0.8985512, 1.5364304, 2.0204124, 2.3347612, 2.4971105, 2.4822631, 2.3284112, 2.0097921, 1.5000159, 0.9358233, 0.3742738], atol=1e-6)


if __name__ == "__main__":
    unittest.main()
