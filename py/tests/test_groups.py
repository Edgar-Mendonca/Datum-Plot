"""Compare-groups analyses and the 0.2.1 tools against R: t.test, wilcox.test, aov + TukeyHSD and
kruskal.test on R's sleep and PlantGrowth data, cor.test on Anscombe, power.t.test; and
hand-checkable cases for transforms, areas, tensile tests and Weibull fits.
Run: python -m unittest discover -s py/tests"""
import math
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datum import analysis as A, graph  # noqa: E402
from test_analysis import AX, AY, cell, num, xy  # noqa: E402


def col(*groups):
    """A column table: one group per data set."""
    n = max(len(g) for g in groups)
    return {"name": "T", "kind": "column", "rows": n, "sets": [{"title": f"G{i}", "entry": "rep", "reps": 1} for i in range(len(groups))],
            "cols": [[None] * n] + [list(g) + [None] * (n - len(g)) for g in groups], "excluded": [], "xTitle": "", "yTitle": "Y"}


def p_of(text):
    return float(str(text).replace("P", "").replace("=", "").strip())


SLEEP1 = [0.7, -1.6, -0.2, -1.2, -0.1, 3.4, 3.7, 0.8, 0.0, 2.0]
SLEEP2 = [1.9, 0.8, 1.1, 0.1, -0.1, 4.4, 5.5, 1.6, 4.6, 3.4]
CTRL = [4.17, 5.58, 5.18, 6.11, 4.50, 4.61, 5.17, 4.53, 5.33, 5.14]
TRT1 = [4.81, 4.17, 4.41, 3.59, 5.87, 3.83, 6.03, 4.89, 4.32, 4.69]
TRT2 = [6.31, 5.12, 5.54, 5.50, 5.37, 5.29, 4.92, 6.15, 5.80, 5.26]


class Robustness(unittest.TestCase):
    def test_awkward_data_gives_messages_not_crashes(self):
        # Every analysis on identical values, one value, NaN, gaps and huge numbers: results or a ValueError.
        kinds = list(A.more_kinds())
        for cols in ([[2.0] * 5, [2.0] * 5], [[1.0], [2.0]], [[1.0, float("nan"), 3.0], [1.0, 2.0, 3.0]], [[1e300, 2e300, 3e300], [1e-300, 2e-300, 3e-300]]):
            for t in (col(*cols), xy(list(range(len(cols[0]))), *cols)):
                for k in kinds:
                    try:
                        A.run(k, t, [], {})
                    except ValueError:
                        pass


class TTests(unittest.TestCase):
    def test_welch_student_and_paired_match_r(self):
        # R: t.test(extra ~ group, sleep): t = -1.8608, df = 17.776, p = 0.07939; var.equal: p = 0.07919
        # paired: t = -4.0621, df = 9, p = 0.002833, mean difference 1.58 (0.7001 to 2.4599)
        t = col(SLEEP1, SLEEP2)
        r = A.run("ttest", t, [], {"test": "unpaired", "welch": True})
        self.assertAlmostEqual(p_of(cell(r, "P value (two-tailed)", None)), 0.0794, places=4)
        self.assertIn("df = 17.78", cell(r, "t, df", None))
        self.assertAlmostEqual(p_of(cell(A.run("ttest", t, [], {"test": "unpaired", "welch": False}), "P value (two-tailed)", None)), 0.0792, places=4)
        r = A.run("ttest", t, [], {"test": "paired"})
        self.assertAlmostEqual(p_of(cell(r, "P value (two-tailed)", None)), 0.0028, places=4)
        self.assertEqual(cell(r, "95% CI", None), "0.70011 to 2.4599")
        self.assertEqual(r["brackets"][0][:2], [0, 1])

    def test_from_mean_sd_n_equals_raw(self):
        a, b = np.array(SLEEP1), np.array(SLEEP2)
        t = {"rows": 1, "kind": "column", "sets": [{"title": "A", "entry": "msn", "reps": 3}, {"title": "B", "entry": "msn", "reps": 3}],
             "cols": [[None], [a.mean()], [a.std(ddof=1)], [10], [b.mean()], [b.std(ddof=1)], [10]], "excluded": []}
        self.assertAlmostEqual(p_of(cell(A.run("ttest", t, [], {}), "P value (two-tailed)", None)), 0.0794, places=4)


class Nonparametric(unittest.TestCase):
    def test_against_r(self):
        # R: wilcox.test(extra ~ group, sleep): W = 25.5, p = 0.06933; paired: p = 0.009091
        # kruskal.test(weight ~ group, PlantGrowth): chi-squared = 7.9882, p = 0.01842
        t = col(SLEEP1, SLEEP2)
        self.assertAlmostEqual(p_of(cell(A.run("nonparam", t, [], {"test": "mw"}), "P value (two-tailed)", None)), 0.0693, places=4)
        self.assertAlmostEqual(p_of(cell(A.run("nonparam", t, [], {"test": "wilcoxon"}), "P value (two-tailed)", None)), 0.0091, places=4)
        r = A.run("nonparam", col(CTRL, TRT1, TRT2), [], {"test": "kw"})
        self.assertAlmostEqual(num(cell(r, "Kruskal-Wallis H", None)), 7.988, places=3)
        self.assertAlmostEqual(p_of(cell(r, "P value", None)), 0.0184, places=4)
        self.assertEqual(len(r["brackets"]), 3)


