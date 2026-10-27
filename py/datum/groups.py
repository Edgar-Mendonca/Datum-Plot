"""Comparing groups (column tables, or the data sets of any table): t-tests, nonparametric tests,
one-way ANOVA with multiple comparisons and effect sizes, correlation, and power. Every function
has the analysis signature (table, ks, options) and returns analysis.result(...)."""
import math
from itertools import combinations

import numpy as np
from scipy import stats as st

from . import stats
from .analysis import ALPHA, COLORS, g, name_of, pv, result, small_plot, stars, values

Z95 = 1.959963984540054  # the normal 97.5 % point, as R qnorm(0.975)


# ---------- data ----------
def column(table, k):
    """The values of data set k by row (the mean of its sub-columns), None where empty: for paired tests."""
    c0, w = stats.set_columns(table)[k]
    w = w if table["sets"][k]["entry"] == "rep" else 1
    ex = {tuple(e) for e in table.get("excluded", [])}
    out = []
    for r in range(table["rows"]):
        v = [x for x in (stats.value(table, r, c, ex) for c in range(c0, c0 + w)) if x is not None and math.isfinite(x)]
        out.append(float(np.mean(v)) if v else None)
    return out


def summary(table, k):
    """(values or None, n, mean, sd): from the values, or from an entered mean with SD/SEM and N (its first row)."""
    s = table["sets"][k]
    if s["entry"] == "rep":
        v = np.array([a for a, _ in values(table, k)], float)
        return v, len(v), float(v.mean()) if len(v) else float("nan"), float(v.std(ddof=1)) if len(v) > 1 else float("nan")
    c0 = stats.set_columns(table)[k][0]
    ex = {tuple(e) for e in table.get("excluded", [])}
    for r in range(table["rows"]):
        d = stats.from_summary(stats.value(table, r, c0, ex), stats.value(table, r, c0 + 1, ex), stats.value(table, r, c0 + 2, ex), s["entry"])
        if d:
            return None, d["n"], d["mean"], d["sd"]
    return None, 0, float("nan"), float("nan")


def cells(table):
    """A grouped table: the rows that hold data as [(row, label)], and {(set, row): [values]}."""
    ex = {tuple(e) for e in table.get("excluded", [])}
    cv, rows = {}, []
    titles = table.get("rowTitles") or []
    for k, (c0, w) in enumerate(stats.set_columns(table)):
        w = w if table["sets"][k]["entry"] == "rep" else 1
        for r in range(table["rows"]):
            v = [x for x in (stats.value(table, r, c, ex) for c in range(c0, c0 + w)) if x is not None and math.isfinite(x)]
            if v:
                cv[(k, r)] = v
    for r in range(table["rows"]):
        if any((k, r) in cv for k in range(len(table["sets"]))):
            rows.append((r, (titles[r] if r < len(titles) else "") or f"Row {r + 1}"))
    return rows, cv


def pairs_of(table, a, b):
    """Rows where both data sets have a value: (x, y) arrays."""
    x, y = column(table, a), column(table, b)
    keep = [(u, v) for u, v in zip(x, y) if u is not None and v is not None]
    return np.array([u for u, _ in keep], float), np.array([v for _, v in keep], float)


def p_text(p):
    t = pv(p)
    return f"P {t}" if t.startswith("<") else f"P = {t}"


def ci_text(lo, hi):
    return f"{g(lo)} to {g(hi)}"


def need(raw, n, what):
    if raw is None:
        raise ValueError(f"{what} needs the individual values; enter them as replicates, not as mean, SD and N.")
    if n < 2:
        raise ValueError(f"{what} needs at least two values in each group.")


def adjust(ps, method):
    """Multiplicity-adjusted P values (Bonferroni, Šidák, Holm-Šidák, Holm or none)."""
    from statsmodels.stats.multitest import multipletests
    if method in ("none", "lsd") or not ps:
        return list(ps)
    m = {"bonferroni": "bonferroni", "sidak": "sidak", "holm": "holm-sidak", "holm-b": "holm", "fdr": "fdr_bh"}[method]
    return list(multipletests(ps, method=m)[1])


def effect_rows(a, b, paired=False):
    """Mean difference, Cohen's d and Hedges' g with approximate 95 % CIs."""
    if paired:
        d = b - a
        n = len(d)
        dz = d.mean() / d.std(ddof=1) if d.std(ddof=1) > 0 else float("nan")
        se = math.sqrt(1 / n + dz * dz / (2 * n))
        return [["Cohen's dz (paired)", g(dz, 4), ci_text(dz - Z95 * se, dz + Z95 * se)]]
    n1, n2 = len(a), len(b)
    sp = math.sqrt(((n1 - 1) * a.var(ddof=1) + (n2 - 1) * b.var(ddof=1)) / (n1 + n2 - 2))
    d = (b.mean() - a.mean()) / sp if sp > 0 else float("nan")
    se = math.sqrt((n1 + n2) / (n1 * n2) + d * d / (2 * (n1 + n2)))
    J = 1 - 3 / (4 * (n1 + n2) - 9)
    return [["Cohen's d", g(d, 4), ci_text(d - Z95 * se, d + Z95 * se)], ["Hedges' g", g(J * d, 4), ci_text(J * (d - Z95 * se), J * (d + Z95 * se))]]


def size_word(d):
    d = abs(d)
    return "negligible" if d < 0.2 else "small" if d < 0.5 else "medium" if d < 0.8 else "large"


def dot_plot(title, groups, names):
    """A small scatter plot of the groups for the results sheet."""
    def draw(ax):
        for i, v in enumerate(groups):
            if v is None or not len(v):
                continue
            jit = (np.arange(len(v)) % 7 - 3) * 0.04
            ax.plot(i + jit, v, "o", ms=3.2, color=COLORS[i % 8], alpha=0.85)
            ax.hlines(np.mean(v), i - 0.25, i + 0.25, color="#3A4655", lw=1.2)
        ax.set_xticks(range(len(groups)), [n[:12] for n in names], fontsize=7)
    return small_plot(title, draw)


