"""Many variables (B21) against R: lm(mpg ~ wt + hp, mtcars), glm(am ~ wt + hp, binomial, mtcars) and
Dobson's Poisson example from ?glm. Run: python -m unittest discover -s py/tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datum import analysis as A, graph  # noqa: E402

# mtcars: mpg, wt, hp, am
MPG = [21, 21, 22.8, 21.4, 18.7, 18.1, 14.3, 24.4, 22.8, 19.2, 17.8, 16.4, 17.3, 15.2, 10.4, 10.4, 14.7, 32.4, 30.4, 33.9, 21.5, 15.5, 15.2, 13.3, 19.2, 27.3, 26, 30.4, 15.8, 19.7, 15, 21.4]
WT = [2.62, 2.875, 2.32, 3.215, 3.44, 3.46, 3.57, 3.19, 3.15, 3.44, 3.44, 4.07, 3.73, 3.78, 5.25, 5.424, 5.345, 2.2, 1.615, 1.835, 2.465, 3.52, 3.435, 3.84, 3.845, 1.935, 2.14, 1.513, 3.17, 2.77, 3.57, 2.78]
HP = [110, 110, 93, 110, 175, 105, 245, 62, 95, 123, 123, 180, 180, 180, 205, 215, 230, 66, 52, 65, 97, 150, 150, 245, 175, 66, 91, 113, 264, 175, 335, 109]
AM = [1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1]


def multi(**cols):
    n = max(len(v) for v in cols.values())
    return {"name": "T", "kind": "multi", "rows": n, "sets": [{"title": k, "entry": "rep", "reps": 1} for k in cols], "cols": [[None] * n] + [list(v) for v in cols.values()],
            "excluded": [], "xTitle": "", "yTitle": "Value", "rowTitles": []}


def cell(r, tab, row, col):
    return r["tabs"][0]["tables"][tab]["rows"][row][col]


class Regression(unittest.TestCase):
    def test_multiple_linear_matches_r(self):
        # R: (Intercept) 37.22727 (1.59879), wt -3.87783 (0.63273), hp -0.03177 (0.00903); R² 0.8268, adj 0.8148, F 69.21 on 2 and 29 DF; AIC 156.6523
        r = A.run("multireg", multi(mpg=MPG, wt=WT, hp=HP), [], {"y": 0})
        self.assertEqual([cell(r, 0, i, 1) for i in range(3)], ["37.227", "-3.8778", "-0.031773"])
        self.assertEqual([cell(r, 0, i, 2) for i in range(3)], ["1.599", "0.6327", "0.00903"])
        self.assertEqual([cell(r, 1, i, 1) for i in (1, 2)], ["0.8268", "0.8148"])
        self.assertTrue(cell(r, 1, 3, 1).startswith("69.211") and cell(r, 1, 6, 1) == "156.65")
        self.assertIn("83%", r["answer"])

    def test_logistic_matches_r(self):
        # R: (Intercept) 18.86630 (7.44356), wt -8.08348 (3.06868), hp 0.03626 (0.01773); null deviance 43.230 on 31, residual 10.059 on 29, AIC 16.059
        r = A.run("multireg", multi(am=AM, wt=WT, hp=HP), [], {"y": 0, "model": "logistic"})
        self.assertEqual([cell(r, 0, i, 1) for i in range(3)], ["18.866", "-8.0835", "0.036256"])
        self.assertEqual([cell(r, 0, i, 2) for i in range(3)], ["7.444", "3.069", "0.01773"])
        self.assertEqual((cell(r, 1, 1, 1), cell(r, 1, 2, 1), cell(r, 1, 6, 1)), ("43.23 (DF = 31)", "10.059 (DF = 29)", "16.059"))
        with self.assertRaises(ValueError):
            A.run("multireg", multi(mpg=MPG, wt=WT), [], {"model": "logistic"})

    def test_poisson_matches_r(self):
        # R ?glm (Dobson 1990): outcome2 -0.4543 (0.2022), outcome3 -0.2930 (0.1927), (Intercept) 3.045; AIC 56.76; treatment terms 0
        counts = [18, 17, 15, 20, 10, 20, 25, 13, 12]
        o2, o3 = [0, 1, 0] * 3, [0, 0, 1] * 3
        t2, t3 = [0, 0, 0, 1, 1, 1, 0, 0, 0], [0] * 6 + [1] * 3
        r = A.run("multireg", multi(counts=counts, o2=o2, o3=o3, t2=t2, t3=t3), [], {"model": "poisson"})
        self.assertEqual([cell(r, 0, i, 1) for i in range(3)], ["3.0445", "-0.45426", "-0.29299"])
        self.assertEqual(cell(r, 1, 6, 1), "56.761")

    def test_missing_rows_graph_and_xy_view(self):
        t = multi(mpg=MPG + [None], wt=WT + [3.0], hp=HP + [None])
        r = A.run("multireg", t, [0, 1], {"y": 0})
        self.assertTrue(any("left out" in c[1] for c in r["checks"]))
        self.assertTrue(A.run("linear", t, [], {})["answer"].startswith("wt:"))  # the first variable (mpg) is X for XY analyses
        self.assertIn("<svg", str(graph.render(t, {})), "mpg")  # X axis title: the first variable
        self.assertIn("hp", str(graph.render(t, {})))


# R's USArrests (Murder, Assault, UrbanPop, Rape), 50 states
US = """13.2 236 58 21.2|10.0 263 48 44.5|8.1 294 80 31.0|8.8 190 50 19.5|9.0 276 91 40.6|7.9 204 78 38.7|3.3 110 77 11.1|5.9 238 72 15.8|15.4 335 80 31.9|17.4 211 60 25.8|
5.3 46 83 20.2|2.6 120 54 14.2|10.4 249 83 24.0|7.2 113 65 21.0|2.2 56 57 11.3|6.0 115 66 18.0|9.7 109 52 16.3|15.4 249 66 22.2|2.1 83 51 7.8|11.3 300 67 27.8|
4.4 149 85 16.3|12.1 255 74 35.1|2.7 72 66 14.9|16.1 259 44 17.1|9.0 178 70 28.2|6.0 109 53 16.4|4.3 102 62 16.5|12.2 252 81 46.0|2.1 57 56 9.5|7.4 159 89 18.8|
11.4 285 70 32.1|11.1 254 86 26.1|13.0 337 45 16.1|0.8 45 44 7.3|7.3 120 75 21.4|6.6 151 68 20.0|4.9 159 67 29.3|6.3 106 72 14.9|3.4 174 87 8.3|14.4 279 48 22.5|
3.8 86 45 12.8|13.2 188 59 26.9|12.7 201 80 25.5|3.2 120 80 22.9|2.2 48 32 11.2|8.5 156 63 20.7|4.0 145 73 26.2|5.7 81 39 9.3|2.6 53 66 10.8|6.8 161 60 15.6"""
USA = [[float(v) for v in r.split()] for r in US.replace("\n", "").split("|")]


class Patterns(unittest.TestCase):
    def test_data_is_r_usarrests(self):
        # R: colMeans(USArrests) 7.788 170.76 65.54 21.232
        self.assertEqual([round(sum(r[j] for r in USA) / 50, 3) for j in range(4)], [7.788, 170.76, 65.54, 21.232])

    def test_pca_matches_r_prcomp(self):
        # R: prcomp(USArrests, scale. = TRUE): sdev 1.5748783 0.9948694 0.5971291 0.4164494; PC1 loadings (sign free) 0.5358995 0.5831836 0.2781909 0.5434321
        t = multi(Murder=[r[0] for r in USA], Assault=[r[1] for r in USA], UrbanPop=[r[2] for r in USA], Rape=[r[3] for r in USA])
        r = A.run("pca", t, [], {})
        self.assertEqual([cell(r, 0, i, 2) for i in range(4)], ["1.575", "0.9949", "0.5971", "0.4164"])
        self.assertEqual([cell(r, 1, j, 1) for j in range(4)], ["0.5359", "0.5832", "0.2782", "0.5434"])
        self.assertEqual(cell(r, 0, 0, 3), "62.0%")
        self.assertTrue(r["answer"].startswith("PC1 explains 62.0%") and "1 component" in r["answer"])
        tb = r["table"]
        self.assertEqual((tb["kind"], tb["rows"], [s["title"] for s in tb["sets"]][:2]), ("multi", 50, ["PC1", "PC2"]))
        self.assertAlmostEqual(sum(tb["cols"][1]), 0, 9)

    def test_clusters_find_two_obvious_groups(self):
        a = [1.0, 1.2, 0.9, 1.1, 1.05, 5.0, 5.2, 4.9, 5.1, 4.95]
        b = [2.0, 2.1, 1.9, 2.05, 2.0, 8.0, 8.1, 7.9, 8.05, 8.0]
        for m in ("ward", "kmeans", "average"):
            r = A.run("cluster", multi(a=a, b=b), [], {"k": 2, "method": m})
            self.assertIn("2 clusters of 5, 5", r["answer"], m)
            self.assertEqual(r["table"]["cols"][-1], [1.0] * 5 + [2.0] * 5)
            self.assertIn("clear structure", r["answer"])
        with self.assertRaises(ValueError):
            A.run("cluster", multi(a=a, b=b), [], {"k": 10})


def surv(groups):
    """A survival table: time in X, one row per subject, 1 (event) or 0 (censored) in its group's column."""
    rows = [(t, k, e) for k, g_ in enumerate(groups.values()) for t, e in g_]
    cols = [[float(t) for t, _, _ in rows]] + [[float(e) if k == j else None for _, k, e in rows] for j in range(len(groups))]
    return {"name": "S", "kind": "survival", "rows": len(rows), "sets": [{"title": n, "entry": "rep", "reps": 1} for n in groups], "cols": cols, "excluded": [], "xTitle": "Weeks", "yTitle": "Percent survival"}


