"""More statistics (B34): three-way ANOVA, ANCOVA, agreement of paired ratings (Cohen's kappa, McNemar and
Bowker tests) and bootstrap confidence intervals. Spline fits are a method of Smooth (tools.smooth)."""
import math
from itertools import combinations

import numpy as np
import scipy.stats as st

from . import stats
from .analysis import ALPHA, COLORS, g, name_of, points, pv, result, values
from .groups import adjust, cells, ci_text, p_text


# ---------- three-way ANOVA ----------
def threeway(table, ks, o):
    """A grouped table: rows are factor A; each data set is a combination of factors B and C, titled "b / c"
    (for example "Young / Drug"); replicates in its sub-columns. Type III sums of squares."""
    import pandas as pd
    import statsmodels.formula.api as smf
    from statsmodels.stats.anova import anova_lm
    alpha = float(o.get("alpha", ALPHA))
    if any(table["sets"][k]["entry"] != "rep" for k in ks):
        raise ValueError("Three-way ANOVA needs the individual values; enter them as replicates.")
    parts = {}
    for k in ks:
        t = [p.strip() for p in name_of(table, k).split("/")]
        if len(t) != 2 or not all(t):
            raise ValueError(f"Name each data set by two factor levels separated by “/”, for example “Young / Drug” (“{name_of(table, k)}” is not).")
        parts[k] = t
    rows, cv = cells(table)
    data = [(lab, parts[k][0], parts[k][1], v) for r, lab in rows for k in ks for v in cv.get((k, r), [])]
    df = pd.DataFrame(data, columns=["Fa", "Fb", "Fc", "y"])  # not "C": that would hide the formula's C()
    if min(df.Fa.nunique(), df.Fb.nunique(), df.Fc.nunique()) < 2:
        raise ValueError("Each factor needs at least two levels: two or more rows, and data sets covering two levels of each of the other two factors.")
    full = df.groupby(["Fa", "Fb", "Fc"]).size()
    if len(full) < df.Fa.nunique() * df.Fb.nunique() * df.Fc.nunique():
        raise ValueError("Every combination of the three factors needs values (some row and data set pairs are empty).")
    inter3 = full.min() > 1
    f = "y ~ C(Fa, Sum) * C(Fb, Sum) * C(Fc, Sum)" if inter3 else "y ~ (C(Fa, Sum) + C(Fb, Sum) + C(Fc, Sum)) ** 2"
    m = smf.ols(f, data=df).fit()
    a = anova_lm(m, typ=3)
    names = {"Fa": o.get("rowname") or "Row factor", "Fb": o.get("bname") or "Factor B", "Fc": o.get("cname") or "Factor C"}
    def label(key):
        fs = [x[2:4] for x in key.split(":")]  # "C(Fa, Sum):C(Fb, Sum)" → Fa, Fb
        return " × ".join(names[x] for x in fs)
    res_ss, res_df = float(a.loc["Residual", "sum_sq"]), float(a.loc["Residual", "df"])
    tab, ans, eta = [], [], []
    keys = [k for k in a.index if k not in ("Intercept", "Residual")]
    keys.sort(key=lambda k: k.count(":"))
    for key in keys:
        ss, d, F, p = float(a.loc[key, "sum_sq"]), float(a.loc[key, "df"]), float(a.loc[key, "F"]), float(a.loc[key, "PR(>F)"])
        tab.append([label(key), g(ss), g(d), g(ss / d), g(F, 4), pv(p)])
        eta.append([label(key), g(ss / (ss + res_ss), 4)])
        if p < alpha:
            ans.append(f"{label(key)} ({p_text(p)})")
    tab.append(["Residual", g(res_ss), g(res_df), g(res_ss / res_df), "", ""])
    checks = [] if inter3 else [(None, "Only one value in some cells, so the three-way interaction cannot be tested; the model has the two-way interactions only.")]
    if len(m.resid) >= 3:
        sw = st.shapiro(m.resid)
        checks.append((sw.pvalue > alpha, f"The residuals {'look' if sw.pvalue > alpha else 'do not look'} normally distributed (Shapiro-Wilk {p_text(sw.pvalue)})."))
    return result("Three-way ANOVA", ("Significant: " + "; ".join(ans) + ".") if ans else "No factor or interaction is significant.",
                  [{"name": "Summary", "tables": [{"title": "Three-way ANOVA (Type III)", "columns": ["Source of variation", "SS", "DF", "MS", "F", "P value"], "rows": tab},
                                                 {"title": "Effect sizes (partial η²)", "columns": ["", "Partial η²"], "rows": eta}]}], checks,
                  methods=f"Data were analysed by three-way ANOVA ({names['Fa']} × {names['Fb']} × {names['Fc']}; Type III sums of squares) (α = {alpha:g}) in Datum Plot (statsmodels).",
                  code="import statsmodels.formula.api as smf\nfrom statsmodels.stats.anova import anova_lm\nm = smf.ols('y ~ C(A, Sum) * C(B, Sum) * C(D, Sum)', data=df).fit()  # name the third factor D: C is the formula's C()\nprint(anova_lm(m, typ=3))")


