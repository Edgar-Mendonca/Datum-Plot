"""Control charts and design of experiments (B35).

Control charts, in time order (rows):
  imr  — individuals and moving range: the first data set's values, one per row;
  xbar — X̄ and R (subgroups up to 10) or X̄ and S charts: each row a subgroup, its values in the sub-columns;
  p    — proportion defective: per row, the first data set holds defectives and the second the number inspected.
Limits are the mean ± 3σ (σ from the ranges or SDs within subgroups, as in ASTM E2587); points beyond the limits
and runs of 8 on one side of the centre are flagged; with specification limits, Cp and Cpk are given.

Design of experiments: a table of many variables whose last variable is the response and the others the
factors (coded −1/+1, or any two levels, which are coded). Effects and their t tests from the model with all
two-factor interactions; without replicates (no residual degrees of freedom), Lenth's pseudo standard error."""
import math

import numpy as np
import scipy.stats as st

from . import stats
from .analysis import COLORS, g, name_of, pv, result, small_plot

# Control chart constants for subgroup size n (d2, d3: ASTM E2587 / Montgomery Table VI).
D2 = {2: 1.128, 3: 1.693, 4: 2.059, 5: 2.326, 6: 2.534, 7: 2.704, 8: 2.847, 9: 2.970, 10: 3.078}
D3 = {2: 0.853, 3: 0.888, 4: 0.880, 5: 0.864, 6: 0.848, 7: 0.833, 8: 0.820, 9: 0.808, 10: 0.797}


def c4(n):
    return math.sqrt(2 / (n - 1)) * math.exp(math.lgamma(n / 2) - math.lgamma((n - 1) / 2))


def rows_of(table, k):
    """Each row's values of data set k (sub-columns), excluded and empty cells left out."""
    ex = {tuple(e) for e in table.get("excluded", [])}
    c0, w = stats.set_columns(table)[k]
    out = []
    for r in range(table["rows"]):
        v = [x for x in (stats.value(table, r, c, ex) for c in range(c0, c0 + w)) if x is not None and math.isfinite(x)]
        out.append(v)
    return out


def flags(x, centre, lo, hi):
    """Indices beyond the limits, and the ends of runs of 8 or more on one side of the centre."""
    out = [i for i, v in enumerate(x) if (hi is not None and v > hi) or (lo is not None and v < lo)]
    run, side = 0, 0
    runs = []
    for i, v in enumerate(x):
        s = 1 if v > centre else -1 if v < centre else 0
        run = run + 1 if s == side and s != 0 else (1 if s != 0 else 0)
        side = s
        if run == 8:
            runs.append(i)
    return out, runs


def chart(title, ylab, x, centre, lo, hi, bad, runs):
    def draw(ax):
        i = np.arange(1, len(x) + 1)
        ax.plot(i, x, "-", color="#8A96A3", lw=0.8)
        ax.plot(i, x, "o", color=COLORS[0], ms=3)
        if bad:
            ax.plot(i[bad], np.asarray(x)[bad], "o", color="#D55E00", ms=5, label="Beyond the limits")
        if runs:
            ax.plot(i[runs], np.asarray(x)[runs], "s", mfc="none", mec="#D55E00", ms=6, label="8 in a row on one side")
        for v, ls in ((centre, "-"), (lo, "--"), (hi, "--")):
            if v is not None:
                ax.axhline(v, color="#333333" if ls == "-" else "#D55E00", lw=0.8, ls=ls)
                ax.annotate(g(v, 4), (len(x) + 0.5, v), fontsize=6, va="center", annotation_clip=False)
        ax.set_xlabel("Sample")
        ax.set_ylabel(ylab)
        from matplotlib.ticker import MaxNLocator
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))  # samples are whole numbers
        if bad or runs:
            ax.legend(fontsize=6, frameon=False, loc="best")
    return small_plot(title, draw, 120, 55)


