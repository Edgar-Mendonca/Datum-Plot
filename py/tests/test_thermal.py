"""Thermal analysis and fatigue (B30, B31) against values known by construction: a Gaussian
endotherm (onset = centre − 2σ, the tangent at the inflection; enthalpy = area ÷ rate), a logistic
TGA step (onset = centre − 2w, mass lost) and an exact Basquin power law.
Run: python -m unittest discover -s py/tests"""
import math
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datum import analysis as A, graph  # noqa: E402
from test_signal import xy  # noqa: E402

T = np.linspace(100, 250, 1501)


class Thermal(unittest.TestCase):
    def test_dsc_endotherm_onset_peak_and_enthalpy(self):
        s, area = 3.0, 6.0  # W/g · °C
        y = -0.2 - 0.002 * (T - 100) - area / (s * math.sqrt(2 * math.pi)) * np.exp(-((T - 170) ** 2) / (2 * s * s))
        r = A.run("thermal", xy(T, y), [], {"mode": "dsc", "rate": 10})
        row = r["tabs"][0]["tables"][0]["rows"][0]
        self.assertEqual((row[2], row[7]), ("170", "endotherm"))
        self.assertAlmostEqual(float(row[1]), 170 - 2 * s, 1)
        self.assertAlmostEqual(float(row[3]), 170 + 2 * s, 1)
        self.assertAlmostEqual(float(row[5]), area, 2)
        self.assertAlmostEqual(float(row[6].split()[0]), area / (10 / 60), 0)  # 36 J/g
        self.assertIn("<svg", graph.render(xy(T, y), {}, [{"kind": "thermal", "options": {"mode": "dsc"}}])["svg"])

    def test_tga_step_onset_and_mass_loss(self):
        w = 4.0
        m = 10 * (1 - 0.4 / (1 + np.exp(-(T - 180) / w)))  # 10 mg losing 40 %
        r = A.run("thermal", xy(T, m), [], {"mode": "tga"})
        row = r["tabs"][0]["tables"][0]["rows"][0]
        self.assertAlmostEqual(float(row[2]), 180, 0)
        self.assertAlmostEqual(float(row[1]), 180 - 2 * w, 0)
        self.assertAlmostEqual(float(row[4]), 40, 0)
        summ = r["tabs"][0]["tables"][1]["rows"]
        self.assertEqual(summ[0][1], "60%")
        self.assertIn("1 step", r["answer"])


class Fatigue(unittest.TestCase):
    def test_basquin_recovers_the_power_law_and_skips_runouts(self):
        N = np.array([1e4, 3e4, 1e5, 3e5, 1e6, 3e6, 2e7, 2e7])
        S = 900 * N ** -0.09
        S[-2:] = [200, 205]  # run-outs
        r = A.run("sn", xy(N, S), [], {"runout": 1e7, "at": "1e6, 1e7"})
        row = r["tabs"][0]["tables"][0]["rows"][0]
        self.assertEqual((row[1], row[2].split(" ±")[0], row[3], row[4], row[5]), ("900", "-0.09", "1", "6", "2"))
        life = r["tabs"][0]["tables"][1]["rows"]
        self.assertEqual(life[1][2], A.g(900 * 1e7 ** -0.09, 4))
        rr = A.run("sn", xy(N[:6], S[:6]), [], {"reversals": True})
        self.assertEqual(rr["tabs"][0]["tables"][0]["rows"][0][1], A.g(900 * 2 ** 0.09, 5))  # S = A'(2N)^b
