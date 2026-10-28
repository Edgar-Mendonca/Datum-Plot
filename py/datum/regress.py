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


# ---------- PCA and clustering (B22) ----------
def matrix(table, ks, o):
    """Complete rows of the chosen variables: (raw X, X used: centred and, by default, scaled to SD 1, rows, names)."""
    if len(ks) < 2:
        raise ValueError("Choose at least two variables.")
    ex, cols = {tuple(e) for e in table.get("excluded", [])}, stats.set_columns(table)
    rows, data = [], []
    for r in range(table["rows"]):
        v = [stats.value(table, r, cols[k][0], ex) for k in ks]
        if all(a is not None and math.isfinite(a) for a in v):
            rows.append(r); data.append(v)
    X = np.array(data, float).reshape(-1, len(ks))
    if len(X) < 3:
        raise ValueError(f"Too few complete rows ({len(X)}); at least 3 are needed.")
    sd = X.std(axis=0, ddof=1)
    if o.get("scale", True) and np.any(sd == 0):
        raise ValueError(f"{', '.join(name_of(table, k) for k, s in zip(ks, sd) if s == 0)} has the same value in every row.")
    Z = (X - X.mean(axis=0)) / (sd if o.get("scale", True) else 1)
    return X, Z, rows, [name_of(table, k) for k in ks]


def scores_table(table, title, rows, heads, cols):
    """A table of many variables with one value per original row (empty where a row was left out)."""
    full = [[None] * table["rows"] for _ in cols]
    for i, r in enumerate(rows):
        for c, col in zip(full, cols):
            c[r] = float(col[i])
    titles = list(table.get("rowTitles") or [])
    return {"name": title, "kind": "multi", "xTitle": "", "xUnits": "", "yTitle": "Value", "yUnits": "", "rows": table["rows"], "rowTitles": titles + [""] * (table["rows"] - len(titles)),
            "sets": [{"title": h, "entry": "rep", "reps": 1} for h in heads], "cols": [[None] * table["rows"]] + full}


def label_of(table, r):
    t = (table.get("rowTitles") or [])
    return t[r] if r < len(t) and t[r] else f"Row {r + 1}"