# ---------- t-tests and effect sizes (B4, B8) ----------
def ttest(table, ks, o):
    test, alpha = o.get("test", "unpaired"), float(o.get("alpha", ALPHA))
    rows, checks, brackets = [], [], []
    if test == "one":
        mu = float(o.get("mu", 0) or 0)
        out = []
        for k in ks:
            v, n, m, sd = summary(table, k)
            if v is None:
                t = (m - mu) / (sd / math.sqrt(n)) if n > 1 and sd > 0 else float("nan")
                p, df = 2 * st.t.sf(abs(t), n - 1), n - 1
            else:
                need(v, n, "A one-sample t-test")
                r = st.ttest_1samp(v, mu)
                t, p, df = float(r.statistic), float(r.pvalue), n - 1
            h = st.t.ppf(0.975, df) * sd / math.sqrt(n)
            out.append([name_of(table, k), g(m), ci_text(m - h, m + h), g(t, 4), g(df), p_text(p), stars(p)])
            rows.append(f"{name_of(table, k)}: mean {g(m, 4)} differs from {g(mu)} ({p_text(p)})." if p < alpha else f"{name_of(table, k)}: no evidence the mean differs from {g(mu)} ({p_text(p)}).")
        tab = {"title": f"One-sample t-test against {g(mu)}", "columns": ["Data set", "Mean", "95% CI of mean", "t", "df", "P value", "Summary"], "rows": out}
        return result("One-sample t-test", " ".join(rows), [{"name": "Summary", "tables": [tab]}], checks,
                      methods=f"Each mean was compared with {g(mu)} by a two-tailed one-sample t-test (α = {alpha:g}) in Datum Plot (SciPy).",
                      code=f"from scipy import stats\nprint(stats.ttest_1samp(v, {mu}))")
    if len(ks) < 2:
        raise ValueError("Choose two data sets to compare.")
    if len(ks) > 2:
        checks.append((None, f"Only the first two data sets ({name_of(table, ks[0])} and {name_of(table, ks[1])}) are compared; use one-way ANOVA for three or more."))
    a_, b_ = ks[0], ks[1]
    na, nb = name_of(table, a_), name_of(table, b_)
    va, n1, m1, s1 = summary(table, a_)
    vb, n2, m2, s2 = summary(table, b_)
    eff, plots = [], []
    if test in ("paired", "ratio"):
        x, y = pairs_of(table, a_, b_)
        if test == "ratio":
            if np.any(x <= 0) or np.any(y <= 0):
                raise ValueError("A ratio t-test needs positive values.")
            x, y = np.log(x), np.log(y)
        n = len(x)
        if n < 2:
            raise ValueError("A paired test needs at least two rows with values in both data sets.")
        r = st.ttest_rel(y, x)
        d = y - x
        df = n - 1
        h = st.t.ppf(0.975, df) * d.std(ddof=1) / math.sqrt(n)
        t, p = float(r.statistic), float(r.pvalue)
        if test == "ratio":
            what, diff, ci = "Geometric mean of ratios", g(math.exp(d.mean()), 4), ci_text(math.exp(d.mean() - h), math.exp(d.mean() + h))
        else:
            what, diff, ci = "Mean of differences", g(d.mean()), ci_text(d.mean() - h, d.mean() + h)
        rc = float(np.corrcoef(x, y)[0, 1]) if n > 2 else float("nan")
        rows = [["Test", "Ratio paired t-test" if test == "ratio" else "Paired t-test"], ["t, df", f"t = {g(t, 4)}, df = {df}"], ["P value (two-tailed)", pv(p)], ["Significant?", f"{'Yes' if p < alpha else 'No'} ({stars(p)})"],
                [f"{what} ({nb} − {na})" if test != "ratio" else f"{what} ({nb} / {na})", diff], ["95% CI", ci], ["Number of pairs", g(n)], ["Correlation of the pairs (r)", g(rc, 4)]]
        eff = effect_rows(x, y, paired=True)
        sw = st.shapiro(d) if n >= 3 else None
        if sw is not None:
            checks.append((sw.pvalue > alpha, f"The differences {'look' if sw.pvalue > alpha else 'do not look'} normally distributed (Shapiro-Wilk {p_text(sw.pvalue)}).{' Consider the Wilcoxon test.' if sw.pvalue <= alpha else ''}"))
        if n > 2 and rc < 0.2:
            checks.append((None, "The pairs are hardly correlated, so pairing gains little; check that the rows really match."))
        plots.append(small_plot("Before and after", lambda ax: ([ax.plot([0, 1], [u, v], "-o", ms=3, color="#8D9AAB", lw=0.8) for u, v in zip(*pairs_of(table, a_, b_))], ax.set_xticks([0, 1], [na[:12], nb[:12]]))))
        ans = f"{'The ratio' if test == 'ratio' else 'The mean difference'} {nb} vs {na} is {diff} (95% CI {ci}); {'significant' if p < alpha else 'not significant'}, {p_text(p)}."
        methods = f"{na} and {nb} were compared by a two-tailed {'ratio ' if test == 'ratio' else ''}paired t-test (α = {alpha:g}) in Datum Plot (SciPy)."
        code = "from scipy import stats\nprint(stats.ttest_rel(after, before))"
    else:
        welch = bool(o.get("welch", True))
        if va is not None and vb is not None:
            need(va, n1, "A t-test"); need(vb, n2, "A t-test")
        r = st.ttest_ind_from_stats(m2, s2, n2, m1, s1, n1, equal_var=not welch)
        t, p = float(r.statistic), float(r.pvalue)
        if welch:
            v1, v2 = s1 * s1 / n1, s2 * s2 / n2
            df = (v1 + v2) ** 2 / (v1 * v1 / (n1 - 1) + v2 * v2 / (n2 - 1))
            se = math.sqrt(v1 + v2)
        else:
            df = n1 + n2 - 2
            se = math.sqrt(((n1 - 1) * s1 * s1 + (n2 - 1) * s2 * s2) / df * (1 / n1 + 1 / n2))
        h = st.t.ppf(0.975, df) * se
        diff = m2 - m1
        rows = [["Test", "Welch's t-test (unequal SDs)" if welch else "Student's t-test (equal SDs)"], ["t, df", f"t = {g(t, 4)}, df = {g(df, 4)}"], ["P value (two-tailed)", pv(p)],
                ["Significant?", f"{'Yes' if p < alpha else 'No'} ({stars(p)})"], [f"Mean of {na}", g(m1)], [f"Mean of {nb}", g(m2)], [f"Difference ({nb} − {na})", g(diff)], ["95% CI of the difference", ci_text(diff - h, diff + h)],
                ["SD of each", f"{g(s1)}, {g(s2)}"], ["n of each", f"{n1}, {n2}"]]
        if va is not None and vb is not None:
            eff = effect_rows(va, vb)
            f = st.levene(va, vb, center="median")
            if not welch and f.pvalue < alpha:
                checks.append((False, f"The SDs differ (Brown-Forsythe {p_text(f.pvalue)}); Welch's t-test is safer."))
            for v, nm in ((va, na), (vb, nb)):
                if len(v) >= 3:
                    sw = st.shapiro(v)
                    checks.append((sw.pvalue > alpha, f"{nm} {'looks' if sw.pvalue > alpha else 'does not look'} normally distributed (Shapiro-Wilk {p_text(sw.pvalue)})."))
            plots.append(dot_plot("The two groups", [va, vb], [na, nb]))
        else:
            checks.append((None, "Calculated from the entered means, SDs and Ns."))
        brackets.append([a_, b_, p])
        ans = f"{nb} − {na} = {g(diff, 4)} (95% CI {g(diff - h, 4)} to {g(diff + h, 4)}); {'significant' if p < alpha else 'not significant'}, {p_text(p)}."
        methods = f"{na} and {nb} were compared by a two-tailed {'Welch' if welch else 'Student'} unpaired t-test (α = {alpha:g}) in Datum Plot (SciPy)."
        code = f"from scipy import stats\nprint(stats.ttest_ind(b, a, equal_var={not welch}))"
    if eff:
        d = float(eff[0][1]) if eff[0][1] not in ("—",) else float("nan")
        rows.append(["Effect size", f"{eff[0][0]} = {eff[0][1]} ({size_word(d)})" if math.isfinite(d) else "—"])
    tabs = [{"name": "Summary", "tables": [{"title": f"{na} vs {nb}", "columns": ["", "Value"], "rows": rows}]}]
    if eff:
        tabs.append({"name": "Effect size", "tables": [{"title": "Effect sizes (95% CI)", "columns": ["", "Value", "95% CI"], "rows": eff}]})
    return result("t-test", ans, tabs, checks, methods=methods, code=code, plots=plots, brackets=brackets if test == "unpaired" else [[a_, b_, p]],
                  legend="Bars show mean and SD; stars: * P < 0.05, ** P < 0.01, *** P < 0.001.")


