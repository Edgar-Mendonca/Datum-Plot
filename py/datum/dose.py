"""Dose-response: IC50 and EC50 (B38, 0.4.11), and whether two compounds' IC50s differ (B39, 0.4.12).

The four-parameter logistic in concentration, Y = Bottom + (Top − Bottom) / (1 + (X50 / X)^Hill), the model of the R
package drc (LL.4) and of the usual "log(dose) vs response" fits: Hill > 0 rises (EC50), Hill < 0 falls (IC50). It is
fitted with log10(X50) as the parameter, so the 95 % CI of the IC50 is the back-transformed CI of its logarithm (uneven
around it, as it should be). Zero concentrations (blanks) count: they sit on the Bottom (rising) or the Top (falling)
plateau. Checked against drc: the ryegrass data give the published LL.4 estimates (see the tests)."""
import math

import numpy as np
from scipy import stats as st

from .analysis import COLORS, g, name_of, points, result, residual_plot
from .groups import p_text

UNITS = {"M": 0, "mM": -3, "µM": -6, "uM": -6, "nM": -9, "pM": -12}


def model(c, bottom, top, logx50, hill):
    """The response at concentrations `c` (zero allowed)."""
    c = np.asarray(c, float)
    with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
        r = np.where(c > 0, (10.0 ** logx50 / np.where(c > 0, c, 1.0)) ** hill, np.inf if hill > 0 else 0.0)
    return bottom + (top - bottom) / (1.0 + r)


def guess(c, y, falling):
    """Starting values: the plateaus from the extremes, X50 where the response crosses half-way, Hill ±1."""
    pos = c > 0
    lc = np.log10(c[pos]) if pos.any() else np.array([0.0])
    order = np.argsort(c)
    lo, hi = float(np.min(y)), float(np.max(y))
    mid = (lo + hi) / 2
    ys = y[order][pos[order]] if pos.any() else y
    xs = lc[np.argsort(c[pos])] if pos.any() else lc
    cross = [0.5 * (xs[i] + xs[i + 1]) for i in range(len(xs) - 1) if (ys[i] - mid) * (ys[i + 1] - mid) <= 0]
    l50 = cross[0] if cross else float(np.median(xs))
    return (lo, hi, l50, -1.0 if falling else 1.0)


def fit(c, y, falling, three=False, fixed=None):
    """Least-squares fit; `three` fixes Hill at ±1, `fixed` maps "bottom"/"top" to fixed values. Returns the four
    parameters, their covariance (zeros where fixed), the residual SD and the degrees of freedom."""
    from scipy.optimize import curve_fit
    fixed = dict(fixed or {})
    if three:
        fixed["hill"] = -1.0 if falling else 1.0
    names = ["bottom", "top", "logx50", "hill"]
    p0 = dict(zip(names, guess(c, y, falling)))
    free = [n for n in names if n not in fixed]

    def f(x, *v):
        p = {**fixed, **dict(zip(free, v))}
        return model(x, p["bottom"], p["top"], p["logx50"], p["hill"])

    v, cov = curve_fit(f, c, y, p0=[p0[n] for n in free], maxfev=20000)
    p = {**fixed, **dict(zip(free, v))}
    full = np.zeros((4, 4))
    idx = [names.index(n) for n in free]
    full[np.ix_(idx, idx)] = cov
    df = len(y) - len(free)
    rss = float(np.sum((y - f(c, *v)) ** 2))
    return np.array([p[n] for n in names]), full, math.sqrt(rss / df) if df > 0 else float("nan"), df, rss


def band(cs, p, cov, t):
    """The 95 % confidence band of the curve (delta method)."""
    eps = 1e-6
    J = np.empty((len(cs), 4))
    for i in range(4):
        d = np.zeros(4); d[i] = eps * max(1.0, abs(p[i]))
        J[:, i] = (model(cs, *(p + d)) - model(cs, *(p - d))) / (2 * d[i])
    se = np.sqrt(np.maximum(np.einsum("ij,jk,ik->i", J, cov, J), 0))
    return t * se


def normalised(c, y, o):
    """0–100 %: from the data's own lowest and highest mean response, or from typed 0 % and 100 % values."""
    how = o.get("normalize", "none")
    if how == "values":
        z, h = o.get("zero"), o.get("hundred")
        if z in (None, "") or h in (None, "") or float(z) == float(h):
            raise ValueError("Type the response that means 0 % and the one that means 100 % (two different values).")
        z, h = float(z), float(h)
    elif how == "range":
        means = [float(np.mean(y[c == u])) for u in np.unique(c)]
        z, h = min(means), max(means)
        if z == h:
            raise ValueError("The responses are all the same: nothing to normalise.")
    else:
        return y
    return (y - z) / (h - z) * 100.0


