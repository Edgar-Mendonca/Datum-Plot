"""Repeated measures and mixed-effects ANOVA (B32), checked against independent results:
the fully repeated design against statsmodels' AnovaRM, the split-plot design against its own
mixed model (identical F tests and DF for complete data), and the switch to the mixed model when
values are missing. Run: python -m unittest discover -s py/tests"""
import os
import sys
import unittest
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datum import analysis as A, repeated as R  # noqa: E402


def grouped(values, rows, sets, reps):
    """A grouped table: values[k][r][j] for data set k, row r, sub-column (subject) j."""
    cols = [[None] * rows]
    for k in range(sets):
        for j in range(reps):
            cols.append([values[k][r][j] for r in range(rows)])
    return {"kind": "grouped", "rows": rows, "rowTitles": [f"T{r}" for r in range(rows)], "excluded": [],
            "sets": [{"title": f"G{k}", "entry": "rep", "reps": reps} for k in range(sets)], "cols": cols}


class RepeatedMeasures(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore")

    def test_fully_repeated_design_matches_anova_rm(self):
        from statsmodels.stats.anova import AnovaRM
        rng = np.random.default_rng(3)
        rows = [(f"a{a}", f"b{b}", f"s{s}", 10 + 2 * a + 3 * b * (a == 2) + u + rng.normal(0, 1)) for s, u in enumerate(rng.normal(0, 2, 6)) for a in range(3) for b in range(2)]
        df = pd.DataFrame(rows, columns=["A", "B", "S", "y"])
        out, eps, _ = R.classic(df, "both")
        ref = AnovaRM(df.rename(columns={"A": "fa", "B": "fb", "S": "subj", "y": "val"}), "val", "subj", within=["fa", "fb"]).fit().anova_table
        for (k, ss, d, _, sse, dfe), key in zip(out, ["fa", "fb", "fa:fb"]):
            self.assertAlmostEqual((ss / d) / (sse / dfe), ref.loc[key, "F Value"], places=6)
            self.assertEqual((d, dfe), (ref.loc[key, "Num DF"], ref.loc[key, "Den DF"]))
        self.assertTrue(0.5 <= eps["A"] <= 1 and eps["B"] == 1.0)

    def test_split_plot_classic_and_mixed_model_agree(self):
        rng = np.random.default_rng(7)
        rows = [(f"t{a}", f"g{gr}", f"{gr}:{j}", 5 + a + 0.5 * gr * a + u + rng.normal(0, 1)) for gr in range(2) for j, u in enumerate(rng.normal(0, 2, 5)) for a in range(4)]
        df = pd.DataFrame(rows, columns=["A", "B", "S", "y"])
        classic = {k: ((ss / d) / (sse / dfe), d, dfe) for k, ss, d, _, sse, dfe in R.classic(df, "rows")[0]}
        mixed = {k: (F, d1, d2) for k, F, d1, d2, _, _ in R.mixed(df, "rows")[0]}
        for k in ("A", "B", "AB"):
            self.assertAlmostEqual(classic[k][0], mixed[k][0], delta=1e-3 * classic[k][0])
            self.assertEqual(classic[k][1:], mixed[k][1:])

    def test_the_analysis_uses_the_mixed_model_when_values_are_missing(self):
        rng = np.random.default_rng(1)
        v = [[[10 + 3 * r + 2 * k * r + s + rng.normal(0, 1) for s in rng.normal(0, 2, 4)] for r in range(3)] for k in range(2)]
        t = grouped(v, 3, 2, 4)
        full = A.run("twoway", t, [], {"rm": "rows"})
        self.assertEqual(full["title"], "Two-way repeated measures ANOVA")
        t["cols"][2][1] = None
        part = A.run("twoway", t, [], {"rm": "rows", "posthoc": "sidak"})
        self.assertEqual(part["title"], "Mixed-effects model")
        self.assertIn("values are missing", " ".join(c[1] for c in part["checks"]))
        self.assertEqual(len(part["brackets"]), 3, "one comparison of the two data sets in each row")
        self.assertEqual(A.run("twoway", t, [], {})["title"], "Two-way ANOVA", "without the option, the ordinary two-way ANOVA")

    def test_every_design_runs_and_bad_designs_say_why(self):
        rng = np.random.default_rng(2)
        v = [[[rng.normal(10, 2) for _ in range(3)] for _ in range(3)] for _ in range(2)]
        for rm in ("rows", "sets", "both"):
            r = A.run("twoway", grouped(v, 3, 2, 3), [], {"rm": rm, "posthoc": "holm", "compare": "sets"})
            self.assertTrue(r["answer"])
        with self.assertRaises(ValueError):
            A.run("twoway", grouped([[[1.0]] * 2] * 2, 2, 2, 1), [], {"rm": "rows"})  # one subject per group


if __name__ == "__main__":
    unittest.main()