# R survival::aml
AML = {"Maintained": [(9, 1), (13, 1), (13, 0), (18, 1), (23, 1), (28, 0), (31, 1), (34, 1), (45, 0), (48, 1), (161, 0)],
       "Nonmaintained": [(5, 1), (5, 1), (8, 1), (8, 1), (12, 1), (16, 0), (23, 1), (27, 1), (30, 1), (33, 1), (43, 1), (45, 1)]}


class Survival(unittest.TestCase):
    def test_kaplan_meier_logrank_and_cox_match_r(self):
        # R: survfit(Surv(time, status) ~ x, aml): medians 31 (18–NA) and 23 (8–NA); Maintained S = .909 .818 .716 .614 .491 .368 .184
        # survdiff: Chisq = 3.4 on 1 df, p = 0.0653 (statsmodels survdiff: 3.39639); coxph: HR 2.498 (0.9159–6.813), p = 0.0737
        r = A.run("survival", surv(AML), [], {})
        s = r["tabs"][0]["tables"]
        self.assertEqual([row[4:] for row in s[0]["rows"]], [["31", "18 to —"], ["23", "8 to —"]])
        self.assertEqual([row[4] for row in r["tabs"][1]["tables"][0]["rows"] if row[2] != "0"], ["0.9091", "0.8182", "0.7159", "0.6136", "0.4909", "0.3682", "0.1841"])
        self.assertEqual((s[1]["rows"][0][1], s[1]["rows"][2][1]), ("3.3964", "0.0653"))
        self.assertEqual(s[2]["rows"][0][1:], ["2.498", "0.9159 to 6.813", "0.0737"])
        self.assertIn("do not differ significantly", r["answer"])

    def test_survival_graph(self):
        out = graph.render(surv(AML), {"error": "ci"})
        self.assertIn("<svg", out["svg"])
        self.assertTrue(any(p and p[1] == 31 and abs(p[2] - 49.09) < 0.01 for p in out["points"]))


