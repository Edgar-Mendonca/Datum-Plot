"""Analyses on a data table. `run(kind, table, sets, options)` returns one shape for every kind:

    {"title", "answer", "tabs": [{"name", "tables": [{"title", "columns", "rows"}]}], "checks": [[ok, text]],
     "methods", "legend", "code", "plots": [{"title", "svg"}], "curves": [...], "cells": [[row, col]]}

`curves` are drawn on the table's graphs (fitted lines with bands and an equation label); `cells`
are values an analysis suggests excluding (outliers). Numbers in tables are already formatted text.
"""
import io
import math

import numpy as np
from scipy import stats as st

from . import stats
from .models import MODELS, R

ALPHA = 0.05


# ---------- formatting ----------
def g(v, d=5):
    """A number with `d` significant digits, as text."""
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return "—"
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    v = float(v)
    if v == 0:
        return "0"
    if not 1e-4 <= abs(v) < 1e7:
        return f"{v:.{d - 1}e}"
    places = d - 1 - math.floor(math.log10(abs(v)))
    dec = max(0, places)
    out = f"{round(v, places):.{dec}f}"
    return out.rstrip("0").rstrip(".") if "." in out else out


def pv(p):
    """APA-style P value: exact, or < 0.0001."""
    return "—" if p is None or not math.isfinite(p) else "< 0.0001" if p < 1e-4 else f"{p:.4f}"


def stars(p):
    return "ns" if p is None or not math.isfinite(p) or p >= 0.05 else "*" if p >= 0.01 else "**" if p >= 0.001 else "***"


def name_of(table, k):
    return table["sets"][k].get("title") or f"Data set {chr(65 + k)}"


def chosen(table, sets):
    n = len(table["sets"])
    return [k for k in (sets or range(n)) if 0 <= k < n]


# ---------- data ----------
def points(table, k, o):
    """(x, y, cells) of data set k: every replicate (or the means), inside the fit range."""
    pts = stats.summarize(table)[k]
    lo, hi = o.get("xmin"), o.get("xmax")
    xs, ys, cells = [], [], []
    c0 = stats.set_columns(table)[k][0]
    ex = {tuple(e) for e in table.get("excluded", [])}
    for p in pts:
        if (lo is not None and p["x"] < lo) or (hi is not None and p["x"] > hi):
            continue
        if o.get("points", "each") == "mean" or table["sets"][k]["entry"] != "rep":
            xs.append(p["x"]); ys.append(p["mean"]); cells.append([p["row"], c0])
        else:
            for j in range(stats.set_columns(table)[k][1]):
                v = stats.value(table, p["row"], c0 + j, ex)
                if v is not None:
                    xs.append(p["x"]); ys.append(v); cells.append([p["row"], c0 + j])
    return np.asarray(xs, float), np.asarray(ys, float), cells


def values(table, k):
    """Every Y value of data set k with its cell, for column statistics."""
    c0, w = stats.set_columns(table)[k]
    ex = {tuple(e) for e in table.get("excluded", [])}
    out = [(stats.value(table, r, c, ex), [r, c]) for r in range(table["rows"]) for c in range(c0, c0 + (w if table["sets"][k]["entry"] == "rep" else 1))]
    return [(v, cell) for v, cell in out if v is not None and math.isfinite(v)]


def grid(x, n=200):
    lo, hi = float(np.min(x)), float(np.max(x))
    return np.geomspace(lo, hi, n) if lo > 0 and hi / lo > 50 else np.linspace(lo, hi, n)


def small_plot(title, draw, w=70, h=50):
    """A small matplotlib picture (residuals, QQ…) as SVG for the results sheet."""
    import matplotlib
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    with matplotlib.rc_context({"font.family": "sans-serif", "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"], "font.size": 8, "svg.fonttype": "none", "svg.hashsalt": "datum-plot"}):
        fig = Figure(figsize=(w / 25.4, h / 25.4), dpi=72, layout="constrained")
        FigureCanvasAgg(fig)
        ax = fig.add_subplot()
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        draw(ax)
        buf = io.StringIO()
        fig.savefig(buf, format="svg", metadata={"Date": None})
    return {"title": title, "svg": buf.getvalue()}


def residual_plot(title, x, res, color):
    def draw(ax):
        ax.axhline(0, color="#8D9AAB", lw=0.8)
        ax.plot(x, res, "o", ms=3.5, color=color)
        ax.set_xlabel("X"); ax.set_ylabel("Residual")
    return small_plot(title, draw)


COLORS = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000"]


def result(title, answer, tabs, checks=(), methods="", legend="", code="", plots=(), curves=(), cells=(), **extra):
    """`extra`: `brackets` ([set, set, P] drawn over column graphs) and `table` (a new data table the result can become)."""
    return {"title": title, "answer": answer, "tabs": tabs, "checks": [[None if c[0] is None else bool(c[0]), c[1]] for c in checks], "methods": methods, "legend": legend, "code": code,
            "plots": list(plots), "curves": list(curves), "cells": list(cells), **extra}


def by_set(table, ks, rows):
    """A Prism-style table: one row per statistic, one column per data set."""
    return {"title": "", "columns": [""] + [name_of(table, k) for k in ks], "rows": rows}


