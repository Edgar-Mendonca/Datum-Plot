"""Multiple t-tests (B33) and the volcano plot (D18).

A grouped table with one row per gene, protein or compound and two data sets (control and treated) with
their replicates in sub-columns. Each row is tested on its own; the P values are then corrected for the number
of rows: by the false discovery rate (Benjamini-Hochberg, or the two-stage step-up of Benjamini, Krieger and
Yekutieli) or by the family-wise error rate (Holm-Šidák, Bonferroni). A row is a "discovery" when its adjusted
P value (q) is below the chosen threshold."""
import math

import numpy as np
import scipy.stats as st

from . import stats
from .analysis import COLORS, g, name_of, pv, result, small_plot
from .groups import p_text

TESTS = {"welch": "Welch's unpaired t-test", "student": "unpaired t-test (equal SDs)", "paired": "paired t-test", "mw": "Mann-Whitney test"}
METHODS = {"fdr_bh": ("Benjamini-Hochberg false discovery rate", "q"), "fdr_tsbky": ("two-stage step-up (Benjamini, Krieger and Yekutieli) false discovery rate", "q"),
           "holm-sidak": ("Holm-Šidák", "adjusted P"), "bonferroni": ("Bonferroni", "adjusted P"), "none": ("no correction", "P")}
SHOWN = 2000  # rows listed on the results sheet (all go into the new table)


def row_values(table, k, r, ex):
    c0, w = stats.set_columns(table)[k]
    return [v for v in (stats.value(table, r, c, ex) for c in range(c0, c0 + w))]


