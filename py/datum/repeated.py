"""Two-way repeated measures ANOVA and its mixed-effects model (B32).

A grouped table's replicate sub-columns are the subjects. `rm` says which factor is repeated:
  "rows" — each sub-column of a data set is one subject measured in every row (rows within, data sets between);
  "sets" — sub-column j of a row is one subject measured in every data set (data sets within, rows between);
  "both" — sub-column j is the same subject in every row and data set.
With every subject complete this is the classic repeated measures ANOVA (error strata as in R's
aov(y ~ A * B + Error(subject / within))) with the Geisser-Greenhouse epsilon; with missing values it is a linear
mixed model fitted by REML (subject as a random effect), its fixed effects tested by Wald F tests with
between–within degrees of freedom. Multiple comparisons come from the fitted mixed model in both cases."""
import math
from itertools import combinations

import numpy as np
import scipy.stats as st

from . import stats
from .analysis import ALPHA, g, name_of, pv, result, stars
from .groups import POSTNAME, adjust, ci_text, p_text

DESIGNS = {"rows": "each sub-column is one subject measured in every row", "sets": "each row's sub-column is one subject measured in every data set",
           "both": "each sub-column is one subject measured in every row and data set"}


def long(table, ks, rm):
    """[(row label, data set name, subject, value)] with None for missing cells, and the row labels and set names in order."""
    ex = {tuple(e) for e in table.get("excluded", [])}
    titles = table.get("rowTitles") or []
    spans = stats.set_columns(table)
    w = max(spans[k][1] for k in ks)
    rows = [r for r in range(table["rows"]) if any(stats.value(table, r, c, ex) is not None for k in ks for c in range(spans[k][0], spans[k][0] + spans[k][1]))]
    labels = {r: (titles[r] if r < len(titles) else "") or f"Row {r + 1}" for r in rows}
    out = []
    for k in ks:
        c0, wk = spans[k]
        for r in rows:
            for j in range(w):
                v = stats.value(table, r, c0 + j, ex) if j < wk else None
                v = v if v is not None and math.isfinite(v) else None
                subj = {"rows": f"{k}:{j}", "sets": f"{r}:{j}", "both": f"{j}"}[rm]
                out.append((labels[r], name_of(table, k), subj, v))
    # Subjects with no value at all are empty sub-columns, not subjects.
    seen = {s for *_, s, v in out if v is not None}
    return [o for o in out if o[2] in seen], [labels[r] for r in rows], [name_of(table, k) for k in ks], rows


def contrasts(a):
    """(a − 1) × a orthonormal contrasts."""
    return np.linalg.qr(np.vstack([np.ones(a), np.eye(a)[:-1] - np.eye(a)[1:]]).T)[0][:, 1:].T


def gg_epsilon(Y, C=None):
    """Geisser-Greenhouse epsilon from subjects × levels values (centred within groups by the caller) and the
    effect's orthonormal contrasts C (all level differences when not given)."""
    C = contrasts(Y.shape[1]) if C is None else C
    if C.shape[0] < 2:
        return 1.0
    M = C @ np.cov(Y, rowvar=False) @ C.T
    return float(min(1.0, np.trace(M) ** 2 / (C.shape[0] * np.trace(M @ M)))) if np.trace(M @ M) > 0 else 1.0