class Anova(unittest.TestCase):
    def test_plantgrowth_matches_r(self):
        # R: summary(aov(weight ~ group, PlantGrowth)): F = 4.846, p = 0.01591;
        # TukeyHSD: trt2-trt1 diff 0.865, p adj 0.0120064; trt1-ctrl 0.3908711; trt2-ctrl 0.1979960
        r = A.run("anova", col(CTRL, TRT1, TRT2), [], {"posthoc": "tukey"})
        self.assertAlmostEqual(num(cell(r, "F", None)), 4.846, places=3)
        self.assertAlmostEqual(p_of(cell(r, "P value", None)), 0.0159, places=4)
        tk = r["tabs"][0]["tables"][3]
        self.assertEqual([row[3] for row in tk["rows"]], ["0.3909", "0.1980", "0.0120"])
        self.assertEqual(tk["rows"][2][1], "-0.865", "TRT1 vs TRT2 is TRT1 − TRT2 (0.4.23)")
        # η² = SSB / SST = 3.7663 / 14.258
        self.assertAlmostEqual(num(cell(r, "R squared (η²)", None)), 0.2641, places=4)

    def test_against_a_control_or_chosen_pairs(self):
        """0.4.20 (B40). R: pairwise.t.test(weight, group, p.adjust = "none") on PlantGrowth: ctrl–trt2 0.0877, trt1–trt2 0.0045."""
        t = col(CTRL, TRT1, TRT2)
        r = A.run("anova", t, [], {"vs": "pairs", "pairs": [[0, 2], [1, 2], [2, 2]], "posthoc": "lsd"})
        self.assertEqual([(b[0], b[1], A.pv(b[2])) for b in r["brackets"]], [(0, 2, "0.0877"), (1, 2, "0.0045")])
        d = A.run("anova", t, [], {"vs": "control", "control": 1, "posthoc": "dunnett"})
        self.assertEqual(sorted((b[0], b[1]) for b in d["brackets"]), [(1, 0), (1, 2)], "each against the second group")
        from scipy import stats as st
        ref = st.dunnett(np.array(CTRL, float), np.array(TRT2, float), control=np.array(TRT1, float))
        self.assertAlmostEqual(d["brackets"][1][2], float(ref.pvalue[1]), places=3)  # Dunnett integrates by random sampling
        # Tukey is for every pair: against a control it becomes Holm-Šidák, and the methods say so
        h = A.run("anova", t, [], {"vs": "control", "control": 2, "posthoc": "tukey"})
        self.assertIn("Holm-Šidák", h["methods"])
        self.assertEqual(sorted((b[0], b[1]) for b in h["brackets"]), [(2, 0), (2, 1)])
        with self.assertRaises(ValueError):
            A.run("anova", t, [], {"vs": "pairs", "pairs": []})

    def test_every_variant_runs(self):
        for o in [{"anova": "welch", "posthoc": "dunnett"}, {"anova": "bf", "posthoc": "holm"}, {"anova": "rm", "posthoc": "bonferroni"}, {"posthoc": "sidak", "trend": True}, {"posthoc": "lsd"}, {"posthoc": "none"}]:
            r = A.run("anova", col(CTRL, TRT1, TRT2), [], o)
            self.assertTrue(r["answer"].startswith("The means"), o)


class Stars(unittest.TestCase):
    """0.4.25 (#69): stars with ≤ thresholds, and a fourth star (P ≤ 0.0001) when the analysis asks for it."""

    def test_thresholds_and_four_stars(self):
        self.assertEqual([A.stars(p) for p in (0.06, 0.05, 0.011, 0.01, 0.001, 0.00001)], ["ns", "*", "*", "**", "***", "***"])
        self.assertEqual([A.stars(p, True) for p in (0.0001, 0.00001, 0.0002)], ["****", "****", "***"])
        far = col([1.0, 1.1, 0.9, 1.05, 0.95, 1.02], [9.0, 9.2, 8.9, 9.1, 9.05, 8.95])
        r = A.run("ttest", far, [], {"ptext": "stars4"})
        self.assertIn("(****)", str(r["tabs"]))
        self.assertIn("**** P ≤ 0.0001", r["legend"])
        self.assertNotIn("****", str(A.run("ttest", far, [], {})["tabs"]), "three stars unless asked")
        self.assertFalse(A.FOUR.get(), "the choice ends with its analysis")
        svg = graph.render(far, {"column": "scatter"}, [{"kind": "ttest", "options": {"ptext": "stars4", "brackets": "all"}}])["svg"]
        self.assertIn("****", svg, "the graph's bracket shows four stars")


