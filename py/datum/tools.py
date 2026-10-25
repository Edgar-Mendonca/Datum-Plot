"""Data tools and materials analyses: transforms, data checks, frequency distributions, area
under the curve, smoothing and derivatives, tensile tests and Weibull analysis. Same signature
as every analysis: (table, ks, options) → analysis.result(...)."""
import math

import numpy as np
from scipy import stats as st

from . import stats
from .analysis import ALPHA, COLORS, g, name_of, points, result, small_plot, values, by_set
from .groups import column, summary


def new_table(table, name, sets, xs, cols, x_title=None, y_title=None, kind="xy"):
    """A data table the result can become (Results: New table from this result); one column per set."""
    n = max([len(xs)] + [len(c) for c in cols] + [1])
    pad = lambda c: [None if v is None or not math.isfinite(v) else float(v) for v in c] + [None] * (n - len(c))
    return {"name": name, "kind": kind, "xTitle": x_title if x_title is not None else table.get("xTitle", "X"), "xUnits": table.get("xUnits", "") if x_title is None else "",
            "yTitle": y_title if y_title is not None else table.get("yTitle", "Y"), "yUnits": table.get("yUnits", "") if y_title is None else "", "rows": n,
            "sets": [{"title": s, "entry": "rep", "reps": 1} for s in sets], "cols": [pad(xs)] + [pad(c) for c in cols]}


def preview(tb, rows=40):
    """The first rows of a new table, as a results table."""
    heads = [tb["xTitle"] or "X"] + [f"{s['title']}" + (f" · {j + 1}" if s["reps"] > 1 and s["entry"] == "rep" else "") for s in tb["sets"] for j in range(s["reps"] if s["entry"] == "rep" else 3)]
    out = [[g(c[r]) if c[r] is not None else "" for c in tb["cols"]] for r in range(min(rows, tb["rows"]))]
    return {"title": "New values" + (f" (first {rows} of {tb['rows']} rows)" if tb["rows"] > rows else ""), "columns": heads[:len(tb["cols"])], "rows": out}


# ---------- transforms (A15) ----------
FUNCS = {"none": lambda v, k: v, "log10": lambda v, k: math.log10(v) if v > 0 else None, "ln": lambda v, k: math.log(v) if v > 0 else None, "recip": lambda v, k: 1 / v if v else None,
         "sqrt": lambda v, k: math.sqrt(v) if v >= 0 else None, "square": lambda v, k: v * v, "exp10": lambda v, k: 10 ** v if v < 300 else None, "exp": lambda v, k: math.exp(v) if v < 700 else None,
         "mul": lambda v, k: v * k, "add": lambda v, k: v + k, "c2k": lambda v, k: v + 273.15, "k2c": lambda v, k: v - 273.15, "pct": lambda v, k: v * 100, "frac": lambda v, k: v / 100}
FNAME = {"none": "", "log10": "log10({})", "ln": "ln({})", "recip": "1/{}", "sqrt": "√{}", "square": "{}²", "exp10": "10^{}", "exp": "e^{}", "mul": "{}×k", "add": "{}+k", "c2k": "{} (K)", "k2c": "{} (°C)", "pct": "{} (%)", "frac": "{} (fraction)"}


