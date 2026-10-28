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
