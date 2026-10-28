"""Peaks and signals on XY data: peak finding with a baseline, heights, widths and areas, optionally
fitted as Gaussian, Lorentzian or Voigt peaks (B24); and signal processing: the Fourier spectrum,
low-, high- and band-pass filters and even resampling (B25)."""
import math

import numpy as np

from .analysis import COLORS, g, name_of, points, result, small_plot
from .tools import new_table, preview


def series(table, k, o):
    """(x, y) of data set k: the means at each X, sorted by X."""
    x, y, _ = points(table, k, {**o, "points": "mean"})
    i = np.argsort(x)
    return x[i], y[i]


def baseline(x, y, how, order=2):
    """none, min, line (first to last point) or poly (a polynomial fitted again and again to the points below it)."""
    if how == "line":
        return y[0] + (y[-1] - y[0]) * (x - x[0]) / (x[-1] - x[0] if x[-1] != x[0] else 1)
    if how == "min":
        return np.full_like(y, y.min())
    if how == "poly":
        t = (x - x.mean()) / (np.ptp(x) or 1)
        keep = np.ones(len(x), bool)
        for _ in range(60):  # refit to the points not lifted by peaks (within the noise of the fit), until they settle
            f = np.polyval(np.polyfit(t[keep], y[keep], order), t)
            new = y <= f + np.std(y[keep] - f[keep])
            if new.sum() <= order + 1 or np.array_equal(new, keep):
                break
            keep = new
        return np.polyval(np.polyfit(t[keep], y[keep], order), t)
    return np.zeros_like(y)


def at(x, i):
    """X at a fractional index."""
    return float(np.interp(i, np.arange(len(x)), x))


