"""Many variables (B21): multiple linear, logistic and Poisson regression on a table with one row per
sample and one data set per variable. Every function has the analysis signature (table, ks, options)."""
import math

import numpy as np
from scipy import stats as st

from . import stats
from .analysis import ALPHA, COLORS, g, name_of, pv, result, small_plot

MODELS = {"linear": "Multiple linear regression", "logistic": "Logistic regression", "poisson": "Poisson regression"}


def xy_view(table):
    """A table of many variables seen as an XY table: the first variable is X (for graphs and XY analyses)."""
    t = dict(table, kind="xy", fromMulti=True, xTitle=name_of(table, 0) if table["sets"] else "X")
    t["cols"] = [table["cols"][1] if len(table["cols"]) > 1 else []] + table["cols"][1:]
    t["excluded"] = list(table.get("excluded", [])) + [[r, 0] for r, c in table.get("excluded", []) if c == 1]
    return t


def frame(table, y, xs):
    """Rows where the outcome and every predictor have a value: (Y, X matrix, row indices, rows left out)."""
    ex = {tuple(e) for e in table.get("excluded", [])}
    cols = stats.set_columns(table)
    rows, out = [], 0
    for r in range(table["rows"]):
        v = [stats.value(table, r, cols[k][0], ex) for k in [y, *xs]]
        if all(a is not None and math.isfinite(a) for a in v):
            rows.append((r, v))
        elif any(a is not None for a in v):
            out += 1
    a = np.array([v for _, v in rows], float).reshape(-1, len(xs) + 1)
    return a[:, 0], a[:, 1:], [r for r, _ in rows], out