def control(table, ks, o):
    kind = o.get("chart", "imr")
    lsl, usl = (float(o[k]) if str(o.get(k, "")).strip() not in ("", "None") else None for k in ("lsl", "usl"))
    plots, limits, checks, sigma, mean_all = [], [], [], None, None
    if kind == "imr":
        x = np.array([v for row in rows_of(table, ks[0]) for v in row], float)
        if len(x) < 5:
            raise ValueError("An individuals chart needs at least five values in time order.")
        mr = np.abs(np.diff(x))
        mrbar, xbar = mr.mean(), x.mean()
        sigma, mean_all = mrbar / D2[2], xbar
        lo, hi = xbar - 3 * sigma, xbar + 3 * sigma
        bad, runs = flags(x, xbar, lo, hi)
        mbad, _ = flags(mr, mrbar, None, 3.267 * mrbar)
        plots += [chart("Individuals", name_of(table, ks[0]), x, xbar, lo, hi, bad, runs), chart("Moving range", "Moving range", mr, mrbar, None, 3.267 * mrbar, mbad, [])]
        limits = [["Individuals", g(xbar, 5), g(lo, 5), g(hi, 5)], ["Moving range", g(mrbar, 5), "0", g(3.267 * mrbar, 5)]]
        name, n_out = "Individuals and moving range", len(bad) + len(mbad)
    elif kind in ("xbar", "xbar_s"):
        groups = [r for r in rows_of(table, ks[0]) if r]
        sizes = {len(r) for r in groups}
        if len(groups) < 5 or min(sizes) < 2:
            raise ValueError("X̄ charts need at least five subgroups (rows), each with two or more values in the sub-columns.")
        if len(sizes) > 1:
            raise ValueError(f"Every subgroup needs the same number of values (found {sorted(sizes)}); exclude or fill values so they match.")
        n = sizes.pop()
        m = np.array([np.mean(r) for r in groups])
        xbb = m.mean()
        use_s = kind == "xbar_s" or n > 10
        if use_s:
            s = np.array([np.std(r, ddof=1) for r in groups])
            sbar = s.mean()
            sigma = sbar / c4(n)
            b = 3 * math.sqrt(1 - c4(n) ** 2) / c4(n)
            slo, shi = max(0.0, sbar * (1 - b)), sbar * (1 + b)
            spread, sname, sc, slo_, shi_ = s, "S", sbar, slo, shi
        else:
            rr = np.array([max(r) - min(r) for r in groups])
            rbar = rr.mean()
            sigma = rbar / D2[n]
            rlo, rhi = max(0.0, rbar * (1 - 3 * D3[n] / D2[n])), rbar * (1 + 3 * D3[n] / D2[n])
            spread, sname, sc, slo_, shi_ = rr, "R", rbar, rlo, rhi
        lo, hi = xbb - 3 * sigma / math.sqrt(n), xbb + 3 * sigma / math.sqrt(n)
        bad, runs = flags(m, xbb, lo, hi)
        sbad, _ = flags(spread, sc, slo_, shi_)
        plots += [chart("X̄ (subgroup means)", name_of(table, ks[0]), m, xbb, lo, hi, bad, runs), chart(f"{sname} (subgroup {'SDs' if sname == 'S' else 'ranges'})", sname, spread, sc, slo_, shi_, sbad, [])]
        limits = [["X̄", g(xbb, 5), g(lo, 5), g(hi, 5)], [sname, g(sc, 5), g(slo_, 5), g(shi_, 5)]]
        name, n_out, mean_all = f"X̄ and {sname} (subgroups of {n})", len(bad) + len(sbad), xbb
        if n > 10 and kind == "xbar":
            checks.append((None, "Subgroups larger than 10 use the S chart instead of the R chart."))
    elif kind == "p":
        if len(ks) < 2:
            raise ValueError("A p chart needs two data sets: the number defective and the number inspected in each row.")
        d = [sum(r) for r in rows_of(table, ks[0])]
        nn = [sum(r) for r in rows_of(table, ks[1])]
        pairs = [(a, b) for a, b in zip(d, nn) if b > 0]
        if len(pairs) < 5 or any(a < 0 or a > b for a, b in pairs):
            raise ValueError("A p chart needs at least five rows with 0 ≤ defective ≤ inspected.")
        p = np.array([a / b for a, b in pairs])
        sizes = np.array([b for _, b in pairs], float)
        pbar = sum(a for a, _ in pairs) / sizes.sum()
        se = np.sqrt(pbar * (1 - pbar) / sizes)
        lo_i, hi_i = np.maximum(0, pbar - 3 * se), np.minimum(1, pbar + 3 * se)
        bad = [i for i in range(len(p)) if p[i] > hi_i[i] or p[i] < lo_i[i]]
        _, runs = flags(p, pbar, None, None)
        lo, hi = (float(lo_i[0]), float(hi_i[0])) if len(set(sizes)) == 1 else (None, None)
        def draw(ax):
            i = np.arange(1, len(p) + 1)
            ax.plot(i, p, "-o", color=COLORS[0], ms=3, lw=0.8)
            ax.step(i, hi_i, where="mid", color="#D55E00", lw=0.8, ls="--")
            ax.step(i, lo_i, where="mid", color="#D55E00", lw=0.8, ls="--")
            ax.axhline(pbar, color="#333333", lw=0.8)
            if bad:
                ax.plot(i[bad], p[bad], "o", color="#D55E00", ms=5)
            ax.set_xlabel("Sample")
            ax.set_ylabel("Proportion defective")
        plots.append(small_plot("p chart", draw, 120, 55))
        limits = [["p", g(pbar, 4), g(lo, 4) if lo is not None else "varies with n", g(hi, 4) if hi is not None else "varies with n"]]
        name, n_out = "p chart", len(bad)
    else:
        raise ValueError("Choose a chart: individuals, X̄ and R, X̄ and S, or p.")
    tabs = [{"title": "Control limits (3σ)", "columns": ["Chart", "Centre line", "Lower limit", "Upper limit"], "rows": limits}]
    cap = ""
    if sigma and (lsl is not None or usl is not None):
        rows = []
        if lsl is not None and usl is not None:
            rows.append(["Cp", g((usl - lsl) / (6 * sigma), 3)])
        parts = ([(usl - mean_all) / (3 * sigma)] if usl is not None else []) + ([(mean_all - lsl) / (3 * sigma)] if lsl is not None else [])
        cpk = min(parts)
        rows += [["Cpk", g(cpk, 3)], ["σ (within)", g(sigma, 4)]]
        tabs.append({"title": "Process capability", "columns": ["", "Value"], "rows": rows})
        cap = f" Cpk = {g(cpk, 3)} ({'capable' if cpk >= 1.33 else 'marginal' if cpk >= 1 else 'not capable'})."
    if runs:
        checks.append((False, f"{len(runs)} run{'s' if len(runs) > 1 else ''} of 8 points on one side of the centre line: the process mean may have shifted."))
    if n_out:
        state = f"{n_out} point{'s' if n_out != 1 else ''} beyond the limits"
    else:
        state = "within the limits, but with a run on one side" if runs else "in control"
    ans = f"{name}: {state}.{cap}"
    return result("Control chart", ans, [{"name": "Summary", "tables": tabs}], checks, plots=plots,
                  methods=f"A {name.lower()} chart was drawn with 3σ limits (σ estimated within subgroups), flagging points beyond the limits and runs of 8 on one side of the centre line, in Datum Plot (NumPy).",
                  code="import numpy as np\nmr = np.abs(np.diff(x)); sigma = mr.mean() / 1.128\nlimits = x.mean() - 3 * sigma, x.mean() + 3 * sigma")