def ic50(table, ks, o):
    falling_opt, three = o.get("direction", "auto"), o.get("model", "4") == "3"
    unit = o.get("unit", "")
    fix = bool(o.get("fix")) and o.get("normalize", "none") != "none"
    rows_all, checks, plots, curves, answers, done = [], [], [], [], [], []
    for k in ks:
        x, y, _ = points(table, k, {"points": "each"})
        name = name_of(table, k)
        x, y = np.asarray(x, float), np.asarray(y, float)
        if o.get("xlog"):
            c = 10.0 ** x
        else:
            if np.any(x < 0):
                checks.append((False, f"{name}: negative concentrations; if X holds log10 concentrations, tick “X is log10 of the concentration”.")); continue
            c = x
        if len(np.unique(c)) < 4:
            checks.append((False, f"{name}: a dose-response curve needs at least four concentrations ({len(np.unique(c))} here).")); continue
        try:
            y = normalised(c, y, o)
        except ValueError as e:
            checks.append((False, f"{name}: {e}")); continue
        lo_c, hi_c = c[c > 0].min(), c.max()
        m_lo, m_hi = float(np.mean(y[c == c.min()])), float(np.mean(y[c == hi_c]))
        falling = (m_hi < m_lo) if falling_opt == "auto" else falling_opt == "inhibit"
        what = "IC50" if falling else "EC50"
        try:
            p, cov, sy, df, rss = fit(c, y, falling, three, {"bottom": 0.0, "top": 100.0} if fix else None)
        except Exception as e:
            checks.append((False, f"{name}: the fit did not converge ({str(e)[:80]}); try 3 parameters or fix the plateaus.")); continue
        tq = float(st.t.ppf(0.975, max(df, 1)))
        se = np.sqrt(np.maximum(np.diag(cov), 0))
        lx, slx = float(p[2]), float(se[2])
        x50, lo, hi = 10 ** lx, 10 ** (lx - tq * slx), 10 ** (lx + tq * slx)
        r2 = 1 - rss / float(np.sum((y - y.mean()) ** 2)) if np.ptp(y) else float("nan")
        cu = f" {unit}" if unit else ""
        rows = [[what, f"{g(x50, 4)}{cu}", f"{g(lo, 4)} to {g(hi, 4)}{cu}"],
                [f"log10 {what}", f"{g(lx, 4)} ± {g(slx, 3)} (SE)", f"{g(lx - tq * slx, 4)} to {g(lx + tq * slx, 4)}"]]
        if unit in UNITS:
            px = -(lx + UNITS[unit])
            rows.append([f"p{what} (−log10 molar)", g(px, 4), f"{g(px - tq * slx, 4)} to {g(px + tq * slx, 4)}"])
        def par(i, label, fixed_note):
            return [label, g(p[i], 4), "fixed" + fixed_note if se[i] == 0 else f"{g(p[i] - tq * se[i], 4)} to {g(p[i] + tq * se[i], 4)}"]
        rows += [par(3, "Hill slope", " (3-parameter model)" if three else ""), par(1, "Top", " at 100 %" if fix else ""), par(0, "Bottom", " at 0 %" if fix else ""),
                 ["R squared", g(r2, 4), ""], ["Sy.x", g(sy, 4), ""], ["Degrees of freedom", g(df), ""], ["Points (concentrations)", f"{len(y)} ({len(np.unique(c))})", ""]]
        rows_all.append({"title": name, "columns": ["", "Best fit", "95% CI"], "rows": rows})
        if not (lo_c <= x50 <= hi_c):
            checks.append((False, f"{name}: the {what} ({g(x50, 3)}{cu}) lies outside the tested concentrations ({g(lo_c, 3)} to {g(hi_c, 3)}); it is an extrapolation."))
        if hi / lo > 100:
            checks.append((False, f"{name}: the {what} is poorly defined (its 95% CI spans more than a hundredfold); test more concentrations around it, or fix the plateaus."))
        if not fix and (se[0] == 0 or se[1] == 0 or se[0] > abs(p[1] - p[0]) or se[1] > abs(p[1] - p[0])):
            checks.append((None, f"{name}: a plateau is poorly defined by the data; consider normalising and fixing Bottom = 0 % and Top = 100 %."))
        cs = np.geomspace(lo_c / 3, hi_c * 1.5, 200)
        fy = model(cs, *p)
        b = band(cs, p, cov, tq)
        xs = np.log10(cs) if o.get("xlog") else cs
        curves.append({"set": k, "x": xs.tolist(), "y": fy.tolist(), "lo": (fy - b).tolist(), "hi": (fy + b).tolist(), "label": f"{what} = {g(x50, 3)}{cu}"})
        res = y - model(c, *p)
        plots.append(residual_plot(f"Residuals · {name}", np.log10(np.where(c > 0, c, lo_c / 3)), res, COLORS[k % 8]))
        answers.append(f"{name}: {what} = {g(x50, 4)}{cu} (95% CI {g(lo, 3)} to {g(hi, 3)}), Hill slope {g(p[3], 3)}.")
        done.append((k, name, c, y, falling, p, rss, df))
    if not done:
        raise ValueError("No data set could be fitted: " + " ".join(m for _, m in checks)[:300] if checks else "Choose data sets with X concentrations and responses.")
    tabs = [{"name": "Summary", "tables": rows_all}]
    if o.get("compare") and len(done) > 1:
        ct, ca = compare(done, three, fix)
        tabs.insert(1, {"name": "Compare", "tables": [ct]})
        answers.append(ca)
    shape = "3-parameter (Hill slope ±1)" if three else "4-parameter (variable slope)"
    norm = {"range": " after normalising each data set to 0–100 % of its own range", "values": " after normalising to 0–100 % of the typed control responses"}.get(o.get("normalize", "none"), "")
    return result("IC50 / EC50", " ".join(answers), tabs, checks, plots=plots, curves=curves,
                  methods=f"Dose-response curves were fitted{norm} with the {shape} logistic model Y = Bottom + (Top − Bottom) / (1 + (X50/X)^Hill) by least squares in Datum Plot (SciPy); "
                          f"the 95% confidence interval of each IC50/EC50 is that of its logarithm, transformed back." + (" Bottom and Top were fixed at 0 % and 100 %." if fix else ""),
                  legend="Curves show the fitted dose-response model; shaded bands its 95% confidence band.",
                  code="import numpy as np\nfrom scipy.optimize import curve_fit\n"
                       "f = lambda x, bottom, top, logx50, hill: bottom + (top - bottom) / (1 + (10**logx50 / x)**hill)\n"
                       "p, cov = curve_fit(f, conc, response, p0=[min(response), max(response), np.log10(np.median(conc)), -1])\n"
                       "print('IC50 =', 10**p[2])")