# ---------- nonparametric tests (B5) ----------
def dunn(groups, method="bonferroni"):
    """Dunn's test after Kruskal-Wallis: [(i, j, mean rank difference, z, adjusted P)]."""
    allv = np.concatenate(groups)
    ranks = st.rankdata(allv)
    N = len(allv)
    _, t = np.unique(allv, return_counts=True)
    tie = np.sum(t ** 3 - t) / (12 * (N - 1))
    idx = np.cumsum([0] + [len(x) for x in groups])
    mr = [ranks[idx[i]:idx[i + 1]].mean() for i in range(len(groups))]
    out = []
    for i, j in combinations(range(len(groups)), 2):
        se = math.sqrt((N * (N + 1) / 12 - tie) * (1 / len(groups[i]) + 1 / len(groups[j])))
        z = (mr[j] - mr[i]) / se
        out.append([i, j, mr[j] - mr[i], z, 2 * st.norm.sf(abs(z))])
    adj = adjust([x[4] for x in out], method)
    return [x[:4] + [min(1.0, a)] for x, a in zip(out, adj)]


def nonparam(table, ks, o):
    test, alpha = o.get("test", "mw"), float(o.get("alpha", ALPHA))
    names = [name_of(table, k) for k in ks]
    vals = []
    for k in ks:
        v, n, *_ = summary(table, k)
        need(v, n, "A nonparametric test")
        vals.append(v)
    checks, tabs, brackets, plots = [], [], [], [dot_plot("The groups", vals, names)]
    meds = [["Median", *[g(np.median(v)) for v in vals]], ["Number of values", *[g(len(v)) for v in vals]]]
    tabs.append({"title": "Medians", "columns": ["", *names], "rows": meds})
    if test in ("mw", "ks", "wilcoxon"):
        if len(ks) < 2:
            raise ValueError("Choose two data sets to compare.")
        a, b = vals[0], vals[1]
        if test == "mw":
            r = st.mannwhitneyu(b, a, alternative="two-sided")
            hl = float(np.median(np.subtract.outer(b, a)))
            rows = [["Test", "Mann-Whitney U"], ["U", g(float(r.statistic))], ["P value (two-tailed)", pv(r.pvalue)], ["Significant?", f"{'Yes' if r.pvalue < alpha else 'No'} ({stars(r.pvalue)})"],
                    [f"Hodges-Lehmann difference ({names[1]} − {names[0]})", g(hl)]]
            p, what = float(r.pvalue), f"the distributions of {names[0]} and {names[1]}"
        elif test == "ks":
            r = st.ks_2samp(a, b)
            rows = [["Test", "Kolmogorov-Smirnov (two samples)"], ["D", g(float(r.statistic), 4)], ["P value", pv(r.pvalue)], ["Significant?", f"{'Yes' if r.pvalue < alpha else 'No'} ({stars(r.pvalue)})"]]
            p, what = float(r.pvalue), f"the cumulative distributions of {names[0]} and {names[1]}"
        else:
            x, y = pairs_of(table, ks[0], ks[1])
            if len(x) < 2:
                raise ValueError("The Wilcoxon test needs at least two rows with values in both data sets.")
            d = y - x
            exact = len(np.unique(np.abs(d))) == len(d) and np.all(d != 0) and len(d) <= 50
            r = st.wilcoxon(y, x, correction=True, method="exact" if exact else "approx")  # as R: normal approximation with ties
            rows = [["Test", "Wilcoxon matched-pairs signed rank"], ["W (sum of positive ranks)", g(float(r.statistic))], ["P value (two-tailed)", pv(r.pvalue)],
                    ["Significant?", f"{'Yes' if r.pvalue < alpha else 'No'} ({stars(r.pvalue)})"], ["Median of differences", g(np.median(y - x))], ["Number of pairs", g(len(x))]]
            p, what = float(r.pvalue), f"the paired values of {names[0]} and {names[1]}"
        brackets.append([ks[0], ks[1], p])
        tabs.insert(0, {"title": f"{names[0]} vs {names[1]}", "columns": ["", "Value"], "rows": rows})
        ans = f"{'There is' if p < alpha else 'No'} evidence that {what} differ ({p_text(p)})."
        meth = {"mw": "a two-tailed Mann-Whitney test", "ks": "a two-sample Kolmogorov-Smirnov test", "wilcoxon": "a two-tailed Wilcoxon matched-pairs signed rank test"}[test]
    else:
        if len(ks) < 2:
            raise ValueError("Choose at least two data sets.")
        if test == "friedman":
            cols = [column(table, k) for k in ks]
            rowsv = [[c[r] for c in cols] for r in range(table["rows"]) if all(c[r] is not None for c in cols)]
            if len(rowsv) < 2 or len(ks) < 3:
                raise ValueError("Friedman's test needs three or more data sets and two or more complete rows.")
            m = np.array(rowsv)
            r = st.friedmanchisquare(*m.T)
            p = float(r.pvalue)
            rows = [["Test", "Friedman (repeated measures)"], ["Friedman statistic", g(float(r.statistic), 4)], ["P value", pv(p)], ["Significant?", f"{'Yes' if p < alpha else 'No'} ({stars(p)})"], ["Number of rows (subjects)", g(len(m))]]
            meth = "Friedman's test"
        else:
            r = st.kruskal(*vals)
            p = float(r.pvalue)
            rows = [["Test", "Kruskal-Wallis"], ["Kruskal-Wallis H", g(float(r.statistic), 4)], ["Degrees of freedom", g(len(vals) - 1)], ["P value", pv(p)], ["Significant?", f"{'Yes' if p < alpha else 'No'} ({stars(p)})"]]
            meth = "the Kruskal-Wallis test followed by Dunn's multiple comparisons (Bonferroni-adjusted)"
            dn = dunn(vals)
            tabs.append({"title": "Dunn's multiple comparisons", "columns": ["Comparison", "Mean rank difference", "z", "Adjusted P", "Summary"],
                         "rows": [[f"{names[i]} vs {names[j]}", g(d), g(z, 4), pv(q), stars(q)] for i, j, d, z, q in dn]})
            brackets += [[ks[i], ks[j], q] for i, j, _, _, q in dn]
        tabs.insert(0, {"title": "Test", "columns": ["", "Value"], "rows": rows})
        ans = f"{'The groups differ' if p < alpha else 'No evidence the groups differ'} ({p_text(p)})."
    return result("Nonparametric test", ans, [{"name": "Summary", "tables": tabs}], checks, plots=plots, brackets=brackets,
                  methods=f"Groups were compared with {meth} (α = {alpha:g}) in Datum Plot (SciPy).", code="from scipy import stats\nprint(stats.mannwhitneyu(b, a), stats.kruskal(a, b, c))",
                  legend="Lines show medians; stars: * P < 0.05, ** P < 0.01, *** P < 0.001.")


