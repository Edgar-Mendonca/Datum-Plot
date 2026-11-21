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



class OwnTestsCheckedAgainstR(unittest.TestCase):
    """0.4.33: analyses that had only our own tests, now against R 4.x (cor.test, pairwise.t.test with a
    Holm-Šidák step-down by hand, e1071's skewness/kurtosis type 2, the Fleiss-Cohen-Everitt SE of kappa,
    power.t.test / power.anova.test)."""

    @classmethod
    def setUpClass(cls):
        A.more_kinds()

    def test_spearman_exact_p_and_t(self):
        x, y = [3.1, 4.7, 2.2, 6.0, 5.5, 7.9, 1.8, 6.6, 4.1, 8.8, 3.6, 7.0], [2.0, 3.9, 3.1, 5.2, 6.8, 6.1, 1.1, 4.4, 5.0, 7.7, 2.5, 8.3]
        from datum import groups
        import scipy.stats as st
        rs = float(st.spearmanr(x, y).statistic)
        self.assertAlmostEqual(groups.spearman_p(x, y, rs)[0], 0.0004433022, places=9)
        self.assertAlmostEqual(groups.spearman_p(list(range(1, 10)), [2, 1, 4, 3, 6, 5, 8, 9, 7], 0.9)[0], 0.002028219, places=8)  # exact (n ≤ 9)
        self.assertEqual(groups.spearman_p(x, y, rs, "t")[1], "t")
        self.assertEqual(groups.spearman_p([1, 2, 2, 3, 4], [1, 3, 2, 4, 5], 0.97)[1], "t")  # ties: the exact method does not apply
        r = A.run("correlation", cols(x, y), [0, 1], {})
        self.assertIn("P = 0.0004", r["tabs"][0]["tables"][0]["rows"][0][4])
        self.assertIn("P exact", r["methods"])

    def test_holm_sidak(self):
        gs = [[9.8, 10.4, 11.1, 9.2, 10.0], [11.5, 12.2, 10.9, 12.8, 11.7, 12.0], [10.6, 11.0, 9.9, 10.8], [12.9, 13.4, 12.1, 13.8, 12.6]]
        r = A.run("anova", cols(*gs), [0, 1, 2, 3], {"posthoc": "holm", "vs": "all"})
        np.testing.assert_allclose([b[2] for b in r["brackets"]], [0.001407966, 0.2849486511, 1.60371415e-05, 0.02110034303, 0.02237234741, 0.0002176496067], rtol=1e-6)

    def test_skewness_kurtosis_and_grubbs(self):
        v = [4.2, 5.1, 3.9, 6.3, 4.8, 5.5, 12.7, 4.4, 5.0, 4.6]
        r = A.run("describe", cols(v), [0], {})
        self.assertEqual((cell(r, "Skewness", None), cell(r, "Kurtosis", None)), ("2.7677", "8.12"))
        self.assertEqual(A.run("outliers", cols(v), [0], {})["tabs"][0]["tables"][0]["rows"][0][1], "12.7")

    def test_weighted_kappa_and_its_error(self):
        K = [[22, 5, 2], [4, 18, 6], [1, 3, 19]]
        t = cols(*[[K[r][k] for r in range(3)] for k in range(3)], kind="grouped")
        for w, kap, se in (("none", "0.6064", "0.0736"), ("linear", "0.6615", "0.0687"), ("quadratic", "0.717", "0.0714")):
            rows = A.run("agreement", t, [0, 1, 2], {"weights": w})["tabs"][0]["tables"][0]["rows"]
            self.assertEqual((rows[1][1], rows[2][1]), (kap, se))

    def test_power(self):
        t = cols([1, 2, 3], [2, 3, 4], [1, 2, 3], [3, 4, 5])
        for o, want in (({"test": "t2", "effect": 0.6, "power": 0.8}, "n = 45 per group"), ({"test": "t2", "effect": 0.6, "n": 20}, "45.6%"),
                        ({"test": "paired", "effect": 0.5, "power": 0.9}, "n = 44 pairs"), ({"test": "anova", "effect": 0.25, "power": 0.8}, "n = 45 per group"),
                        ({"test": "prop", "effect": 0.3, "power": 0.8}, "n = 175 per group")):
            self.assertIn(want, A.run("power", t, [0, 1, 2, 3], o)["answer"])


    # 0.4.34 (step 2b): regression items, against lm(), nls() and hclust() in R
    def test_line_through_origin_and_polynomial(self):
        r = A.run("linear", xy(AX, AY), [0], {"model": "origin"})
        self.assertEqual((cell(r, "Slope", None), cell(r, "Slope", None, 2), cell(r, "R squared", None)), ("0.7968", "0.049616", "0.9627"))
        r = A.run("linear", xy(AX, AY), [0], {"model": "poly", "order": 2})
        self.assertEqual([cell(r, b, None) for b in ("B0", "B1", "B2", "R squared")], ["0.75507", "1.0693", "-0.03162", "0.6873"])

    def test_dose_response_three_parameters_and_comparison(self):
        c = [10 ** v for v in np.arange(-9, -5.4, 0.5)]
        y1, y2 = [98.1, 95.4, 88.0, 70.2, 41.5, 20.3, 9.8, 6.1], [99.0, 97.2, 94.5, 86.1, 68.0, 42.2, 21.9, 11.0]
        r = A.run("ic50", xy(c, y1), [0], {"model": "3"})
        self.assertEqual(cell(r, "IC50", None), "6.733e-08")
        r = A.run("ic50", xy(c, y1, y2), [0, 1], {"model": "4", "compare": True})
        self.assertIn("F(1, 8) = 2055", r["tabs"][1]["tables"][0]["rows"][0][1])

    def test_clusters_as_hclust(self):
        a = [1.0, 1.2, 0.8, 1.1, 5.0, 5.3, 4.8, 5.1, 2.9, 3.2, 9.0, 3.0]
        b = [2.0, 2.3, 1.9, 2.1, 2.2, 1.8, 2.1, 2.4, 6.0, 6.3, 5.8, 6.2]
        for m, sizes in (("ward", "4, 4, 4"), ("average", "8, 3, 1"), ("complete", "8, 3, 1")):
            self.assertIn(f"in 3 clusters of {sizes}", A.run("cluster", cols(a, b), [0, 1], {"method": m, "k": 3})["answer"])


    # 0.4.34 (step 2c): quality, materials and signals against published constants, R and curves with known answers
    def test_area_split_where_the_curve_crosses_the_baseline(self):
        r = A.run("auc", xy([0, 1, 2], [1, -1, 1]), [0], {})
        self.assertEqual(r["tabs"][0]["tables"][0]["rows"][0][1:4], ["0", "0.5", "-0.5"])  # was 1 and -1
        self.assertEqual([x[5] for x in r["tabs"][0]["tables"][1]["rows"]], ["0.25", "0.25"])  # was 0.5 each

    def test_sn_line_two_ways(self):
        N, S = [2.1e4, 3.5e4, 6.0e4, 1.1e5, 2.4e5, 4.0e5, 9.5e5, 1.8e6], [420, 400, 370, 350, 320, 300, 280, 260]
        e739 = A.run("sn", xy(N, S), [0], {})["tabs"][0]["tables"][0]  # R: lm(log10(N) ~ log10(S)), turned round
        self.assertEqual(e739["rows"][0][1:3], ["1229.7", "-0.1083 (-0.1143 to -0.1028)"])
        self.assertIn("E739", e739["title"])
        self.assertEqual(A.run("sn", xy(N, S), [0], {"fit": "basquin"})["tabs"][0]["tables"][0]["rows"][0][1], "1225.3")  # lm(log10(S) ~ log10(N))

    def test_tensile_and_dsc_known_curves(self):
        e = np.r_[np.linspace(0, 0.0015, 31)[:-1], np.linspace(0.0015, 0.1, 400), np.linspace(0.1, 0.12, 21)[1:]]
        s = np.where(e <= 0.0015, 200000 * e, np.where(e <= 0.1, 300 + 2000 * (e - 0.0015), 497 - (e - 0.1) / 0.02 * 27))
        t = xy(e.tolist(), s.tolist()); t["yUnits"] = "MPa"
        row = A.run("tensile", t, [0], {"offset": 0.2})["tabs"][0]["tables"][1]["rows"][0]
        self.assertEqual(row[1:6], ["200", "304", "497", "10", "12"])  # E (GPa), Rp0.2 = 304.04, UTS, strain at UTS, elongation
        T = np.linspace(100, 200, 1001)
        dsc = A.run("thermal", xy(T.tolist(), (-0.1 - 2 * np.exp(-0.5 * ((T - 150) / 3) ** 2)).tolist()), [0], {"mode": "dsc", "rate": 10})["tabs"][0]["tables"][0]["rows"][0]
        self.assertEqual(dsc[1:4] + [dsc[6]], ["144", "150", "156", "90.24 J/g"])  # onset x0 − 2σ, endset x0 + 2σ, A·σ·√(2π) ÷ (10/60)

    def test_xbar_r_chart_limits(self):
        G = [[50.1, 49.2, 51.0, 48.7, 50.5], [49.8, 50.9, 50.2, 51.3, 49.1], [48.9, 50.0, 49.5, 50.7, 51.2], [50.6, 49.4, 50.8, 49.9, 50.3], [51.1, 50.2, 49.0, 50.4, 49.6], [49.5, 50.8, 50.1, 49.3, 50.9]]
        t = {"rows": 6, "sets": [{"title": "S", "entry": "rep", "reps": 5}], "cols": [[None] * 6] + [[g[j] for g in G] for j in range(5)], "excluded": [], "xTitle": "", "yTitle": ""}
        xb = np.mean(G); rb = np.mean([max(g) - min(g) for g in G])
        lim = A.run("control", t, [0], {"chart": "xbar"})["tabs"][0]["tables"][0]["rows"]
        self.assertAlmostEqual(float(lim[0][3]), xb + 0.577 * rb, places=2)  # A2 = 0.577 for n = 5
        self.assertAlmostEqual(float(lim[1][3]), 2.114 * rb, places=2)  # D4 = 2.114