# ---------- ANCOVA ----------
def ancova(table, ks, o):
    """An XY table: X is the covariate, each data set a group. Do the groups differ once X is allowed for?
    First the slopes are compared (they must be parallel); then the groups' adjusted means."""
    import pandas as pd
    import statsmodels.formula.api as smf
    from statsmodels.stats.anova import anova_lm
    alpha = float(o.get("alpha", ALPHA))
    if len(ks) < 2:
        raise ValueError("ANCOVA compares two or more groups (data sets).")
    rows = []
    for k in ks:
        x, y, _ = points(table, k, {"points": "each"})
        rows += [(name_of(table, k), float(a), float(b)) for a, b in zip(x, y)]
    df = pd.DataFrame(rows, columns=["G", "x", "y"])
    if df.groupby("G").size().min() < 3:
        raise ValueError("Each group needs at least three points.")
    full = smf.ols("y ~ C(G, Sum) * x", data=df).fit()
    par = smf.ols("y ~ C(G, Sum) + x", data=df).fit()
    slopes = anova_lm(par, full)
    p_sl = float(slopes["Pr(>F)"].iloc[1])
    a = anova_lm(par, typ=3)
    F, p = float(a.loc["C(G, Sum)", "F"]), float(a.loc["C(G, Sum)", "PR(>F)"])
    xbar = float(df.x.mean())
    groups = list(dict.fromkeys(df.G))
    X = pd.DataFrame({"G": groups, "x": [xbar] * len(groups)})
    pred = par.get_prediction(X).summary_frame(alpha=0.05)
    adj = [[gname, g(float(pred["mean"].iloc[i])), g(float(pred["mean_se"].iloc[i])), ci_text(float(pred["mean_ci_lower"].iloc[i]), float(pred["mean_ci_upper"].iloc[i]))] for i, gname in enumerate(groups)]
    # Pairwise differences of the adjusted means (Šidák).
    from patsy import dmatrix
    info = dmatrix("C(G, Sum) + x", df, return_type="dataframe").design_info
    Xm = dmatrix(info, X, return_type="dataframe").to_numpy()
    b, V = par.params.to_numpy(), par.cov_params().to_numpy()
    comps, raw = [], []
    for i, j in combinations(range(len(groups)), 2):
        L = Xm[j] - Xm[i]
        d, se = float(L @ b), float(math.sqrt(L @ V @ L))
        comps.append((f"{groups[j]} vs {groups[i]}", d, se))
        raw.append(2 * float(st.t.sf(abs(d / se), par.df_resid)))
    padj = adjust(raw, "sidak")
    slope = float(par.params["x"])
    curves = []
    xs = np.linspace(df.x.min(), df.x.max(), 50)
    for i, k in enumerate(ks):
        yy = par.predict(pd.DataFrame({"G": [groups[i]] * len(xs), "x": xs}))
        curves.append({"set": k, "x": xs.tolist(), "y": [float(v) for v in yy], "label": ""})
    checks = [(p_sl > alpha, f"The slopes {'are' if p_sl > alpha else 'are not'} parallel (F test of the group × covariate interaction, {p_text(p_sl)})" + ("." if p_sl > alpha else "; the adjusted means depend on the value of X, so compare the lines (Linear regression) instead."))]
    sw = st.shapiro(par.resid) if len(par.resid) >= 3 else None
    if sw is not None:
        checks.append((sw.pvalue > alpha, f"The residuals {'look' if sw.pvalue > alpha else 'do not look'} normally distributed (Shapiro-Wilk {p_text(sw.pvalue)})."))
    xt = table.get("xTitle") or "X"
    return result("ANCOVA", f"Allowing for {xt}, the groups {'differ' if p < alpha else 'do not differ'} (F = {g(F, 4)}, {p_text(p)}); common slope {g(slope, 4)}.",
                  [{"name": "Summary", "tables": [{"title": "ANCOVA (Type III)", "columns": ["Source", "SS", "DF", "F", "P value"],
                                                  "rows": [[nm, g(float(a.loc[key, 'sum_sq'])), g(float(a.loc[key, 'df'])), g(float(a.loc[key, 'F']), 4) if key != "Residual" else "", pv(float(a.loc[key, 'PR(>F)'])) if key != "Residual" else ""]
                                                           for key, nm in (("C(G, Sum)", "Groups"), ("x", f"Covariate ({xt})"), ("Residual", "Residual"))]},
                                                 {"title": f"Adjusted means (at {xt} = {g(xbar, 4)})", "columns": ["Group", "Adjusted mean", "SE", "95% CI"], "rows": adj},
                                                 {"title": "Šidák comparisons of the adjusted means", "columns": ["Comparison", "Difference", "Adjusted P"], "rows": [[c[0], g(c[1]), pv(q)] for c, q in zip(comps, padj)]}]}],
                  checks, curves=curves,
                  methods=f"Groups were compared by analysis of covariance with {xt} as the covariate (Type III sums of squares), after testing that the slopes were parallel; adjusted means are at the mean of {xt}, compared with Šidák's correction (α = {alpha:g}), in Datum Plot (statsmodels).",
                  legend="Lines: the fitted parallel lines of the ANCOVA.",
                  code="import statsmodels.formula.api as smf\nfrom statsmodels.stats.anova import anova_lm\nm = smf.ols('y ~ C(G, Sum) + x', data=df).fit()\nprint(anova_lm(m, typ=3))")


