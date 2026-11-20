"""Nested data (A8, B20): each group (data set) has sub-columns, one per subgroup (a batch, an animal),
with its replicates down the rows. The nested t-test (two groups) and nested one-way ANOVA test the
groups against the variation between subgroups, not between single replicates."""
import math

import numpy as np
from scipy import stats as st

from . import stats
from .analysis import ALPHA, COLORS, g, name_of, pv, result, small_plot


def subgroups(table, k):
    """The values of each subgroup (sub-column) of group k that has any."""
    c0, w = stats.set_columns(table)[k]
    ex = {tuple(e) for e in table.get("excluded", [])}
    out = []
    for c in range(c0, c0 + (w if table["sets"][k]["entry"] == "rep" else 1)):
        v = [x for x in (stats.value(table, r, c, ex) for r in range(table["rows"])) if x is not None and math.isfinite(x)]
        if v:
            out.append(np.array(v, float))
    return out


def reml_group_test(data, var_s, var_r):
    """0.4.27: the groups' F test from the nested mixed model (REML variances), with Satterthwaite's denominator df
    (as R's lmerTest): exact where the classic F is not, i.e. when subgroups hold different numbers of values.
    data: [(k, [subgroup values…])]. Returns (F, DFn, DFd)."""
    y, gi, sid = [], [], []
    for i, (_, s) in enumerate(data):
        for j, v in enumerate(s):
            y += list(v); gi += [i] * len(v); sid += [(i, j)] * len(v)
    y, a = np.asarray(y, float), len(data)
    X = np.array([[1.0] + [1.0 if g_ == q else 0.0 for q in range(1, a)] for g_ in gi])
    subs = sorted(set(sid))
    Z = np.array([[1.0 if s_ == u else 0.0 for u in subs] for s_ in sid])
    ZZ, I = Z @ Z.T, np.eye(len(y))
    var_s, var_r = max(var_s, 0.0), max(var_r, 1e-300)
    V = var_s * ZZ + var_r * I
    Vi = np.linalg.inv(V)
    C = np.linalg.inv(X.T @ Vi @ X)
    beta = C @ X.T @ Vi @ y
    P = Vi - Vi @ X @ C @ X.T @ Vi
    dV = [ZZ, I] if var_s > 0 else [I]  # a variance on the boundary (0) is held fixed, as lmerTest does
    # the observed information of the REML likelihood (as lmerTest): −0.5 tr(P Vi P Vj) + y'P Vi P Vj P y
    Py = P @ y
    info = np.array([[-0.5 * np.trace(P @ Di @ P @ Dj) + float(Py @ Di @ P @ Dj @ Py) for Dj in dV] for Di in dV])
    Acov = np.linalg.pinv(info)
    L = np.hstack([np.zeros((a - 1, 1)), np.eye(a - 1)])
    LCL = L @ C @ L.T
    F = float(beta @ L.T @ np.linalg.solve(LCL, L @ beta)) / (a - 1)
    w, U = np.linalg.eigh(LCL)
    nus = []
    for m in range(a - 1):  # one Satterthwaite df per eigen-direction, combined (Fai & Cornelius; lmerTest)
        l = U[:, m] @ L
        g_ = np.array([-(l @ C @ X.T @ Vi @ Di @ Vi @ X @ C @ l) for Di in dV])
        nus.append(2 * float(l @ C @ l) ** 2 / float(g_ @ Acov @ g_))
    if a - 1 == 1:
        return F, 1, nus[0]
    E = sum(n_ / (n_ - 2) for n_ in nus if n_ > 2)
    q = a - 1
    return F, q, (2 * E / (E - q)) if E > q else 1.0