# ---------- one-way ANOVA, multiple comparisons, effect sizes (B6, B7, B8) ----------
def anova(table, ks, o):
    kind, post, alpha = o.get("anova", "ordinary"), o.get("posthoc", "tukey"), float(o.get("alpha", ALPHA))
    if len(ks) < 2:
        raise ValueError("Choose at least two data sets.")
    names = [name_of(table, k) for k in ks]
    sm_ = [summary(table, k) for k in ks]
    raw = all(s[0] is not None for s in sm_)
    if kind == "rm" and not raw:
        raise ValueError("Repeated measures ANOVA needs the individual values.")
    n = np.array([s[1] for s in sm_], float)
    m = np.array([s[2] for s in sm_], float)
    sd = np.array([s[3] for s in sm_], float)
    if np.any(n < 2):
        raise ValueError("Every group needs at least two values.")
    checks, plots, tabs, brackets = [], [], [], []
    N, kk = n.sum(), len(ks)
    grand = float((n * m).sum() / N)
    ssb = float((n * (m - grand) ** 2).sum())
    ssw = float(((n - 1) * sd ** 2).sum())
    if kind == "rm":
        cols = [column(table, k) for k in ks]
        M = np.array([[c[r] for c in cols] for r in range(table["rows"]) if all(c[r] is not None for c in cols)])
        s_, nr = M.shape[0], M.shape[0]
        if s_ < 2:
            raise ValueError("Repeated measures ANOVA needs two or more complete rows (subjects).")
        gm = M.mean()
        ss_t = float(((M.mean(0) - gm) ** 2).sum() * nr)
        ss_s = float(((M.mean(1) - gm) ** 2).sum() * kk)
        ss_e = float(((M - gm) ** 2).sum()) - ss_t - ss_s
        df1, df2 = kk - 1, (kk - 1) * (nr - 1)
        F = (ss_t / df1) / (ss_e / df2) if ss_e > 0 else float("inf")
        # Geisser-Greenhouse epsilon from the covariance of the treatments.
        S = np.cov(M.T)
        C = np.eye(kk) - 1 / kk
        D = C @ S @ C
        eps = min(1.0, float(np.trace(D) ** 2 / ((kk - 1) * np.sum(D * D)))) if np.sum(D * D) > 0 else 1.0
        p = float(st.f.sf(F, df1 * eps, df2 * eps))
        rows = [["Test", "Repeated measures one-way ANOVA (Geisser-Greenhouse corrected)"], ["F", g(F, 4)], ["DFn, DFd", f"{g(df1 * eps, 4)}, {g(df2 * eps, 4)}"], ["Geisser-Greenhouse ε", g(eps, 4)], ["P value", pv(p)],
                ["Significant?", f"{'Yes' if p < alpha else 'No'} ({stars(p)})"], ["Number of subjects", g(nr)]]
        ss_tot = ss_t + ss_s + ss_e
        tabs.append({"title": "ANOVA table", "columns": ["Source", "SS", "DF", "MS", "F", "P"], "rows": [["Treatment (between columns)", g(ss_t), g(df1), g(ss_t / df1), g(F, 4), pv(p)],
                     ["Subjects (rows)", g(ss_s), g(nr - 1), g(ss_s / (nr - 1)), "", ""], ["Residual", g(ss_e), g(df2), g(ss_e / df2), "", ""], ["Total", g(ss_tot), g(kk * nr - 1), "", "", ""]]})
        eta = ss_t / (ss_t + ss_e) if ss_t + ss_e > 0 else float("nan")
        mse, dfe = ss_e / df2, df2
        meth = "repeated measures one-way ANOVA with the Geisser-Greenhouse correction"
    else:
        df1, df2 = kk - 1, N - kk
        if kind in ("welch", "bf") and raw:
            from statsmodels.stats.oneway import anova_oneway
            r = anova_oneway([s[0] for s in sm_], use_var="unequal" if kind == "welch" else "bf", welch_correction=True)
            F, p = float(r.statistic), float(r.pvalue)
            d1, d2 = (float(x) for x in r.df)
            rows = [["Test", "Welch's ANOVA" if kind == "welch" else "Brown-Forsythe ANOVA"], ["F", g(F, 4)], ["DFn, DFd", f"{g(d1, 4)}, {g(d2, 4)}"], ["P value", pv(p)], ["Significant?", f"{'Yes' if p < alpha else 'No'} ({stars(p)})"]]
            meth = "Welch's ANOVA" if kind == "welch" else "Brown-Forsythe ANOVA"
        else:
            F = (ssb / df1) / (ssw / df2)
            p = float(st.f.sf(F, df1, df2))
            rows = [["Test", "Ordinary one-way ANOVA"], ["F", g(F, 4)], ["DFn, DFd", f"{g(df1)}, {g(df2)}"], ["P value", pv(p)], ["Significant?", f"{'Yes' if p < alpha else 'No'} ({stars(p)})"]]
            meth = "ordinary one-way ANOVA"
        tabs.append({"title": "ANOVA table", "columns": ["Source", "SS", "DF", "MS", "F", "P"], "rows": [["Treatment (between columns)", g(ssb), g(df1), g(ssb / df1), g((ssb / df1) / (ssw / df2), 4), pv(float(st.f.sf((ssb / df1) / (ssw / df2), df1, df2)))],
                     ["Residual (within columns)", g(ssw), g(df2), g(ssw / df2), "", ""], ["Total", g(ssb + ssw), g(N - 1), "", "", ""]]})
        eta = ssb / (ssb + ssw)
        mse, dfe = ssw / df2, df2
        if raw:
            bf, bart = st.levene(*[s[0] for s in sm_], center="median"), st.bartlett(*[s[0] for s in sm_])
            ok = bf.pvalue > alpha
            checks.append((ok if kind == "ordinary" else True, f"The SDs {'are similar' if ok else 'differ'} (Brown-Forsythe {p_text(bf.pvalue)}; Bartlett {p_text(bart.pvalue)}).{' Consider Welch’s ANOVA.' if not ok and kind == 'ordinary' else ''}"))
            res = np.concatenate([s[0] - s[2] for s in sm_])
            if len(res) >= 3:
                sw = st.shapiro(res)
                checks.append((sw.pvalue > alpha, f"The residuals {'look' if sw.pvalue > alpha else 'do not look'} normally distributed (Shapiro-Wilk {p_text(sw.pvalue)}).{'' if sw.pvalue > alpha else ' Consider the Kruskal-Wallis test.'}"))
            rows.append(["Brown-Forsythe test (equal SDs?)", p_text(bf.pvalue)])
    omega = (ssb - df1 * (ssw / max(N - kk, 1))) / (ssb + ssw + ssw / max(N - kk, 1)) if kind != "rm" else float("nan")
    rows += [["R squared (η²)", g(eta, 4)]] + ([["ω²", g(omega, 4)]] if kind != "rm" else [])
    tabs.insert(0, {"title": "One-way ANOVA", "columns": ["", "Value"], "rows": rows})
    tabs.append({"title": "Groups", "columns": ["", *names], "rows": [["Mean", *[g(x) for x in m]], ["SD", *[g(x) for x in sd]], ["n", *[g(int(x)) for x in n]]]})
    comps = []
    if post != "none":
        comps, label = posthoc(table, ks, sm_, post, mse, dfe, kind)
        tabs.append({"title": label, "columns": ["Comparison", "Mean difference", "95% CI", "Adjusted P", "Summary"], "rows": [[f"{names[i]} vs {names[j]}", g(d), ci, pv(q), stars(q)] for i, j, d, ci, q in comps]})
        brackets = [[ks[i], ks[j], q] for i, j, _, _, q in comps]
    if o.get("trend") and kk > 2:
        w = np.arange(kk) - (kk - 1) / 2
        L = float((w * m).sum())
        se = math.sqrt(mse * float((w * w / n).sum()))
        t = L / se
        pt = 2 * float(st.t.sf(abs(t), dfe))
        tabs.append({"title": "Test for linear trend (columns in order)", "columns": ["", "Value"], "rows": [["Slope of the trend (per column)", g(L / float((w * w).sum()))], ["t", g(t, 4)], ["P value", pv(pt)], ["Significant?", f"{'Yes' if pt < alpha else 'No'} ({stars(pt)})"]]})
    if raw:
        plots.append(dot_plot("The groups", [s[0] for s in sm_], names))
    sig = [f"{names[i]} vs {names[j]}" for i, j, *_, q in comps if q < alpha]
    ans = f"The means {'differ' if p < alpha else 'do not differ significantly'} ({meth}, F = {g(F, 4)}, {p_text(p)})." + (f" Different pairs: {', '.join(sig)}." if sig else "")
    return result("One-way ANOVA", ans, [{"name": "Summary", "tables": tabs}], checks, plots=plots, brackets=brackets,
                  methods=f"Groups were compared by {meth}{'' if post == 'none' else ' with ' + POSTNAME[post] + ' multiple comparisons'} (α = {alpha:g}) in Datum Plot (SciPy, statsmodels).",
                  legend="Stars: * P < 0.05, ** P < 0.01, *** P < 0.001 (multiplicity-adjusted).",
                  code="from scipy import stats\nprint(stats.f_oneway(a, b, c))\nprint(stats.tukey_hsd(a, b, c))")