def classic(df, rm):
    """Repeated measures ANOVA of complete data: [(source, SS, DF, error source)] and the GG epsilon per within source."""
    A, B = df.A.unique(), df.B.unique()
    m = df.y.mean()
    out, eps = [], {}
    if rm == "both":
        n = df.S.nunique()
        mA, mB, mS = df.groupby("A").y.mean(), df.groupby("B").y.mean(), df.groupby("S").y.mean()
        mAB, mAS, mBS = df.groupby(["A", "B"]).y.mean(), df.groupby(["A", "S"]).y.mean(), df.groupby(["B", "S"]).y.mean()
        a, b = len(A), len(B)
        ssA, ssB, ssS = b * n * ((mA - m) ** 2).sum(), a * n * ((mB - m) ** 2).sum(), a * b * ((mS - m) ** 2).sum()
        ssAB = n * sum((mAB[i, j] - mA[i] - mB[j] + m) ** 2 for i in A for j in B)
        ssAS = b * sum((mAS[i, s] - mA[i] - mS[s] + m) ** 2 for i in A for s in mS.index)
        ssBS = a * sum((mBS[j, s] - mB[j] - mS[s] + m) ** 2 for j in B for s in mS.index)
        ssE = float(((df.y - df.y.mean()) ** 2).sum()) - ssA - ssB - ssS - ssAB - ssAS - ssBS
        out = [("A", ssA, a - 1, "A×S", ssAS, (a - 1) * (n - 1)), ("B", ssB, b - 1, "B×S", ssBS, (b - 1) * (n - 1)), ("AB", ssAB, (a - 1) * (b - 1), "A×B×S", ssE, (a - 1) * (b - 1) * (n - 1))]
        wide = lambda f: df.pivot_table(index="S", columns=f, values="y", aggfunc="mean").to_numpy()
        cells = df.pivot_table(index="S", columns=["A", "B"], values="y")  # columns: A outer, B inner, both sorted
        eps = {"A": gg_epsilon(wide("A")), "B": gg_epsilon(wide("B")), "AB": gg_epsilon(cells.to_numpy(), np.kron(contrasts(a), contrasts(b)))}
        return out, eps, n
    # Split plot: W within subjects, G between (subjects nested in G).
    W, G = ("A", "B") if rm == "rows" else ("B", "A")
    w = df[W].nunique()
    subj = df.groupby("S").agg(y=("y", "mean"), G=(G, "first"))
    ssG = w * sum(len(gr) * (gr.y.mean() - m) ** 2 for _, gr in subj.groupby("G"))
    ssS = w * float(((subj.y - m) ** 2).sum()) - ssG
    nS, nG = len(subj), subj.G.nunique()
    # Within-subject stratum: deviations from each subject's mean, fitted by W and W×G.
    import statsmodels.formula.api as smf
    from statsmodels.stats.anova import anova_lm
    d = df.assign(r=df.y - df.groupby("S").y.transform("mean"))
    t = anova_lm(smf.ols(f"r ~ C({W}) + C({W}):C({G})", data=d).fit(), typ=1)
    ssW, ssWG = float(t.loc[f"C({W})", "sum_sq"]), float(t.loc[f"C({W}):C({G})", "sum_sq"])
    dfE = (w - 1) * (nS - nG)
    ssE = float(((d.r) ** 2).sum()) - ssW - ssWG
    out = [(G, ssG, nG - 1, "S", ssS, nS - nG), (W, ssW, w - 1, f"{W}×S", ssE, dfE), ("AB", ssWG, (w - 1) * (nG - 1), f"{W}×S", ssE, dfE)]
    # Pooled within-group covariance of the subjects' values across the within levels.
    Y = df.pivot_table(index="S", columns=W, values="y").join(subj.G)
    pooled = np.vstack([gr.drop(columns="G").to_numpy() - gr.drop(columns="G").to_numpy().mean(0) for _, gr in Y.groupby("G")])
    e = gg_epsilon(pooled)
    eps = {W: e, "AB": e}
    return out, eps, nS


def mixed(df, rm):
    """The mixed model (REML; subject random, and subject × factor for "both"), its Wald F tests with
    between–within DF, and the fit (for comparisons)."""
    import statsmodels.formula.api as smf
    vc = {"SA": "0 + C(A)", "SB": "0 + C(B)"} if rm == "both" else None
    import warnings
    model, m, err = smf.mixedlm("y ~ C(A, Sum) * C(B, Sum)", df, groups=df["S"], re_formula="1", vc_formula=vc), None, None
    for how in ("lbfgs", "bfgs", "powell", "nm"):  # the first optimizer that converges
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                m = model.fit(reml=True, method=how)
            if np.all(np.isfinite(m.fe_params)) and np.all(np.isfinite(np.diag(m.cov_params()))):
                break
        except (np.linalg.LinAlgError, ValueError) as e:
            m, err = None, e
    if m is None:
        raise ValueError(f"The mixed-effects model could not be fitted to these data ({err}).")
    names = list(m.fe_params.index)
    nS, N = df.S.nunique(), len(df)
    W = {"rows": {"A"}, "sets": {"B"}, "both": {"A", "B"}}[rm]
    p_between = 1 + sum(1 for n in names if n != "Intercept" and not any(f"C({x}, Sum)" in n for x in W))
    tests = []
    for key, fac in (("A", {"A"}), ("B", {"B"}), ("AB", {"A", "B"})):
        idx = [i for i, n in enumerate(names) if (("C(A, Sum)" in n) == ("A" in fac)) and (("C(B, Sum)" in n) == ("B" in fac)) and n != "Intercept"]
        L = np.zeros((len(idx), len(names)))
        for r, i in enumerate(idx):
            L[r, i] = 1
        b = m.fe_params.to_numpy()
        V = m.cov_params().iloc[:len(names), :len(names)].to_numpy()
        Lb = L @ b
        chi = float(Lb @ np.linalg.pinv(L @ V @ L.T) @ Lb)
        within = bool(fac & W)
        ddf = (N - nS - (len(names) - p_between)) if within else (nS - p_between)
        F = chi / len(idx)
        tests.append((key, F, len(idx), max(ddf, 1), float(st.f.sf(F, len(idx), max(ddf, 1))), within))
    return tests, m