# ---------- agreement: kappa, McNemar, Bowker ----------
def agreement(table, ks, o):
    """A contingency table of paired ratings: rows are the first rater's (or method's, or the first time's)
    categories, data sets the second's, in the same order. Cohen's kappa (weighted for ordered categories) and
    McNemar's test (2 × 2) or Bowker's test of symmetry (larger tables)."""
    from statsmodels.stats.contingency_tables import SquareTable, mcnemar
    from statsmodels.stats.inter_rater import cohens_kappa
    rows, cv = cells(table)
    M = np.array([[sum(cv.get((k, r), [0])) for k in ks] for r, _ in rows], float)
    if M.shape[0] != M.shape[1] or M.shape[0] < 2:
        raise ValueError(f"Agreement needs a square table: the same categories in the rows and the data sets, in the same order (this one is {M.shape[0]} × {M.shape[1]}).")
    if np.any(M < 0) or np.any(M != np.round(M)):
        raise ValueError("Enter counts: whole numbers of zero or more.")
    n = M.sum()
    weights = o.get("weights", "none")
    kp = cohens_kappa(M, wt={"none": None, "linear": "linear", "quadratic": "quadratic"}.get(weights))
    kappa, se = float(kp.kappa), float(kp.std_kappa)
    lo, hi = kappa - 1.959964 * se, kappa + 1.959964 * se
    # Landis & Koch: ≤ 0 poor, to 0.20 slight, to 0.40 fair, to 0.60 moderate, to 0.80 substantial, above almost perfect.
    words = next((w for c, w in ((0.0, "poor"), (0.2, "slight"), (0.4, "fair"), (0.6, "moderate"), (0.8, "substantial")) if kappa <= c + 1e-9), "almost perfect")
    tabs = [["Observed agreement", f"{g(100 * np.trace(M) / n, 4)}%" if n else ""], [f"Cohen's kappa{'' if weights == 'none' else f' ({weights} weights)'}", g(kappa, 4)],
            ["Std. error", g(se, 3)], ["95% CI", ci_text(lo, hi)], ["Strength (Landis & Koch)", words.capitalize()]]
    if M.shape[0] == 2:
        exact = (M[0, 1] + M[1, 0]) < 25
        mc = mcnemar(M, exact=exact, correction=True)
        test = ["McNemar's test" + (" (exact binomial)" if exact else " (χ², continuity corrected)"), g(float(mc.statistic), 4) if not exact else f"{int(min(M[0, 1], M[1, 0]))} of {int(M[0, 1] + M[1, 0])} discordant", pv(float(mc.pvalue))]
        p_sym = float(mc.pvalue)
    else:
        b = SquareTable(M, shift_zeros=False).symmetry()
        test = ["Bowker's test of symmetry (χ²)", f"{g(float(b.statistic), 4)} (df {int(b.df)})", pv(float(b.pvalue))]
        p_sym = float(b.pvalue)
    a, bset = name_of_rows(table), [name_of(table, k) for k in ks]
    ans = f"Cohen's kappa = {g(kappa, 3)} (95% CI {ci_text(lo, hi)}): {words} agreement; the two ratings {'differ' if p_sym < 0.05 else 'do not differ'} systematically ({test[0].split(' (')[0]}, {p_text(p_sym)})."
    return result("Agreement", ans, [{"name": "Summary", "tables": [{"title": "Agreement", "columns": ["", "Value"], "rows": tabs},
                                                                 {"title": "Do the two ratings differ?", "columns": ["Test", "Statistic", "P value"], "rows": [test]}]}],
                  [(None, f"{int(n)} paired ratings; rows ({', '.join(a[:4])}{'…' if len(a) > 4 else ''}) and data sets ({', '.join(bset[:4])}{'…' if len(bset) > 4 else ''}) must list the categories in the same order.")],
                  methods=f"Agreement was measured by Cohen's kappa{'' if weights == 'none' else ' with ' + weights + ' weights'} (95% CI from its standard error) and a systematic difference tested by {test[0].split(' (')[0]}, in Datum Plot (statsmodels).",
                  code="from statsmodels.stats.inter_rater import cohens_kappa\nfrom statsmodels.stats.contingency_tables import mcnemar\nprint(cohens_kappa(M))\nprint(mcnemar(M, exact=True))")