def transform(table, ks, o):
    fx, fy, kx, ky = o.get("x", "none"), o.get("y", "none"), float(o.get("kx", 1) or 0), float(o.get("ky", 1) or 0)
    base, norm, means = o.get("baseline", "none"), o.get("normalize", "none"), bool(o.get("means"))
    ex = {tuple(e) for e in table.get("excluded", [])}
    rows = table["rows"]
    f = lambda name, v, k: None if v is None else FUNCS[name](v, k)
    xs = [f(fx, stats.value(table, r, 0, ex), kx) for r in range(rows)]
    sets, cols, checks = [], [], []
    for k in ks:
        c0, w = stats.set_columns(table)[k]
        w = w if table["sets"][k]["entry"] == "rep" else 1
        sub = [[f(fy, stats.value(table, r, c, ex), ky) for r in range(rows)] for c in range(c0, c0 + w)]
        ys = [v for c in sub for v in c if v is not None]
        if not ys:
            checks.append((False, f"{name_of(table, k)}: no values left after the transform.")); continue
        if base != "none":
            b = {"first": next(v for r in range(rows) for c in sub if (v := c[r]) is not None), "min": min(ys), "value": float(o.get("base", 0) or 0)}[base]
            sub = [[None if v is None else v - b for v in c] for c in sub]
            ys = [v - b for v in ys]
        if norm != "none":
            lo = min(ys) if norm == "range" else 0.0
            hi = {"range": max(ys), "max": max(ys), "first": next(v for r in range(rows) for c in sub if (v := c[r]) is not None)}[norm]
            span = (hi - lo) or 1.0
            sub = [[None if v is None else 100 * (v - lo) / span for v in c] for c in sub]
        if means and w > 1:
            arr = [[c[r] for c in sub if c[r] is not None] for r in range(rows)]
            sub = [[float(np.mean(a)) if a else None for a in arr], [float(np.std(a, ddof=1)) if len(a) > 1 else (0.0 if a else None) for a in arr], [float(len(a)) if a else None for a in arr]]
            sets.append({"title": name_of(table, k), "entry": "msn", "reps": 3})
        else:
            sets.append({"title": name_of(table, k), "entry": "rep", "reps": w})
        cols += sub
    if not sets:
        raise ValueError("Nothing to transform.")
    yt = FNAME[fy].format(table.get("yTitle", "Y")) if fy != "none" else table.get("yTitle", "Y")
    if norm != "none":
        yt = f"{yt} (% of {'range' if norm == 'range' else 'maximum' if norm == 'max' else 'first value'})"
    tb = new_table(table, f"{table.get('name', 'Data')} transformed", [], xs, cols, x_title=FNAME[fx].format(table.get("xTitle", "X")) if fx != "none" else None,
                   y_title=yt if fy != "none" or norm != "none" else None)
    tb["sets"] = sets
    steps = [x for x in [f"X → {FNAME[fx].format('X')}" if fx != "none" else "", f"Y → {FNAME[fy].format('Y')}" if fy != "none" else "", f"subtract the baseline ({base})" if base != "none" else "",
                         f"normalise to 0–100 % ({norm})" if norm != "none" else "", "replicates → mean, SD and N" if means else ""] if x]
    return result("Transform", f"{len(sets)} data set{'s' if len(sets) > 1 else ''} transformed: {'; '.join(steps) or 'unchanged'}. Make it a data table to graph or analyse it.",
                  [{"name": "Summary", "tables": [preview(tb)]}], checks + [(None, "Values that cannot be transformed (log of zero or a negative number, 1/0) are left empty.")],
                  methods=f"Data were transformed ({'; '.join(steps) or 'no change'}) in Datum Plot.", table=tb,
                  code="import numpy as np\ny2 = np.log10(y)  # or 1/y, (y - y.min()) / np.ptp(y) * 100 …")