def twoway_rm(table, ks, o):
    import pandas as pd
    rm = o.get("rm")
    alpha, post, within = float(o.get("alpha", ALPHA)), o.get("posthoc", "sidak"), o.get("compare", "rows")
    if any(table["sets"][k]["entry"] != "rep" for k in ks):
        raise ValueError("Repeated measures ANOVA needs the individual values; enter them as replicates (one sub-column per subject).")
    data, rlab, slab, rix = long(table, ks, rm)
    df_all = pd.DataFrame(data, columns=["A", "B", "S", "y"])
    df = df_all.dropna()
    if df.A.nunique() < 2 or df.B.nunique() < 2:
        raise ValueError("Repeated measures ANOVA needs at least two rows and two data sets with values.")
    if df.S.nunique() < 3:
        raise ValueError("Repeated measures ANOVA needs at least three subjects (sub-columns with values).")
    cellsize = df.groupby(["A", "B", "S"]).size()
    if cellsize.max() > 1:
        raise ValueError("Each subject has one value per cell; check the repeated measures design.")
    complete = len(df) == len(df_all) and df.groupby("S").size().nunique() == 1
    if rm == "both" and complete and df.groupby(["A", "B"]).S.nunique().nunique() != 1:
        complete = False
    rowname, colname = o.get("rowname") or "Row factor", o.get("colname") or "Column factor"
    label = {"A": rowname, "B": colname, "AB": "Interaction"}
    tests, fit = mixed(df, rm)
    tab, ans, ps, eps = [], [], {}, {}
    if complete:
        rows_, eps, _ = classic(df, rm)
        gg = o.get("gg", True)
        errs = {}
        for src, ss, d, esrc, sse, dfe in rows_:
            e = eps.get(src, 1.0) if gg and src != ({"rows": "B", "sets": "A"}.get(rm)) else 1.0
            F = (ss / d) / (sse / dfe) if sse > 0 else float("inf")
            p = float(st.f.sf(F, d * e, dfe * e))
            ps[src] = p
            tab.append([label[src], g(ss), g(d * e, 4) if e < 1 else g(d), g(ss / d), g(F, 4), pv(p), "", ""])
            errs[esrc] = (sse, dfe)
        for esrc, (sse, dfe) in errs.items():
            nm = {"S": "Subjects (between)", "A×S": f"Subjects × {rowname}", "B×S": f"Subjects × {colname}", "A×B×S": "Residual"}.get(esrc, "Residual")
            tab.append([nm, g(sse), g(dfe), g(sse / dfe) if dfe else "", "", "", "", ""])
        method = "repeated measures ANOVA" + (" with the Geisser-Greenhouse correction" if gg and any(v < 1 for v in eps.values()) else "")
        title, cols = "Two-way repeated measures ANOVA", ["Source of variation", "SS", "DF", "MS", "F", "P value", "", ""]
    else:
        for key, F, d1, d2, p, _ in tests:
            ps[key] = p
            tab.append([label[key], g(F, 4), f"{d1}, {g(d2)}", pv(p)])
        method = "a mixed-effects model (REML) because values are missing"
        title, cols = "Mixed-effects model (fixed effects)", ["Source of variation", "F", "DFn, DFd", "P value"]
    order = ["AB", "A", "B"]
    for key in order:
        if key in ps:
            ans.append(f"{label[key]}: {'significant' if ps[key] < alpha else 'not significant'} ({p_text(ps[key])})")
    tabs = [{"title": title, "columns": cols[:6] if complete else cols, "rows": [r[:6] for r in tab] if complete else tab}]
    if complete and eps:
        tabs.append({"title": "Sphericity", "columns": ["", "Geisser-Greenhouse ε"], "rows": [[label[k], g(v, 4)] for k, v in eps.items() if k != "AB" or rm == "both"]})
    vc = [["Subjects (SD)", g(math.sqrt(max(float(fit.cov_re.iloc[0, 0]), 0)), 4)], ["Residual (SD)", g(math.sqrt(fit.scale), 4)]]
    tabs.append({"title": "Random effects (mixed model)", "columns": ["", "Value"], "rows": vc})
    means = df.groupby(["A", "B"]).y.agg(["mean", "count"])
    tabs.append({"title": "Cell means", "columns": ["", *slab], "rows": [[r, *[f"{g(means.loc[(r, s), 'mean'])} (n = {int(means.loc[(r, s), 'count'])})" if (r, s) in means.index else "" for s in slab]] for r in rlab]})
    checks = [(None, f"Design: {DESIGNS[rm]} ({df.S.nunique()} subjects).")]
    if not complete:
        checks.append((None, f"{len(df_all) - len(df)} values are missing, so a mixed-effects model was fitted instead of repeated measures ANOVA; its F tests use between–within degrees of freedom."))
    if ps.get("AB", 1) < alpha:
        checks.append((None, "The interaction is significant: the effect of one factor depends on the other, so compare within each row rather than the main effects."))
    for k, e in eps.items():
        if e < 0.75:
            checks.append((False, f"Sphericity is doubtful for {label[k]} (ε = {g(e, 3)}); the Geisser-Greenhouse correction is {'applied' if o.get('gg', True) else 'off'}."))
    if len(fit.resid) >= 3:
        sw = st.shapiro(fit.resid)
        checks.append((sw.pvalue > alpha, f"The residuals {'look' if sw.pvalue > alpha else 'do not look'} normally distributed (Shapiro-Wilk {p_text(sw.pvalue)})."))
    brackets = []
    if post != "none":
        brackets = comparisons(fit, df, rm, ks, rlab, slab, rix, tests, within, post, tabs)
    return result("Two-way repeated measures ANOVA" if complete else "Mixed-effects model", "; ".join(ans) + ".", [{"name": "Summary", "tables": tabs}], checks, brackets=brackets,
                  methods=f"Data were analysed by {method} ({rowname} × {colname}; {DESIGNS[rm]}){'' if post == 'none' else ', with ' + POSTNAME.get(post, 'Šidák') + ' multiple comparisons from the mixed model'} (α = {alpha:g}) in Datum Plot (statsmodels).",
                  legend="Points show each subject; stars: * P < 0.05, ** P < 0.01, *** P < 0.001 (multiplicity-adjusted).",
                  code="import statsmodels.formula.api as smf\n# df: one row per value with columns y, A (row), B (data set), S (subject)\nm = smf.mixedlm('y ~ C(A, Sum) * C(B, Sum)', df, groups=df['S']).fit(reml=True)\nprint(m.summary())")


