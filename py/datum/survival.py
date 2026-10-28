"""Survival (A5, B19, D9): a survival table has the time in X and, for each group (data set), 1 for
an event (death, failure) or 0 for censored (still going when the study ended) on that subject's row.
Kaplan-Meier curves with Greenwood log CIs (as R survfit), the log-rank test (R survdiff) and Cox
hazard ratios (R coxph, Efron ties)."""
import math

import numpy as np
from scipy import stats as st

from . import stats
from .analysis import ALPHA, COLORS, g, name_of, pv, result, small_plot

Z95 = 1.959963984540054


def subjects(table, k):
    """(times, events) of group k: rows with a time and 1 (event) or 0 (censored)."""
    ex = {tuple(e) for e in table.get("excluded", [])}
    c0 = stats.set_columns(table)[k][0]
    t, e = [], []
    for r in range(table["rows"]):
        x, v = stats.value(table, r, 0, ex), stats.value(table, r, c0, ex)
        if x is not None and v is not None and math.isfinite(x) and v in (0.0, 1.0) and x >= 0:
            t.append(x); e.append(int(v))
    return np.array(t, float), np.array(e, int)


def km(t, e):
    """Kaplan-Meier: one row per distinct time with an event or a censoring: (time, at risk, events, censored, S, SE, low, high)."""
    out, s, gw = [], 1.0, 0.0
    for u in np.unique(t):
        n, d, c = int((t >= u).sum()), int(((t == u) & (e == 1)).sum()), int(((t == u) & (e == 0)).sum())
        if d:
            s *= 1 - d / n
            gw += d / (n * (n - d)) if n > d else math.inf
        se = s * math.sqrt(gw) if math.isfinite(gw) else 0.0
        if s > 0 and math.isfinite(gw):
            w = Z95 * math.sqrt(gw)
            lo, hi = s * math.exp(-w), min(1.0, s * math.exp(w))
        else:
            lo, hi = s, (s if s > 0 else float("nan"))  # no upper limit once the curve reaches zero (R: NA)
        out.append((float(u), n, d, c, s, se, lo, hi))
    return out


def median(rows, col=4):
    """The first time the curve (or a CI limit) reaches 0.5 or less; halfway to the next event time when it sits exactly at 0.5 (as R)."""
    ev = [r for r in rows if r[2] > 0]
    for i, r in enumerate(ev):
        if r[col] <= 0.5 + 1e-12:
            if abs(r[col] - 0.5) < 1e-12 and col == 4 and i + 1 < len(ev):
                return (r[0] + ev[i + 1][0]) / 2
            return r[0]
    return None


def logrank(groups):
    """Log-rank (Mantel-Cox) test of k groups [(t, e)]: (chi², df, P, observed, expected)."""
    times = np.unique(np.concatenate([t[e == 1] for t, e in groups]))
    k = len(groups)
    O, E, V = np.zeros(k), np.zeros(k), np.zeros((k, k))
    for u in times:
        n = np.array([(t >= u).sum() for t, _ in groups], float)
        d = np.array([((t == u) & (e == 1)).sum() for t, e in groups], float)
        N, D = n.sum(), d.sum()
        if N < 1:
            continue
        O += d
        E += D * n / N
        if N > 1:
            f = D * (N - D) / (N * N * (N - 1))
            V += f * (np.diag(n * N) - np.outer(n, n))
    x = (O - E)[:-1]
    try:
        chi = float(x @ np.linalg.solve(V[:-1, :-1], x))
    except np.linalg.LinAlgError:
        chi = float("nan")
    return chi, k - 1, float(st.chi2.sf(chi, k - 1)) if math.isfinite(chi) else float("nan"), O, E