# ---------- descriptive statistics (B1) ----------
def describe(table, ks, o):
    names = ["Number of values", "Mean", "Std. deviation", "Std. error of mean", "Lower 95% CI of mean", "Upper 95% CI of mean", "Minimum", "25% percentile", "Median",
             "75% percentile", "Maximum", "Range", "Coefficient of variation", "Geometric mean", "Geometric SD factor", "Skewness", "Kurtosis", "Sum"]
    cols, checks = [], []
    for k in ks:
        v = np.array([a for a, _ in values(table, k)])
        n = len(v)
        if n == 0:
            cols.append(["0"] + ["—"] * (len(names) - 1)); continue
        m, sd = v.mean(), v.std(ddof=1) if n > 1 else 0.0
        sem = sd / math.sqrt(n) if n > 1 else 0.0
        t = st.t.ppf(0.975, n - 1) if n > 1 else float("nan")
        q1, med, q3 = np.percentile(v, [25, 50, 75])
        pos = bool(np.all(v > 0))
        gm = float(np.exp(np.log(v).mean())) if pos else None
        gsd = float(np.exp(np.log(v).std(ddof=1))) if pos and n > 1 else None
        cols.append([g(n), g(m), g(sd), g(sem), g(m - t * sem), g(m + t * sem), g(v.min()), g(q1), g(med), g(q3), g(v.max()), g(np.ptp(v)),
                     f"{g(100 * sd / m, 4)}%" if m else "—", g(gm), g(gsd), g(st.skew(v, bias=False)) if n > 2 else "—", g(st.kurtosis(v, bias=False)) if n > 3 else "—", g(v.sum())])
        if n < 3:
            checks.append((False, f"{name_of(table, k)} has only {n} value{'s' if n != 1 else ''}; most statistics need at least 3."))
    rows = [[nm] + [c[i] for c in cols] for i, nm in enumerate(names)]
    k0 = ks[0] if ks else 0
    answer = f"{name_of(table, k0)}: mean {cols[0][1]} ± {cols[0][2]} (SD), n = {cols[0][0]}." if cols else "No data."
    return result("Descriptive statistics", answer, [{"name": "Summary", "tables": [by_set(table, ks, rows)]}], checks,
                  methods="Descriptive statistics (mean, standard deviation, standard error and 95% confidence interval of the mean) were calculated in Datum Plot.",
                  code="import numpy as np\nfrom scipy import stats\nv = np.array([...])  # the values of one data set\nprint(v.mean(), v.std(ddof=1), stats.sem(v), stats.t.interval(0.95, len(v) - 1, v.mean(), stats.sem(v)))")


# ---------- normality (B2) ----------
def normality(table, ks, o):
    alpha = float(o.get("alpha", ALPHA))
    rows = {n: [n] for n in ["Shapiro-Wilk W", "  P value", "  Passed (normal)?", "D'Agostino-Pearson K2", "  P value", "  Passed (normal)?", "Anderson-Darling A2", "  P value", "  Passed (normal)?", "Kolmogorov-Smirnov D (Lilliefors)", "  P value", "  Passed (normal)?", "Number of values"]}
    keys = list(rows)
    plots, checks, fails = [], [], []
    for i, k in enumerate(ks):
        v = np.array([a for a, _ in values(table, k)])
        res = []
        if len(v) >= 3:
            w, p = st.shapiro(v); res += [g(w, 4), pv(p), "Yes" if p > alpha else "No"]
            if p <= alpha:
                fails.append(name_of(table, k))
        else:
            res += ["—", "—", "Too few"]
        if len(v) >= 8:
            k2, p = st.normaltest(v); res += [g(k2, 4), pv(p), "Yes" if p > alpha else "No"]
        else:
            res += ["—", "—", "n < 8"]
        if len(v) >= 4:
            from statsmodels.stats.diagnostic import normal_ad, lilliefors
            a2, p = normal_ad(v); res += [g(a2, 4), pv(p), "Yes" if p > alpha else "No"]
            d, p = lilliefors(v, dist="norm", pvalmethod="table"); res += [g(d, 4), pv(p), "Yes" if p > alpha else "No"]
        else:
            res += ["—", "—", "Too few"] * 2
        res.append(g(len(v)))
        for key, r in zip(keys, res):
            rows[key].append(r)
        if len(v) >= 3:
            (osm, osr), (slope, icpt, _) = st.probplot(v)
            plots.append(small_plot(f"QQ plot · {name_of(table, k)}", lambda ax, osm=osm, osr=osr, slope=slope, icpt=icpt, c=COLORS[k % 8]: (
                ax.plot(osm, slope * osm + icpt, color="#8D9AAB", lw=0.8), ax.plot(osm, osr, "o", ms=3.5, color=c), ax.set_xlabel("Normal quantile"), ax.set_ylabel("Value"))))
        if len(v) < 8:
            checks.append((None, f"{name_of(table, k)}: with {len(v)} values, normality tests have little power; a QQ plot is a better guide."))
    ans = (f"Shapiro-Wilk: {', '.join(fails)} {'does' if len(fails) == 1 else 'do'} not look normally distributed (P ≤ {alpha:g})." if fails
           else f"Shapiro-Wilk finds no evidence against normality in {'any data set' if len(ks) > 1 else name_of(table, ks[0])} (P > {alpha:g}).")
    return result("Normality tests", ans, [{"name": "Summary", "tables": [by_set(table, ks, list(rows.values()))]}], checks, plots=plots,
                  methods=f"Normality was tested with the Shapiro-Wilk, D'Agostino-Pearson, Anderson-Darling and Kolmogorov-Smirnov (Lilliefors) tests (α = {alpha:g}).",
                  code="from scipy import stats\nprint(stats.shapiro(v), stats.normaltest(v))")