def comparisons(fit, df, rm, ks, rlab, slab, rix, tests, within, post, tabs):
    """Differences of cell means from the mixed model, within each row (or each data set)."""
    import pandas as pd
    names = list(fit.fe_params.index)
    b, V = fit.fe_params.to_numpy(), fit.cov_params().iloc[:len(names), :len(names)].to_numpy()
    from patsy import dmatrix
    design = dmatrix("C(A, Sum) * C(B, Sum)", df, return_type="dataframe").design_info  # the model's own coding
    assert list(design.column_names) == names
    row = lambda a, s: dmatrix(design, pd.DataFrame({"A": [a], "B": [s]}), return_type="dataframe").to_numpy()[0]
    dfw = {k: d2 for k, _, _, d2, _, w_ in tests if w_}
    dfb = {k: d2 for k, _, _, d2, _, w_ in tests if not w_}
    comps = []
    if within == "rows":
        for r in rlab:
            for i, j in combinations(range(len(slab)), 2):
                comps.append((f"{r}: {slab[i]} vs {slab[j]}", r, slab[i], r, slab[j], ks[i], ks[j], rix[rlab.index(r)], "B"))
    else:
        for s in slab:
            for i, j in combinations(range(len(rlab)), 2):
                comps.append((f"{s}: {rlab[i]} vs {rlab[j]}", rlab[i], s, rlab[j], s, None, None, None, "A"))
    out, raw = [], []
    for c in comps:
        L = row(c[3], c[4]) - row(c[1], c[2])
        d, se = float(L @ b), float(math.sqrt(max(L @ V @ L, 0)))
        rep = c[8] in {"rows": {"A"}, "sets": {"B"}, "both": {"A", "B"}}[rm]
        ddf = (dfw.get(c[8]) if rep else dfb.get(c[8])) or min(list(dfw.values()) + list(dfb.values()))
        raw.append(2 * float(st.t.sf(abs(d / se), ddf)) if se > 0 else float("nan"))
        out.append((c, d, se, ddf))
    adj = adjust(raw, post)
    q = 1 - 0.95 ** (1 / len(out)) if post in ("sidak", "holm") else 0.05 / len(out) if post == "bonferroni" else 0.05
    tabs.append({"title": f"{POSTNAME.get(post, 'Šidák')} multiple comparisons {'within each row' if within == 'rows' else 'within each data set'}", "columns": ["Comparison", "Mean difference", "95% CI", "Adjusted P", "Summary"],
                 "rows": [[c[0], g(d), ci_text(d - st.t.ppf(1 - q / 2, ddf) * se, d + st.t.ppf(1 - q / 2, ddf) * se), pv(p), stars(p)] for (c, d, se, ddf), p in zip(out, adj)]})
    return [[c[5], c[6], float(p), c[7]] for (c, d, se, ddf), p in zip(out, adj) if c[5] is not None]