# ---------- data checks (A18) ----------
def check(table, ks, o):
    issues = []
    ex = {tuple(e) for e in table.get("excluded", [])}
    rows, xy = table["rows"], table.get("kind", "xy") == "xy"
    add = lambda sev, where, what: issues.append([sev, where, what])
    if xy:
        xs = [stats.value(table, r, 0, ex) for r in range(rows)]
        filled = [r for r in range(rows) if any(stats.value(table, r, c, ex) is not None for c in range(1, len(table["cols"])))]
        for r in filled:
            if xs[r] is None:
                add("Problem", f"Row {r + 1}", "Has Y values but no X value, so graphs and fits skip it.")
        xv = [x for x in xs if x is not None]
        dup = sorted({x for x in xv if xv.count(x) > 1})
        if dup:
            add("Note", "X column", f"Repeated X values ({', '.join(g(d) for d in dup[:6])}{'…' if len(dup) > 6 else ''}); fine for replicate rows, but check they are not typing mistakes.")
        if len(xv) > 2 and xv != sorted(xv) and xv != sorted(xv, reverse=True):
            add("Note", "X column", "X values are not in order. Sort the table if you join the points with lines (Data › Sort).")
        if any(x <= 0 for x in xv):
            add("Note", "X column", "Zero or negative X values cannot be shown on a log X axis.")
    for k in ks:
        nm, s = name_of(table, k), table["sets"][k]
        v = np.array([a for a, _ in values(table, k)], float)
        if not len(v):
            add("Problem", nm, "Has no values."); continue
        if s["entry"] == "rep" and xy:
            pts = stats.summarize(table)[k]
            few = [p["row"] + 1 for p in pts if p["n"] < 2]
            if few and s["reps"] > 1:
                add("Note", nm, f"Only one value at row{'s' if len(few) > 1 else ''} {', '.join(map(str, few[:8]))}{'…' if len(few) > 8 else ''}: no error bar there.")
        if s["entry"] != "rep":
            c0 = stats.set_columns(table)[k][0]
            for r in range(rows):
                m, sd, n = (stats.value(table, r, c0 + j, ex) for j in range(3))
                if m is not None and (n is None or n < 1):
                    add("Problem", f"{nm}, row {r + 1}", "A mean without N; enter N (the number of values behind the mean).")
                if sd is not None and sd < 0:
                    add("Problem", f"{nm}, row {r + 1}", "A negative SD or SEM.")
        if len(v) >= 5:
            med = np.median(v)
            mad = np.median(np.abs(v - med)) * 1.4826
            far = [x for x in v if mad > 0 and abs(x - med) > 5 * mad]
            if far:
                add("Note", nm, f"{len(far)} value{'s' if len(far) > 1 else ''} far from the rest ({', '.join(g(x) for x in far[:4])}); check for typing mistakes or run Outliers.")
        if np.any(v <= 0):
            add("Note", nm, "Zero or negative values cannot be shown on a log Y axis.")
        if len(v) < 3:
            add("Note", nm, f"Only {len(v)} value{'s' if len(v) != 1 else ''}; most statistics need three or more.")
    n_ex = len(table.get("excluded", []))
    if n_ex:
        add("Note", "Table", f"{n_ex} value{'s are' if n_ex > 1 else ' is'} excluded (blue italics) and left out of graphs and analyses.")
    probs = sum(1 for i in issues if i[0] == "Problem")
    ans = "No problems found: the table is ready to graph and analyse." if not issues else f"{probs} problem{'s' if probs != 1 else ''} and {len(issues) - probs} note{'s' if len(issues) - probs != 1 else ''} to look at."
    return result("Data checks", ans, [{"name": "Summary", "tables": [{"title": "What to check", "columns": ["", "Where", "What"], "rows": issues or [["OK", "", "Nothing to report."]]}]}],
                  [(probs == 0, "Problems change results; notes are worth a look.")], methods="The table was checked for missing X values, repeated or unordered X, missing N, extreme values and values unsuitable for log axes.")