POSTNAME = {"tukey": "Tukey's", "dunnett": "Dunnett's (each against the first group)", "bonferroni": "Bonferroni", "sidak": "Šidák", "holm": "Holm-Šidák", "lsd": "Fisher's LSD (unadjusted)"}


def posthoc(table, ks, sm_, post, mse, dfe, kind):
    """Multiple comparisons after ANOVA: [(i, j, difference, CI text, adjusted P)] and a title."""
    kk = len(ks)
    m = [s[2] for s in sm_]
    n = [s[1] for s in sm_]
    raw = all(s[0] is not None for s in sm_)
    if kind == "rm" and post in ("tukey", "dunnett"):
        post = "holm"
    if post == "tukey" and raw:
        r = st.tukey_hsd(*[s[0] for s in sm_])
        ci = r.confidence_interval(0.95)
        return [(i, j, m[j] - m[i], ci_text(-ci.high[i, j], -ci.low[i, j]), float(r.pvalue[i, j])) for i, j in combinations(range(kk), 2)], "Tukey's multiple comparisons"
    if post == "dunnett" and raw:
        r = st.dunnett(*[s[0] for s in sm_[1:]], control=sm_[0][0])
        ci = r.confidence_interval(0.95)
        return [(0, j, m[j] - m[0], ci_text(ci.low[j - 1], ci.high[j - 1]), float(r.pvalue[j - 1])) for j in range(1, kk)], "Dunnett's multiple comparisons (against the first group)"
    pairs = list(combinations(range(kk), 2)) if post != "dunnett" else [(0, j) for j in range(1, kk)]
    out = []
    for i, j in pairs:
        if kind == "rm":
            x, y = pairs_of(table, ks[i], ks[j])
            d = y - x
            se, df = d.std(ddof=1) / math.sqrt(len(d)), len(d) - 1
            diff = float(d.mean())
        else:
            se, df, diff = math.sqrt(mse * (1 / n[i] + 1 / n[j])), dfe, m[j] - m[i]
        out.append([i, j, diff, se, df, 2 * float(st.t.sf(abs(diff / se), df)) if se > 0 else float("nan")])
    adj = adjust([x[5] for x in out], {"tukey": "holm", "dunnett": "holm"}.get(post, post))
    mult = {"bonferroni": len(out), "sidak": None}.get(post)
    res = []
    for (i, j, diff, se, df, _), q in zip(out, adj):
        a = 0.05 / mult if mult else 1 - 0.95 ** (1 / len(out)) if post in ("sidak", "holm") else 0.05
        h = st.t.ppf(1 - a / 2, df) * se
        res.append((i, j, diff, ci_text(diff - h, diff + h), float(q)))
    return res, f"{POSTNAME.get(post, 'Holm-Šidák')} multiple comparisons"