class CheckedAgainstR(unittest.TestCase):
    """0.4.27: the fixes from the validation against R (the user's hardening request after #67). Made-up or textbook
    data; the expected values were computed in R (stats, car, emmeans, lmerTest) and are written here."""

    def test_dunn_is_first_minus_second(self):
        # R by hand on PlantGrowth: mean ranks ctrl − trt1 = 4.4, ctrl − trt2 = −6.65, trt1 − trt2 = −11.05; Bonferroni P
        r = A.run("nonparam", col(CTRL, TRT1, TRT2), [], {"test": "kw"})
        rows = [x for t in r["tabs"][0]["tables"] if "Dunn" in t["title"] for x in t["rows"]]
        self.assertEqual([(x[1], x[3]) for x in rows], [("4.4", "0.7911"), ("-6.65", "0.2735"), ("-11.05", "0.0150")])

    def test_brown_forsythe_and_mehrotra(self):
        # Brown & Forsythe (1974) on PlantGrowth: F* = 4.846, DF 2 and 22.21, P = 0.01793; Mehrotra's DFn 1.805, P = 0.0205
        t = col(CTRL, TRT1, TRT2)
        bf = A.run("anova", t, [], {"anova": "bf", "posthoc": "none", "bayes": False})
        self.assertEqual(cell(bf, "DFn, DFd", None), "2, 22.21")
        self.assertEqual(cell(bf, "P value", None), "0.0179")
        self.assertIn("Brown-Forsythe ANOVA", bf["methods"])
        m = A.run("anova", t, [], {"anova": "bfm", "posthoc": "none", "bayes": False})
        self.assertEqual((cell(m, "DFn, DFd", None), cell(m, "P value", None)), ("1.805, 22.21", "0.0205"))
        self.assertIn("Mehrotra", m["methods"])

    RM = {(0, 0): [20.686, 19.747, 24.197, 24.29, 26.985], (0, 1): [20.956, 25.672, 26.21, 26.144, 29.264], (0, 2): [26.52, 29.082, 23.853, 30.266, 30.93],
          (1, 0): [22.812, 22.487, 28.514, 24.977, 30.134], (1, 1): [27.604, 23.301, 27.395, 26.882, 31.488], (1, 2): [30.029, 32.547, 26.444, 30.35, 34.407]}

    def test_repeated_measures_between_subject_comparisons(self):
        """Subjects nested in the data sets, measured in every row. Comparing the data sets at one row crosses subjects:
        R (lmer, emmeans, Satterthwaite) gives SE 1.919 on 17.85 df, P 0.1917, 0.3916, 0.1883; within a data set the
        rows are compared on 16 df (P 0.1120, 0.0039, 0.1103 for the first)."""
        from test_repeated import grouped
        vals = [[self.RM[(k, r)] for r in range(3)] for k in range(2)]
        r = A.run("twoway", grouped(vals, 3, 2, 5), [], {"rm": "rows", "gg": False, "posthoc": "lsd", "compare": "rows+sets"})
        rows = [x for t in r["tabs"][0]["tables"] if "multiple comparisons" in t["title"] for x in t["rows"]]
        between, within = rows[:3], rows[3:6]
        self.assertEqual([(x[7], x[9], x[3]) for x in between], [("1.919", "17.85", "0.1917"), ("1.919", "17.85", "0.3916"), ("1.919", "17.85", "0.1883")])
        self.assertEqual([(x[9], x[3]) for x in within], [("16", "0.1120"), ("16", "0.0039"), ("16", "0.1103")])

    def test_normality_rows_line_up(self):
        """0.4.29: every test on its own rows. R (PlantGrowth ctrl): Shapiro-Wilk W 0.9567, P 0.7475; D'Agostino K2
        0.2335, P 0.8898; Anderson-Darling A2 0.2829, P 0.5546; Lilliefors D 0.1735 (the rows had shifted)."""
        r = A.run("normality", col(CTRL), [], {})
        rows = [(x[0].strip(), x[1]) for x in r["tabs"][0]["tables"][0]["rows"]]
        self.assertEqual(rows, [("Shapiro-Wilk W", "0.9567"), ("P value", "0.7475"), ("Passed (normal)?", "Yes"), ("D'Agostino-Pearson K2", "0.2335"), ("P value", "0.8898"),
                                ("Passed (normal)?", "Yes"), ("Anderson-Darling A2", "0.2829"), ("P value", "0.5546"), ("Passed (normal)?", "Yes"),
                                ("Kolmogorov-Smirnov D (Lilliefors)", "0.1735"), ("P value", "0.5315"), ("Passed (normal)?", "Yes"), ("Number of values", "10")])

    def test_awkward_data_gives_a_message(self):
        """0.4.30 (hardening: every analysis on empty, single, equal, tied, missing, tiny, huge and large data): an empty
        agreement table says what to enter (it raised an internal IndexError); no outliers says so in words."""
        empty = {"kind": "contingency", "rows": 2, "rowTitles": ["a", "b"], "sets": [{"title": "a", "entry": "rep", "reps": 1}, {"title": "b", "entry": "rep", "reps": 1}],
                 "cols": [[None, None], [None, None], [None, None]], "excluded": [], "name": "K"}
        with self.assertRaisesRegex(ValueError, "Enter the counts"):
            A.run("agreement", empty, [], {})
        r = A.run("outliers", col([10, 11, 12, 10.5, 11.5]), [], {})
        self.assertEqual(r["tabs"][0]["tables"][0]["rows"][0][0], "No outliers found")

    def test_many_dots_draw_quickly(self):
        """0.4.30: a box plot showing 20 000 values per group took three minutes (every dot was checked against every
        other); now well under the limit."""
        import time
        rng = np.random.default_rng(0)
        t0 = time.time()
        graph.render(col(*[list(rng.normal(10, 2, 20000)) for _ in range(3)]), {"column": "box", "points": "each"})
        self.assertLess(time.time() - t0, 20)

    NESTED2 = [[[10.41, 10.83, 8.36], [10.44, 9.72, 10.53, 9.41, 10.72], [11.36, 11.1]], [[9.95, 10.6, 9.91, 9.64], [11.92, 10.59], [13.57, 13.12, 10.4, 12.67, 11.3, 12.43], [13.14, 11.11, 12.87]]]
    NESTED3 = [[[9.52, 7.62, 9.93], [10.58, 11.46, 11.28, 10.63, 10.17], [9.58, 8.12]], [[13.9, 13.35, 12.41, 14.46], [11.91, 9.95], [9.44, 13.31, 10.87, 10.58, 11.78, 10.08], [10.32, 12.04, 10.45]],
               [[9.35, 8.48, 10.5, 9.97, 10.46], [11.33, 11.71, 12.73], [10.67, 10.47, 11.21, 10.69]]]

    @staticmethod
    def nested(groups):
        n = max(len(v) for s_ in groups for v in s_)
        cols = [[None] * n] + [list(v) + [None] * (n - len(v)) for s_ in groups for v in s_]
        return {"name": "N", "kind": "nested", "rows": n, "sets": [{"title": f"G{i}", "entry": "rep", "reps": len(s_)} for i, s_ in enumerate(groups)], "cols": cols, "excluded": [], "xTitle": "", "yTitle": "Y"}

    def test_nested_with_unequal_subgroups(self):
        """Subgroups of different sizes: the groups are tested from the mixed model. R lmerTest (Satterthwaite):
        two groups F = 2.1886 on 1 and 5.2154 df, P 0.1967 (the classic F said 2.832 and P 0.153); three groups
        F = 2.3464 on 2 and 7.192 df, P 0.1643."""
        two = A.run("nested", self.nested(self.NESTED2), [], {})["tabs"][0]["tables"][0]["rows"][1]
        self.assertEqual((two[4], two[5]), ("F = 2.189 (DFn 1, DFd 5.215; mixed model)", "0.1967"))
        three = A.run("nested", self.nested(self.NESTED3), [], {})["tabs"][0]["tables"][0]["rows"][0]
        self.assertEqual((three[4], three[5]), ("F = 2.346 (DFn 2, DFd 7.19; mixed model)", "0.1643"))  # R 7.192: REML optimisers agree to 4 digits


