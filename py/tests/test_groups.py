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
        self.assertEqual(tk["rows"][2][1], "0.865")
        # η² = SSB / SST = 3.7663 / 14.258
        self.assertAlmostEqual(num(cell(r, "R squared (η²)", None)), 0.2641, places=4)

    def test_every_variant_runs(self):
        for o in [{"anova": "welch", "posthoc": "dunnett"}, {"anova": "bf", "posthoc": "holm"}, {"anova": "rm", "posthoc": "bonferroni"}, {"posthoc": "sidak", "trend": True}, {"posthoc": "lsd"}, {"posthoc": "none"}]:
            r = A.run("anova", col(CTRL, TRT1, TRT2), [], o)
            self.assertTrue(r["answer"].startswith("The means"), o)


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