# ---------- correlation (B16) ----------
def correlation(table, ks, o):
    alpha = float(o.get("alpha", ALPHA))
    xy = table.get("kind", "xy") == "xy" and not o.get("between")
    pairs = []
    if xy:
        from .analysis import points
        for k in ks:
            x, y, _ = points(table, k, {"points": "each"})
            pairs.append((table.get("xTitle") or "X", name_of(table, k), x, y))
    else:
        if len(ks) < 2:
            raise ValueError("Choose at least two data sets to correlate.")
        for a, b in combinations(ks, 2):
            x, y = pairs_of(table, a, b)
            pairs.append((name_of(table, a), name_of(table, b), x, y))
    rows, plots, ans = [], [], []
    for i, (na, nb, x, y) in enumerate(pairs):
        n = len(x)
        if n < 3:
            rows.append([f"{na} vs {nb}", "—", "—", "—", "—", "—", g(n)]); continue
        r, p = st.pearsonr(x, y)
        z, se = math.atanh(min(max(r, -0.999999), 0.999999)), 1 / math.sqrt(n - 3) if n > 3 else float("inf")
        lo, hi = math.tanh(z - Z95 * se), math.tanh(z + Z95 * se)
        rs, ps = st.spearmanr(x, y)
        tau, pk = st.kendalltau(x, y)
        rows.append([f"{na} vs {nb}", g(r, 4), ci_text(lo, hi), p_text(p), f"{g(rs, 4)} ({p_text(ps)})", f"{g(tau, 4)} ({p_text(pk)})", g(n)])
        ans.append(f"{na} vs {nb}: r = {g(r, 4)} (95% CI {g(lo, 3)} to {g(hi, 3)}), {p_text(p)}.")
        if i < 6:
            plots.append(small_plot(f"{nb} vs {na}"[:40], lambda ax, x=x, y=y, c=COLORS[i % 8]: (ax.plot(x, y, "o", ms=3.2, color=c), ax.set_xlabel(na[:20]), ax.set_ylabel(nb[:20]))))
    tabs = [{"title": "Correlation", "columns": ["Pair", "Pearson r", "95% CI of r", "P value", "Spearman rs", "Kendall τ", "Number of pairs"], "rows": rows}]
    if not xy and len(ks) > 2:
        cols = [column(table, k) for k in ks]
        mat = [[name_of(table, a)] + [g(st.pearsonr(*pairs_of(table, a, b))[0], 3) if a != b and len(pairs_of(table, a, b)[0]) > 2 else "1" if a == b else "—" for b in ks] for a in ks]
        tabs.append({"title": "Correlation matrix (Pearson r)", "columns": ["", *[name_of(table, k) for k in ks]], "rows": mat})
        del cols
    return result("Correlation", " ".join(ans) or "Not enough pairs.", [{"name": "Summary", "tables": tabs}], [(None, "Correlation measures how two variables move together; it does not show that one causes the other.")], plots=plots,
                  methods=f"Pearson's r (with a 95% CI from Fisher's z), Spearman's rank and Kendall's τ correlations were calculated in Datum Plot (SciPy), α = {alpha:g}.",
                  code="from scipy import stats\nprint(stats.pearsonr(x, y), stats.spearmanr(x, y), stats.kendalltau(x, y))")


# ---------- power and sample size (B23) ----------
def power(table, ks, o):
    from statsmodels.stats import power as pw
    test, alpha, want = o.get("test", "t2"), float(o.get("alpha", ALPHA)), float(o.get("power", 0.8))
    eff, src = o.get("effect"), "entered"
    eff = float(eff) if eff not in (None, "") else None
    if eff is None:
        src = "from the data"
        sm_ = [summary(table, k) for k in ks]
        if test in ("t2", "paired") and len(sm_) >= 2:
            if test == "paired":
                x, y = pairs_of(table, ks[0], ks[1])
                d = y - x
                eff = abs(d.mean() / d.std(ddof=1)) if len(d) > 2 and d.std(ddof=1) > 0 else None
            else:
                (_, n1, m1, s1), (_, n2, m2, s2) = sm_[:2]
                sp = math.sqrt(((n1 - 1) * s1 * s1 + (n2 - 1) * s2 * s2) / max(n1 + n2 - 2, 1))
                eff = abs(m2 - m1) / sp if sp > 0 else None
        elif test == "anova" and len(sm_) >= 2:
            m = np.array([s[2] for s in sm_]); sd = np.array([s[3] for s in sm_])
            eff = float(m.std() / math.sqrt(np.mean(sd ** 2))) if np.all(sd > 0) else None
        if eff is None:
            raise ValueError("Type an effect size, or choose data sets that give one.")
    kk = max(2, len(ks)) if test == "anova" else 2
    solver = {"t2": pw.TTestIndPower(), "paired": pw.TTestPower(), "anova": pw.FTestAnovaPower(), "prop": pw.NormalIndPower()}[test]
    kw = {"k_groups": kk} if test == "anova" else {}
    have = o.get("n")
    have = int(float(have)) if have not in (None, "") else None
    def n_for(p):
        n = float(solver.solve_power(effect_size=eff, alpha=alpha, power=p, **kw))
        return n / kk if test == "anova" else n
    def pow_for(n):
        return float(solver.power(eff, n * kk if test == "anova" else n, alpha, **kw))
    unit = {"t2": "per group", "paired": "pairs", "anova": "per group", "prop": "per group"}[test]
    ename = {"t2": "Cohen's d", "paired": "Cohen's dz", "anova": "Cohen's f", "prop": "Cohen's h"}[test]
    rows = [["Test", {"t2": "Unpaired t-test", "paired": "Paired t-test", "anova": f"One-way ANOVA, {kk} groups", "prop": "Two proportions"}[test]], [f"Effect size ({ename}, {src})", g(eff, 4)], ["α (two-tailed)", g(alpha)]]
    if have:
        pw_ = pow_for(have)
        rows += [[f"Sample size ({unit})", g(have)], ["Power", f"{g(100 * pw_, 3)}%"]]
        ans = f"With n = {have} {unit}, the power to detect {ename} = {g(eff, 3)} is {g(100 * pw_, 3)}%."
    else:
        need_n = math.ceil(n_for(want))
        rows += [["Power wanted", f"{g(100 * want, 3)}%"], [f"Sample size needed ({unit})", g(need_n)]]
        ans = f"To detect {ename} = {g(eff, 3)} with {g(100 * want, 3)}% power at α = {g(alpha)}, you need n = {need_n} {unit}."
    ns = np.arange(2, max(40, int((have or n_for(want)) * 2.5)) + 1)
    curve = [pow_for(n) for n in ns]
    plot = small_plot("Power against sample size", lambda ax: (ax.plot(ns, np.array(curve) * 100, color=COLORS[0], lw=1.4), ax.axhline(100 * want, color="#8D9AAB", lw=0.8, ls="--"), ax.set_xlabel(f"n {unit}"), ax.set_ylabel("Power (%)"), ax.set_ylim(0, 100)))
    table_rows = [[g(int(n)), f"{g(100 * pow_for(n), 3)}%"] for n in [n for n in (3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 75, 100) if n <= ns[-1]]]
    return result("Power and sample size", ans, [{"name": "Summary", "tables": [{"title": "Power analysis", "columns": ["", "Value"], "rows": rows}, {"title": "Power for other sample sizes", "columns": [f"n {unit}", "Power"], "rows": table_rows}]}],
                  [(None, "Effect sizes: about 0.2 is small, 0.5 medium and 0.8 large for d (0.1, 0.25 and 0.4 for f).")], plots=[plot],
                  methods=f"Sample size was calculated for a two-tailed {rows[0][1].lower()} (α = {g(alpha)}, effect size {ename} = {g(eff, 3)}) with statsmodels in Datum Plot.",
                  code=f"from statsmodels.stats.power import TTestIndPower\nprint(TTestIndPower().solve_power(effect_size={g(eff, 4)}, alpha={alpha}, power={want}))")