class RandomCheckFindings(unittest.TestCase):
    """0.4.35 (full check, step 3: thousands of random data sets against R): what it found, as R gives it."""

    @classmethod
    def setUpClass(cls):
        A.more_kinds()

    def test_kolmogorov_smirnov_exact_with_ties(self):
        a, b = [5, 7, 7, 8, 9, 9, 9, 10, 11, 12, 12], [8, 9, 10, 10, 11, 12, 12, 13, 14, 14, 15, 16]
        r = A.run("nonparam", cols(a, b), [0, 1], {"test": "ks"})["tabs"][0]["tables"][0]["rows"]
        self.assertEqual(r[2], ["P value (exact)", "0.0798"])  # R's ks.test; SciPy's exact P assumes no ties

    def test_mann_whitney_exact_up_to_49(self):
        x = [4.12, 5.31, 3.87, 6.02, 5.55, 4.98, 5.73, 4.44, 6.31, 5.09, 4.76, 5.92, 3.95, 6.48, 5.27]
        y = [5.94, 6.71, 5.02, 7.33, 6.18, 6.89, 5.46, 7.05, 6.52, 5.81, 7.48, 6.36]
        rows = A.run("nonparam", cols(x, y), [0, 1], {"test": "mw"})["tabs"][0]["tables"][0]["rows"]
        self.assertEqual(rows[2], ["P value (two-tailed, exact)", "0.0009"])  # R 0.000934; the normal approximation gives 0.0013
        self.assertIn("normal approximation", A.run("nonparam", cols(x, y), [0, 1], {"test": "mw", "exactp": "approx"})["tabs"][0]["tables"][0]["rows"][2][0])

    def test_kendall_exact_up_to_49(self):
        u = [16.8, 80.8, 38.5, 32.8, 60.2, 60.4, 12.5, 29.5, 57.8, 63.1, 51.2, 50.5, 53.4, 55.7, 86.8, 83, 11.1, 70.4, 89.7, 28, 22.8, 1.5, 12.9, 9.3, 23.7, 79.1, 60, 91, 56, 75.6, 37.9, 37.3, 17, 45.3, 25.8, 33.6, 89, 20.2, 57.9, 20.8]
        v = [32.3, 98.8, 26.9, 65.3, 57, 41.9, 7.9, 17.7, 45.9, 95.8, 35.7, 33.9, 101.1, 113.2, 106.1, 111.8, 49.9, 40, 35.2, 35, 87.3, 6.1, 83.5, 12.8, 82.6, 50.3, 91.9, 76.8, 50.2, 28.2, 85.5, 85.4, 94.6, 108, 58, 63.3, 38.6, 21.5, 93.1, 80.3]
        from datum import groups
        self.assertAlmostEqual(groups.kendall_p(u, v)[1], 0.04848249004, places=9)

    def test_wilcoxon_reports_the_positive_rank_sum(self):
        a, b = [4.1, 5.2, 3.3, 6.4, 5.5, 4.6, 5.0], [6.1, 7.2, 5.9, 6.8, 7.7, 6.0, 8.1]
        rows = A.run("nonparam", cols(a, b), [0, 1], {"test": "wilcoxon"})["tabs"][0]["tables"][0]["rows"]
        self.assertEqual(rows[1], ["W (sum of positive ranks of G1 − G0)", "28"])  # R's V; was the smaller sum, 0


    def test_clear_messages_where_r_gives_nan_or_warns(self):
        with self.assertRaisesRegex(ValueError, "spread in every group"):  # Welch's ANOVA with a constant group: R's oneway.test gives NaN
            A.run("anova", cols([13.0, 5, 16, 8, 10], [9.0, 9, 9], [10.9, 12.3, 13.6, 7.8]), [0, 1, 2], {"anova": "welch"})
        r = A.run("linear", xy([8, 8, 11, 11, 11], [16.7, 19.1, 25.9, 26.5, 24.4]), [0], {"model": "poly", "order": 2})
        self.assertIn("at least 3 different X values", str(r["checks"]))  # was a quadratic fitted anyway; R drops a term
        t = {"kind": "multi", "rows": 8, "sets": [{"title": k, "entry": "rep", "reps": 1} for k in ("y", "x1", "x2")], "excluded": [], "xTitle": "", "yTitle": "", "rowTitles": [],
             "cols": [[None] * 8, [0, 0, 0, 0, 1, 1, 1, 1], [-2, -1.5, -1, -.5, .5, 1, 1.5, 2], [1, 2, 1, 3, 2, 1, 3, 2]]}
        with self.assertRaisesRegex(ValueError, "separates the outcomes perfectly"):  # was "try other units"
            A.run("multireg", t, [], {"y": 0, "model": "logistic"})

    def test_dunnett_gives_the_same_p_every_time(self):
        g = [[11.1, 6.7, 2.1, 5.0, 6.5, 8.5, 1.9], [8.2, 7.5, 3.9, 5.6, 5.4, 5.4, 6.5, 3.8, 4.9], [9.9, 10.4, 12.0, 11.1, 8.7, 13.0], [4.0, 5.1, 6.3, 4.4, 5.9]]
        runs = {tuple(round(b[2], 9) for b in A.run("anova", cols(*g), [0, 1, 2, 3], {"posthoc": "dunnett", "vs": "control"})["brackets"]) for _ in range(3)}
        self.assertEqual(len(runs), 1)
        self.assertAlmostEqual(list(runs)[0][1], 0.000925, delta=2e-5)  # R multcomp, abseps 1e-6: 0.0009250


if __name__ == "__main__":
    unittest.main()