class CorrelationPower(unittest.TestCase):
    def test_pearson_matches_r(self):
        # R: cor.test(anscombe$x1, anscombe$y1): r = 0.8164205, p = 0.00217, 95% CI 0.4243912 to 0.9506933 (Fisher z)
        r = A.run("correlation", xy(AX, AY), [], {})
        row = r["tabs"][0]["tables"][0]["rows"][0]
        self.assertEqual(row[1], "0.8164")
        self.assertEqual(row[2], "0.42439 to 0.95069")

    def test_power_matches_r(self):
        # R: power.t.test(delta = 1, sd = 1, power = 0.8): n = 16.71477 per group
        r = A.run("power", col(CTRL, TRT1), [], {"test": "t2", "effect": 1, "power": 0.8})
        self.assertIn("n = 17 per group", r["answer"])


class Tools(unittest.TestCase):
    def test_transform_and_new_table(self):
        r = A.run("transform", xy([1, 2, 3], [10, 100, 1000]), [], {"y": "log10"})
        self.assertEqual(r["table"]["cols"][1], [1.0, 2.0, 3.0])
        r = A.run("transform", xy([1, 2, 3], [2, 4, 6], [4, 6, 8], reps=2), [], {"normalize": "max", "means": True})
        self.assertEqual(r["table"]["sets"][0]["entry"], "msn")
        self.assertEqual(r["table"]["cols"][1], [37.5, 62.5, 87.5])

    def test_area_by_the_trapezoid_rule(self):
        r = A.run("auc", xy([0, 1, 2, 3], [0, 2, 2, 0]), [], {})
        self.assertEqual(cell(r, None, 0, 1), "4")
        r = A.run("auc", xy([0, 1, 2, 3], [1, 3, 3, 1]), [], {"baseline": "line"})
        self.assertEqual(cell(r, None, 0, 1), "4")

    def test_smooth_derivative_integral(self):
        x = np.linspace(0, 10, 41)
        r = A.run("smooth", xy(x, 3 * x + 1), [], {"mode": "deriv1"})
        self.assertTrue(np.allclose(r["table"]["cols"][1], 3))
        r = A.run("smooth", xy(x, 2 * x), [], {"mode": "integral", "method": "none"})
        self.assertAlmostEqual(r["table"]["cols"][1][-1], 100, places=6)

    def test_tensile_on_an_ideal_curve(self):
        # Linear elastic to 400 MPa at E = 200 GPa, then perfectly plastic: Rp0.2 = 400, UTS = 400.
        e = np.linspace(0, 0.05, 501)
        s = np.minimum(200_000 * e, 400.0)
        t = xy(e, s)
        t["yUnits"] = "MPa"
        r = A.run("tensile", t, [], {})
        row = r["tabs"][0]["tables"][1]["rows"][0]
        self.assertAlmostEqual(num(row[1]), 200, places=3)
        self.assertAlmostEqual(num(row[2]), 400, places=1)
        self.assertAlmostEqual(num(row[3]), 400, places=3)
        self.assertAlmostEqual(num(row[5]), 5.0, places=3)

    def test_weibull_recovers_its_parameters(self):
        rng = np.random.default_rng(4)
        v = 500 * rng.weibull(12, 400)
        r = A.run("weibull", col(list(v)), [], {"method": "mle"})
        m, s0 = num(cell(r, None, 0, 1)), num(cell(r, None, 0, 2))
        self.assertTrue(10.5 < m < 13.5 and abs(s0 - 500) < 8, (m, s0))

    def test_frequency_and_checks(self):
        r = A.run("frequency", col([1, 2, 2, 3, 3, 3]), [], {"width": 1})
        self.assertEqual(sum(r["table"]["cols"][1]), 6)
        r = A.run("check", xy([1, None, 2], [1, 2, 3]), [], {})
        self.assertIn("1 problem", r["answer"])

    def test_global_fit_shares_a_parameter(self):
        x = np.linspace(0, 5, 30)
        t = xy(x, 10 * np.exp(-0.7 * x) + 1, 6 * np.exp(-0.7 * x) + 2)
        r = A.run("fit", t, [], {"model": "exp_decay", "shared": "K"})
        gt = next(tb for tab in r["tabs"] if tab["name"] == "Global fit" for tb in tab["tables"])
        k = next(row for row in gt["rows"] if row[0].startswith("K"))
        self.assertAlmostEqual(num(k[2]), 0.7, places=4)


class ColumnGraphs(unittest.TestCase):
    def test_every_column_graph_draws_with_brackets(self):
        t = col(CTRL, TRT1, TRT2)
        for kind in ["scatter", "bars", "box", "violin", "paired", "mean"]:
            r = graph.render(t, {"column": kind, "points": "each", "palette": "viridis"}, [{"kind": "anova", "options": {"brackets": "all"}}])
            self.assertIn("<svg", r["svg"])
            self.assertEqual(len(r["points"]), 3)
        self.assertEqual(graph.palette({"palette": "#112233, #445566"}, 2), ["#112233", "#445566"])
        self.assertEqual(len(graph.palette({"palette": "grey"}, 5)), 5)


if __name__ == "__main__":
    unittest.main()