# ---------- two-way ANOVA (B15) ----------
def twoway(table, ks, o):
    """Two-way ANOVA of a grouped table: rows are one factor, data sets the other, replicates in each
    cell. Type III sums of squares (sum-to-zero contrasts), so unbalanced designs are handled as in
    Prism and R's car::Anova; then multiple comparisons within each row (or within each data set)."""
    import pandas as pd
    import statsmodels.formula.api as smf
    from statsmodels.stats.anova import anova_lm
    alpha, post, within = float(o.get("alpha", ALPHA)), o.get("posthoc", "sidak"), o.get("compare", "rows")
    if any(table["sets"][k]["entry"] != "rep" for k in ks):
        raise ValueError("Two-way ANOVA needs the individual values; enter them as replicates.")
    rows, cv = cells(table)
    data = [(lab, name_of(table, k), v) for r, lab in rows for k in ks for v in cv.get((k, r), [])]
    if len({d[0] for d in data}) < 2 or len({d[1] for d in data}) < 2:
        raise ValueError("Two-way ANOVA needs at least two rows and two data sets with values.")
    df = pd.DataFrame(data, columns=["A", "B", "y"])
    empty = [f"{lab} × {name_of(table, k)}" for r, lab in rows for k in ks if len(cv.get((k, r), [])) == 0]
    if empty:
        raise ValueError(f"Every row needs values in every data set (missing: {', '.join(empty[:4])}).")
    inter = bool(o.get("interaction", True)) and df.groupby(["A", "B"]).size().min() > 1
    m = smf.ols("y ~ C(A, Sum) * C(B, Sum)" if inter else "y ~ C(A, Sum) + C(B, Sum)", data=df).fit()
    a = anova_lm(m, typ=3)
    rowname, colname = o.get("rowname") or "Row factor", o.get("colname") or "Column factor"
    label = {"C(A, Sum)": rowname, "C(B, Sum)": colname, "C(A, Sum):C(B, Sum)": "Interaction", "Residual": "Residual"}
    tot = float(((df.y - df.y.mean()) ** 2).sum())
    res_ms = float(a.loc["Residual", "sum_sq"] / a.loc["Residual", "df"])
    dfe = float(a.loc["Residual", "df"])
    tab, ans, ps = [], [], {}
    for key in ["C(A, Sum):C(B, Sum)", "C(A, Sum)", "C(B, Sum)", "Residual"]:
        if key not in a.index:
            continue
        ss, d = float(a.loc[key, "sum_sq"]), float(a.loc[key, "df"])
        if key == "Residual":
            tab.append([label[key], g(ss), g(d), g(ss / d), "", "", ""]); continue
        F, p = float(a.loc[key, "F"]), float(a.loc[key, "PR(>F)"])
        ps[key] = p
        tab.append([label[key], g(ss), g(d), g(ss / d), g(F, 4), pv(p), f"{g(100 * ss / tot, 3)}%"])
        ans.append(f"{label[key]}: {'significant' if p < alpha else 'not significant'} ({p_text(p)})")
    eta = [[label[k], g(float(a.loc[k, "sum_sq"]) / (float(a.loc[k, "sum_sq"]) + float(a.loc["Residual", "sum_sq"])), 4)] for k in ps]
    tabs = [{"title": "Two-way ANOVA (Type III)", "columns": ["Source of variation", "SS", "DF", "MS", "F", "P value", "% of total variation"], "rows": tab},
            {"title": "Effect sizes (partial η²)", "columns": ["", "Partial η²"], "rows": eta},
            {"title": "Cell means", "columns": ["", *[name_of(table, k) for k in ks]], "rows": [[lab, *[f"{g(np.mean(cv[(k, r)]))} (n = {len(cv[(k, r)])})" for k in ks]] for r, lab in rows]}]
    checks, brackets = [], []
    if not inter and o.get("interaction", True):
        checks.append((None, "Only one value per cell, so the interaction cannot be tested; the model has main effects only."))
    if ps.get("C(A, Sum):C(B, Sum)", 1) < alpha:
        checks.append((None, "The interaction is significant: the effect of one factor depends on the other, so compare within each row rather than the main effects."))
    groups = [np.asarray(cv[(k, r)]) for r, _ in rows for k in ks if len(cv[(k, r)]) > 1]
    if len(groups) > 1:
        bf = st.levene(*groups, center="median")
        checks.append((bf.pvalue > alpha, f"The SDs of the cells {'are similar' if bf.pvalue > alpha else 'differ'} (Brown-Forsythe {p_text(bf.pvalue)})."))
    if len(m.resid) >= 3:
        sw = st.shapiro(m.resid)
        checks.append((sw.pvalue > alpha, f"The residuals {'look' if sw.pvalue > alpha else 'do not look'} normally distributed (Shapiro-Wilk {p_text(sw.pvalue)})."))
    if post != "none":
        comps = []
        if within == "rows":
            for r, lab in rows:
                for i, j in combinations(range(len(ks)), 2):
                    a_, b_ = cv[(ks[i], r)], cv[(ks[j], r)]
                    comps.append((f"{lab}: {name_of(table, ks[i])} vs {name_of(table, ks[j])}", ks[i], ks[j], r, np.mean(b_) - np.mean(a_), math.sqrt(res_ms * (1 / len(a_) + 1 / len(b_)))))
        else:
            for k in ks:
                for (ri, li), (rj, lj) in combinations(rows, 2):
                    a_, b_ = cv[(k, ri)], cv[(k, rj)]
                    comps.append((f"{name_of(table, k)}: {li} vs {lj}", None, None, None, np.mean(b_) - np.mean(a_), math.sqrt(res_ms * (1 / len(a_) + 1 / len(b_)))))
        raw = [2 * float(st.t.sf(abs(d / se), dfe)) if se > 0 else float("nan") for *_, d, se in comps]
        adj = adjust(raw, post)
        q = 1 - 0.95 ** (1 / len(comps)) if post in ("sidak", "holm") else 0.05 / len(comps) if post == "bonferroni" else 0.05
        tt = st.t.ppf(1 - q / 2, dfe)
        tabs.append({"title": f"{POSTNAME.get(post, 'Šidák')} multiple comparisons {'within each row' if within == 'rows' else 'within each data set'}", "columns": ["Comparison", "Mean difference", "95% CI", "Adjusted P", "Summary"],
                     "rows": [[c[0], g(c[4]), ci_text(c[4] - tt * c[5], c[4] + tt * c[5]), pv(p), stars(p)] for c, p in zip(comps, adj)]})
        brackets = [[c[1], c[2], float(p), c[3]] for c, p in zip(comps, adj) if c[1] is not None]
    return result("Two-way ANOVA", "; ".join(ans) + ".", [{"name": "Summary", "tables": tabs}], checks, brackets=brackets,
                  methods=f"Data were analysed by two-way ANOVA ({rowname} × {colname}{'' if inter else ', main effects only'}; Type III sums of squares){'' if post == 'none' else ' with ' + POSTNAME.get(post, 'Šidák') + ' multiple comparisons'} (α = {alpha:g}) in Datum Plot (statsmodels).",
                  legend="Bars show mean and SD; stars: * P < 0.05, ** P < 0.01, *** P < 0.001 (multiplicity-adjusted).",
                  code="import statsmodels.formula.api as smf\nfrom statsmodels.stats.anova import anova_lm\nm = smf.ols('y ~ C(A, Sum) * C(B, Sum)', data=df).fit()\nprint(anova_lm(m, typ=3))")


