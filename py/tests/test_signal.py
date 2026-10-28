"""Peaks and signals (B24, B25) against values known by construction: Gaussian peaks on a sloping
baseline (position, FWHM = 2.3548 σ, area = A) and sine waves (frequency, filtering).
Run: python -m unittest discover -s py/tests"""
import math
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datum import analysis as A, graph  # noqa: E402


def xy(x, *ys):
    return {"name": "T", "kind": "xy", "rows": len(x), "sets": [{"title": f"S{i}", "entry": "rep", "reps": 1} for i in range(len(ys))],
            "cols": [list(map(float, x))] + [list(map(float, y)) for y in ys], "excluded": [], "xTitle": "Time", "yTitle": "Y"}


def gauss(x, a, c, s):
    return a / (s * math.sqrt(2 * math.pi)) * np.exp(-((x - c) ** 2) / (2 * s * s))


X = np.linspace(0, 100, 801)
Y = 2 + 0.01 * X + gauss(X, 30, 30, 2.5) + gauss(X, 50, 65, 4)


class Peaks(unittest.TestCase):
    def test_two_gaussians_on_a_sloping_baseline(self):
        r = A.run("peaks", xy(X, Y), [], {"baseline": "line"})
        rows = r["tabs"][0]["tables"][0]["rows"]
        self.assertEqual([row[2] for row in rows], ["30", "65"])
        self.assertAlmostEqual(float(rows[0][5]), 2.3548 * 2.5, 1)
        self.assertAlmostEqual(float(rows[1][6]), 50, delta=1.0)  # area to the baseline meeting points: nearly all of A
        self.assertIn("2 peaks", r["answer"])

    def test_gaussian_fit_recovers_the_parameters(self):
        r = A.run("peaks", xy(X, Y), [], {"baseline": "line", "fit": "gauss"})
        f = r["tabs"][0]["tables"][1]["rows"]
        self.assertEqual([row[2].split(" ±")[0] for row in f], ["30", "65"])
        self.assertAlmostEqual(float(f[0][4]), 2.3548 * 2.5, 3)
        self.assertAlmostEqual(float(f[1][5].split(" ±")[0]), 50, 2)
        self.assertEqual(f[0][6], "1")
        self.assertIn("<svg", graph.render(xy(X, Y), {}, [{"kind": "peaks", "options": {"fit": "gauss"}}])["svg"])

    def test_dips_and_the_polynomial_baseline(self):
        r = A.run("peaks", xy(X, 5 + 0.0004 * (X - 50) ** 2 - gauss(X, 40, 50, 3)), [], {"baseline": "poly", "direction": "down"})
        rows = r["tabs"][0]["tables"][0]["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][2], "50")
        self.assertAlmostEqual(float(rows[0][6]), -40, delta=1.5)


T = np.arange(0, 2, 0.005)  # 200 per second
S = np.sin(2 * math.pi * 5 * T) + 0.3 * np.sin(2 * math.pi * 40 * T)


class Signals(unittest.TestCase):
    def test_spectrum_finds_both_frequencies(self):
        r = A.run("signal", xy(T, S), [], {"op": "fft"})
        self.assertIn("strongest frequency is 5 per Time", r["answer"])
        tb = r["table"]
        f, a = np.array(tb["cols"][0]), np.array(tb["cols"][1])
        self.assertAlmostEqual(a[np.argmin(abs(f - 40))], 0.3, 2)
        self.assertAlmostEqual(a[np.argmin(abs(f - 5))], 1.0, 2)

    def test_low_pass_removes_the_fast_wave(self):
        r = A.run("signal", xy(T, S), [], {"op": "lowpass", "high": 15})
        yf = np.array(r["table"]["cols"][1])
        mid = slice(40, 360)
        self.assertLess(np.max(np.abs(yf[mid] - np.sin(2 * math.pi * 5 * T[mid]))), 0.02)
        self.assertTrue(r["curves"])
        with self.assertRaises(ValueError):
            A.run("signal", xy(T, S), [], {"op": "lowpass", "high": 150})

    def test_high_pass_and_resample(self):
        yf = np.array(A.run("signal", xy(T, S), [], {"op": "highpass", "low": 20})["table"]["cols"][1])
        self.assertLess(np.max(np.abs(yf[40:360] - 0.3 * np.sin(2 * math.pi * 40 * T[40:360]))), 0.03)
        r = A.run("signal", xy([0, 1, 3, 6, 10, 15, 21, 28, 36], [0, 1, 3, 6, 10, 15, 21, 28, 36]), [], {"op": "resample", "n": 5})
        self.assertEqual(r["table"]["cols"][0], [0, 9, 18, 27, 36])
        self.assertEqual(r["table"]["cols"][1], [0, 9, 18, 27, 36])