def compare(done, three, fix):
    """0.4.12 (B39): do the data sets' IC50s differ? Extra sum-of-squares F test: one shared log X50 against one per
    data set (each keeping its own plateaus and slope); and each one's ratio to the first."""
    from scipy.optimize import least_squares
    sets = [(c, y, falling, p) for _, _, c, y, falling, p, _, _ in done]
    rss_sep = sum(r for *_, r, _ in done)
    df_sep = sum(d for *_, d in done)

    def resid(v):
        shared = v[0]
        out, i = [], 1
        for c, y, falling, p in sets:
            b, t_ = (0.0, 100.0) if fix else (v[i], v[i + 1])
            i += 0 if fix else 2
            h = (-1.0 if falling else 1.0) if three else v[i]
            i += 0 if three else 1
            out.append(y - model(c, b, t_, shared, h))
        return np.concatenate(out)
    v0 = [float(np.mean([p[2] for *_, p in sets]))]
    for *_, p in sets:
        v0 += ([] if fix else [p[0], p[1]]) + ([] if three else [p[3]])
    r = least_squares(resid, v0)
    rss_one = float(np.sum(r.fun ** 2))
    n = sum(len(y) for _, y, _, _ in sets)
    df_one = n - len(v0)
    dn = df_one - df_sep
    F = ((rss_one - rss_sep) / dn) / (rss_sep / df_sep) if dn > 0 and rss_sep > 0 else float("nan")
    P = float(st.f.sf(F, dn, df_sep)) if math.isfinite(F) else float("nan")
    first = done[0]
    rows = [["Do the IC50/EC50s differ?", f"F({dn}, {df_sep}) = {g(F, 4)}, {p_text(P)}", "Yes" if P < 0.05 else "No"]]
    for k, name, c, y, falling, p, *_ in done[1:]:
        ratio = 10 ** (p[2] - first[5][2])
        rows.append([f"{name} / {first[1]}", g(ratio, 4), f"{'less' if ratio > 1 else 'more'} potent than {first[1]}" if ratio != 1 else "the same"])
    ans = (f"The IC50/EC50s {'differ' if P < 0.05 else 'do not differ significantly'} (extra sum-of-squares F test, {p_text(P)})."
           + ("" if len(done) != 2 else f" {done[1][1]} / {first[1]} = {g(10 ** (done[1][5][2] - first[5][2]), 3)}."))
    return {"title": "Comparison of the IC50/EC50s (one shared against one per data set)", "columns": ["", "Value", ""], "rows": rows}, ans