# ---------- outliers (B3) ----------
def grubbs(v, alpha):
    """Iterative two-sided Grubbs' test: indices of outliers in v."""
    idx, out = list(range(len(v))), []
    while len(idx) > 2:
        a = np.array([v[i] for i in idx])
        sd = a.std(ddof=1)
        if sd == 0:
            break
        j = int(np.argmax(np.abs(a - a.mean())))
        G, n = abs(a[j] - a.mean()) / sd, len(a)
        t = st.t.ppf(1 - alpha / (2 * n), n - 2)
        if G <= (n - 1) / math.sqrt(n) * math.sqrt(t * t / (n - 2 + t * t)):
            break
        out.append(idx.pop(j))
    return out


def outliers(table, ks, o):
    alpha = float(o.get("alpha", ALPHA))
    rows, cells, found = [], [], 0
    for k in ks:
        vals = values(table, k)
        for i in grubbs([v for v, _ in vals], alpha):
            v, cell = vals[i]
            rows.append([name_of(table, k), g(v), str(cell[0] + 1), cell[1]])
            cells.append(cell)
            found += 1
    ans = f"Grubbs' test found {found} outlier{'s' if found != 1 else ''} (α = {alpha:g})." if found else f"Grubbs' test found no outliers (α = {alpha:g})."
    tab = {"title": "Outliers", "columns": ["Data set", "Value", "Row", "Column"], "rows": [[r[0], r[1], r[2], str(r[3])] for r in rows] or [["None", "", "", ""]]}
    return result("Outliers", ans, [{"name": "Summary", "tables": [tab]}],
                  [(None, "Exclude outliers only with a reason; Grubbs' test assumes the other values are normally distributed.")] if found else [],
                  methods=f"Outliers were identified with the iterative two-sided Grubbs' test (α = {alpha:g}).", cells=cells,
                  code="# Grubbs: G = max|x - mean| / sd, compared with the critical value from the t distribution")


# ---------- linear regression (B9, B13) ----------
def runs_test(res):
    s = np.sign(res[res != 0])
    if len(s) < 3:
        return None, None
    runs = 1 + int(np.sum(s[1:] != s[:-1]))
    n1, n2 = int(np.sum(s > 0)), int(np.sum(s < 0))
    if n1 == 0 or n2 == 0:
        return runs, None
    mu = 2 * n1 * n2 / (n1 + n2) + 1
    var = 2 * n1 * n2 * (2 * n1 * n2 - n1 - n2) / ((n1 + n2) ** 2 * (n1 + n2 - 1))
    return runs, float(st.norm.cdf((runs - mu) / math.sqrt(var))) if var > 0 else None


def ols(x, y, model, order, w=None):
    """Least squares: returns (statsmodels result, design function)."""
    import statsmodels.api as sm
    if model == "poly":
        X = lambda t: np.vander(np.asarray(t, float), order + 1, increasing=True)
    elif model == "origin":
        X = lambda t: np.asarray(t, float)[:, None]
    else:
        X = lambda t: sm.add_constant(np.asarray(t, float), has_constant="add")
    r = (sm.WLS(y, X(x), weights=w) if w is not None else sm.OLS(y, X(x))).fit()
    return r, X


def deming(x, y, ratio=1.0):
    """Deming regression (errors in X and Y, variance ratio `ratio`): slope, intercept and jackknife SEs."""
    def fit(x, y):
        mx, my = x.mean(), y.mean()
        sxx, syy, sxy = np.mean((x - mx) ** 2), np.mean((y - my) ** 2), np.mean((x - mx) * (y - my))
        b = (syy - ratio * sxx + math.sqrt((syy - ratio * sxx) ** 2 + 4 * ratio * sxy ** 2)) / (2 * sxy)
        return b, my - b * mx
    b, a = fit(x, y)
    n = len(x)
    jk = np.array([fit(np.delete(x, i), np.delete(y, i)) for i in range(n)])
    se = np.sqrt((n - 1) / n * np.sum((jk - jk.mean(0)) ** 2, axis=0))
    return b, a, se[0], se[1]


def weights(y, o):
    return 1 / np.maximum(y * y, 1e-300) if o.get("weight") == "1/y2" else None