def survival(table, ks, o):
    alpha = float(o.get("alpha", ALPHA))
    groups = [(k, *subjects(table, k)) for k in ks]
    groups = [x for x in groups if len(x[1])]
    if not groups:
        raise ValueError("Enter a time in X and 1 (event) or 0 (censored) in a group's column on each subject's row.")
    unit = table.get("xUnits") or ""
    tu = lambda v: "not reached" if v is None else f"{g(v, 4)}{' ' + unit if unit else ''}"
    summ, curves, details, ans = [], {}, [], []
    for k, t, e in groups:
        rows = km(t, e)
        curves[k] = rows
        med, lo, hi = median(rows), median(rows, 6), median(rows, 7)
        summ.append([name_of(table, k), g(len(t)), g(int(e.sum())), g(int(len(t) - e.sum())), tu(med), f"{'—' if lo is None else g(lo, 4)} to {'—' if hi is None else g(hi, 4)}"])
        details.append({"title": name_of(table, k), "columns": ["Time", "At risk", "Events", "Censored", "Survival", "Std. error", "95% CI"],
                        "rows": [[g(r[0]), g(r[1]), g(r[2]), g(r[3]), g(r[4], 4), g(r[5], 3), f"{g(r[6], 3)} to {g(r[7], 3)}"] for r in rows]})
        ans.append(f"{name_of(table, k)}: median {tu(med)}")
    tables = [{"title": "Survival", "columns": ["Group", "Subjects", "Events", "Censored", "Median survival", "95% CI of median"], "rows": summ}]
    checks = [(None, "Censored subjects (0) count while they are followed and then leave the risk set; that assumes their leaving has nothing to do with their chance of the event.")]
    answer = "; ".join(ans) + "."
    methods = f"Survival was estimated by the Kaplan-Meier method (Greenwood 95% CIs on the log scale)"
    if len(groups) > 1:
        chi, df, p, O, E = logrank([(t, e) for _, t, e in groups])
        tables.append({"title": "Log-rank (Mantel-Cox) test", "columns": ["", "Value"], "rows": [["Chi-square", g(chi, 5)], ["DF", g(df)], ["P value", pv(p)],
                       ["Curves differ (α = " + f"{alpha:g})", "Yes" if p < alpha else "No"]] + [[f"Observed / expected events, {name_of(table, k)}", f"{g(O[i])} / {g(E[i], 4)}"] for i, (k, _, _) in enumerate(groups)]})
        answer += f" The curves {'differ' if p < alpha else 'do not differ significantly'} (log-rank χ² = {g(chi, 4)}, P {pv(p) if p < 1e-4 else '= ' + pv(p)})."
        methods += f", and the curves were compared with the log-rank (Mantel-Cox) test"
        try:
            from statsmodels.duration.hazard_regression import PHReg
            tt = np.concatenate([t for _, t, _ in groups]); ee = np.concatenate([e for _, _, e in groups])
            X = np.zeros((len(tt), len(groups) - 1)); i0 = len(groups[0][1])
            for j, (_, t, _) in enumerate(groups[1:]):
                X[i0:i0 + len(t), j] = 1; i0 += len(t)
            f = PHReg(tt, X, status=ee, ties="efron").fit()
            ci = f.conf_int()
            ref = name_of(table, groups[0][0])
            tables.append({"title": f"Hazard ratios (Cox, against {ref})", "columns": ["Group", "Hazard ratio", "95% CI", "P value"],
                           "rows": [[name_of(table, k), g(math.exp(f.params[j]), 4), f"{g(math.exp(ci[j][0]), 4)} to {g(math.exp(ci[j][1]), 4)}", pv(f.pvalues[j])] for j, (k, _, _) in enumerate(groups[1:])]})
            if len(groups) == 2:
                answer += f" Hazard ratio {name_of(table, groups[1][0])} vs {ref}: {g(math.exp(f.params[0]), 3)} (95% CI {g(math.exp(ci[0][0]), 3)} to {g(math.exp(ci[0][1]), 3)})."
            methods += "; hazard ratios come from a Cox proportional hazards model (Efron ties)"
        except Exception:
            pass
    for k, t, e in groups:
        if e.sum() == 0:
            checks.append((False, f"{name_of(table, k)} has no events, so its curve stays at 100% and its median is not reached."))

    def draw(ax):
        for i, (k, t, e) in enumerate(groups):
            xs, ys = steps(curves[k])
            ax.plot(xs, ys, color=COLORS[i % 8], lw=1, drawstyle="steps-post")
        ax.set_ylim(0, 105); ax.set_xlabel(table.get("xTitle") or "Time"); ax.set_ylabel("% survival")
    return result("Survival analysis", answer, [{"name": "Summary", "tables": tables}, {"name": "Survival tables", "tables": details}], checks,
                  plots=[small_plot("Kaplan-Meier curves", draw)], legend="Kaplan-Meier survival curves; ticks mark censored subjects.",
                  methods=methods + " in Datum Plot (SciPy, statsmodels).",
                  code="from statsmodels.duration.survfunc import SurvfuncRight, survdiff\nprint(SurvfuncRight(time, status).summary(), survdiff(time, status, group))")


def steps(rows):
    """The curve's corners in percent, starting at 100 % at time 0."""
    xs, ys = [0.0], [100.0]
    for r in rows:
        xs.append(r[0]); ys.append(100 * r[4])
    return xs, ys