def pca(table, ks, o):
    X, Z, rows, names = matrix(table, ks, o)
    n, p = Z.shape
    U, s, Vt = np.linalg.svd(Z, full_matrices=False)
    sign = np.where(Vt[np.arange(len(s)), np.argmax(np.abs(Vt), axis=1)] < 0, -1.0, 1.0)  # largest loading positive, so signs never flip between runs
    Vt, U = Vt * sign[:, None], U * sign
    ev = s ** 2 / (n - 1)
    share = ev / ev.sum()
    m = len(ev)
    pcs = [f"PC{i + 1}" for i in range(m)]
    scaled = o.get("scale", True)
    keep = int(np.sum(ev > 1)) if scaled else int(np.searchsorted(np.cumsum(share), 0.8) + 1)
    keep = max(1, min(keep, m))
    var_rows = [[pcs[i], g(ev[i], 4), g(math.sqrt(ev[i]), 4), f"{100 * share[i]:.1f}%", f"{100 * share[:i + 1].sum():.1f}%"] for i in range(m)]
    show = min(m, 6)
    load_rows = [[names[j]] + [g(Vt[i, j], 4) for i in range(show)] for j in range(p)]
    cor_rows = [[names[j]] + [g(Vt[i, j] * math.sqrt(ev[i]) / (1 if scaled else Z[:, j].std(ddof=1)), 3) for i in range(show)] for j in range(p)]
    S = U * s
    sc_rows = [[label_of(table, r)] + [g(S[i, c], 4) for c in range(min(show, 4))] for i, r in enumerate(rows[:200])]
    rule = "eigenvalue above 1 (Kaiser)" if scaled else "80% of the variance"
    ans = (f"PC1 explains {100 * share[0]:.1f}% of the variation{f' and PC2 {100 * share[1]:.1f}%' if m > 1 else ''}; {keep} component{'s' * (keep > 1)} "
           f"({100 * share[:keep].sum():.0f}% together) {'are' if keep > 1 else 'is'} worth keeping ({rule}). PC1 is mostly {', '.join(names[j] for j in np.argsort(-np.abs(Vt[0]))[:2])}.")
    c = COLORS[0]

    def scree(ax):
        ax.plot(range(1, m + 1), 100 * share, "o-", ms=3.5, color=c, lw=1)
        ax.set_xticks(range(1, m + 1)); ax.set_xlabel("Component"); ax.set_ylabel("% of variance")

    def biplot(ax):
        ax.axhline(0, color="#D5DBE3", lw=0.6); ax.axvline(0, color="#D5DBE3", lw=0.6)
        ax.plot(S[:, 0], S[:, 1], "o", ms=2.8, color=c, alpha=0.8)
        k = 0.85 * min(np.abs(S[:, i]).max() / max(np.abs(Vt[i]).max(), 1e-12) for i in (0, 1))
        ax.plot(1.25 * k * Vt[0], 1.25 * k * Vt[1], linestyle="none")  # room for the arrow labels
        for j in range(p):
            ax.annotate("", (k * Vt[0, j], k * Vt[1, j]), (0, 0), arrowprops={"arrowstyle": "->", "color": "#D55E00", "lw": 0.8})
            ax.text(1.08 * k * Vt[0, j], 1.08 * k * Vt[1, j], names[j][:14], color="#D55E00", fontsize=6, ha="center", va="center")
        ax.set_xlabel(f"PC1 ({100 * share[0]:.0f}%)"); ax.set_ylabel(f"PC2 ({100 * share[1]:.0f}%)")
    plots = [small_plot("Scree plot", scree)] + ([small_plot("Biplot: scores and loadings", biplot, 80, 70)] if m > 1 else [])
    checks = [(None, f"{'Each variable was scaled to SD 1 (the correlation matrix), so units do not matter' if scaled else 'Variables were only centred (the covariance matrix): those with large values and units dominate'}."),
              (n >= 5 * p, f"{n} rows for {p} variables{': fewer than five per variable, so the components may not be stable' if n < 5 * p else ''}.")]
    left = sum(1 for r in range(table["rows"]) if r not in set(rows) and any(stats.value(table, r, stats.set_columns(table)[k][0]) is not None for k in ks))
    if left:
        checks.append((None, f"{left} row{'s' * (left > 1)} with a missing value {'were' if left > 1 else 'was'} left out."))
    tb = scores_table(table, f"{table.get('name') or 'Data'} PC scores", rows, pcs[:show], [S[:, i] for i in range(show)])
    return result("Principal component analysis", ans, [
        {"name": "Summary", "tables": [{"title": "Variance explained", "columns": ["Component", "Eigenvalue", "SD", "% of variance", "Cumulative"], "rows": var_rows},
                                       {"title": "Loadings (eigenvectors)", "columns": ["Variable", *pcs[:show]], "rows": load_rows}]},
        {"name": "Details", "tables": [{"title": "Correlation of each variable with each component", "columns": ["Variable", *pcs[:show]], "rows": cor_rows},
                                       {"title": "Scores" + (f" (first 200 of {n} rows)" if n > 200 else ""), "columns": ["Row", *pcs[:min(show, 4)]], "rows": sc_rows}]}],
        checks, plots=plots, table=tb, legend=f"Principal component analysis of {', '.join(names)} (n = {n}).",
        methods=f"Principal component analysis of {p} variables ({', '.join(names)}; n = {n}) was performed on the {'correlation' if scaled else 'covariance'} matrix by singular value decomposition in Datum Plot (numpy); components were retained by the {rule} rule.",
        code="import numpy as np\nZ = (X - X.mean(0)) / X.std(0, ddof=1)\nU, s, Vt = np.linalg.svd(Z, full_matrices=False)\nprint(s**2 / (len(Z) - 1), Vt)")


def silhouette(Z, lab):
    """Mean silhouette width (-1 to 1): how well each row sits in its own cluster rather than the nearest other."""
    if len(Z) > 3000 or len(set(lab)) < 2:
        return None
    D = np.sqrt(((Z[:, None, :] - Z[None, :, :]) ** 2).sum(-1))
    out = []
    for i in range(len(Z)):
        same = lab == lab[i]
        if same.sum() < 2:
            out.append(0.0); continue
        a = D[i, same].sum() / (same.sum() - 1)
        b = min(D[i, lab == c].mean() for c in set(lab) if c != lab[i])
        out.append((b - a) / max(a, b) if max(a, b) > 0 else 0.0)
    return float(np.mean(out))