def linear(table, ks, o):
    model, order = o.get("model", "line"), int(o.get("order", 2))
    cols, details, plots, curves, checks, answers, interp = [], [], [], [], [], [], []
    fits = []
    for k in ks:
        x, y, _ = points(table, k, o)
        name, c = name_of(table, k), COLORS[k % 8]
        npar = order + 1 if model == "poly" else 1 if model == "origin" else 2
        if len(x) < npar + 1:
            cols.append(None); checks.append((False, f"{name}: not enough points to fit ({len(x)}).")); continue
        if model == "deming":
            b, a, sb, sa = deming(x, y, float(o.get("ratio", 1.0)))
            n, t = len(x), st.t.ppf(0.975, len(x) - 2)
            pred = a + b * x
            res = y - pred
            ss = float(np.sum(res ** 2))
            r2 = 1 - ss / float(np.sum((y - y.mean()) ** 2))
            cols.append([("Slope", g(b), g(sb), f"{g(b - t * sb)} to {g(b + t * sb)}"), ("Y-intercept", g(a), g(sa), f"{g(a - t * sa)} to {g(a + t * sa)}"),
                         ("X-intercept", g(-a / b) if b else "—", "", ""), ("R squared (of Y on X)", g(r2, 4), "", ""), ("Number of points", g(n), "", "")])
            eq = f"Y = {g(b, 4)}·X {'+' if a >= 0 else '−'} {g(abs(a), 4)}"
            xs = grid(x)
            curves.append({"set": k, "x": xs.tolist(), "y": (a + b * xs).tolist(), "label": eq})
            answers.append(f"{name}: slope {g(b, 4)} (95% CI {g(b - t * sb, 4)} to {g(b + t * sb, 4)}).")
            fits.append((k, x, y, lambda v, a=a, b=b: a + b * v, None))
            plots.append(residual_plot(f"Residuals · {name}", x, res, c))
            continue
        w = weights(y, o)
        r, X = ols(x, y, model, order, w)
        n, p = len(x), len(r.params)
        t = st.t.ppf(0.975, r.df_resid)
        ci = r.conf_int(0.05)
        labels = ["Y-intercept", "Slope"] if model == "line" else ["Slope"] if model == "origin" else [f"B{i}" for i in range(p)]
        rows = [(lab, g(v), g(se), f"{g(lo)} to {g(hi)}") for lab, v, se, (lo, hi) in zip(labels, r.params, r.bse, ci)]
        if model == "line":
            rows = [rows[1], rows[0]]
            b, a = r.params[1], r.params[0]
            rows += [("X-intercept", g(-a / b) if b else "—", "", ""), ("1/slope", g(1 / b) if b else "—", "", "")]
        syx = math.sqrt(r.ssr / r.df_resid) if r.df_resid > 0 else float("nan")
        r2 = r.rsquared
        rows += [("R squared", g(r2, 4), "", ""), ("Adjusted R squared", g(r.rsquared_adj, 4), "", ""), ("Sy.x", g(syx), "", ""), ("Number of points", g(n), "", "")]
        if model != "poly":
            pf = float(r.f_pvalue) if model == "line" else float(r.pvalues[0])
            rows += [("Is the slope different from zero?", f"P {pv(pf)}" if pv(pf).startswith("<") else f"P = {pv(pf)}", stars(pf), "Yes" if pf < ALPHA else "No")]
        res = y - r.fittedvalues
        runs, prun = runs_test(res[np.argsort(x)])
        if prun is not None and prun < ALPHA:
            checks.append((False, f"{name}: the runs test says the points do not scatter randomly around the line (P = {pv(prun)}); try a curve."))
        else:
            checks.append((True, f"{name}: residuals scatter randomly around the fit (runs test)."))
        if n < 6:
            checks.append((None, f"{name}: only {n} points; confidence intervals are wide."))
        cols.append(rows)
        details.append({"title": f"ANOVA · {name}", "columns": ["Source", "SS", "DF", "MS", "F", "P"],
                        "rows": [["Regression", g(r.ess), g(int(r.df_model)), g(r.ess / max(r.df_model, 1)), g(r.fvalue) if r.fvalue is not None else "—", pv(float(r.f_pvalue)) if r.f_pvalue is not None else "—"],
                                 ["Residual", g(r.ssr), g(int(r.df_resid)), g(r.ssr / max(r.df_resid, 1)), "", ""], ["Total", g(r.ssr + r.ess), g(int(r.df_model + r.df_resid)), "", "", ""]]})
        details.append({"title": f"Runs test · {name}", "columns": ["Runs", "P (too few runs)"], "rows": [[g(runs), pv(prun)]]})
        xs = grid(x)
        pr = r.get_prediction(X(xs)).summary_frame(alpha=0.05)
        if model == "line":
            eq = f"Y = {g(b, 4)}·X {'+' if a >= 0 else '−'} {g(abs(a), 4)}"
            answers.append(f"{name}: slope {g(b, 4)} (95% CI {g(ci[1][0], 4)} to {g(ci[1][1], 4)}), R² = {g(r2, 4)}.")
        elif model == "origin":
            eq = f"Y = {g(r.params[0], 4)}·X"
            answers.append(f"{name}: slope {g(r.params[0], 4)} through the origin, R² = {g(r2, 4)}.")
        else:
            eq = "Y = " + " + ".join(f"{g(v, 4)}·X^{i}" if i > 1 else f"{g(v, 4)}·X" if i == 1 else g(v, 4) for i, v in enumerate(r.params))
            answers.append(f"{name}: polynomial of order {order}, R² = {g(r2, 4)}.")
        curves.append({"set": k, "x": xs.tolist(), "y": pr["mean"].tolist(), "lo": pr["mean_ci_lower"].tolist(), "hi": pr["mean_ci_upper"].tolist(),
                       "plo": pr["obs_ci_lower"].tolist(), "phi": pr["obs_ci_upper"].tolist(), "label": f"{eq}, R² = {g(r2, 4)}"})
        fits.append((k, x, y, lambda v, r=r, X=X: r.predict(X(np.atleast_1d(v))), (r, X)))
        plots.append(residual_plot(f"Residuals · {name}", x, res, c))
    heads = ["Best-fit value", "Std. error", "95% CI"]
    tabs = [{"name": "Summary", "tables": [{"title": name_of(table, k), "columns": ["", *heads], "rows": [list(rw) for rw in rows]} for k, rows in zip(ks, cols) if rows]}]
    if model in ("line", "origin") and len(fits) > 1 and o.get("compare", True):
        tabs[0]["tables"].append(compare_lines(table, fits, model))
    if details:
        tabs.append({"name": "Details", "tables": details})
    if o.get("unknowns"):
        tabs.append({"name": "Interpolated", "tables": [interpolate(table, fits, o["unknowns"])]})
    what = {"line": "a straight line by least squares", "origin": "a straight line through the origin", "poly": f"a polynomial of order {order}", "deming": "Deming regression (errors in X and Y)"}[model]
    rng = "" if o.get("xmin") is None and o.get("xmax") is None else f" over X from {g(o.get('xmin')) if o.get('xmin') is not None else 'the start'} to {g(o.get('xmax')) if o.get('xmax') is not None else 'the end'}"
    return result("Linear regression", " ".join(answers) or "No fit.", tabs, checks, plots=plots, curves=curves,
                  methods=f"Data were fitted with {what}{rng} ({'every replicate' if o.get('points', 'each') == 'each' else 'means'}{', weighted by 1/Y²' if o.get('weight') == '1/y2' else ''}) using Datum Plot (Python, statsmodels).",
                  legend="Lines show the best fit; shaded bands the 95% confidence interval of the line.",
                  code="import numpy as np, statsmodels.api as sm\nx, y = np.array([...]), np.array([...])\nr = sm.OLS(y, sm.add_constant(x)).fit()\nprint(r.summary())")