class TwoWay(unittest.TestCase):
    def test_warpbreaks_matches_r(self):
        # R: anova(lm(breaks ~ wool * tension, warpbreaks)) (balanced, so Type I = Type III):
        # wool SS 450.7 F 3.765 P 0.058213; tension SS 2034.3 F 8.498 P 0.000693; interaction SS 1002.8 F 4.189 P 0.021044; residual SS 5745.1, 48 df
        A_ = [[26, 30, 54, 25, 70, 52, 51, 26, 67], [18, 21, 29, 17, 12, 18, 35, 30, 36], [36, 21, 24, 18, 10, 43, 28, 15, 26]]
        B_ = [[27, 14, 29, 19, 29, 31, 41, 20, 44], [42, 26, 19, 16, 39, 28, 21, 39, 29], [20, 21, 24, 17, 13, 15, 15, 16, 28]]
        cols = [[None] * 3] + [[A_[r][j] for r in range(3)] for j in range(9)] + [[B_[r][j] for r in range(3)] for j in range(9)]
        t = {"kind": "grouped", "rows": 3, "rowTitles": ["L", "M", "H"], "sets": [{"title": "A", "entry": "rep", "reps": 9}, {"title": "B", "entry": "rep", "reps": 9}], "cols": cols, "excluded": []}
        r = A.run("twoway", t, [], {"rowname": "Tension", "colname": "Wool"})
        rows = {x[0]: x for x in r["tabs"][0]["tables"][0]["rows"]}
        self.assertEqual((rows["Wool"][1], rows["Wool"][4], rows["Wool"][5]), ("450.67", "3.765", "0.0582"))
        self.assertEqual((rows["Tension"][1], rows["Tension"][4], rows["Tension"][5]), ("2034.3", "8.498", "0.0007"))
        self.assertEqual((rows["Interaction"][1], rows["Interaction"][4], rows["Interaction"][5]), ("1002.8", "4.189", "0.0210"))
        self.assertEqual((rows["Residual"][1], rows["Residual"][2]), ("5745.1", "48"))
        self.assertEqual(len(r["brackets"]), 3)
        for kind in ["bars", "stacked", "scatter", "lines", "heatmap"]:
            self.assertIn("<svg", graph.render(t, {"column": kind, "points": "each"}, [{"kind": "twoway", "options": {"brackets": "all"}}])["svg"])

    def test_rows_within_each_data_set_and_both(self):
        """0.4.19 (#61): the rows compared within each data set (across rows), alone or with the data sets within each
        row; each family corrected on its own; brackets across rows. Checked by hand: pooled t with the residual
        mean square (48 df) and Šidák over the family's comparisons."""
        from scipy import stats as st
        A_ = [[26, 30, 54, 25, 70, 52, 51, 26, 67], [18, 21, 29, 17, 12, 18, 35, 30, 36], [36, 21, 24, 18, 10, 43, 28, 15, 26]]
        B_ = [[27, 14, 29, 19, 29, 31, 41, 20, 44], [42, 26, 19, 16, 39, 28, 21, 39, 29], [20, 21, 24, 17, 13, 15, 15, 16, 28]]
        cols = [[None] * 3] + [[A_[r][j] for r in range(3)] for j in range(9)] + [[B_[r][j] for r in range(3)] for j in range(9)]
        t = {"kind": "grouped", "rows": 3, "rowTitles": ["L", "M", "H"], "sets": [{"title": "A", "entry": "rep", "reps": 9}, {"title": "B", "entry": "rep", "reps": 9}], "cols": cols, "excluded": []}
        r = A.run("twoway", t, [], {"compare": "sets", "posthoc": "sidak"})
        self.assertEqual(len(r["brackets"]), 6)
        self.assertTrue(all(len(b) == 5 and b[0] == b[1] for b in r["brackets"]), r["brackets"])
        d = np.mean(A_[1]) - np.mean(A_[0])
        p = 2 * st.t.sf(abs(d) / np.sqrt(5745.1111 / 48 * 2 / 9), 48)
        sid = 1 - (1 - p) ** 6
        ab = [b for b in r["brackets"] if b[0] == 0 and {b[3], b[4]} == {0, 1}][0]
        self.assertAlmostEqual(ab[2], sid, places=6)
        both = A.run("twoway", t, [], {"compare": "both", "brackets": "all"})
        titles = [x["title"] for x in both["tabs"][0]["tables"]]
        self.assertTrue(any("within each row" in x for x in titles) and any("within each data set" in x for x in titles), titles)
        self.assertEqual(len(both["brackets"]), 3 + 6)
        # Drawn: each across-row bracket joins the same data set in two rows (its ends a whole group apart).
        import matplotlib
        g = {"column": "box"}
        with matplotlib.rc_context(graph.rc_for(g)):
            fig, ax, _, _ = graph.figure(t, g, [{"kind": "twoway", "options": {"compare": "sets", "brackets": "all"}}])
        spans = sorted(round(max(x) - min(x), 3) for x in (l.get_xdata() for l in ax.lines) if len(x) == 4 and min(x) != max(x))
        self.assertEqual(len(spans), 6, spans)
        self.assertGreater(spans[0], 0.9, "each joins boxes in different rows")


WB_A = [[26, 30, 54, 25, 70, 52, 51, 26, 67], [18, 21, 29, 17, 12, 18, 35, 30, 36], [36, 21, 24, 18, 10, 43, 28, 15, 26]]
WB_B = [[27, 14, 29, 19, 29, 31, 41, 20, 44], [42, 26, 19, 16, 39, 28, 21, 39, 29], [20, 21, 24, 17, 13, 15, 15, 16, 28]]
WB = {"kind": "grouped", "rows": 3, "rowTitles": ["L", "M", "H"], "sets": [{"title": "A", "entry": "rep", "reps": 9}, {"title": "B", "entry": "rep", "reps": 9}],
      "cols": [[None] * 3] + [[WB_A[r][j] for r in range(3)] for j in range(9)] + [[WB_B[r][j] for r in range(3)] for j in range(9)], "excluded": []}