# ---------- frequency distributions (D4) ----------
def frequency(table, ks, o):
    data = [(k, np.array([a for a, _ in values(table, k)], float)) for k in ks]
    data = [(k, v) for k, v in data if len(v)]
    if not data:
        raise ValueError("No values.")
    allv = np.concatenate([v for _, v in data])
    bins = o.get("bins", "auto")
    if o.get("width") not in (None, ""):
        wd = float(o["width"])
        lo = math.floor(allv.min() / wd) * wd
        edges = np.arange(lo, allv.max() + wd * 1.0001, wd)
    else:
        edges = np.histogram_bin_edges(allv, bins=int(bins) if str(bins).isdigit() else "auto")
    if len(edges) > 201:
        edges = np.histogram_bin_edges(allv, bins=200)
    what = o.get("y", "count")
    cum = bool(o.get("cumulative"))
    centers = (edges[:-1] + edges[1:]) / 2
    rows, cols, plots = [], [], []
    for k, v in data:
        c, _ = np.histogram(v, edges)
        c = np.cumsum(c) if cum else c
        y = c / len(v) * 100 if what == "percent" else c / len(v) if what == "fraction" else c.astype(float)
        cols.append(y.tolist())
        col = COLORS[k % 8]
        def draw(ax, v=v, col=col):
            ax.hist(v, edges, color=col, alpha=0.55, edgecolor=col, cumulative=cum)
            if len(v) > 2 and not cum and v.std(ddof=1) > 0:
                xs = np.linspace(edges[0], edges[-1], 200)
                ax.plot(xs, st.norm.pdf(xs, v.mean(), v.std(ddof=1)) * len(v) * (edges[1] - edges[0]), color="#3A4655", lw=1)
            ax.set_ylabel("Count")
        plots.append(small_plot(f"Histogram · {name_of(table, k)}", draw))
        if len(v) > 2:
            (osm, osr), (slope, icpt, _) = st.probplot(v)
            plots.append(small_plot(f"QQ plot · {name_of(table, k)}", lambda ax, osm=osm, osr=osr, slope=slope, icpt=icpt, col=col: (ax.plot(osm, slope * osm + icpt, color="#8D9AAB", lw=0.8), ax.plot(osm, osr, "o", ms=3, color=col), ax.set_xlabel("Normal quantile"), ax.set_ylabel("Value"))))
            sv = np.sort(v)
            plots.append(small_plot(f"Cumulative · {name_of(table, k)}", lambda ax, sv=sv, col=col: (ax.step(sv, np.arange(1, len(sv) + 1) / len(sv) * 100, where="post", color=col), ax.set_ylabel("Cumulative %"))))
    unit = {"count": "Count", "percent": "Percent", "fraction": "Fraction"}[what]
    tab = {"title": "Frequency distribution", "columns": ["Bin from", "to", "Centre", *[name_of(table, k) for k, _ in data]],
           "rows": [[g(edges[i]), g(edges[i + 1]), g(centers[i]), *[g(c[i]) for c in cols]] for i in range(len(centers))]}
    tb = new_table(table, f"{table.get('name', 'Data')} histogram", [name_of(table, k) for k, _ in data], centers.tolist(), cols, x_title=f"{table.get('yTitle', 'Value')}", y_title=f"{'Cumulative ' if cum else ''}{unit.lower()}")
    tb["xUnits"] = table.get("yUnits", "")
    return result("Frequency distribution", f"{len(centers)} bins of width {g(edges[1] - edges[0])} from {g(edges[0])} to {g(edges[-1])}; {sum(len(v) for _, v in data)} values.",
                  [{"name": "Summary", "tables": [tab]}], plots=plots, table=tb,
                  methods=f"Values were binned into a {'cumulative ' if cum else ''}frequency distribution (bin width {g(edges[1] - edges[0])}) in Datum Plot (numpy).",
                  code="import numpy as np\ncounts, edges = np.histogram(v, bins='auto')")


# ---------- area under the curve (B14) ----------
def auc(table, ks, o):
    base = o.get("baseline", "zero")
    rows, curves, ans, peaks_rows = [], [], [], []
    for k in ks:
        x, y, _ = points(table, k, {**o, "points": "mean"})
        if len(x) < 2:
            continue
        i = np.argsort(x)
        x, y = x[i], y[i]
        b = {"zero": np.zeros_like(y), "value": np.full_like(y, float(o.get("base", 0) or 0)), "first": np.full_like(y, y[0]), "min": np.full_like(y, y.min()),
             "line": y[0] + (y[-1] - y[0]) * (x - x[0]) / (x[-1] - x[0] if x[-1] != x[0] else 1)}[base]
        d = y - b
        tot = float(np.trapezoid(d, x))
        pos = float(np.trapezoid(np.clip(d, 0, None), x))
        neg = float(np.trapezoid(np.clip(d, None, 0), x))
        j = int(np.argmax(np.abs(d)))
        rows.append([name_of(table, k), g(tot), g(pos), g(neg), g(x[j]), g(y[j]), g(len(x))])
        ans.append(f"{name_of(table, k)}: area {g(tot, 4)}.")
        # Regions above the baseline (peaks).
        above = d > 0
        start = None
        for q in range(len(x) + 1):
            if q < len(x) and above[q] and start is None:
                start = q
            elif (q == len(x) or not above[q]) and start is not None:
                a, e = max(start - 1, 0), min(q, len(x) - 1)
                area = float(np.trapezoid(np.clip(d[a:e + 1], 0, None), x[a:e + 1]))
                top = start + int(np.argmax(d[start:q]))
                if q - start >= 1 and abs(area) > 0.01 * max(abs(pos), 1e-300):
                    peaks_rows.append([name_of(table, k), g(x[a]), g(x[e]), g(x[top]), g(d[top]), g(area)])
                start = None
        curves.append({"set": k, "x": x.tolist(), "y": y.tolist(), "fill": b.tolist(), "label": f"Area = {g(tot, 4)}", "thin": True})
    tabs = [{"name": "Summary", "tables": [{"title": "Area under the curve", "columns": ["Data set", "Total area", "Positive area", "Negative area", "Peak X", "Peak Y", "Points"], "rows": rows},
                                           {"title": "Peaks (regions above the baseline)", "columns": ["Data set", "From X", "To X", "Peak X", "Height", "Area"], "rows": peaks_rows or [["None", "", "", "", "", ""]]}]}]
    return result("Area under the curve", " ".join(ans) or "Not enough points.", tabs, [(None, "Areas use the trapezoid rule on the means at each X; units are X units × Y units.")], curves=curves,
                  methods=f"The area under each curve was calculated by the trapezoid rule above a baseline ({base}) in Datum Plot (numpy).", legend="Shaded areas lie between each curve and its baseline.",
                  code="import numpy as np\nprint(np.trapezoid(y - baseline, x))")