def multit(table, ks, o):
    from statsmodels.stats.multitest import multipletests
    test, method, q = o.get("test", "welch"), o.get("method", "fdr_bh"), float(o.get("q", 0.05))
    if len(ks) < 2:
        raise ValueError("Multiple t-tests compare two data sets (for example Control and Treated); choose two.")
    if any(table["sets"][k]["entry"] != "rep" for k in ks[:2]):
        raise ValueError("Multiple t-tests need the individual values: enter each data set's replicates in its sub-columns.")
    if not 0 < q < 1:
        raise ValueError("The threshold must be between 0 and 1 (usually 0.05 or 0.01).")
    a_k, b_k = ks[0], ks[1]
    ex = {tuple(e) for e in table.get("excluded", [])}
    titles = table.get("rowTitles") or []
    rows, skipped = [], 0
    with np.errstate(all="ignore"):
        for r in range(table["rows"]):
            a, b = row_values(table, a_k, r, ex), row_values(table, b_k, r, ex)
            if test == "paired":
                pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None and math.isfinite(x) and math.isfinite(y)]
                a, b = [x for x, _ in pairs], [y for _, y in pairs]
            else:
                a, b = [x for x in a if x is not None and math.isfinite(x)], [y for y in b if y is not None and math.isfinite(y)]
            if not a and not b:
                continue
            name = (titles[r] if r < len(titles) else "") or f"Row {r + 1}"
            a, b = np.array(a, float), np.array(b, float)
            if len(a) < 2 or len(b) < 2 or (test != "mw" and np.std(np.r_[a - a.mean(), b - b.mean()]) == 0 and (test != "paired" or np.std(b - a) == 0)):
                skipped += 1
                continue
            if test == "paired":
                t, p = st.ttest_rel(b, a)
            elif test == "mw":
                t, p = st.mannwhitneyu(b, a, alternative="two-sided")
            else:
                t, p = st.ttest_ind(b, a, equal_var=test == "student")
            ma, mb = float(a.mean()), float(b.mean())
            fc = math.log2(mb / ma) if ma > 0 and mb > 0 else float("nan")
            if math.isfinite(p):
                rows.append((name, r, ma, mb, mb - ma, fc, float(t), float(p)))
            else:
                skipped += 1
    if len(rows) < 2:
        raise ValueError("Multiple t-tests need at least two rows with two or more values in each data set.")
    ps = [x[7] for x in rows]
    adj = list(ps) if method == "none" else list(multipletests(ps, alpha=q, method=method)[1])
    hits = [p_ < q for p_ in adj]
    mname, qname = METHODS.get(method, METHODS["fdr_bh"])
    na, nb = name_of(table, a_k), name_of(table, b_k)
    useFC = o.get("x", "log2") == "log2" and all(math.isfinite(x[5]) for x in rows)
    xs = [x[5] if useFC else x[4] for x in rows]
    ys = [-math.log10(max(p_, 1e-300)) for p_ in ps]
    xlab = f"log₂ fold change ({nb} / {na})" if useFC else f"Difference ({nb} − {na})"
    order = sorted(range(len(rows)), key=lambda i: ps[i])
    tab = [[rows[i][0], g(rows[i][2], 4), g(rows[i][3], 4), g(rows[i][4], 4), g(rows[i][5], 4) if math.isfinite(rows[i][5]) else "", g(rows[i][6], 4), pv(ps[i]), pv(adj[i]), "Yes" if hits[i] else "No"] for i in order[:SHOWN]]
    up = sum(1 for i, h in enumerate(hits) if h and rows[i][4] > 0)
    down = sum(hits) - up
    label = int(o.get("label", 10))

    def volcano(ax):
        xs_, ys_ = np.array(xs), np.array(ys)
        h = np.array(hits)
        ax.scatter(xs_[~h], ys_[~h], s=6, color="#B8C0CA", linewidths=0, label="Not discoveries")
        ax.scatter(xs_[h], ys_[h], s=9, color=COLORS[0], linewidths=0, label="Discoveries")
        if any(hits):
            cut = min(ys_[h])
            ax.axhline(cut, color="#8A96A3", lw=0.6, ls="--")
        ax.axvline(0, color="#8A96A3", lw=0.6)
        for i in [i for i in order if hits[i]][:label]:
            ax.annotate(rows[i][0], (xs[i], ys[i]), fontsize=6, xytext=(3, 2), textcoords="offset points")
        ax.set_xlabel(xlab)
        ax.set_ylabel("−log₁₀ P")
        ax.legend(fontsize=6, frameon=False, loc="lower left")
    plot = small_plot("Volcano plot", volcano, 110, 85)
    n = len(rows)
    new = {"name": f"{table.get('name') or 'Data'} volcano", "kind": "xy", "xTitle": xlab, "xUnits": "", "yTitle": "−log₁₀ P", "yUnits": "", "rows": n,
           "rowTitles": [x[0] for x in rows], "sets": [{"title": "Discoveries", "entry": "rep", "reps": 1}, {"title": "Not discoveries", "entry": "rep", "reps": 1}],
           "cols": [[float(v) for v in xs], [y if h else None for y, h in zip(ys, hits)], [None if h else y for y, h in zip(ys, hits)]]}
    summary = [["Rows tested", str(n)], ["Rows not tested (fewer than two values, or no variation)", str(skipped)], ["Test", TESTS.get(test, TESTS["welch"])],
               ["Correction", mname], [f"Threshold ({qname})", g(q)], ["Discoveries", f"{sum(hits)} ({up} higher in {nb}, {down} lower)"]]
    checks = [(None, f"{n} rows were tested{f'; {skipped} had too few values or no variation and were left out' if skipped else ''}.")]
    if useFC is False and o.get("x", "log2") == "log2":
        checks.append((None, "Fold changes need positive means in every row, so the volcano plot shows differences instead."))
    if test == "mw" and rows:
        least = 2 / math.comb(sum(len(row_values(table, k, 0, ex)) for k in (a_k, b_k)), len(row_values(table, a_k, 0, ex)))
        if least > q / len(rows) * 10:
            checks.append((False, f"With so few values per group, the Mann-Whitney test cannot give a P value below {g(least, 2)}, which can rarely pass a correction for {len(rows)} rows; a t-test, or more replicates, can."))
    if method == "none":
        checks.append((False, f"Without a correction, about {g(0.05 * n, 2)} of {n} rows would pass P < 0.05 by chance alone."))
    ans = f"{sum(hits)} of {n} rows are discoveries ({qname} < {g(q)}, {mname}): {up} higher and {down} lower in {nb} than in {na}."
    return result("Multiple t-tests", ans, [{"name": "Summary", "tables": [{"title": "Multiple t-tests", "columns": ["", "Value"], "rows": summary}]},
                                               {"name": "Rows", "tables": [{"title": f"Each row, by P value{f' (first {SHOWN} of {n}; all are in the new table)' if n > SHOWN else ''}",
                                                                            "columns": ["Row", f"Mean {na}", f"Mean {nb}", "Difference", "log₂ fold change", "U" if test == "mw" else "t", "P", qname, "Discovery"], "rows": tab}]}],
                  checks, plots=[plot], table=new, graph={"line": False, "error": "none", "points": "each", "legend": {"show": True, "loc": "best"}},
                  methods=f"Each row was compared with a {TESTS.get(test, TESTS['welch'])} ({nb} vs {na}); P values were corrected for {n} comparisons by the {mname} method, and rows with {qname} < {g(q)} were called discoveries, in Datum Plot (SciPy, statsmodels).",
                  legend=f"Volcano plot: each point is a row; discoveries ({qname} < {g(q)}) are coloured and the {min(label, sum(hits))} smallest P values labelled.",
                  code="from scipy import stats\nfrom statsmodels.stats.multitest import multipletests\n# a, b: arrays of rows × replicates\nt, p = stats.ttest_ind(b, a, axis=1, equal_var=False)\nreject, q, *_ = multipletests(p, alpha=0.05, method='fdr_bh')")