def compare_lines(table, fits, model):
    """F tests: are the slopes equal, then (if so) the intercepts? (Zar, as Prism.)"""
    import statsmodels.api as sm
    xs = np.concatenate([f[1] for f in fits]); ys = np.concatenate([f[2] for f in fits])
    g_ = np.concatenate([np.full(len(f[1]), i) for i, f in enumerate(fits)])
    m = len(fits)
    D = np.eye(m)[g_]
    sep = sm.OLS(ys, np.column_stack([D, D * xs[:, None]])).fit()      # own slope and intercept
    common_slope = sm.OLS(ys, np.column_stack([D, xs])).fit()          # own intercepts, one slope
    one = sm.OLS(ys, sm.add_constant(xs)).fit()                        # one line
    def ftest(big, small):
        dfn = small.df_resid - big.df_resid
        F = ((small.ssr - big.ssr) / dfn) / (big.ssr / big.df_resid)
        return F, dfn, big.df_resid, float(st.f.sf(F, dfn, big.df_resid))
    F, a, b, p = ftest(sep, common_slope)
    rows = [["Are the slopes equal?", f"F = {g(F, 4)}", f"DFn = {int(a)}, DFd = {int(b)}", f"P = {pv(p)}" if not pv(p).startswith("<") else f"P {pv(p)}", "No, they differ" if p < ALPHA else "Yes (no evidence they differ)"]]
    if p >= ALPHA:
        F2, a2, b2, p2 = ftest(common_slope, one)
        rows.append(["Are the intercepts (elevations) equal?", f"F = {g(F2, 4)}", f"DFn = {int(a2)}, DFd = {int(b2)}", f"P = {pv(p2)}" if not pv(p2).startswith("<") else f"P {pv(p2)}", "No, they differ" if p2 < ALPHA else "Yes (no evidence they differ)"])
        rows.append(["Pooled slope", g(common_slope.params[-1]), "", "", ""])
    return {"title": "Comparing the lines", "columns": ["Question", "F", "Degrees of freedom", "P value", "Answer"], "rows": rows}


def interpolate(table, fits, unknowns):
    """X for each unknown Y, read off each fitted line or curve (inside the data range)."""
    from scipy.optimize import brentq
    ys = [float(v) for v in str(unknowns).replace(";", ",").split(",") if v.strip()]
    rows = []
    for k, x, y, f, _ in fits:
        xs = grid(x, 400)
        fy = np.asarray(f(xs), float)
        for u in ys:
            s = np.sign(fy - u)
            i = np.where(s[:-1] * s[1:] <= 0)[0]
            if len(i):
                x0 = brentq(lambda v: float(np.asarray(f(v)).ravel()[0]) - u, xs[i[0]], xs[i[0] + 1]) if s[i[0]] != 0 else xs[i[0]]
                rows.append([name_of(table, k), g(u), g(x0)])
            else:
                rows.append([name_of(table, k), g(u), "outside the curve"])
    return {"title": "Unknowns read off the fit", "columns": ["Data set", "Y (unknown)", "X (interpolated)"], "rows": rows}


# ---------- nonlinear curve fitting (B10, B11) ----------
def expression(o):
    """(equation in X, guess function, model name) from the options."""
    if o.get("model", "exp_decay") == "custom":
        eq = str(o.get("equation", "")).split("=", 1)[-1].strip()
        if not eq:
            raise ValueError("Type an equation such as Y = A*exp(-k*X) + C.")
        return eq, None, "your equation"
    name, eq, guess, _ = MODELS[o.get("model", "exp_decay")]
    return eq, guess, name


def make_model(eq):
    import re
    from lmfit.models import ExpressionModel
    py = re.sub(r"\bX\b", "x", eq.replace("^", "**"))
    return ExpressionModel(py, independent_vars=["x"]), py


def start(model, guess, x, y, o):
    """Starting values: 1, then the model's guess, then the user's values and fixed parameters."""
    p = model.make_params(**{n: 1.0 for n in model.param_names})
    if guess:
        try:
            for n, v in guess(x, y).items():
                if n in p and math.isfinite(v):
                    p[n].set(value=float(v))
        except Exception:
            pass
    for n, v in (o.get("init") or {}).items():
        if n in p and v not in (None, ""):
            p[n].set(value=float(v))
    for n, v in (o.get("fixed") or {}).items():
        if n in p and v not in (None, ""):
            p[n].set(value=float(v), vary=False)
    return p