# ---------- design of experiments ----------
def doe(table, ks, o):
    """Effects of two-level factors (all variables but the last) on the response (the last variable)."""
    import pandas as pd
    import statsmodels.formula.api as smf
    from itertools import combinations
    ex = {tuple(e) for e in table.get("excluded", [])}
    spans = stats.set_columns(table)
    if len(spans) < 3:
        raise ValueError("A factorial design needs at least two factor columns and a response (the last column).")
    names = [s.get("title") or f"Variable {chr(65 + k)}" for k, s in enumerate(table["sets"])]
    rows = []
    for r in range(table["rows"]):
        v = [stats.value(table, r, c0, ex) for c0, _ in spans]
        if all(x is not None and math.isfinite(x) for x in v):
            rows.append(v)
    if len(rows) < 4:
        raise ValueError("A factorial design needs at least four runs with every factor and the response filled in.")
    V = np.array(rows, float)
    F, y = V[:, :-1], V[:, -1]
    coded = np.zeros_like(F)
    for j in range(F.shape[1]):
        lv = np.unique(F[:, j])
        lo, hi = lv.min(), lv.max()
        if lo == hi:
            raise ValueError(f"The factor “{names[j]}” has only one level.")
        mid = (lo + hi) / 2
        if not np.all(np.isclose(F[:, j], lo) | np.isclose(F[:, j], hi) | np.isclose(F[:, j], mid)):
            raise ValueError(f"The factor “{names[j]}” has more than two levels (and centre points); a two-level design is needed.")
        coded[:, j] = (F[:, j] - mid) / ((hi - lo) / 2)
    k = F.shape[1]
    letters = [f"X{j + 1}" for j in range(k)]
    df = pd.DataFrame(coded, columns=letters).assign(y=y)
    terms = letters + [f"{a}:{b}" for a, b in combinations(letters, 2)]
    while len(terms) + 1 > len(df):  # too few runs for every interaction: drop the last ones
        terms.pop()
    m = smf.ols("y ~ " + " + ".join(terms), data=df).fit()
    label = lambda t: " × ".join(names[letters.index(x)] for x in t.split(":"))
    eff = {t: 2 * float(m.params[t]) for t in terms}
    if m.df_resid >= 1:
        se = {t: 2 * float(m.bse[t]) for t in terms}
        p = {t: float(m.pvalues[t]) for t in terms}
        how, df_t = "t tests on the residual", m.df_resid
    else:  # Lenth's method for unreplicated designs
        a = np.abs(list(eff.values()))
        s0 = 1.5 * np.median(a)
        pse = 1.5 * np.median(a[a < 2.5 * s0]) if np.any(a < 2.5 * s0) else s0
        df_t = len(a) / 3
        se = {t: pse for t in terms}
        p = {t: 2 * float(st.t.sf(abs(eff[t]) / pse, df_t)) if pse > 0 else float("nan") for t in terms}
        how = "Lenth's pseudo standard error (no replicates)"
    order = sorted(terms, key=lambda t: -abs(eff[t] / se[t]) if se[t] > 0 else 0)
    tab = [[label(t), g(eff[t], 4), g(se[t], 3), g(eff[t] / se[t], 4) if se[t] > 0 else "", pv(p[t])] for t in order]
    crit = float(st.t.ppf(0.975, df_t))
    def pareto(ax):
        vals = [abs(eff[t] / se[t]) if se[t] > 0 else 0 for t in order][::-1]
        ax.barh(range(len(vals)), vals, color=[COLORS[0] if v > crit else "#B8C0CA" for v in vals])
        ax.set_yticks(range(len(vals)), [label(t) for t in order][::-1], fontsize=6)
        ax.axvline(crit, color="#D55E00", lw=0.8, ls="--")
        ax.set_xlabel("|Standardised effect|")
    def mains(ax):
        for j in range(k):
            lo_, hi_ = y[coded[:, j] < 0].mean(), y[coded[:, j] > 0].mean()
            ax.plot([j * 1.5, j * 1.5 + 1], [lo_, hi_], "-o", color=COLORS[j % 8], ms=3)
        ax.set_xticks([j * 1.5 + 0.5 for j in range(k)], names[:k], fontsize=6)
        ax.axhline(y.mean(), color="#B8C0CA", lw=0.6, ls=":")
        ax.set_ylabel(f"Mean {names[-1]}")
    plots = [small_plot("Pareto chart of the effects", pareto, 100, 60), small_plot("Main effects (low → high)", mains, 100, 55)]
    sig = [label(t) for t in order if p[t] < 0.05]
    ans = (f"Significant effects on {names[-1]}: " + ", ".join(sig) + "." if sig else f"No factor has a significant effect on {names[-1]} (P < 0.05).") + f" Largest: {label(order[0])} (effect {g(eff[order[0]], 4)})."
    return result("Factorial design", ans, [{"name": "Summary", "tables": [{"title": f"Effects (high − low), by size ({how})", "columns": ["Term", "Effect", "SE", "t", "P value"], "rows": tab},
                                                                        {"title": "Model", "columns": ["", "Value"], "rows": [["Runs", str(len(y))], ["Factors", str(k)], ["R²", g(m.rsquared, 4) if m.df_resid >= 1 else "saturated"]]}]}],
                  [(None, f"Factors coded −1 (low) and +1 (high); {len(terms) - k} two-factor interactions in the model.")], plots=plots,
                  methods=f"A two-level factorial design ({k} factors, {len(y)} runs) was analysed with main effects and two-factor interactions; effects were tested by {how}, in Datum Plot (statsmodels).",
                  code="import statsmodels.formula.api as smf\nm = smf.ols('y ~ (X1 + X2 + X3) ** 2', data=df).fit()\nprint(2 * m.params)")