# ---------- smoothing, derivatives and integrals (B14) ----------
def smooth(table, ks, o):
    from scipy.signal import savgol_filter
    method, mode = o.get("method", "sg"), o.get("mode", "smooth")
    win = int(o.get("window", 7) or 7)
    cols, curves, sets, xs_all = [], [], [], None
    for k in ks:
        x, y, _ = points(table, k, {**o, "points": "mean"})
        if len(x) < 3:
            continue
        i = np.argsort(x)
        x, y = x[i], y[i]
        w = max(3, min(win | 1, len(x) - (1 - len(x) % 2)))
        if method == "sg":
            ys = savgol_filter(y, w, min(int(o.get("order", 2)), w - 1)) if len(x) > 3 else y
        elif method == "lowess":
            from statsmodels.nonparametric.smoothers_lowess import lowess
            ys = lowess(y, x, frac=float(o.get("frac", 0.3)), return_sorted=False)
        elif method == "ma":
            ys = np.convolve(np.pad(y, w // 2, mode="edge"), np.ones(w) / w, mode="valid")
        else:
            ys = y
        if mode == "deriv1":
            out = np.gradient(ys, x)
        elif mode == "deriv2":
            out = np.gradient(np.gradient(ys, x), x)
        elif mode == "integral":
            out = np.concatenate([[0.0], np.cumsum((ys[1:] + ys[:-1]) / 2 * np.diff(x))])
        else:
            out = ys
        if mode == "smooth":
            curves.append({"set": k, "x": x.tolist(), "y": out.tolist(), "label": ""})
        xs_all = x if xs_all is None or len(x) > len(xs_all) else xs_all
        cols.append((name_of(table, k), x, out))
    if not cols:
        raise ValueError("Each data set needs at least three points.")
    xs = xs_all
    tbcols = [np.interp(xs, x, y).tolist() if len(x) != len(xs) or np.any(x != xs) else y.tolist() for _, x, y in cols]
    what = {"smooth": "Smoothed", "deriv1": "First derivative", "deriv2": "Second derivative", "integral": "Cumulative integral"}[mode]
    yt = {"smooth": None, "deriv1": f"d{table.get('yTitle', 'Y')}/d{table.get('xTitle', 'X')}", "deriv2": f"d²{table.get('yTitle', 'Y')}/d{table.get('xTitle', 'X')}²", "integral": f"∫{table.get('yTitle', 'Y')} d{table.get('xTitle', 'X')}"}[mode]
    tb = new_table(table, f"{table.get('name', 'Data')} {what.lower()}", [c[0] for c in cols], xs.tolist(), tbcols, y_title=yt)
    mname = {"sg": f"Savitzky-Golay smoothing (window {win}, order {o.get('order', 2)})", "lowess": f"LOWESS (fraction {o.get('frac', 0.3)})", "ma": f"a moving average of {win} points", "none": "no smoothing"}[method]
    plots = [small_plot(f"{what} · {c[0]}"[:40], lambda ax, c=c, i=i: (ax.plot(c[1], c[2], color=COLORS[ks[i] % 8], lw=1.2), ax.set_xlabel(table.get("xTitle", "X")[:20]))) for i, c in enumerate(cols)] if mode != "smooth" else []
    return result(what, f"{what}: {len(cols)} data set{'s' if len(cols) > 1 else ''} ({mname}). Make it a data table to graph or analyse it.", [{"name": "Summary", "tables": [preview(tb)]}],
                  [(None, "Smoothing changes the data; analyse the raw values, and use smoothing to show trends.")] if mode == "smooth" else [], curves=curves, plots=plots, table=tb,
                  methods=f"Curves were processed with {mname}{'' if mode == 'smooth' else ', then the ' + what.lower() + ' was taken numerically'} in Datum Plot (SciPy).",
                  code="from scipy.signal import savgol_filter\nys = savgol_filter(y, 7, 2)\ndy = np.gradient(ys, x)")


# ---------- tensile test analysis (B27) ----------
def tensile_one(e, s, o):
    """Young's modulus, offset yield, UTS, elongation and toughness of one stress–strain curve."""
    pct = o.get("strain", "abs") == "pct"
    e = e / 100 if pct else e
    off = float(o.get("offset", 0.2) or 0.2) / 100
    j = int(np.argmax(s))
    uts, e_uts = float(s[j]), float(e[j])
    lo, hi = o.get("xmin"), o.get("xmax")
    if lo is not None or hi is not None:
        lo = (float(lo) / 100 if pct else float(lo)) if lo is not None else -np.inf
        hi = (float(hi) / 100 if pct else float(hi)) if hi is not None else np.inf
        m = (e >= lo) & (e <= hi)
    else:
        m = (np.arange(len(e)) <= j) & (s >= 0.1 * uts) & (s <= 0.4 * uts)
        if m.sum() < 2:
            m = np.arange(len(e)) <= max(2, j // 3)
    if m.sum() < 2:
        return None
    E, b = np.polyfit(e[m], s[m], 1)
    # Offset yield: where the curve falls below the offset line E·(ε − offset) + b.
    d = s - (E * (e - off) + b)
    ys = ey = None
    for i in range(1, len(e)):
        if e[i] > off and d[i - 1] > 0 >= d[i]:
            t = d[i - 1] / (d[i - 1] - d[i])
            ey, ys = float(e[i - 1] + t * (e[i] - e[i - 1])), float(s[i - 1] + t * (s[i] - s[i - 1]))
            break
    eb = float(e[-1])
    tough = float(np.trapezoid(s, e))
    return {"E": float(E), "b": float(b), "ys": ys, "ey": ey, "uts": uts, "euts": e_uts, "eb": eb, "ep": eb - float(s[-1]) / E if E else float("nan"), "tough": tough, "n": int(m.sum())}


def tensile(table, ks, o):
    gpa = (table.get("yUnits") or "").strip().lower() == "mpa"
    pct = o.get("strain", "abs") == "pct"
    ex = {tuple(e) for e in table.get("excluded", [])}
    tabs, curves, checks, ans, summary_rows = [], [], [], [], []
    names = ["Young's modulus" + (" (GPa)" if gpa else ""), f"Yield strength Rp{g(float(o.get('offset', 0.2) or 0.2))}", "Ultimate tensile strength", "Strain at UTS (%)", "Elongation at break (%)", "Plastic elongation (%)", "Toughness (area)"]
    for k in ks:
        c0, w = stats.set_columns(table)[k]
        if table["sets"][k]["entry"] != "rep":
            checks.append((False, f"{name_of(table, k)}: enter each specimen's stress as a replicate column.")); continue
        res = []
        for c in range(c0, c0 + w):
            pts = [(stats.value(table, r, 0, ex), stats.value(table, r, c, ex)) for r in range(table["rows"])]
            pts = sorted((a, b) for a, b in pts if a is not None and b is not None)
            if len(pts) < 4:
                continue
            e, s = np.array(pts, float).T
            r = tensile_one(e, s, o)
            if r:
                res.append((c - c0 + 1, r))
        if not res:
            checks.append((False, f"{name_of(table, k)}: needs at least four strain–stress points per specimen.")); continue
        f = 1e-3 if gpa else 1.0
        vals = lambda r: [r["E"] * f, r["ys"], r["uts"], 100 * r["euts"], 100 * r["eb"], 100 * r["ep"], r["tough"]]
        rows = [[f"Specimen {i}", *[g(v, 4) if v is not None else "not reached" for v in vals(r)]] for i, r in res]
        arr = np.array([[np.nan if v is None else v for v in vals(r)] for _, r in res], float)
        mean, sd = np.nanmean(arr, 0), np.nanstd(arr, 0, ddof=1) if len(res) > 1 else np.full(arr.shape[1], np.nan)
        rows += [["Mean", *[g(v, 4) for v in mean]], ["SD", *[g(v, 3) for v in sd]]]
        tabs.append({"title": name_of(table, k), "columns": ["", *names], "rows": rows})
        summary_rows.append([name_of(table, k), *[f"{g(a, 4)} ± {g(b, 2)}" if math.isfinite(b) else g(a, 4) for a, b in zip(mean, sd)]])
        if any(r["ys"] is None for _, r in res):
            checks.append((None, f"{name_of(table, k)}: some specimens never cross the offset line (brittle, or the curve ends early)."))
        E, b = float(np.mean([r["E"] for _, r in res])), float(np.mean([r["b"] for _, r in res]))
        yv = [r for _, r in res if r["ey"] is not None]
        off = float(o.get("offset", 0.2) or 0.2) / 100
        top = float(np.mean([r["ey"] for r in yv])) if yv else float(np.mean([r["euts"] for _, r in res]))
        xs = np.linspace(off, top, 30)
        scale = 100 if pct else 1
        curves.append({"set": k, "x": (xs * scale).tolist(), "y": (E * (xs - off) + b).tolist(), "label": f"E = {g(E * f, 4)}{' GPa' if gpa else ''}" + (f", Rp = {g(np.mean([r['ys'] for r in yv]), 4)}" if yv else ""), "dash": True})
        ans.append(f"{name_of(table, k)}: E = {g(mean[0], 4)}{' GPa' if gpa else ''}, yield {g(mean[1], 4)}, UTS {g(mean[2], 4)} {table.get('yUnits', '')}.".replace("  ", " "))
    if not tabs:
        raise ValueError("No stress–strain curves to analyse: X is strain, each replicate column one specimen's stress.")
    tabs.insert(0, {"title": "Mean ± SD", "columns": ["Data set", *names], "rows": summary_rows})
    rng = "" if o.get("xmin") is None and o.get("xmax") is None else f" fitted from strain {g(o.get('xmin')) if o.get('xmin') is not None else 0} to {g(o.get('xmax')) if o.get('xmax') is not None else 'the end'}"
    return result("Tensile test", " ".join(ans), [{"name": "Summary", "tables": tabs}], checks + [(None, "The modulus is a straight-line fit of the elastic part" + (rng or " (10–40 % of the UTS)") + "; for precise moduli use an extensometer.")],
                  curves=curves, legend=f"Dashed lines show the {g(float(o.get('offset', 0.2) or 0.2))} % offset line used for the yield strength.",
                  methods=f"Young's modulus was fitted by least squares to the elastic region{rng or ' (10–40 % of the ultimate tensile strength)'}; the yield strength is the {g(float(o.get('offset', 0.2) or 0.2))} % offset (proof) stress; the elongation at break is the last strain recorded; the toughness is the area under the curve (trapezoid rule). Calculated in Datum Plot (numpy).",
                  code="import numpy as np\nE, b = np.polyfit(strain[elastic], stress[elastic], 1)\nyield_ = first stress where stress < E*(strain - 0.002) + b")


# ---------- Weibull analysis (B29) ----------
def weibull(table, ks, o):
    method = o.get("method", "mle")
    tabs, plots, checks, ans, rows = [], [], [], [], []
    def draw(ax):
        for k, v, m, s0 in fits:
            n = len(v)
            sv = np.sort(v)
            F = (np.arange(1, n + 1) - 0.3) / (n + 0.4)
            ax.plot(np.log(sv), np.log(-np.log(1 - F)), "o", ms=3.2, color=COLORS[k % 8])
            xs = np.linspace(np.log(sv[0]), np.log(sv[-1]), 50)
            ax.plot(xs, m * (xs - math.log(s0)), color=COLORS[k % 8], lw=1)
        ax.set_xlabel("ln(strength)"); ax.set_ylabel("ln(ln(1/(1 − F)))")
    fits = []
    for k in ks:
        v = np.array([a for a, _ in values(table, k)], float)
        v = v[v > 0]
        n = len(v)
        if n < 3:
            checks.append((False, f"{name_of(table, k)}: needs at least three positive values.")); continue
        sv = np.sort(v)
        F = (np.arange(1, n + 1) - 0.3) / (n + 0.4)
        X, Y = np.log(sv), np.log(-np.log(1 - F))
        lr = st.linregress(X, Y)
        m_lr, s_lr = float(lr.slope), float(math.exp(-lr.intercept / lr.slope))
        c, _, sc = st.weibull_min.fit(v, floc=0)
        m_ml, s_ml = float(c), float(sc)
        # 95 % CIs: maximum likelihood from the observed information; regression from its standard errors.
        def nll(p):
            mm, ss = p
            return -np.sum(st.weibull_min.logpdf(v, mm, scale=ss))
        h = np.array([m_ml * 1e-4, s_ml * 1e-4])
        H = np.zeros((2, 2))
        p0 = np.array([m_ml, s_ml])
        for i in range(2):
            for j in range(2):
                ei, ej = np.eye(2)[i] * h[i], np.eye(2)[j] * h[j]
                H[i, j] = (nll(p0 + ei + ej) - nll(p0 + ei - ej) - nll(p0 - ei + ej) + nll(p0 - ei - ej)) / (4 * h[i] * h[j])
        try:
            se = np.sqrt(np.diag(np.linalg.inv(H)))
        except np.linalg.LinAlgError:
            se = np.array([np.nan, np.nan])
        m, s0 = (m_ml, s_ml) if method == "mle" else (m_lr, s_lr)
        fits.append((k, v, m, s0))
        t = st.t.ppf(0.975, n - 2)
        rows_k = [["Weibull modulus m (maximum likelihood)", g(m_ml, 4), f"{g(m_ml - 1.96 * se[0], 4)} to {g(m_ml + 1.96 * se[0], 4)}"],
                  ["Characteristic strength σ0 (maximum likelihood)", g(s_ml, 5), f"{g(s_ml - 1.96 * se[1], 5)} to {g(s_ml + 1.96 * se[1], 5)}"],
                  ["Weibull modulus m (linear regression)", g(m_lr, 4), f"{g(m_lr - t * lr.stderr, 4)} to {g(m_lr + t * lr.stderr, 4)}"], ["Characteristic strength σ0 (linear regression)", g(s_lr, 5), ""],
                  ["R squared of the Weibull plot", g(lr.rvalue ** 2, 4), ""], ["Strength at 1 % failure probability", g(s0 * (-math.log(0.99)) ** (1 / m), 4), ""],
                  ["Strength at 10 % failure probability", g(s0 * (-math.log(0.9)) ** (1 / m), 4), ""], ["Mean strength", g(s0 * math.gamma(1 + 1 / m), 4), ""], ["Number of specimens", g(n), ""]]
        tabs.append({"title": name_of(table, k), "columns": ["", "Value", "95% CI"], "rows": rows_k})
        rows.append([name_of(table, k), g(m, 4), g(s0, 5), g(n)])
        ans.append(f"{name_of(table, k)}: m = {g(m, 3)}, σ0 = {g(s0, 4)}.")
        if n < 30:
            checks.append((None, f"{name_of(table, k)}: {n} specimens; standards ask for at least 30 for a reliable Weibull modulus."))
    if not fits:
        raise ValueError("No strengths to analyse.")
    plots.append(small_plot("Weibull plot", draw, 80, 60))
    mname = "maximum likelihood" if method == "mle" else "linear regression of the Weibull plot (median ranks)"
    return result("Weibull analysis", " ".join(ans), [{"name": "Summary", "tables": [{"title": f"Weibull parameters ({mname})", "columns": ["Data set", "Weibull modulus m", "Characteristic strength σ0", "Specimens"], "rows": rows}, *tabs]}], checks, plots=plots,
                  methods=f"Weibull parameters were estimated by {mname}; failure probabilities use median ranks F = (i − 0.3)/(n + 0.4). Calculated in Datum Plot (SciPy).",
                  legend="Weibull plot: ln(ln(1/(1 − F))) against ln(strength); the line is the fitted two-parameter Weibull distribution.",
                  code="from scipy import stats\nm, _, s0 = stats.weibull_min.fit(strengths, floc=0)")
