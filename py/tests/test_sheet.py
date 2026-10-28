"""Worksheets and column formulas (A9, A11): formulas against numpy, their safety checks, chained
recalculation, and a worksheet seen as an XY table (X column, Y with its error column).
Run: python -m unittest discover -s py/tests"""
import math
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datum import analysis as A, graph, sheet  # noqa: E402


def ws(*cols, roles=None, formulas=None):
    n = max(len(c) for c in cols)
    return {"name": "W", "kind": "sheet", "rows": n, "xTitle": "", "yTitle": "", "excluded": [],
            "sets": [{"title": f"C{k}", "entry": "rep", "reps": 1, "role": (roles or [""] * len(cols))[k], "units": "", "formula": (formulas or [""] * len(cols))[k]} for k in range(len(cols))],
            "cols": [[None] * n] + [list(c) + [None] * (n - len(c)) for c in cols]}


A_ = [1.0, 10.0, 100.0, None, 1000.0]
B_ = [2.0, 4.0, 6.0, 8.0, 10.0]


class Formulas(unittest.TestCase):
    def test_arithmetic_functions_and_empty_rows(self):
        t = ws(A_, B_)
        self.assertEqual(sheet.evaluate(t, "log10(A)"), [0.0, 1.0, 2.0, None, 3.0])
        self.assertEqual(sheet.evaluate(t, "=B^2 / 2 + i"), [3.0, 10.0, 21.0, 36.0, 55.0])
        z = sheet.evaluate(t, "(B - mean(B)) / sd(B)")
        self.assertTrue(np.allclose(z, (np.array(B_) - 6) / np.std(B_, ddof=1)))
        self.assertEqual(sheet.evaluate(t, "if(B > 5, 1, 0)"), [0.0, 0.0, 1.0, 1.0, 1.0])
        self.assertEqual(sheet.evaluate(t, 'col("c1") * 2'), [4.0, 8.0, 12.0, 16.0, 20.0])
        self.assertEqual(sheet.evaluate(t, "cumsum(B)"), [2.0, 6.0, 12.0, 20.0, 30.0])
        self.assertTrue(np.allclose(sheet.evaluate(t, "pi"), math.pi, rtol=1e-14))
        self.assertEqual(sheet.evaluate(ws([200.2]), "A + 273.15"), [473.35])

    def test_unsafe_or_wrong_formulas_are_refused(self):
        t = ws(A_, B_)
        for bad in ["__import__('os')", "A.__class__", "open('x')", "[1, 2]", "lambda: 1", "Q + 1", "(A", "B[0]", "'a' * 9", "10^10^10^10"]:
            with self.assertRaises(ValueError, msg=bad):
                sheet.evaluate(t, bad)

    def test_recalc_chains_left_to_right(self):
        t = ws(B_, [None] * 5, [None] * 5, formulas=["", "A * 10", "B + 1"])
        out = sheet.recalc(t)["sets"]
        self.assertEqual(out, [[1, [20.0, 40.0, 60.0, 80.0, 100.0]], [2, [21.0, 41.0, 61.0, 81.0, 101.0]]])
        self.assertEqual(sheet.recalc(t, 1, "")["sets"][0][1], [None] * 5)  # B cleared: C has nothing to add to


class Worksheet(unittest.TestCase):
    def test_view_graph_and_analysis(self):
        t = ws([1, 2, 3, 4], [2.1, 3.9, 6.2, 7.8], [0.2, 0.3, 0.2, 0.4], [5, 5, 5, 5], roles=["x", "", "yerr", "skip"])
        v = sheet.sheet_view(t)
        self.assertEqual((v["cols"][0], v["sets"][1]["entry"], v["hidden"]), ([1, 2, 3, 4], "msn", [0, 2, 3]))
        out = graph.render(t, {"error": "sd"})
        pts = [p for p in out["points"] if p]
        self.assertEqual([(p[0], p[1], p[2], p[4]) for p in pts][:2], [(1, 1, 2.1, 0.2), (1, 2, 3.9, 0.3)])
        self.assertEqual({p[0] for p in pts}, {1})
        r = A.run("linear", t, [], {})
        self.assertTrue(r["answer"].startswith("C1:"))