def name_of_rows(table):
    titles = table.get("rowTitles") or []
    return [(titles[r] if r < len(titles) else "") or f"Row {r + 1}" for r in range(table["rows"])]


# ---------- bootstrap confidence intervals ----------
STATS = {"mean": np.mean, "median": np.median, "sd": lambda a, axis=-1: np.std(a, ddof=1, axis=axis)}


def bootstrap(table, ks, o):
    """BCa bootstrap 95 % confidence intervals of each data set's mean, median or SD, and of the difference
    between the first two data sets. A fixed seed, so the same data always give the same interval."""
    what, nres = o.get("stat", "mean"), int(o.get("n", 9999))
    if what not in STATS:
        raise ValueError("Choose the mean, the median or the SD.")
    nres = min(max(nres, 999), 99999)
    fn = STATS[what]
    rng = np.random.default_rng(int(o.get("seed", 1)))
    rows, kept = [], []
    for k in ks:
        v = np.array([x for x, _ in values(table, k)], float)
        if len(v) < 3:
            continue
        r = st.bootstrap((v,), lambda a, axis=-1: fn(a, axis=axis), n_resamples=nres, method="BCa", random_state=rng)
        pct = st.bootstrap((v,), lambda a, axis=-1: fn(a, axis=axis), n_resamples=nres, method="percentile", random_state=np.random.default_rng(int(o.get("seed", 1))))
        est = float(fn(v))
        rows.append([name_of(table, k), str(len(v)), g(est, 4), ci_text(r.confidence_interval.low, r.confidence_interval.high), ci_text(pct.confidence_interval.low, pct.confidence_interval.high), g(float(r.standard_error), 3)])
        kept.append((k, v))
    if not rows:
        raise ValueError("Each data set needs at least three values for a bootstrap.")
    tabs = [{"title": f"Bootstrap 95% confidence intervals of the {what if what != 'sd' else 'SD'} ({nres} resamples)", "columns": ["Data set", "n", "Estimate", "95% CI (BCa)", "95% CI (percentile)", "Bootstrap SE"], "rows": rows}]
    ans = "; ".join(f"{r[0]}: {r[2]} (95% CI {r[3]})" for r in rows[:4])
    if len(kept) >= 2:
        (ka, a), (kb, b) = kept[0], kept[1]
        diff = st.bootstrap((a, b), lambda x, y, axis=-1: fn(y, axis=axis) - fn(x, axis=axis), n_resamples=nres, method="BCa", random_state=np.random.default_rng(int(o.get("seed", 1))))
        dl, dh = diff.confidence_interval.low, diff.confidence_interval.high
        tabs.append({"title": f"Difference of the {what if what != 'sd' else 'SD'}s", "columns": ["Comparison", "Difference", "95% CI (BCa)", "Includes 0?"],
                     "rows": [[f"{name_of(table, kb)} − {name_of(table, ka)}", g(float(fn(b) - fn(a)), 4), ci_text(dl, dh), "Yes" if dl <= 0 <= dh else "No"]]})
        ans += f". {name_of(table, kb)} − {name_of(table, ka)}: 95% CI {ci_text(dl, dh)}{' (includes 0)' if dl <= 0 <= dh else ' (excludes 0)'}"
    return result("Bootstrap", ans + ".", [{"name": "Summary", "tables": tabs}],
                  [(None, "Bootstrap intervals need no assumption about the distribution, but with fewer than about 15 values they can be too narrow.")] if any(int(r[1]) < 15 for r in rows) else [],
                  methods=f"95% confidence intervals of the {what if what != 'sd' else 'SD'} were obtained by the bias-corrected and accelerated (BCa) bootstrap with {nres} resamples (fixed seed), in Datum Plot (SciPy).",
                  code=f"from scipy import stats\nimport numpy as np\nr = stats.bootstrap((v,), np.{what if what != 'sd' else 'std'}, n_resamples={nres}, method='BCa')\nprint(r.confidence_interval)")