class Comparisons(unittest.TestCase):
    """0.4.20 (B40): what to compare after two-way ANOVA (cells, main effects) and how many (every pair, against a
    control, chosen pairs). Warpbreaks again; the residual mean square 5745.1111 / 48 df."""
    A_, B_, T = WB_A, WB_B, WB
    MSE = 5745.1111 / 48

    def p_of(self, d, se, df=48):
        from scipy import stats as st
        return 2 * st.t.sf(abs(d) / se, df)

    def rows_of(self, r, i=-1):
        return r["tabs"][0]["tables"][i]["rows"]

    def test_main_effect_of_the_data_sets_is_the_anova_f_test(self):
        # balanced: the data sets' means compared is the wool F test (R: P = 0.058213)
        r = A.run("twoway", self.T, [], {"compare": "mainsets"})
        row = self.rows_of(r)
        self.assertEqual(len(row), 1)
        self.assertEqual(row[0][3], "0.0582")
        self.assertEqual(r["brackets"], [], "main effects draw no brackets")

    def test_every_cell_against_a_control_and_chosen_pairs(self):
        cells = A.run("twoway", self.T, [], {"compare": "cells", "posthoc": "bonferroni"})
        self.assertEqual(len(self.rows_of(cells)), 15)
        self.assertEqual(len(cells["brackets"]), 15)
        ctrl = A.run("twoway", self.T, [], {"compare": "cells", "vs": "control", "controlSet": 1, "controlRow": 2, "posthoc": "bonferroni"})
        rows = self.rows_of(ctrl)
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(x[0].startswith("H · B vs") for x in rows), rows)
        # A · L against B · H by hand: Bonferroni over 5
        d = np.mean(self.A_[0]) - np.mean(self.B_[2])
        p = min(1, 5 * self.p_of(d, np.sqrt(self.MSE * 2 / 9)))
        b = [x for x in ctrl["brackets"] if (x[0], x[3], x[1], x[4]) == (1, 2, 0, 0)][0]
        self.assertAlmostEqual(b[2], p, places=6)
        pr = A.run("twoway", self.T, [], {"vs": "pairs", "pairs": [[0, 0, 1, 2], [0, 0, 0, 0], [5, 0, 1, 1]], "posthoc": "sidak"})
        self.assertEqual(len(pr["brackets"]), 1, "the same cell twice and unknown data sets are left out")
        self.assertAlmostEqual(pr["brackets"][0][2], self.p_of(np.mean(self.B_[2]) - np.mean(self.A_[0]), np.sqrt(self.MSE * 2 / 9)), places=6)
        with self.assertRaises(ValueError):
            A.run("twoway", self.T, [], {"vs": "pairs", "pairs": []})

    def test_rows_against_a_control_row_and_the_rows_main_effect(self):
        r = A.run("twoway", self.T, [], {"compare": "sets+mainrows", "vs": "control", "controlRow": 2})
        titles = [x["title"] for x in r["tabs"][0]["tables"]]
        self.assertTrue(any("within each data set, each against H" in x for x in titles) and any("rows' means (main effect), each against H" in x for x in titles), titles)
        main = self.rows_of(r)
        self.assertEqual([x[0] for x in main], ["H vs L", "H vs M"])
        # the rows' means (averaged over A and B) by hand: L against H, Šidák over 2
        d = (np.mean(self.A_[0]) + np.mean(self.B_[0])) / 2 - (np.mean(self.A_[2]) + np.mean(self.B_[2])) / 2
        p = 1 - (1 - self.p_of(d, np.sqrt(self.MSE * 2 * 2 / 9 / 4))) ** 2
        self.assertEqual(main[0][3], A.pv(p))
        self.assertEqual(len(r["brackets"]), 2 * 2)

    def test_false_discovery_rate_and_residual_plots(self):
        """0.4.22: the false discovery rate as a correction (Benjamini-Hochberg on the family's raw P values) and the
        three residual plots, for ordinary and repeated-measures two-way and one-way ANOVA."""
        from statsmodels.stats.multitest import multipletests
        raw = A.run("twoway", self.T, [], {"compare": "sets", "posthoc": "lsd"})["brackets"]
        fdr = A.run("twoway", self.T, [], {"compare": "sets", "posthoc": "fdr", "resplots": True})
        self.assertEqual([round(b[2], 9) for b in fdr["brackets"]], [round(q, 9) for q in multipletests([b[2] for b in raw], method="fdr_bh")[1]])
        self.assertIn("false discovery rate", fdr["tabs"][0]["tables"][-1]["title"])
        self.assertEqual([x["title"] for x in fdr["plots"]], ["Residuals: is the model right?", "Spread: equal variance?", "Normal QQ: normal residuals?"])
        self.assertEqual(A.run("twoway", self.T, [], {})["plots"], [], "only when asked")
        from test_repeated import grouped
        rng = np.random.default_rng(4)
        v = [[[rng.normal(10, 2) for _ in range(3)] for _ in range(3)] for _ in range(2)]
        self.assertEqual(len(A.run("twoway", grouped(v, 3, 2, 3), [], {"rm": "rows", "resplots": True})["plots"]), 3)
        one = A.run("anova", col(CTRL, TRT1, TRT2), [], {"resplots": True, "posthoc": "fdr", "vs": "all"})
        self.assertTrue(sum("QQ" in x["title"] for x in one["plots"]) == 1 and "false discovery rate" in one["methods"], one["methods"])
        rm = A.run("anova", col(CTRL, TRT1, TRT2), [], {"anova": "rm", "resplots": True})
        self.assertEqual(sum("QQ" in x["title"] for x in rm["plots"]), 1, "repeated measures too (subject and group effects removed)")

    def test_main_effects_model_compares_its_predicted_means(self):
        """0.4.23 (#67): without the interaction, comparisons use the model's predicted (least-squares) means, as other
        programs and R's emmeans do, also with unequal n. Made-up data (4 rows × 2 data sets, one cell with 4 values);
        checked against an independent least-squares fit of the additive model (numpy, dummy coding)."""
        vals = {(0, 0): [9.8, 11.2, 10.4, 8.9, 10.7], (0, 1): [16.1, 17.4, 15.2, 18.3, 16.8], (1, 0): [12.1, 13.0, 11.4, 12.8],
                (1, 1): [19.9, 21.3, 18.2, 20.6, 22.0], (2, 0): [8.4, 9.9, 9.1, 8.0, 9.5], (2, 1): [18.7, 17.2, 19.5, 20.1, 18.0],
                (3, 0): [14.6, 12.9, 13.8, 15.1, 14.0], (3, 1): [30.2, 27.9, 31.5, 29.1, 28.4]}
        R, S, n = 4, 2, 5
        cols = [[None] * R] + [[vals[(r, k)][j] if j < len(vals[(r, k)]) else None for r in range(R)] for k in range(S) for j in range(n)]
        t = {"kind": "grouped", "rows": R, "rowTitles": ["P", "Q", "U", "V"], "sets": [{"title": "Low", "entry": "rep", "reps": n}, {"title": "High", "entry": "rep", "reps": n}], "cols": cols, "excluded": []}
        r = A.run("twoway", t, [], {"interaction": False, "compare": "cells", "vs": "control", "posthoc": "bonferroni"})
        rows = r["tabs"][0]["tables"][-1]["rows"]
        # the additive model by hand: y = μ + row + data set; cell prediction x·β
        X, y = [], []
        for (rr, k), v in vals.items():
            for x in v:
                X.append([1] + [1 if rr == i else 0 for i in range(1, R)] + [1 if k == 1 else 0]); y.append(x)
        X, y = np.array(X, float), np.array(y)
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        res = y - X @ beta
        dfe = len(y) - X.shape[1]
        cov = res @ res / dfe * np.linalg.inv(X.T @ X)
        xc = lambda rr, k: np.array([1] + [1 if rr == i else 0 for i in range(1, R)] + [1 if k == 1 else 0], float)
        a_, b_ = xc(0, 0), xc(0, 1)
        d, se = (a_ - b_) @ beta, np.sqrt((a_ - b_) @ cov @ (a_ - b_))
        first = rows[0]  # P · Low vs P · High
        self.assertTrue(first[0].startswith("P · Low vs P · High"), first[0])
        self.assertAlmostEqual(float(first[1]), d, places=3)
        self.assertAlmostEqual(float(first[5]), a_ @ beta, places=3)
        self.assertAlmostEqual(float(first[7]), se, places=4)
        self.assertEqual(first[9], str(dfe))
        from scipy import stats as st
        self.assertEqual(first[3], A.pv(min(1, 7 * 2 * st.t.sf(abs(d / se), dfe))))
        self.assertLess(d, 0, "first minus second: Low − High is negative here")

    def test_repeated_measures_take_every_choice(self):
        rng = np.random.default_rng(3)
        from test_repeated import grouped
        v = [[[rng.normal(10, 2) for _ in range(3)] for _ in range(3)] for _ in range(2)]
        for o in ({"compare": "cells"}, {"compare": "mainsets+mainrows"}, {"compare": "rows", "vs": "control", "controlSet": 1}, {"vs": "pairs", "pairs": [[0, 0, 1, 2]]}):
            for rm in ("rows", "sets", "both"):
                r = A.run("twoway", grouped(v, 3, 2, 3), [], {"rm": rm, **o})
                self.assertTrue(r["answer"], (rm, o))