# ---------- contingency tables (B17) ----------
def contingency(table, ks, o):
    """Counts in rows × data sets: chi-square, Fisher's exact test (2 × 2), relative risk and odds ratio."""
    from scipy.stats import contingency as ct
    alpha = float(o.get("alpha", ALPHA))
    rows, cv = cells(table)
    M = np.array([[sum(cv.get((k, r), [0])) for k in ks] for r, _ in rows], float)
    rn, cn = [lab for _, lab in rows], [name_of(table, k) for k in ks]
    if M.shape[0] < 2 or M.shape[1] < 2:
        raise ValueError("A contingency table needs at least two rows and two data sets of counts.")
    if np.any(M < 0) or np.any(M != np.round(M)):
        raise ValueError("Enter counts: whole numbers of zero or more.")
    keep_r, keep_c = M.sum(1) > 0, M.sum(0) > 0
    M, rn, cn = M[keep_r][:, keep_c], [x for x, k in zip(rn, keep_r) if k], [x for x, k in zip(cn, keep_c) if k]
    yates = bool(o.get("yates", False))
    chi2, p, dof, E = st.chi2_contingency(M, correction=yates and M.shape == (2, 2))
    n = M.sum()
    V = math.sqrt(chi2 / (n * (min(M.shape) - 1))) if n > 0 else float("nan")
    rows_out = [["Chi-square" + (" (Yates' correction)" if yates and M.shape == (2, 2) else ""), g(chi2, 4)], ["Degrees of freedom", g(int(dof))], ["P value", pv(p)],
                ["Significant?", f"{'Yes' if p < alpha else 'No'} ({stars(p)})"], ["Cramér's V", g(V, 3)], ["Total count", g(int(n))]]
    checks, tabs = [], []
    small = int(np.sum(E < 5))
    checks.append((small == 0, "Every expected count is 5 or more, so the chi-square test is reliable." if not small else f"{small} expected count{'s are' if small > 1 else ' is'} below 5: {'use Fisher’s exact test.' if M.shape == (2, 2) else 'combine rows or columns, as the chi-square P value may be wrong.'}"))
    ans = f"Chi-square = {g(chi2, 4)}, df = {int(dof)}, {p_text(p)}: the proportions {'differ' if p < alpha else 'do not differ significantly'} between the rows."
    if M.shape == (2, 2):
        (a, b), (c, d) = M
        orr, pf = st.fisher_exact(M)
        rows_out = [["Fisher's exact test, P value (two-tailed)", pv(pf)], ["Significant (Fisher)?", f"{'Yes' if pf < alpha else 'No'} ({stars(pf)})"]] + rows_out
        tab2 = []
        if (a + b) > 0 and (c + d) > 0 and c > 0:
            rr = ct.relative_risk(int(a), int(a + b), int(c), int(c + d))
            lo, hi = rr.confidence_interval(0.95)
            tab2.append([f"Relative risk ({rn[0]} vs {rn[1]})", g(rr.relative_risk, 4), ci_text(lo, hi)])
        if b * c > 0:
            od = ct.odds_ratio(M.astype(int), kind="sample")
            lo, hi = od.confidence_interval(0.95)
            tab2.append(["Odds ratio", g(od.statistic, 4), ci_text(lo, hi)])
        tab2 += [[f"{cn[0]} in {rn[0]}", f"{g(100 * a / (a + b), 4)}%" if a + b else "—", ""], [f"{cn[0]} in {rn[1]}", f"{g(100 * c / (c + d), 4)}%" if c + d else "—", ""],
                 ["Difference of proportions", f"{g(100 * (a / (a + b) - c / (c + d)), 4)}%" if a + b and c + d else "—", ""]]
        if o.get("diagnostic"):
            tab2 += [["Sensitivity", f"{g(100 * a / (a + c), 4)}%" if a + c else "—", ""], ["Specificity", f"{g(100 * d / (b + d), 4)}%" if b + d else "—", ""],
                     ["Positive predictive value", f"{g(100 * a / (a + b), 4)}%" if a + b else "—", ""], ["Negative predictive value", f"{g(100 * d / (c + d), 4)}%" if c + d else "—", ""]]
        tabs.append({"title": "Effect size (95% CI)", "columns": ["", "Value", "95% CI"], "rows": tab2})
        ans = f"Fisher's exact test {p_text(pf)}: {'the proportions differ' if pf < alpha else 'no evidence the proportions differ'}" + (f" (relative risk {tab2[0][1]}, 95% CI {tab2[0][2]})." if tab2 and tab2[0][0].startswith("Relative") else ".")
    tabs.insert(0, {"title": "Test", "columns": ["", "Value"], "rows": rows_out})
    tabs.append({"title": "Observed (expected) counts", "columns": ["", *cn, "Total"], "rows": [[rn[i], *[f"{g(int(M[i, j]))} ({g(E[i, j], 3)})" for j in range(len(cn))], g(int(M[i].sum()))] for i in range(len(rn))]
                 + [["Total", *[g(int(M[:, j].sum())) for j in range(len(cn))], g(int(n))]]})
    tabs.append({"title": "Row percentages", "columns": ["", *cn], "rows": [[rn[i], *[f"{g(100 * M[i, j] / M[i].sum(), 3)}%" if M[i].sum() else "—" for j in range(len(cn))]] for i in range(len(rn))]})
    two = M.shape == (2, 2)
    return result("Contingency", ans, [{"name": "Summary", "tables": tabs}], checks,
                  methods=f"Counts were analysed with {'Fisher’s exact test and ' if two else ''}the chi-square test{' with Yates’ correction' if yates and two else ''} (α = {alpha:g}){', with the relative risk (Koopman CI) and odds ratio' if two else ''} in Datum Plot (SciPy).",
                  code="from scipy import stats\nprint(stats.chi2_contingency(M), stats.fisher_exact(M))")