def multireg(table, ks, o):
    import statsmodels.api as sm
    model, alpha = o.get("model", "linear"), float(o.get("alpha", ALPHA))
    y = int(o.get("y", 0))
    xs = [k for k in ks if k != y]
    if not 0 <= y < len(table["sets"]):
        raise ValueError("Choose the outcome (Y) variable.")
    if not xs:
        raise ValueError("Choose at least one predictor besides the outcome.")
    yv, X, _, left = frame(table, y, xs)
    n, p = len(yv), len(xs)
    if n < p + 2:
        raise ValueError(f"Too few complete rows: {n} for {p} predictor{'s' * (p > 1)} (need at least {p + 2}).")
    yn, names = name_of(table, y), [name_of(table, k) for k in xs]
    if model == "logistic" and not np.all(np.isin(yv, (0, 1))):
        raise ValueError(f"Logistic regression needs an outcome of 0 and 1 ({yn} has other values).")
    if model == "poisson" and (np.any(yv < 0) or np.any(yv != np.round(yv))):
        raise ValueError(f"Poisson regression needs counts (whole numbers ≥ 0) as the outcome ({yn} has other values).")
    D = sm.add_constant(X, has_constant="add")
    checks = []
    if model == "linear":
        f = sm.OLS(yv, D).fit()
    else:
        fam = sm.families.Binomial() if model == "logistic" else sm.families.Poisson()
        try:
            f = sm.GLM(yv, D, family=fam).fit()
        except Exception as e:  # perfect separation and similar
            raise ValueError(f"The model cannot be fitted: {e}. A predictor may separate the outcomes perfectly.")
    lin, q = model == "linear", st.t.ppf(1 - alpha / 2, f.df_resid) if model == "linear" else st.norm.ppf(1 - alpha / 2)
    lo, hi = f.params - q * f.bse, f.params + q * f.bse
    terms = ["Intercept", *names]
    pct = f"{100 * (1 - alpha):g}%"
    cols = ["Term", "Estimate", "Std. error", "t" if lin else "z", "P value", f"{pct} CI"]
    rows = [[terms[i], g(f.params[i]), g(f.bse[i], 4), g(f.tvalues[i], 4), pv(f.pvalues[i]), f"{g(lo[i], 4)} to {g(hi[i], 4)}"] for i in range(p + 1)]
    if lin and p > 1:
        from statsmodels.stats.outliers_influence import variance_inflation_factor as vif
        v = [vif(D, i) for i in range(1, p + 1)]
        cols.append("VIF")
        rows = [r + (["—"] if i == 0 else [g(v[i - 1], 3)]) for i, r in enumerate(rows)]
        big = [names[i] for i in range(p) if v[i] > 10]
        checks.append((not big, f"Predictors {'overlap strongly (VIF > 10): ' + ', '.join(big) if big else 'do not overlap much (every VIF ≤ 10)'}."))
    if not lin:
        word = "Odds ratio" if model == "logistic" else "Rate ratio"
        cols.append(f"{word} ({pct} CI)")
        rows = [r + (["—"] if i == 0 else [f"{g(math.exp(f.params[i]), 4)} ({g(math.exp(lo[i]), 4)} to {g(math.exp(hi[i]), 4)})"]) for i, r in enumerate(rows)]
    pred = f.fittedvalues if lin else f.mu
    res = yv - pred
    if lin:
        aic = -2 * f.llf + 2 * (p + 2)  # as R's AIC(lm): the residual SD counts as a parameter
        fit_rows = [["Number of rows", g(n)], ["R squared", g(f.rsquared, 4)], ["Adjusted R squared", g(f.rsquared_adj, 4)], ["F", f"{g(f.fvalue, 5)} (DFn = {p}, DFd = {g(f.df_resid)})"],
                    ["P value", pv(f.f_pvalue)], ["Residual SD (Sy.x)", g(math.sqrt(f.scale), 5)], ["AIC", g(aic, 5)]]
        ans = f"R² = {g(f.rsquared, 3)}: the {p} predictor{'s' * (p > 1)} explain {100 * f.rsquared:.0f}% of the variation in {yn} (F = {g(f.fvalue, 4)}, P {pv(f.f_pvalue) if f.f_pvalue < 1e-4 else '= ' + pv(f.f_pvalue)})."
        if n >= 3:
            sw = st.shapiro(res)[1] if n <= 5000 else None
            if sw is not None:
                checks.append((sw >= 0.05, f"Residuals {'pass' if sw >= 0.05 else 'fail'} the Shapiro-Wilk normality test (P = {pv(sw)})."))
    else:
        lr = f.null_deviance - f.deviance
        plr = st.chi2.sf(lr, p)
        fit_rows = [["Number of rows", g(n)], ["Null deviance", f"{g(f.null_deviance, 5)} (DF = {n - 1})"], ["Residual deviance", f"{g(f.deviance, 5)} (DF = {g(f.df_resid)})"],
                    ["Likelihood ratio χ²", f"{g(lr, 5)} (DF = {p})"], ["P value", pv(plr)], ["Pseudo R² (McFadden)", g(1 - f.llf / f.llnull, 4)], ["AIC", g(f.aic, 5)]]
        ans = f"The {p} predictor{'s' * (p > 1)} {'improve' if plr < alpha else 'do not significantly improve'} the prediction of {yn} (likelihood ratio χ² = {g(lr, 4)}, P {pv(plr) if plr < 1e-4 else '= ' + pv(plr)})."
        if model == "logistic":
            hit = float(np.mean((pred >= 0.5) == (yv == 1)))
            fit_rows.append(["Correctly classified (at 0.5)", f"{100 * hit:.1f}%"])
        else:
            disp = float(np.sum(res ** 2 / pred) / f.df_resid) if f.df_resid > 0 else float("nan")
            fit_rows.append(["Dispersion (Pearson χ² / DF)", g(disp, 4)])
            checks.append((disp <= 1.5, f"Dispersion {g(disp, 3)}: {'the counts vary as a Poisson model expects' if disp <= 1.5 else 'the counts vary more than a Poisson model expects (overdispersion), so P values are too small'}."))
    sig = [names[i] for i in range(p) if f.pvalues[i + 1] < alpha]
    ans += f" Significant predictors: {', '.join(sig)}." if sig else " No single predictor is significant."
    if n < 10 * p:
        checks.append((False, f"{n} rows for {p} predictors: fewer than ten per predictor, so the estimates may be unstable."))
    if left:
        checks.append((None, f"{left} row{'s' * (left > 1)} with a missing value {'were' if left > 1 else 'was'} left out."))
    c = COLORS[0]
    plots = [small_plot(f"Predicted vs actual {yn}"[:40], lambda ax: (ax.plot(pred, yv, "o", ms=3.2, color=c), ax.axline((float(np.mean(yv)),) * 2, slope=1, color="#8D9AAB", lw=0.8) if lin else None,
                                                                     ax.set_xlabel("Predicted"), ax.set_ylabel("Actual"))),
             small_plot("Residuals", lambda ax: (ax.axhline(0, color="#8D9AAB", lw=0.8), ax.plot(pred, res, "o", ms=3.2, color=c), ax.set_xlabel("Predicted"), ax.set_ylabel("Residual")))]
    eq = " + ".join(names)
    how = {"linear": "ordinary least squares", "logistic": "maximum likelihood (logit link)", "poisson": "maximum likelihood (log link)"}[model]
    code = {"linear": "sm.OLS(y, sm.add_constant(X)).fit()", "logistic": "sm.GLM(y, sm.add_constant(X), family=sm.families.Binomial()).fit()",
            "poisson": "sm.GLM(y, sm.add_constant(X), family=sm.families.Poisson()).fit()"}[model]
    return result(MODELS[model], ans, [{"name": "Summary", "tables": [{"title": f"{yn} ~ {eq}", "columns": cols, "rows": rows}, {"title": "Goodness of fit", "columns": ["", "Value"], "rows": fit_rows}]}],
                  checks, plots=plots, legend=f"{MODELS[model]} of {yn} on {eq} (n = {n}).",
                  methods=f"{MODELS[model]} of {yn} on {eq} was fitted by {how} in Datum Plot (statsmodels), using the {n} rows with every value; {'t' if lin else 'Wald'} {pct} confidence intervals, α = {alpha:g}.",
                  code=f"import statsmodels.api as sm\nprint({code}.summary())")