class Contingency(unittest.TestCase):
    @staticmethod
    def ct(M):
        R, C = len(M), len(M[0])
        return {"kind": "contingency", "rows": R, "rowTitles": [f"R{i}" for i in range(R)], "sets": [{"title": f"C{j}", "entry": "rep", "reps": 1} for j in range(C)],
                "cols": [[None] * R] + [[M[i][j] for i in range(R)] for j in range(C)], "excluded": []}

    def test_against_r(self):
        # R: chisq.test(rbind(c(762, 327, 468), c(484, 239, 477))): X-squared = 30.07, df = 2, p = 2.954e-07
        r = A.run("contingency", self.ct([[762, 327, 468], [484, 239, 477]]), [], {})
        self.assertEqual((cell(r, "Chi-square", None), cell(r, "Degrees of freedom", None)), ("30.07", "2"))
        # R: fisher.test(matrix(c(3, 1, 1, 3), 2)): p = 0.4857
        r = A.run("contingency", self.ct([[3, 1], [1, 3]]), [], {})
        self.assertEqual(cell(r, "Fisher's exact test, P value (two-tailed)", None), "0.4857")
        self.assertEqual(cell(r, None, 1, 1, t=1), "9")
        self.assertIn("<svg", graph.render(self.ct([[14, 36], [5, 45]]), {"column": "percent"})["svg"])
        with self.assertRaises(ValueError):
            A.run("contingency", self.ct([[1.5, 2], [3, 4]]), [], {})


class Parts(unittest.TestCase):
    def test_fractions_with_wilson_intervals(self):
        # Wilson 95% CI for 885 of 1000: 0.8641 to 0.9029 (R: prop.test(885, 1000, correct = FALSE)$conf.int)
        t = {"kind": "parts", "rows": 3, "rowTitles": ["a", "b", "c"], "sets": [{"title": "S", "entry": "rep", "reps": 1}], "cols": [[None] * 3, [35, 885, 80]], "excluded": []}
        r = A.run("parts", t, [], {})
        self.assertEqual(cell(r, None, 1, 2), "88.5%")
        self.assertEqual(cell(r, None, 1, 3), "86.4% to 90.3%")
        for kind in ["pie", "donut", "percent"]:
            self.assertIn("<svg", graph.render(t, {"column": kind})["svg"])