def nested(table, ks, o):
    alpha = float(o.get("alpha", ALPHA))
    data = [(k, subgroups(table, k)) for k in ks]
    data = [(k, s) for k, s in data if s]
    a = len(data)
    if a < 2:
        raise ValueError("Enter values for at least two groups, each with its subgroups in sub-columns.")
    if any(len(s) < 2 for _, s in data):
        raise ValueError("Each group needs at least two subgroups (sub-columns) with values: the test compares groups against the spread between subgroups.")
    allv = np.concatenate([np.concatenate(s) for _, s in data])
    N, gm = len(allv), allv.mean()
    nsub = sum(len(s) for _, s in data)
    ss_g = sum(np.concatenate(s).size * (np.concatenate(s).mean() - gm) ** 2 for _, s in data)
    ss_s = sum(len(v) * (v.mean() - np.concatenate(s).mean()) ** 2 for _, s in data for v in s)
    ss_r = sum(((v - v.mean()) ** 2).sum() for _, s in data for v in s)
    df_g, df_s, df_r = a - 1, nsub - a, N - nsub
    if df_r < 1:
        raise ValueError("Each subgroup needs more than one value.")
    ms_g, ms_s, ms_r = ss_g / df_g, ss_s / df_s, ss_r / df_r
    f_g, f_s = ms_g / ms_s if ms_s > 0 else math.inf, ms_s / ms_r if ms_r > 0 else math.inf
    p_g, p_s = float(st.f.sf(f_g, df_g, df_s)), float(st.f.sf(f_s, df_s, df_r))
    rows = [["Between groups", g(ss_g, 5), g(df_g), g(ms_g, 5), f"F = {g(f_g, 4)} (DFn {df_g}, DFd {df_s})", pv(p_g)],
            ["Between subgroups within groups", g(ss_s, 5), g(df_s), g(ms_s, 5), f"F = {g(f_s, 4)} (DFn {df_s}, DFd {df_r})", pv(p_s)],
            ["Residual (within subgroups)", g(ss_r, 5), g(df_r), g(ms_r, 5), "", ""], ["Total", g(ss_g + ss_s + ss_r, 5), g(N - 1), "", "", ""]]
    # Variance components from a mixed model (REML): subgroup as a random effect inside the fixed groups.
    var_s = var_r = None
    try:
        import warnings
        from statsmodels.regression.mixed_linear_model import MixedLM
        obs = [(y, i, f"{i}.{j}") for i, (_, s) in enumerate(data) for j, v in enumerate(s) for y in v]
        X = np.array([[1.0] + [1.0 if i == q else 0.0 for q in range(1, a)] for _, i, _ in obs])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = MixedLM(np.array([y for y, _, _ in obs]), X, groups=[s_ for _, _, s_ in obs]).fit(reml=True)
        var_s, var_r = float(np.asarray(m.cov_re)[0, 0]), float(m.scale)
    except Exception:
        n0 = (N - sum(sum(len(v) ** 2 for v in s) / sum(len(v) for v in s) for _, s in data)) / max(nsub - a, 1)  # values per subgroup (n when balanced)
        var_s, var_r = max(0.0, (ms_s - ms_r) / n0), ms_r
    icc = var_s / (var_s + var_r) if var_s + var_r > 0 else float("nan")
    means = [[name_of(table, k), g(len(s)), g(sum(len(v) for v in s)), g(np.concatenate(s).mean(), 5), g(np.mean([v.mean() for v in s]), 5),
              g(np.std([v.mean() for v in s], ddof=1), 4)] for k, s in data]
    tables = [{"title": "Nested ANOVA" if a > 2 else "Nested t-test", "columns": ["Source", "SS", "DF", "MS", "F", "P value"], "rows": rows},
              {"title": "Groups", "columns": ["Group", "Subgroups", "Values", "Mean", "Mean of subgroup means", "SD of subgroup means"], "rows": means},
              {"title": "Variance components (mixed model, REML)", "columns": ["", "Value"], "rows": [["Between subgroups", g(var_s, 4)], ["Within subgroups (residual)", g(var_r, 4)],
                                                                                                    ["Intraclass correlation", g(icc, 3)]]}]
    names = [name_of(table, k) for k, _ in data]
    # 0.4.27: subgroups with different numbers of values make the classic F (groups over subgroups) only approximate;
    # the groups are then tested from the mixed model with Satterthwaite's df, as R (lmerTest) and other programs do.
    unequal = len({len(v) for _, s in data for v in s}) > 1
    dfd = df_s
    if unequal and N <= 4000:
        try:
            f_g, _, dfd = reml_group_test(data, var_s, var_r)
            p_g = float(st.f.sf(f_g, df_g, dfd))
            tables[0]["rows"][0][4], tables[0]["rows"][0][5] = f"F = {g(f_g, 4)} (DFn {df_g}, DFd {g(dfd, 4)}; mixed model)", pv(p_g)
        except (np.linalg.LinAlgError, ValueError, ZeroDivisionError):
            unequal = False
    if a == 2:
        t = math.copysign(math.sqrt(f_g), np.concatenate(data[1][1]).mean() - np.concatenate(data[0][1]).mean())
        tables[0]["rows"].insert(0, ["t (from F)", "", g(dfd, 4), "", f"t = {g(t, 4)}", pv(p_g)])
    ans = (f"The {'two ' if a == 2 else ''}groups {'differ' if p_g < alpha else 'do not differ significantly'} (F = {g(f_g, 4)}, DFn {df_g}, DFd {g(dfd, 4)}, P {pv(p_g) if p_g < 1e-4 else '= ' + pv(p_g)}), "
           f"tested against the variation between {nsub} subgroups. {100 * icc:.0f}% of the variation lies between subgroups (intraclass correlation {g(icc, 2)}).")
    checks = [(None, "The groups are tested against the subgroups (DFd = subgroups − groups), not against every replicate: replicates within a subgroup are not independent."),
              (p_s >= alpha, f"Subgroups within groups {'do not differ significantly' if p_s >= alpha else 'differ'} (P {pv(p_s) if p_s < 1e-4 else '= ' + pv(p_s)}){'' if p_s >= alpha else ': the nested test is the right one'}.")]
    sizes = {len(v) for _, s in data for v in s} | {len(s) for _, s in data}
    if len({len(v) for _, s in data for v in s}) > 1 or len({len(s) for _, s in data}) > 1:
        checks.append((None, "Subgroups hold different numbers of values, so the groups are tested from the mixed model (REML) with Satterthwaite's degrees of freedom; the classic F would only be approximate." if unequal else
                       "The groups have different numbers of subgroups; with the same number of values in every subgroup the F test is still exact."))
    del sizes

    def draw(ax):
        for i, (_, s) in enumerate(data):
            for j, v in enumerate(s):
                x = i + (j - (len(s) - 1) / 2) * 0.7 / max(len(s), 1)
                ax.plot(np.full(len(v), x), v, "o", ms=2.5, color=COLORS[i % 8], alpha=0.8)
                ax.hlines(v.mean(), x - 0.05, x + 0.05, color="#222222", lw=1)
        ax.set_xticks(range(a), [n[:12] for n in names]); ax.set_xlim(-0.6, a - 0.4)
    return result("Nested ANOVA" if a > 2 else "Nested t-test", ans, [{"name": "Summary", "tables": tables}], checks, plots=[small_plot("Subgroups in each group", draw)],
                  legend=f"Nested {'one-way ANOVA' if a > 2 else 't-test'}: {', '.join(names)}, subgroups as a random factor.",
                  methods=f"Groups were compared by a nested {'one-way ANOVA' if a > 2 else 't-test'} with subgroups as a random factor nested in groups ({'tested from the mixed model with Satterthwaite degrees of freedom, as subgroups hold different numbers of values' if unequal else 'F tested against the subgroup mean square'}; {nsub} subgroups, {N} values) in Datum Plot (SciPy); variance components came from a linear mixed model fitted by REML (statsmodels), α = {alpha:g}.",
                  code="import statsmodels.formula.api as smf\nprint(smf.mixedlm('y ~ C(group)', df, groups=df['subgroup']).fit(reml=True).summary())")