def fit_one(model, guess, x, y, o):
    w = None if o.get("weight") != "1/y2" else 1 / np.maximum(np.abs(y), 1e-300)
    return model.fit(y, start(model, guess, x, y, o), x=x, weights=w, nan_policy="omit")


def aicc_of(ss, n, k):
    return n * math.log(ss / n) + 2 * k + (2 * k * (k + 1) / (n - k - 1) if n - k - 1 > 0 else float("inf")) if ss > 0 else float("nan")


def nonlinear(table, ks, o):
    eq, guess, mname = expression(o)
    model, py = make_model(eq)
    tabs_rows, checks, plots, curves, answers, fits, details, done = [], [], [], [], [], [], [], []
    for k in ks:
        x, y, _ = points(table, k, o)
        name, c = name_of(table, k), COLORS[k % 8]
        npar = len(model.param_names)
        if len(x) <= npar:
            checks.append((False, f"{name}: {len(x)} points cannot fit {npar} parameters.")); continue
        try:
            r = fit_one(model, guess, x, y, o)
        except Exception as e:
            checks.append((False, f"{name}: the fit failed ({e}).")); continue
        n, nv = len(x), r.nvarys
        df = max(n - nv, 1)
        t = st.t.ppf(0.975, df)
        rows = []
        for pn in model.param_names:
            par = r.params[pn]
            se = par.stderr
            ci = f"{g(par.value - t * se)} to {g(par.value + t * se)}" if se is not None and par.vary else ""
            rows.append([pn, g(par.value), g(se) if se is not None and par.vary else ("fixed" if not par.vary else "—"), ci])
        res = y - r.best_fit
        ss = float(np.sum(res ** 2))
        r2 = 1 - ss / float(np.sum((y - y.mean()) ** 2)) if np.ptp(y) else float("nan")
        aicc = aicc_of(ss, n, nv)
        done.append((k, x, y, ss, nv))
        rows += [["R squared", g(r2, 4), "", ""], ["Sy.x", g(math.sqrt(ss / df)), "", ""], ["Sum of squares", g(ss), "", ""], ["Degrees of freedom", g(df), "", ""], ["AICc", g(aicc), "", ""],
                 ["Number of points", g(n), "", ""], ["Converged", "Yes" if r.success else "No", "", ""]]
        if not r.success:
            checks.append((False, f"{name}: the fit did not converge; give better starting values or fix a parameter."))
        if any(r.params[pn].stderr is None for pn in model.param_names if r.params[pn].vary):
            checks.append((False, f"{name}: some parameters could not be estimated (ambiguous fit); fix one or use a simpler model."))
        runs, prun = runs_test(res[np.argsort(x)])
        checks.append((prun is None or prun >= ALPHA, f"{name}: {'residuals scatter randomly around the curve' if prun is None or prun >= ALPHA else 'the curve misses a trend in the data (runs test P = ' + pv(prun) + ')'}."))
        tabs_rows.append({"title": name, "columns": ["Parameter", "Best-fit value", "Std. error", "95% CI"], "rows": rows})
        xs = grid(x)
        fit_y = r.eval(x=xs)
        cur = {"set": k, "x": xs.tolist(), "y": np.asarray(fit_y, float).tolist(), "label": f"R² = {g(r2, 4)}"}
        try:
            band = r.eval_uncertainty(x=xs, sigma=float(t))
            cur["lo"], cur["hi"] = (fit_y - band).tolist(), (fit_y + band).tolist()
        except Exception:
            pass
        curves.append(cur)
        fits.append((k, x, y, lambda v, r=r: r.eval(x=np.atleast_1d(np.asarray(v, float))), None))
        plots.append(residual_plot(f"Residuals · {name}", x, res, c))
        main = [pn for pn in model.param_names if r.params[pn].vary][:2]
        answers.append(f"{name}: " + ", ".join(f"{pn} = {g(r.params[pn].value, 4)}" for pn in main) + f" (R² = {g(r2, 4)}).")
        details.append({"title": f"Correlation of parameters · {name}", "columns": ["", *[pn for pn in model.param_names if r.params[pn].vary]],
                        "rows": [[a] + [g((r.params[a].correl or {}).get(b, 1.0 if a == b else float("nan")), 3) for b in model.param_names if r.params[b].vary] for a in model.param_names if r.params[a].vary]})
    tabs = [{"name": "Summary", "tables": tabs_rows}, {"name": "Details", "tables": details}]
    shared = [n.strip() for n in str(o.get("shared", "")).replace(";", ",").split(",") if n.strip() in model.param_names]
    if shared and len(done) > 1:
        gt, gc, ga = global_fit(table, model, guess, done, o, shared)
        tabs.insert(1, {"name": "Global fit", "tables": gt})
        curves, answers = gc, [ga]
    if o.get("model2") and done:
        ct, ca = compare_models(table, model, done, o)
        tabs.insert(1, {"name": "Model comparison", "tables": [ct]})
        answers.append(ca)
    if o.get("unknowns") and fits:
        tabs.append({"name": "Interpolated", "tables": [interpolate(table, fits, o["unknowns"])]})
    return result("Nonlinear regression", " ".join(answers) or "No fit.", tabs, checks, plots=plots, curves=curves,
                  methods=f"Data were fitted by nonlinear least squares ({mname}: Y = {eq}) with Datum Plot (Python, lmfit/SciPy, Levenberg-Marquardt); 95% confidence intervals are asymptotic.",
                  legend="Curves show the best fit; shaded bands the 95% confidence band.",
                  code=f"import numpy as np\nfrom lmfit.models import ExpressionModel\nm = ExpressionModel('{py}')\nr = m.fit(y, m.make_params(...), x=x)\nprint(r.fit_report())")


