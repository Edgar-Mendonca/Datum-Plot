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