def nest(*groups):
    """A nested table: each group a data set whose sub-columns are its subgroups, replicates down the rows."""
    n = max(len(v) for gr in groups for v in gr)
    cols = [[None] * n] + [list(v) + [None] * (n - len(v)) for gr in groups for v in gr]
    return {"name": "N", "kind": "nested", "rows": n, "sets": [{"title": f"G{i}", "entry": "rep", "reps": len(gr)} for i, gr in enumerate(groups)], "cols": cols, "excluded": [], "xTitle": "", "yTitle": "Y"}


G1 = [[50.1, 51.3, 49.8, 50.6], [52.4, 53.1, 51.9, 52.8], [49.2, 48.7, 50.0, 49.5]]
G2 = [[54.0, 55.2, 53.7, 54.4], [51.8, 52.6, 52.1, 51.5], [55.9, 56.3, 55.1, 56.0]]
G3 = [[50.5, 49.9, 51.2, 50.8], [53.3, 52.7, 53.9, 53.0], [51.1, 51.6, 50.4, 51.0]]


class Nested(unittest.TestCase):
    def test_balanced_nested_anova_is_anova_of_subgroup_means(self):
        # Balanced design: the nested F for groups equals one-way ANOVA on the subgroup means (as R aov(y ~ g + Error(sub))),
        # and the REML variance components equal the ANOVA estimators (MS_sub − MS_res) / n and MS_res.
        from scipy import stats as st
        import numpy as np
        r = A.run("nested", nest(G1, G2, G3), [], {})
        f, p = st.f_oneway(*[[np.mean(v) for v in gr] for gr in (G1, G2, G3)])
        rows = r["tabs"][0]["tables"][0]["rows"]
        self.assertEqual(rows[0][4], f"F = {A.g(f, 4)} (DFn 2, DFd 6)")
        self.assertEqual(rows[0][5], A.pv(p))
        ms = {row[0]: float(row[3]) for row in rows if row[3]}
        vc = r["tabs"][0]["tables"][2]["rows"]
        self.assertAlmostEqual(float(vc[0][1]), (ms["Between subgroups within groups"] - ms["Residual (within subgroups)"]) / 4, 2)
        self.assertAlmostEqual(float(vc[1][1]), ms["Residual (within subgroups)"], 3)

    def test_two_groups_give_a_nested_t_test(self):
        from scipy import stats as st
        import numpy as np
        r = A.run("nested", nest(G1, G2), [], {})
        t, p = st.ttest_ind([np.mean(v) for v in G2], [np.mean(v) for v in G1])
        row = r["tabs"][0]["tables"][0]["rows"][0]
        self.assertEqual((r["title"], row[4], row[5]), ("Nested t-test", f"t = {A.g(t, 4)}", A.pv(p)))
        with self.assertRaises(ValueError):
            A.run("nested", nest([[1, 2]], [[3, 4]]), [], {})

    def test_nested_graph(self):
        out = graph.render(nest(G1, G2, G3), {})
        self.assertIn("<svg", out["svg"])
        self.assertEqual(len([p for p in out["points"] if p]), 9)  # one hover point per subgroup
