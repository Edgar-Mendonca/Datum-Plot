"""Time–frequency analysis (B36, 0.4.0): the Morlet wavelet scalogram and the spectrogram, checked against what
theory says: a sine peaks at its own frequency, a chirp's ridge follows its instantaneous frequency, and white noise
has a mean normalised wavelet power of 1 (Torrence & Compo 1998, eq. 13 with σ² normalisation).
Run: python -m unittest discover -s py/tests"""
import math
import os
import sys
import unittest
import warnings

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datum import analysis as A, signal  # noqa: E402


def table(x, y):
    n = len(x)
    return {"name": "S", "kind": "xy", "rows": n, "xTitle": "Time", "xUnits": "s", "yTitle": "V", "yUnits": "", "excluded": [],
            "sets": [{"title": "Signal", "entry": "rep", "reps": 1}], "cols": [list(map(float, x)), list(map(float, y))]}


class TimeFrequency(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore")

    def test_a_sine_peaks_at_its_frequency(self):
        t = np.arange(0, 4, 1 / 200)
        y = np.sin(2 * math.pi * 5 * t)
        p, coi = signal.morlet(y, 1 / 200, np.geomspace(1, 50, 120))
        f = np.geomspace(1, 50, 120)
        mid = p[:, len(t) // 2]
        self.assertAlmostEqual(f[int(np.argmax(mid))] / 5, 1, delta=0.03)
        # Within one frequency step: 64 steps over the range (wavelet), 200/128 Hz bins (spectrogram, 128-point window).
        for op, step in (("cwt", 0.09 * 5), ("stft", 200 / 128 / 2 + 1e-9)):
            r = A.run("signal", table(t, y), [], {"op": op})
            found = float(r["answer"].split("strongest at ")[1].split(" ")[0])
            self.assertLessEqual(abs(found - 5), step, r["answer"])
            self.assertTrue(r["plots"], "a heat map")

    def test_a_chirp_ridge_follows_its_frequency(self):
        t = np.arange(0, 10, 1 / 400)
        f0, f1 = 2.0, 20.0
        y = np.sin(2 * math.pi * (f0 * t + (f1 - f0) / (2 * 10) * t ** 2))  # instantaneous frequency f0 + (f1-f0) t/10
        r = A.run("signal", table(t, y), [], {"op": "cwt", "low": 1, "high": 40})
        x, ridge = np.array(r["table"]["cols"][0], float), np.array(r["table"]["cols"][1], float)
        inner = (x > 1.5) & (x < 8.5)
        expected = f0 + (f1 - f0) * x[inner] / 10
        self.assertLess(np.median(np.abs(ridge[inner] / expected - 1)), 0.08)

    def test_white_noise_has_mean_normalised_power_one(self):
        rng = np.random.default_rng(3)
        y = rng.normal(size=4096)
        f = np.geomspace(0.02, 0.4, 20)
        p, coi = signal.morlet(y, 1.0, f)
        inside = (1 / f)[:, None] < coi[None, :]
        self.assertAlmostEqual(float(p[inside].mean()), 1.0, delta=0.12)

    def test_too_short_or_wrong_range_says_why(self):
        t = np.arange(10.0)
        with self.assertRaises(ValueError):
            A.run("signal", table(t, np.sin(t)), [], {"op": "cwt"})
        t = np.arange(0, 4, 0.01)
        with self.assertRaises(ValueError):
            A.run("signal", table(t, np.sin(t)), [], {"op": "cwt", "low": 10, "high": 5})


if __name__ == "__main__":
    unittest.main()
