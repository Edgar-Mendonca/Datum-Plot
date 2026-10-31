"""Multiple t-tests and the volcano plot (B33, D18): each row's test equals SciPy's, the
Benjamini-Hochberg q values equal the step-up formula worked by hand, and the volcano table holds every
row. Run: python -m unittest discover -s py/tests"""
import os
import sys
import unittest

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datum import analysis as A  # noqa: E402


def table(ctrl, trt):
    G, reps = ctrl.shape
    return {"name": "Expression", "kind": "grouped", "rows": G, "rowTitles": [f"Gene{i + 1}" for i in range(G)], "excluded": [],
            "sets": [{"title": "Control", "entry": "rep", "reps": reps}, {"title": "Treated", "entry": "rep", "reps": reps}],
            "cols": [[None] * G] + [list(ctrl[:, j]) for j in range(reps)] + [list(trt[:, j]) for j in range(reps)]}


def bh(p):
    """Benjamini-Hochberg by hand: q(i) = min over j ≥ i of p(j)·n/j, in sorted order."""
    p = np.asarray(p)
    n, o = len(p), np.argsort(p)
    q = np.minimum.accumulate((p[o] * n / np.arange(1, n + 1))[::-1])[::-1]
    out = np.empty(n)
    out[o] = np.minimum(q, 1)
    return out


class MultipleTTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(5)
        self.G, reps = 60, 4
        eff = np.zeros(self.G)
        eff[:8] = [2, -2, 2.5, -1.5, 3, -3, 1.8, -2.2]
        base = rng.uniform(5, 12, self.G)
        self.ctrl = base[:, None] + rng.normal(0, 0.5, (self.G, reps))
        self.trt = base[:, None] + eff[:, None] + rng.normal(0, 0.5, (self.G, reps))
        self.t = table(self.ctrl, self.trt)

    def test_each_row_and_the_false_discovery_rate(self):
        r = A.run("multit", self.t, [], {"test": "welch", "method": "fdr_bh", "q": 0.05})
        t, p = stats.ttest_ind(self.trt, self.ctrl, axis=1, equal_var=False)
        q = bh(p)
        self.assertIn(f"{int((q < 0.05).sum())} of {self.G} rows are discoveries", r["answer"])
        rows = {row[0]: row for row in r["tabs"][1]["tables"][0]["rows"]}
        for i in (0, 5, 40):
            self.assertAlmostEqual(float(rows[f"Gene{i + 1}"][5]), t[i], delta=abs(t[i]) * 1e-3)
            self.assertEqual(rows[f"Gene{i + 1}"][8], "Yes" if q[i] < 0.05 else "No")
        new = r["table"]
        self.assertEqual((new["rows"], len(new["cols"]), new["rowTitles"][0]), (self.G, 3, "Gene1"))
        ys = [a if a is not None else b for a, b in zip(new["cols"][1], new["cols"][2])]
        self.assertTrue(np.allclose(sorted(ys, reverse=True)[:3], sorted(-np.log10(p), reverse=True)[:3]))
        self.assertEqual(len(r["plots"]), 1)

    def test_other_tests_and_corrections_run_and_are_stricter_or_looser(self):
        hits = {m: int(A.run("multit", self.t, [], {"method": m})["answer"].split(" of ")[0]) for m in ("none", "fdr_bh", "fdr_tsbky", "holm-sidak", "bonferroni")}
        self.assertTrue(hits["none"] >= hits["fdr_bh"] >= hits["holm-sidak"] >= hits["bonferroni"])
        self.assertGreaterEqual(hits["fdr_tsbky"], hits["fdr_bh"] - 1)
        for test in ("student", "paired", "mw"):
            self.assertIn("rows are discoveries", A.run("multit", self.t, [], {"test": test})["answer"])

    def test_bad_input_says_why(self):
        one = dict(self.t, sets=self.t["sets"][:1], cols=self.t["cols"][:5])
        with self.assertRaises(ValueError):
            A.run("multit", one, [], {})
        with self.assertRaises(ValueError):
            A.run("multit", self.t, [], {"q": 2})


if __name__ == "__main__":
    unittest.main()