class Agreement(unittest.TestCase):
    def test_bland_altman_by_hand(self):
        a, b = [10, 12, 14, 16, 18], [11, 12, 15, 18, 19]
        r = A.run("blandaltman", col(a, b), [], {})
        d = np.subtract(b, a)
        self.assertEqual(cell(r, None, 0, 1), "1")
        self.assertEqual(cell(r, None, 2, 1), A.g(d.mean() - 1.959963984540054 * d.std(ddof=1)))
        self.assertEqual(r["table"]["cols"][1], list(map(float, d)))

    def test_roc_auc_is_the_mann_whitney_probability(self):
        # P(case > control) + ½ P(tie) for controls 1, 2, 3 and cases 2, 3, 4 = 7/9
        r = A.run("roc", col([1, 2, 3], [2, 3, 4]), [], {})
        self.assertEqual(cell(r, None, 0, 1), "0.7778")
        self.assertEqual(cell(A.run("roc", col([1, 2, 3], [2, 3, 4]), [], {"direction": "lower"}), None, 0, 1), "0.2222")
        self.assertEqual(len(A.run("anova", col(CTRL, TRT1, TRT2), [], {})["plots"]), 2)


class AxisTools(unittest.TestCase):
    def test_right_axis_and_axis_break(self):
        t = xy([0, 1, 2, 3], [1, 2, 3, 4], [100, 104, 110, 113])
        r = graph.render(t, {"sets": [{}, {"right": True}]}, [{"kind": "linear", "options": {}}])
        right = [p for p in r["points"] if p[0] == 1]
        self.assertTrue(all(len(p) == 7 and r["ylim"][0] <= p[6] <= r["ylim"][1] for p in right), right)
        r = graph.render(t, {"y": {"breakFrom": 5, "breakTo": 95}}, [])
        self.assertEqual(r["ylim"][1], 5)
        self.assertTrue(graph.export(t, {"y": {"breakFrom": 5, "breakTo": 95}}, "png")["data"])


class Notes(unittest.TestCase):
    def test_notes_draw_and_never_move_the_axes(self):
        t = xy([0, 1, 2, 3], [1, 4, 2, 5])
        base = graph.render(t, {})
        n = [{"kind": k, "x": 1, "y": 40, "x2": 9, "y2": -5, "text": "far"} for k in ("text", "arrow", "line", "box")]
        r = graph.render(t, {"notes": n})
        self.assertEqual((r["xlim"], r["ylim"]), (base["xlim"], base["ylim"]))
        self.assertIn("far", r["svg"])


class EmptySets(unittest.TestCase):
    def test_empty_groups_are_left_out(self):
        t = col(SLEEP1, SLEEP2, [])
        r = A.run("anova", t, [], {})
        self.assertIn("Left out because it is empty: G2.", r["checks"][-1][1])
        self.assertAlmostEqual(p_of(cell(A.run("ttest", t, [], {}), "P value (two-tailed)", None)), 0.0794, places=4)

    def test_x_axis_break(self):
        t = xy([0, 1, 2, 50, 51], [1, 2, 3, 4, 5])
        r = graph.render(t, {"x": {"breakFrom": 3, "breakTo": 49}})
        self.assertEqual(r["xlim"][1], 3)


class Pages(unittest.TestCase):
    def test_a_page_of_two_graphs_with_letters_and_cmyk_tiff(self):
        import io as _io
        from PIL import Image
        t = xy([0, 1, 2, 3], [1, 4, 2, 5])
        panels = {"1": {"table": t, "graph": {}, "overlays": []}, "2": {"table": col(CTRL, TRT1), "graph": {"column": "bars"},
                  # 0.4.6 (#52): brackets inside a layout (a sub-figure has no size of its own; the guide caught it)
                  "overlays": [{"kind": "ttest", "sets": [], "options": {"brackets": "all"}}]}}
        L = {"width": 174, "height": 70, "letters": "A", "items": [{"kind": "graph", "graph": 1, "x": 0, "y": 0, "w": 85, "h": 70}, {"kind": "graph", "graph": 2, "x": 89, "y": 0, "w": 85, "h": 70},
                                                               {"kind": "graph", "graph": 9, "x": 0, "y": 0, "w": 50, "h": 50}, {"kind": "text", "x": 1, "y": 66, "text": "Figure 1"}]}
        svg = graph.page(L, panels)["svg"]
        self.assertTrue(all(s in svg for s in (">A<", ">B<", "Figure 1")) and ">C<" not in svg)
        im = Image.open(_io.BytesIO(__import__("base64").b64decode(graph.page(L, panels, "tiff", dpi=150, cmyk=True)["data"])))
        self.assertEqual((im.mode, round(im.size[0] / 150 * 25.4)), ("CMYK", 174))
        self.assertTrue(graph.export(t, {}, "tiff", dpi=100, cmyk=True)["data"])

    def test_aligned_stacked_panels_and_an_inset(self):
        t, u = xy([0, 1, 2, 3], [1, 4, 2, 5]), xy([0, 1, 2], [1000, 2000, 1500])
        panels = {"1": {"table": t, "graph": {}, "overlays": []}, "2": {"table": u, "graph": {}, "overlays": []}}
        L = {"width": 100, "height": 120, "letters": "A", "align": True, "items": [{"kind": "graph", "graph": 1, "x": 0, "y": 0, "w": 100, "h": 60, "hideX": True},
                                                                                 {"kind": "graph", "graph": 2, "x": 0, "y": 60, "w": 100, "h": 60}, {"kind": "graph", "graph": 1, "x": 55, "y": 65, "w": 40, "h": 30, "inset": True}]}
        svg = graph.page(L, panels)["svg"]
        self.assertTrue(">A<" in svg and ">B<" in svg and ">C<" not in svg, "insets have no letter")
        self.assertNotEqual(svg, graph.page({**L, "align": False}, panels)["svg"], "lining up moves the frames (Y numbers of different widths)")