def cluster(table, ks, o):
    from scipy.cluster import hierarchy, vq
    X, Z, rows, names = matrix(table, ks, o)
    n = len(Z)
    k = int(o.get("k") or 3)
    if not 2 <= k < n:
        raise ValueError(f"Choose between 2 and {n - 1} clusters.")
    method = o.get("method", "ward")
    L = None
    if method == "kmeans":
        best = None
        for seed in range(10):  # the best of ten starts, always the same ones
            cent, lab = vq.kmeans2(Z, k, minit="++", seed=seed)
            w = float(((Z - cent[lab]) ** 2).sum())
            if len(set(lab)) == k and (best is None or w < best[0]):
                best = (w, lab)
        if best is None:
            raise ValueError("k-means could not find that many clusters; choose fewer.")
        lab = best[1]
    else:
        L = hierarchy.linkage(Z, method=method if method in ("ward", "average", "complete", "single") else "ward")
        lab = hierarchy.fcluster(L, k, criterion="maxclust") - 1
    order = sorted(set(lab), key=lambda c: min(i for i in range(n) if lab[i] == c))  # cluster 1 holds the first row
    lab = np.array([order.index(c) for c in lab])
    sil = silhouette(Z, lab)
    sizes = [int((lab == c).sum()) for c in range(k)]
    mean_rows = [[f"Cluster {c + 1}", g(sizes[c])] + [g(X[lab == c, j].mean(), 4) for j in range(len(names))] for c in range(k)]
    within = sum(float(((Z[lab == c] - Z[lab == c].mean(0)) ** 2).sum()) for c in range(k))
    total = float(((Z - Z.mean(0)) ** 2).sum())
    mem = [[label_of(table, r), str(lab[i] + 1)] for i, r in enumerate(rows[:500])]
    how = {"kmeans": "k-means (best of 10 starts, k-means++)", "ward": "hierarchical, Ward's linkage", "average": "hierarchical, average linkage",
           "complete": "hierarchical, complete linkage", "single": "hierarchical, single linkage"}.get(method, "hierarchical, Ward's linkage")
    ans = (f"{n} rows in {k} clusters of {', '.join(map(str, sizes))} ({how}). The clusters account for {100 * (1 - within / total):.0f}% of the spread"
           + (f"; mean silhouette {sil:.2f} ({'clear' if sil > 0.5 else 'reasonable' if sil > 0.25 else 'weak'} structure)." if sil is not None else "."))
    U, s, Vt = np.linalg.svd(Z - Z.mean(0), full_matrices=False)
    S = U * s

    def scatter(ax):
        for c in range(k):
            ax.plot(S[lab == c, 0], S[lab == c, 1] if S.shape[1] > 1 else np.zeros(sizes[c]), "o", ms=3, color=COLORS[c % 8], label=f"{c + 1}")
        ax.set_xlabel("PC1"); ax.set_ylabel("PC2"); ax.legend(fontsize=6, frameon=False, title="Cluster", title_fontsize=6)

    def dendro(ax):
        hierarchy.dendrogram(L, ax=ax, no_labels=n > 40, labels=[label_of(table, r)[:10] for r in rows] if n <= 40 else None, leaf_font_size=5,
                             color_threshold=0, above_threshold_color="#5B6878")
        ax.axhline((L[-k, 2] + L[-(k - 1), 2]) / 2, color="#D55E00", lw=0.8, ls="--")  # where the tree is cut into k clusters
        ax.set_ylabel("Distance")
    plots = [small_plot("Clusters on the first two components", scatter, 80, 65)] + ([small_plot("Dendrogram", dendro, 90, 60)] if L is not None else [])
    checks = [(None, "Clustering always finds groups, even in data without any; check that they make sense." + (f" A mean silhouette of {sil:.2f} says how distinct they are (above 0.5 clear, below 0.25 weak)." if sil is not None else ""))]
    if not o.get("scale", True):
        checks.append((None, "Variables were not scaled: those with large values and units dominate the distances."))
    tb = scores_table(table, f"{table.get('name') or 'Data'} clusters", rows, [*names, "Cluster"], [*X.T, lab + 1])
    return result("Cluster analysis", ans, [
        {"name": "Summary", "tables": [{"title": "Cluster means", "columns": ["Cluster", "Rows", *names], "rows": mean_rows}]},
        {"name": "Members", "tables": [{"title": "Cluster of each row" + (f" (first 500 of {n})" if n > 500 else ""), "columns": ["Row", "Cluster"], "rows": mem}]}],
        checks, plots=plots, table=tb, legend=f"Cluster analysis of {', '.join(names)} ({how}; n = {n}).",
        methods=f"Rows were grouped into {k} clusters by {how} on {'standardised' if o.get('scale', True) else 'raw'} values of {', '.join(names)} (Euclidean distance; n = {n}) in Datum Plot (SciPy).",
        code="from scipy.cluster import hierarchy\nlab = hierarchy.fcluster(hierarchy.linkage(Z, 'ward'), k, 'maxclust')")