def global_fit(table, model, guess, done, o, shared):
    """One fit of every data set with `shared` parameters in common (B12), and the F test of
    whether those parameters differ between the data sets (global against separate fits)."""
    from lmfit import Parameters, minimize
    starts = [start(model, guess, x, y, o) for _, x, y, _, _ in done]
    P = Parameters()
    for n in model.param_names:
        if n in shared:
            P.add(n, value=float(np.mean([s_[n].value for s_ in starts])), vary=starts[0][n].vary)
        else:
            for i, s_ in enumerate(starts):
                P.add(f"{n}_{i}", value=s_[n].value, vary=s_[n].vary)
    vals = lambda P, i: {n: P[n].value if n in shared else P[f"{n}_{i}"].value for n in model.param_names}
    r = minimize(lambda P: np.concatenate([model.eval(x=x, **vals(P, i)) - y for i, (_, x, y, _, _) in enumerate(done)]), P)
    ssg, N = float(np.sum(r.residual ** 2)), sum(len(d[1]) for d in done)
    dfg = N - r.nvarys
    sss, dfs = sum(d[3] for d in done), sum(len(d[1]) - d[4] for d in done)
    rows = []
    for n in model.param_names:
        for key, where in [(n, "All data sets")] if n in shared else [(f"{n}_{i}", name_of(table, d[0])) for i, d in enumerate(done)]:
            par = r.params[key]
            rows.append([f"{n}{' (shared)' if n in shared else ''}", where, g(par.value), g(par.stderr) if par.stderr is not None and par.vary else "fixed" if not par.vary else "—"])
    out = [{"title": "Global fit: shared parameters in common", "columns": ["Parameter", "Data set", "Best-fit value", "Std. error"], "rows": rows}]
    ans = f"Global fit: {', '.join(f'{n} = {g(r.params[n].value, 4)}' for n in shared)} (shared)."
    if dfg > dfs and dfs > 0 and sss > 0:
        F = ((ssg - sss) / (dfg - dfs)) / (sss / dfs)
        p = float(st.f.sf(F, dfg - dfs, dfs))
        out.append({"title": f"Does {', '.join(shared)} differ between the data sets?", "columns": ["", "Value"], "rows": [["Separate fits: SS, DF", f"{g(sss)}, {dfs}"], ["Global fit: SS, DF", f"{g(ssg)}, {dfg}"],
                    ["F (DFn, DFd)", f"{g(F, 4)} ({dfg - dfs}, {dfs})"], ["P value", pv(p)], ["Answer", f"{'Yes, it differs' if p < ALPHA else 'No evidence it differs'} (P {'<' if p < 1e-4 else '='} {pv(p).lstrip('< ')})"]]})
        ans += f" {'The shared parameter differs' if p < ALPHA else 'No evidence the shared parameter differs'} between data sets (extra sum-of-squares F test, P {'<' if p < 1e-4 else '='} {pv(p).lstrip('< ')})."
    curves = []
    for i, (k, x, y, _, _) in enumerate(done):
        xs = grid(x)
        curves.append({"set": k, "x": xs.tolist(), "y": np.asarray(model.eval(x=xs, **vals(r.params, i)), float).tolist(), "label": f"{name_of(table, k)} (global)"})
    return out, curves, ans


def compare_models(table, model, done, o):
    """Fits a second model to each data set and compares the two (extra sum-of-squares F test and AICc)."""
    if o["model2"] == "custom":
        eq2, guess2, name2 = str(o.get("equation2", "")).split("=", 1)[-1].strip(), None, "your second equation"
        if not eq2:
            raise ValueError("Type the second equation.")
    else:
        name2, eq2, guess2, _ = MODELS[o["model2"]]
    m2, _ = make_model(eq2)
    name1 = expression(o)[2]
    rows, prefer = [], []
    for k, x, y, ss1, k1 in done:
        try:
            r2 = fit_one(m2, guess2, x, y, {**o, "init": {}, "fixed": {}})
        except Exception:
            rows.append([name_of(table, k), "the second model did not fit", "", "", "", ""]); continue
        n, k2 = len(x), r2.nvarys
        ss2 = float(np.sum((y - r2.best_fit) ** 2))
        a1, a2 = aicc_of(ss1, n, k1), aicc_of(ss2, n, k2)
        d = a2 - a1
        p1 = 1 / (1 + math.exp(-0.5 * d)) if math.isfinite(d) and abs(d) < 700 else (1.0 if d > 0 else 0.0)
        Ftxt = "—"
        if k1 != k2:
            (sa, ka), (sb, kb) = sorted([(ss1, k1), (ss2, k2)], key=lambda t: t[1])
            if n - kb > 0 and sb > 0:
                F = ((sa - sb) / (kb - ka)) / (sb / (n - kb))
                pf = float(st.f.sf(F, kb - ka, n - kb))
                Ftxt = f"F = {g(F, 4)}, P = {pv(pf)}"
        best = name1 if p1 >= 0.5 else name2
        prefer.append(f"{name_of(table, k)}: {best}")
        rows.append([name_of(table, k), f"{g(ss1)} / {g(ss2)}", f"{g(a1, 4)} / {g(a2, 4)}", f"{g(100 * p1, 3)}% / {g(100 * (1 - p1), 3)}%", Ftxt, best])
    tab = {"title": f"{name1} (1) against {name2} (2)", "columns": ["Data set", "Sum of squares 1 / 2", "AICc 1 / 2", "Probability correct 1 / 2", "F test (nested models)", "Preferred"], "rows": rows}
    return tab, "Preferred model: " + "; ".join(prefer) + "."


