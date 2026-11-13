"""Bayes factors (B37, 0.4.4), checked against R's BayesFactor package and against the identities they must obey:
the paired t-test on the classic sleep data gives BF₁₀ = 17.25888 (ttestBF, default prior √2/2, as in its manual);
a one-way ANOVA of two groups equals the unpaired t-test (Rouder et al. 2012); the closed form for Pearson's r
(Ly et al. 2016) equals direct integration of its likelihood.
Run: python -m unittest discover -s py/tests"""
import math
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datum import analysis as A, bayes  # noqa: E402

# The sleep data (Cushny & Peebles 1905; R's `sleep`): extra hours of sleep with two drugs, the same ten patients.
D1 = [0.7, -1.6, -0.2, -1.2, -0.1, 3.4, 3.7, 0.8, 0.0, 2.0]
D2 = [1.9, 0.8, 1.1, 0.1, -0.1, 4.4, 5.5, 1.6, 4.6, 3.4]


def column(*sets):
    n = max(len(s) for s in sets)
    return {"name": "T", "kind": "column", "rows": n, "sets": [{"title": f"G{i + 1}", "entry": "rep", "reps": 1} for i in range(len(sets))],
            "cols": [[None] * n] + [list(s) + [None] * (n - len(s)) for s in sets], "excluded": [], "xTitle": "", "yTitle": "Y"}


def value(res, label):
    for tab in res["tabs"][0]["tables"]:
        for row in tab["rows"]:
            if row[0] == label:
                return row[1]
    raise KeyError(label)


class BayesFactors(unittest.TestCase):
    def test_paired_t_test_matches_r(self):
        r = A.run("ttest", column(D1, D2), [], {"test": "paired", "bayes": True})
        self.assertAlmostEqual(float(value(r, "Bayes factor BF₁₀")), 17.26, places=2)
        self.assertIn("strong evidence for a difference", r["answer"])
        from scipy import stats
        t = float(stats.ttest_rel(D2, D1).statistic)
        self.assertAlmostEqual(bayes.t_bf(t, 10, 9), 17.25888, places=4)

    def test_two_group_anova_equals_the_t_test(self):
        a, b = D1, D2[:7]  # unequal groups too
        t = A.run("ttest", column(a, b), [], {"test": "unpaired", "welch": False, "bayes": True})
        f = A.run("anova", column(a, b), [], {"posthoc": "none", "bayes": True})
        self.assertEqual(value(t, "Bayes factor BF₁₀"), value(f, "Bayes factor BF₁₀"))
        self.assertAlmostEqual(bayes.anova_bf([10, 10], [np.mean(D1), np.mean(D2)], float(np.var(D1) * 10 + np.var(D2) * 10), 0.5),
                               bayes.t_bf(float((np.mean(D2) - np.mean(D1)) / math.sqrt((np.var(D1, ddof=1) + np.var(D2, ddof=1)) / 2 * 0.2)), 5, 18), places=9)

    def test_wider_prior_and_no_effect(self):
        same = column([1.0, 2, 3, 4, 5, 6], [1.1, 2.1, 2.9, 4.2, 4.8, 6.1], [0.9, 2, 3.1, 3.9, 5.1, 6])
        r = A.run("anova", same, [], {"posthoc": "none", "bayes": True})
        self.assertLess(float(value(r, "Bayes factor BF₁₀")), 1 / 3, "groups alike: evidence for no difference")
        self.assertIn("for no difference", value(r, "Evidence"))
        med = bayes.t_bf(2.5, 10, 9)
        self.assertLess(bayes.t_bf(2.5, 10, 9, math.sqrt(2)), med, "a wider prior is more sceptical of small effects")

    def test_correlation_closed_form(self):
        from scipy.integrate import quad
        from scipy.special import hyp2f1
        for n, r in ((10, 0.5), (30, 0.7), (15, 0.0)):
            direct = quad(lambda p: 0.5 * (1 - p * p) ** ((n - 1) / 2) * hyp2f1((n - 1) / 2, (n - 1) / 2, 0.5, (r * p) ** 2), -1, 1)[0]
            self.assertAlmostEqual(bayes.corr_bf(r, n) / direct, 1, places=8)
        self.assertTrue(math.isfinite(bayes.corr_bf(0.3, 5000)), "large samples stay finite")
        x = np.arange(12.0)
        tab = {"name": "T", "kind": "xy", "rows": 12, "sets": [{"title": "Y", "entry": "rep", "reps": 1}], "cols": [list(x), list(2 * x + np.sin(x))], "excluded": [], "xTitle": "X", "yTitle": "Y"}
        res = A.run("correlation", tab, [], {"bayes": True})
        self.assertIn("Bayes factor BF₁₀", res["tabs"][0]["tables"][0]["columns"])

    def test_identical_groups_do_not_stop_the_anova(self):
        # 0.4.5 (#50): four groups of 1, 2, 3 (and a fifth with a 4 added) gave "math domain error": the old matrix
        # inverse lost precision. The tester's own data too (two identical groups, one far higher).
        for sets in ([[1, 2, 3]] * 4, [[1, 2, 3]] * 4 + [[1, 2, 3, 4]], [[1, 2, 3]] * 10):
            r = A.run("anova", column(*sets), [], {"posthoc": "tukey", "bayes": True})
            self.assertLess(float(value(r, "Bayes factor BF₁₀")), 1, "identical groups: evidence for no difference")
        ctrl = [1, 2, 5, 6, 8, 2, 3, 5, 1, 4, 5, 2, 6, 5, 2, 1, 1]
        a_ = [5, 8, 9, 12, 11, 6, 7, 4, 6, 5, 4, 8, 11, 12, 10, 10, 10]
        b_ = [12, 20, 21, 19, 18, 16, 17, 22, 26, 30, 24, 23, 25, 25, 22, 21, 21]
        r = A.run("anova", column(ctrl, a_, b_, ctrl), [], {"posthoc": "tukey", "bayes": True})
        self.assertGreater(float(value(r, "Bayes factor BF₁₀")), 1e20)
        self.assertIn("extreme evidence for a difference", r["answer"])

    def test_same_values_as_before_where_it_worked(self):
        # The stable formula is the old one rewritten exactly: the values from 0.4.4 stay.
        self.assertAlmostEqual(bayes.anova_bf([5, 5, 5], [1, 2, 3], 8, 0.5), 6.939054833662717, places=9)
        self.assertAlmostEqual(bayes.anova_bf([10, 7], [np.mean(D1), np.mean(D2[:7])], float(np.var(D1) * 10 + np.var(D2[:7]) * 7)), 0.7138180168741699, places=9)

    def test_a_bayes_factor_that_cannot_be_worked_out_is_a_dash(self):
        self.assertTrue(math.isnan(bayes.t_bf(float("inf"), 10, 9)))
        self.assertTrue(math.isnan(bayes.anova_bf([3, 3], [1, 2], 0.0)))
        self.assertEqual(bayes.text(float("nan")), "—")

    def test_off_unless_asked(self):
        r = A.run("ttest", column(D1, D2), [], {"test": "paired"})
        with self.assertRaises(KeyError):
            value(r, "Bayes factor BF₁₀")

    def test_words(self):
        self.assertEqual(bayes.words(1.2), "no real evidence either way")
        self.assertEqual(bayes.words(5), "moderate evidence for a difference")
        self.assertEqual(bayes.words(1 / 40), "very strong evidence for no difference")
        self.assertEqual(bayes.words(500), "extreme evidence for a difference")


if __name__ == "__main__":
    unittest.main()
