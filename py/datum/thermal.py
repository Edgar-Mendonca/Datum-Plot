"""Materials curves: thermal analysis (B31) of DSC peaks (peak and extrapolated onset temperatures,
enthalpy from the area and the heating rate) and TGA steps (onset, the temperature of fastest
loss, mass lost, residue), and fatigue S–N curves with a Basquin fit (B30)."""
import math

import numpy as np
from scipy import stats as st

from .analysis import COLORS, g, name_of, points, pv, result, small_plot
from .signal import baseline, series


def tangent_x(x, y, i, level):
    """Where the tangent to the curve at index i reaches `level` (an extrapolated onset)."""
    d = np.gradient(y, x)[i]
    return float(x[i] + (level - y[i]) / d) if d else float("nan")


def dsc(table, k, o, unit):
    from scipy.signal import find_peaks, peak_widths, savgol_filter
    x, y = series(table, k, o)
    sign = 1.0 if o.get("direction", "down") == "up" else -1.0
    b = baseline(x, y, o.get("baseline", "line"))
    yc = sign * (y - b)
    w = min(len(x) // 60 * 2 + 5, len(x) - 1 if len(x) % 2 == 0 else len(x) - 2)
    sm = savgol_filter(yc, w, 2) if w >= 5 else yc
    idx, pr = find_peaks(sm, prominence=float(o.get("prominence", 10) or 10) / 100 * (np.ptp(sm) or 1), width=2)
    rate = float(o.get("rate") or 10)
    rows, marks = [], []
    for j, i in enumerate(idx):
        i = max(i - 3, 0) + int(np.argmax(yc[max(i - 3, 0):i + 4]))
        pw = peak_widths(sm, [i], rel_height=1.0)
        lo, hi = int(pw[2][0]), min(int(math.ceil(pw[3][0])), len(x) - 1)
        lo, hi = (max(lo, idx[j - 1]) if j else lo), (min(hi, idx[j + 1]) if j + 1 < len(idx) else hi)
        lead, trail = lo + int(np.argmax(np.gradient(sm, x)[lo:i + 1])), i + int(np.argmin(np.gradient(sm, x)[i:hi + 1]))  # steepest points either side
        on, end = tangent_x(x, yc, lead, 0.0), tangent_x(x, yc, trail, 0.0)
        area = float(np.trapezoid(yc[lo:hi + 1], x[lo:hi + 1]))
        h = area / (rate / 60)  # ∫ P dT ÷ (dT/dt): W/g · K ÷ K/s = J/g
        rows.append([str(j + 1), g(on, 5), g(x[i], 5), g(end, 5), g(sign * yc[i], 4), g(area, 4), f"{g(h, 4)}{' ' + unit if unit else ''}", "endotherm" if sign < 0 else "exotherm"])
        marks.append([float(x[i]), float(y[i]), str(j + 1), sign < 0])
    return x, y, b, rows, marks


def tga(table, k, o):
    from scipy.signal import find_peaks, peak_widths, savgol_filter
    x, y = series(table, k, o)
    m0 = y[0]
    pct = y / m0 * 100 if o.get("percent", True) and m0 else y
    w = min(len(x) // 30 * 2 + 5, len(x) - 1 if len(x) % 2 == 0 else len(x) - 2)
    d = -np.gradient(savgol_filter(pct, w, 2) if w >= 5 else pct, x)  # DTG: rate of loss
    idx, _ = find_peaks(d, prominence=float(o.get("prominence", 10) or 10) / 100 * (np.ptp(d) or 1), width=2)
    rows, marks = [], []
    for j, i in enumerate(idx):
        pw = peak_widths(d, [i], rel_height=0.98)
        lo, hi = int(pw[2][0]), min(int(math.ceil(pw[3][0])), len(x) - 1)
        lo, hi = (max(lo, idx[j - 1]) if j else lo), (min(hi, idx[j + 1]) if j + 1 < len(idx) else hi)  # neighbouring steps split at their DTG peaks
        before, after = pct[lo], pct[hi]
        tang = lambda lvl: float(x[i] + (lvl - pct[i]) / -d[i]) if d[i] else float("nan")  # tangent at the fastest loss
        rows.append([str(j + 1), g(tang(before), 5), g(x[i], 5), g(tang(after), 5), g(before - after, 4), g(d[i], 4)])
        marks.append([float(x[i]), float(y[i]), str(j + 1)])
    t5 = next((float(np.interp(pct[0] - 5, [pct[q + 1], pct[q]], [x[q + 1], x[q]])) for q in range(len(x) - 1) if pct[q] >= pct[0] - 5 > pct[q + 1]), None)
    return x, y, pct, d, rows, marks, t5


def thermal(table, ks, o):
    mode = o.get("mode", "dsc")
    tu = table.get("xUnits") or "°C"
    tabs, curves, plots, ans = [], [], [], []
    for k in ks:
        x, _ = series(table, k, o)
        if len(x) < 10:
            continue
        name = name_of(table, k)
        if mode == "tga":
            x, y, pct, d, rows, marks, t5 = tga(table, k, o)
            tabs.append({"title": name, "columns": ["Step", f"Onset ({tu})", f"Fastest loss ({tu})", f"End ({tu})", "Mass lost (%)", f"Rate at fastest (%/{tu})"], "rows": rows})
            tabs.append({"title": f"{name}: summary", "columns": ["", "Value"], "rows": [["Residue at the end", f"{g(pct[-1], 4)}%"], [f"5% mass loss at ({tu})", g(t5, 5) if t5 is not None else "—"],
                                                                                    ["Total mass lost", f"{g(pct[0] - pct[-1], 4)}%"]]})
            ans.append(f"{name}: {len(rows)} step{'s' * (len(rows) != 1)}{', the main one at ' + max(rows, key=lambda r: float(r[4]))[2] + ' ' + tu if rows else ''}; residue {g(pct[-1], 3)}%")
            curves.append({"set": k, "x": [], "y": [], "label": "", "marks": marks})
            plots.append(small_plot(f"DTG · {name}"[:40], lambda ax, x=x, d=d, c=COLORS[k % 8]: (ax.plot(x, d, color=c, lw=1), ax.set_xlabel(f"Temperature ({tu})"), ax.set_ylabel("Rate of loss"))))
        else:
            x, y, b, rows, marks = dsc(table, k, o, "J/g")
            tabs.append({"title": name, "columns": ["Peak", f"Onset ({tu})", f"Peak ({tu})", f"Endset ({tu})", "Height", "Area (Y·°C)", "Enthalpy", "Kind"], "rows": rows})
            ans.append(f"{name}: " + ("; ".join(f"{r[7]} peak at {r[2]} {tu} (onset {r[1]} {tu}, ΔH {r[6]})" for r in rows) if rows else "no peaks"))
            curves.append({"set": k, "x": x.tolist(), "y": y.tolist(), "fill": b.tolist(), "label": "", "marks": marks})
    if not tabs:
        raise ValueError("Each curve needs at least ten points.")
    rate = float(o.get("rate") or 10)
    checks = [(None, "Onsets are extrapolated: where the tangent at the steepest point of the leading edge meets the baseline (or, for TGA, the plateau before the step).")]
    if mode != "tga":
        checks.append((None, f"Enthalpy = area ÷ heating rate ({rate:g} K/min): with Y in W/g it is in J/g. Set the rate to the one you used."))
    return result("Thermal analysis (TGA)" if mode == "tga" else "Thermal analysis (DSC)", "; ".join(ans) + ".", [{"name": "Summary", "tables": tabs}], checks, plots=plots, curves=curves,
                  legend="Numbers mark the " + ("steps (fastest loss)." if mode == "tga" else "peaks; the dashed line is the baseline."),
                  methods=("TGA steps were found from the peaks of the derivative (DTG); onsets are the intersections of the tangent at the fastest loss with the plateaus" if mode == "tga" else
                           f"DSC peaks were integrated above a {o.get('baseline', 'line')} baseline; onsets are the extrapolated intersections of the steepest tangent with the baseline, and enthalpies the areas divided by the heating rate ({rate:g} K/min)") + " in Datum Plot (SciPy).",
                  code="dy = np.gradient(y, x); onset = x[i] + (base[i] - y[i]) / dy[i]")


def life_text(v):
    """10⁷ for powers of ten, else the number."""
    e = math.log10(v) if v > 0 else 0.5
    return "10" + str(int(round(e))).translate(str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")) if abs(e - round(e)) < 1e-9 else g(v, 3)


def sn(table, ks, o):
    """S–N curves: Basquin S = A · N^b, fitted as a straight line of log S on log N; run-outs (N ≥ the run-out limit) are shown but left out."""
    rev = bool(o.get("reversals"))
    run = float(o["runout"]) if o.get("runout") not in (None, "") else None
    at = [float(v) for v in str(o.get("at") or "1e6, 1e7").replace(";", ",").split(",") if v.strip()]
    rows, curves, ans, life = [], [], [], []
    for k in ks:
        N, S, _ = points(table, k, {**o, "points": "each"})
        ok = (N > 0) & (S > 0)
        out = ok & (N >= run) if run else np.zeros_like(ok)
        use = ok & ~out
        if use.sum() < 3:
            continue
        n_ = 2 * N[use] if rev else N[use]
        lr = st.linregress(np.log10(n_), np.log10(S[use]))
        b, A = lr.slope, 10 ** lr.intercept
        tq = st.t.ppf(0.975, use.sum() - 2)
        name = name_of(table, k)
        rows.append([name, g(A, 5), f"{g(b, 4)} ± {g(tq * lr.stderr, 2)}", g(lr.rvalue ** 2, 4), g(int(use.sum())), g(int(out.sum())), pv(lr.pvalue)])
        life += [[name, f"{life_text(v)} {'reversals' if rev else 'cycles'}", g(A * v ** b, 4)] for v in at]
        xs = np.geomspace(N[use].min(), max(N[use].max(), run or 0), 100)
        curves.append({"set": k, "x": xs.tolist(), "y": (A * (2 * xs if rev else xs) ** b).tolist(), "label": f"S = {g(A, 4)}·{'(2N)' if rev else 'N'}^{g(b, 3)}",
                       "marks": [[float(a_), float(b_), "→"] for a_, b_ in zip(N[out], S[out])]})  # run-outs
        ans.append(f"{name}: S = {g(A, 4)} · {'(2N)' if rev else 'N'}^{g(b, 3)} (R² = {g(lr.rvalue ** 2, 3)})" + (f", fatigue strength at {life_text(at[-1])} {'reversals' if rev else 'cycles'}: {g(A * at[-1] ** b, 4)}" if at else ""))
    if not rows:
        raise ValueError("Each data set needs at least three failures with N and S above zero (X = cycles to failure, Y = stress).")
    checks = [(None, "The Basquin line is fitted to log S against log N; extrapolating beyond the tested lives is uncertain.")]
    if run:
        checks.append((None, f"Points at {life_text(run)} cycles or more are run-outs (no failure): they are drawn but left out of the fit."))
    return result("S–N curve (Basquin)", "; ".join(ans) + ".", [{"name": "Summary", "tables": [
        {"title": "Basquin fit", "columns": ["Data set", "Coefficient A", "Exponent b ± 95% CI", "R²", "Failures", "Run-outs", "P (slope)"], "rows": rows},
        {"title": "Fatigue strength", "columns": ["Data set", "Life", "Stress"], "rows": life}]}], checks, curves=curves,
        methods=f"Fatigue data were fitted with Basquin's relation S = A·{'(2N)' if rev else 'N'}^b by least squares on log S against log N{', leaving out run-outs' if run else ''} in Datum Plot (SciPy).",
        code="from scipy import stats\nfit = stats.linregress(np.log10(N), np.log10(S)); A, b = 10**fit.intercept, fit.slope")