# ---------- Arrhenius (B28) ----------
def arrhenius(table, ks, o):
    import statsmodels.api as sm
    celsius, unit = o.get("tunit", "C") == "C", o.get("eunit", "kJ/mol")
    conv = {"kJ/mol": 1e-3, "eV": 1 / 96485.33212, "J/mol": 1.0, "kcal/mol": 1 / 4184}[unit]
    tabs, checks, plots, curves, answers = [], [], [], [], []
    for k in ks:
        T, kk, _ = points(table, k, o)
        T = T + 273.15 if celsius else T
        m = (T > 0) & (kk > 0)
        T, kk = T[m], kk[m]
        name = name_of(table, k)
        if len(T) < 3:
            checks.append((False, f"{name}: needs at least 3 positive rates at different temperatures.")); continue
        X, Y = 1 / T, np.log(kk)
        r = sm.OLS(Y, sm.add_constant(X)).fit()
        (a, b), (sa, sb) = r.params, r.bse
        t = st.t.ppf(0.975, r.df_resid)
        Ea, sEa = -b * R * conv, sb * R * conv
        A = math.exp(a)
        tabs.append({"title": name, "columns": ["", "Value", "Std. error", "95% CI"], "rows": [
            [f"Activation energy Ea ({unit})", g(Ea), g(sEa), f"{g(Ea - t * sEa)} to {g(Ea + t * sEa)}"],
            ["Pre-exponential factor A", g(A), "", f"{g(math.exp(a - t * sa))} to {g(math.exp(a + t * sa))}"],
            ["Slope of ln(k) against 1/T (K)", g(b), g(sb), ""], ["R squared", g(r.rsquared, 4), "", ""], ["Number of points", g(len(T)), "", ""]]})
        answers.append(f"{name}: Ea = {g(Ea, 4)} {unit} (95% CI {g(Ea - t * sEa, 4)} to {g(Ea + t * sEa, 4)}).")
        checks.append((r.rsquared > 0.98, f"{name}: the Arrhenius plot is {'straight' if r.rsquared > 0.98 else 'curved or scattered'} (R² = {g(r.rsquared, 4)})."))
        Ts = np.linspace(T.min(), T.max(), 200)
        curves.append({"set": k, "x": (Ts - 273.15 if celsius else Ts).tolist(), "y": (A * np.exp(-(-b) / Ts)).tolist(), "label": f"Ea = {g(Ea, 4)} {unit}"})
        plots.append(small_plot(f"Arrhenius plot · {name}", lambda ax, X=X, Y=Y, a=a, b=b, c=COLORS[k % 8]: (
            ax.plot(1000 * X, Y, "o", ms=3.5, color=c), ax.plot(1000 * np.sort(X), a + b * np.sort(X), color=c, lw=1), ax.set_xlabel("1000/T (1/K)"), ax.set_ylabel("ln(k)"))))
    return result("Arrhenius analysis", " ".join(answers) or "No fit.", [{"name": "Summary", "tables": tabs}], checks, plots=plots, curves=curves,
                  methods=f"Activation energies were obtained from a linear least-squares fit of ln(k) against 1/T (T in kelvin), Ea = −slope·R, R = 8.314 J/(mol·K), in Datum Plot.",
                  legend="Curves show k = A·exp(−Ea/RT) with the fitted Ea and A.",
                  code="import numpy as np, statsmodels.api as sm\nT = np.array([...]) + 273.15; k = np.array([...])\nr = sm.OLS(np.log(k), sm.add_constant(1 / T)).fit()\nEa = -r.params[1] * 8.314462618  # J/mol")


KINDS = {"describe": describe, "normality": normality, "outliers": outliers, "linear": linear, "fit": nonlinear, "arrhenius": arrhenius}


def more_kinds():
    """The analyses in groups.py and tools.py (imported here, as they use the helpers above)."""
    from . import groups, tools
    KINDS.update({"ttest": groups.ttest, "nonparam": groups.nonparam, "anova": groups.anova, "correlation": groups.correlation, "power": groups.power, "twoway": groups.twoway, "contingency": groups.contingency, "parts": groups.parts, "blandaltman": groups.blandaltman, "roc": groups.roc,
                  "transform": tools.transform, "check": tools.check, "frequency": tools.frequency, "auc": tools.auc, "smooth": tools.smooth, "tensile": tools.tensile, "weibull": tools.weibull})
    return KINDS


# Analyses that compare data sets: empty ones are left out (a new column table starts with three).
COMPARE = {"ttest", "nonparam", "anova", "correlation", "power", "blandaltman", "roc", "weibull", "describe", "normality", "outliers"}


def run(kind, table, sets, options):
    ks = chosen(table, sets)
    empty = [k for k in ks if kind in COMPARE and not values(table, k)]
    ks = [k for k in ks if k not in empty]
    if not ks:
        raise ValueError("Choose at least one data set." if not empty else "The chosen data sets have no values yet.")
    r = (KINDS if kind in KINDS else more_kinds())[kind](table, ks, options or {})
    if empty:
        r["checks"].append([None, f"Left out because {'it is' if len(empty) == 1 else 'they are'} empty: {', '.join(name_of(table, k) for k in empty)}."])
    return r


def model_list():
    return [[k, v[0], v[1], v[3]] for k, v in MODELS.items()]