def peaks(table, ks, o):
    from scipy.signal import find_peaks, peak_widths, savgol_filter
    how, sign = o.get("baseline", "line"), -1.0 if o.get("direction") == "down" else 1.0
    prom, fit = float(o.get("prominence", 10) or 10) / 100, o.get("fit", "none")
    rows, fits, curves, plots, ans, cols = [], [], [], [], [], []
    for k in ks:
        x, y = series(table, k, o)
        if len(x) < 5:
            continue
        b = baseline(x, y, how, int(o.get("order", 2) or 2)) if how != "poly" or sign > 0 else -baseline(x, -y, how, int(o.get("order", 2) or 2))
        yc = sign * (y - b)
        w = min(len(x) // 60 * 2 + 5, len(x) - 1 if len(x) % 2 == 0 else len(x) - 2)  # odd, and shorter than the data
        sm = savgol_filter(yc, w, 2) if w >= 5 else yc
        idx, pr = find_peaks(sm, prominence=prom * (np.ptp(sm) or 1), width=2, distance=max(1, int(o.get("distance", 1) or 1)))  # found on a lightly smoothed copy, so noise is not a peak
        idx = np.array([max(i - 3, 0) + int(np.argmax(yc[max(i - 3, 0):i + 4])) for i in idx], int)
        idx = np.unique(idx[np.argsort(-pr["prominences"])][:int(o.get("max", 20) or 20)])
        name = name_of(table, k)
        cols.append((name, x, sign * yc))
        if not len(idx):
            ans.append(f"{name}: no peaks above {100 * prom:g}% of the range"); continue
        w50 = peak_widths(yc, idx, rel_height=0.5)
        wb = peak_widths(yc, idx, rel_height=1.0)
        found = []
        for j, i in enumerate(idx):
            vl = idx[j - 1] + int(np.argmin(yc[idx[j - 1]:i + 1])) if j else 0  # neighbouring peaks split at the lowest point between them
            vr = i + int(np.argmin(yc[i:idx[j + 1] + 1])) if j + 1 < len(idx) else len(x) - 1
            l_, r_ = at(x, max(wb[2][j], vl)), at(x, min(wb[3][j], vr))
            m = (x >= l_) & (x <= r_)
            xs, ys = np.concatenate([[l_], x[m], [r_]]), np.concatenate([[np.interp(l_, x, yc)], yc[m], [np.interp(r_, x, yc)]])
            area = float(np.trapezoid(ys, xs)) if hasattr(np, "trapezoid") else float(np.trapz(ys, xs))
            fw = at(x, w50[3][j]) - at(x, w50[2][j])
            found.append((float(x[i]), float(yc[i]), fw, area))
            rows.append([name, str(j + 1), g(x[i], 5), g(sign * yc[i], 4), g(y[i], 4), g(fw, 4), g(sign * area, 4)])
        ans.append(f"{name}: {len(found)} peak{'s' * (len(found) > 1)}, the largest at {g(max(found, key=lambda f: f[1])[0], 4)}")
        marks = [[p[0], float(y[np.argmin(np.abs(x - p[0]))]), str(j + 1)] for j, p in enumerate(found)]
        curves.append({"set": k, "x": x.tolist(), "y": b.tolist(), "label": "", "dash": True, "marks": marks})
        if fit in ("gauss", "lorentz", "voigt"):
            from lmfit.models import GaussianModel, LorentzianModel, VoigtModel
            M = {"gauss": GaussianModel, "lorentz": LorentzianModel, "voigt": VoigtModel}[fit]
            model, pars = None, None
            for j, (cx, h, fw, area) in enumerate(found):
                mj = M(prefix=f"p{j}_")
                pj = mj.make_params(center=cx, sigma=max(fw, 1e-12) / (2.3548 if fit == "gauss" else 2.0 if fit == "lorentz" else 3.6), amplitude=max(area, 1e-12))
                pj[f"p{j}_center"].set(min=x[0], max=x[-1])
                model, pars = (mj, pj) if model is None else (model + mj, pars.update(pj) or pars)
            try:
                r = model.fit(yc, pars, x=x)
            except Exception as e:
                raise ValueError(f"The peak fit did not converge: {e}")
            ss = float(np.sum(r.residual ** 2)); r2 = 1 - ss / float(np.sum((yc - yc.mean()) ** 2)) if np.ptp(yc) else float("nan")
            for j in range(len(found)):
                P = lambda n: r.params[f"p{j}_{n}"]
                se = lambda n: g(P(n).stderr, 3) if P(n).stderr is not None else "—"
                fits.append([name, str(j + 1), f"{g(P('center').value, 5)} ± {se('center')}", g(sign * P("height").value, 4), g(P("fwhm").value, 4), f"{g(sign * P('amplitude').value, 4)} ± {se('amplitude')}", g(r2, 4)])
            xf = np.linspace(x[0], x[-1], 400)
            curves.append({"set": k, "x": xf.tolist(), "y": (np.interp(xf, x, b) + sign * r.eval(x=xf)).tolist(), "label": ""})
        plots.append(small_plot(f"Baseline-corrected · {name}"[:40], lambda ax, x=x, yc=yc, f=found, c=COLORS[k % 8]: (ax.plot(x, yc, color=c, lw=1), ax.plot([p[0] for p in f], [p[1] for p in f], "v", ms=4, color="#D55E00"),
                                                                                                  ax.axhline(0, color="#8D9AAB", lw=0.6), ax.set_xlabel(table.get("xTitle", "X")[:20]))))
    if not cols:
        raise ValueError("Each data set needs at least five points.")
    tabs = [{"title": "Peaks", "columns": ["Data set", "Peak", "Position (X)", "Height above baseline", "Y at peak", "Width at half height", "Area above baseline"], "rows": rows}]
    if fits:
        names = {"gauss": "Gaussian", "lorentz": "Lorentzian", "voigt": "Voigt"}
        tabs.append({"title": f"{names[fit]} peak fit", "columns": ["Data set", "Peak", "Centre ± SE", "Height", "FWHM", "Area ± SE", "R² of the fit"], "rows": fits})
    xs = max((c[1] for c in cols), key=len)
    tb = new_table(table, f"{table.get('name', 'Data')} baseline-corrected", [c[0] for c in cols], xs.tolist(), [np.interp(xs, c[1], c[2]).tolist() for c in cols])
    bname = {"none": "no baseline", "min": "the minimum as baseline", "line": "a straight baseline from the first to the last point", "poly": f"an iterative polynomial baseline (order {o.get('order', 2)})"}.get(how, how)
    return result("Peak analysis", "; ".join(ans) + ".", [{"name": "Summary", "tables": tabs}, {"name": "Corrected data", "tables": [preview(tb)]}],
                  [(None, f"Peaks are maxima{' (minima: the curve was turned over)' if sign < 0 else ''} rising at least {100 * prom:g}% of the range above their surroundings; areas run between the points where each peak meets the baseline.")],
                  plots=plots, curves=curves, table=tb, legend=f"Peaks found above {bname}; numbers mark each peak.",
                  methods=f"Peaks were found after subtracting {bname} (SciPy find_peaks, prominence ≥ {100 * prom:g}% of the range); widths are full widths at half height and areas trapezoidal integrals above the baseline"
                          + (f"; peaks were fitted as a sum of {names[fit]} functions by least squares (lmfit)" if fits else "") + " in Datum Plot.",
                  code="from scipy.signal import find_peaks, peak_widths\nidx, _ = find_peaks(y - base, prominence=0.05 * np.ptp(y))\nprint(x[idx], peak_widths(y - base, idx, 0.5)[0])")


def even(x, y):
    """Evenly spaced copies (linear interpolation onto as many points) when the spacing varies by more than 1 %."""
    d = np.diff(x)
    if len(d) and np.ptp(d) <= 0.01 * abs(d.mean()):
        return x, y, False
    xe = np.linspace(x[0], x[-1], len(x))
    return xe, np.interp(xe, x, y), True


def signal(table, ks, o):
    from scipy.signal import butter, sosfiltfilt
    op = o.get("op", "fft")
    lo, hi = (float(o[k]) if o.get(k) not in (None, "") else None for k in ("low", "high"))
    xt = table.get("xTitle") or "X"
    out, curves, ans, plots, uneven = [], [], [], [], False
    for k in ks:
        x, y = series(table, k, o)
        if len(x) < 8:
            continue
        name = name_of(table, k)
        if op == "resample":
            n = int(o.get("n") or len(x))
            xe = np.linspace(x[0], x[-1], max(n, 2))
            out.append((name, xe, np.interp(xe, x, y)))
            ans.append(f"{name}: {len(x)} points → {len(xe)} evenly spaced")
            continue
        x, y, u = even(x, y)
        uneven |= u
        dx = float(x[1] - x[0])
        fs = 1 / dx
        if op == "fft":
            f = np.fft.rfftfreq(len(y), dx)
            a = 2 * np.abs(np.fft.rfft(y - y.mean())) / len(y)
            out.append((name, f, a))
            top = int(np.argmax(a[1:]) + 1) if len(a) > 1 else 0
            ans.append(f"{name}: the strongest frequency is {g(f[top], 4)} per {xt} (period {g(1 / f[top], 4)}, amplitude {g(a[top], 4)})")
            plots.append(small_plot(f"Spectrum · {name}"[:40], lambda ax, f=f, a=a, c=COLORS[k % 8]: (ax.plot(f, a, color=c, lw=1), ax.set_xlabel(f"Frequency (per {xt[:12]})"), ax.set_ylabel("Amplitude"))))
            continue
        nyq = fs / 2
        cut = {"lowpass": hi, "highpass": lo, "bandpass": [lo, hi]}[op]
        if cut is None or (op == "bandpass" and None in cut):
            raise ValueError("Enter the cut-off frequency (cycles per X unit)." if op != "bandpass" else "Enter the low and high cut-off frequencies.")
        c = np.atleast_1d(cut) / nyq
        if np.any(c <= 0) or np.any(c >= 1) or (op == "bandpass" and c[0] >= c[1]):
            raise ValueError(f"Cut-offs must lie between 0 and {g(nyq, 4)} (half the sampling rate of {g(fs, 4)} per {xt}).")
        sos = butter(int(o.get("order", 4) or 4), c if op == "bandpass" else c[0], btype={"lowpass": "low", "highpass": "high", "bandpass": "band"}[op], output="sos")
        yf = sosfiltfilt(sos, y)
        out.append((name, x, yf))
        curves.append({"set": k, "x": x.tolist(), "y": yf.tolist(), "label": ""})
        ans.append(f"{name}: filtered")
    if not out:
        raise ValueError("Each data set needs at least eight points.")
    xs = max((c[1] for c in out), key=len)
    title = {"fft": "Fourier spectrum", "lowpass": "Low-pass filter", "highpass": "High-pass filter", "bandpass": "Band-pass filter", "resample": "Resample"}[op]
    tb = new_table(table, f"{table.get('name', 'Data')} {title.lower()}", [c[0] for c in out], xs.tolist(), [np.interp(xs, c[1], c[2]).tolist() for c in out],
                   x_title=f"Frequency (per {xt})" if op == "fft" else None, y_title="Amplitude" if op == "fft" else None)
    checks = [(None, "The data were not evenly spaced, so they were first interpolated onto even steps.")] if uneven else []
    if op in ("lowpass", "highpass", "bandpass"):
        checks.append((None, "A Butterworth filter run forwards and backwards: no shift in X, but the edges of the curve are less reliable."))
    how = {"fft": "the amplitude spectrum by the fast Fourier transform (mean removed)", "lowpass": f"a low-pass Butterworth filter (cut-off {hi:g}, order {o.get('order', 4)})" if hi else "",
           "highpass": f"a high-pass Butterworth filter (cut-off {lo:g}, order {o.get('order', 4)})" if lo else "", "bandpass": f"a band-pass Butterworth filter ({lo:g} to {hi:g}, order {o.get('order', 4)})" if lo and hi else "",
           "resample": "linear interpolation onto evenly spaced points"}[op]
    return result(title, "; ".join(ans) + ". Make it a data table to graph or analyse it.", [{"name": "Summary", "tables": [preview(tb)]}], checks, plots=plots, curves=curves, table=tb,
                  methods=f"Signals were processed with {how}{', run forwards and backwards (zero phase)' if op in ('lowpass', 'highpass', 'bandpass') else ''} in Datum Plot (NumPy, SciPy).",
                  code="import numpy as np\nfrom scipy.signal import butter, sosfiltfilt\nf = np.fft.rfftfreq(len(y), dx); a = 2 * abs(np.fft.rfft(y - y.mean())) / len(y)\nyf = sosfiltfilt(butter(4, cut / (fs / 2), output='sos'), y)")
