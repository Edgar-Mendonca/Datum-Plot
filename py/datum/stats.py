"""Summary statistics for data tables: what error bars and (later) analyses start from.

A table arrives as the engine's JSON (see crates/core/src/model.rs): `cols` is the flat list of
grid columns (column 0 is X, then each data set's sub-columns), `excluded` lists [row, col] cells.
"""
import math
import warnings

import numpy as np
from scipy import stats as st


def set_columns(table):
    """(first grid column, number of sub-columns) for each data set."""
    out, c = [], 1
    for s in table["sets"]:
        n = s["reps"] if s["entry"] == "rep" else 3
        out.append((c, n))
        c += n
    return out


def value(table, r, c, ex=frozenset()):
    """The number in a cell, or None when it is empty or excluded (`ex`: set of (row, col))."""
    col = table["cols"][c] if c < len(table["cols"]) else []
    v = col[r] if r < len(col) else None
    if v is None or (r, c) in ex:
        return None
    v = float(v)
    return v if math.isfinite(v) else None  # NaN or infinity counts as empty


def describe(vals):
    """N, mean, SD, SEM, 95 % CI half-width, min and max of a list of numbers."""
    a = np.asarray([v for v in vals if v is not None and math.isfinite(v)], float)
    n = len(a)
    if n == 0:
        return None
    mean = float(a.mean())
    sd = float(a.std(ddof=1)) if n > 1 else 0.0
    sem = sd / math.sqrt(n) if n > 1 else 0.0
    ci = float(st.t.ppf(0.975, n - 1)) * sem if n > 1 else 0.0
    return {"n": n, "mean": mean, "sd": sd, "sem": sem, "ci": ci, "min": float(a.min()), "max": float(a.max())}


def from_summary(mean, spread, n, kind):
    """The same figures from an entered mean with its SD or SEM and N."""
    if mean is None:
        return None
    n = int(n) if n is not None and n >= 1 else 1
    spread = spread or 0.0
    sd = spread if kind == "msn" else spread * math.sqrt(n)
    sem = sd / math.sqrt(n)
    ci = float(st.t.ppf(0.975, n - 1)) * sem if n > 1 else 0.0
    return {"n": n, "mean": mean, "sd": sd, "sem": sem, "ci": ci, "min": None, "max": None}


def column(table, c, ex):
    """Grid column c as floats (NaN where empty or excluded)."""
    n = table["rows"]
    col = table["cols"][c] if c < len(table["cols"]) else []
    a = np.full(n, np.nan)
    a[:min(n, len(col))] = np.array(col[:n], dtype=float)
    for r, cc in ex:
        if cc == c and r < n:
            a[r] = np.nan
    return a


def summarize_fast(table, ex):
    """The same as summarize for replicate data sets, worked out a column at a time (large tables, D17)."""
    x = column(table, 0, ex)
    out = []
    for s, (c0, nc) in zip(table["sets"], set_columns(table)):
        if s["entry"] != "rep":
            out.append(None)
            continue
        V = np.column_stack([column(table, c0 + j, ex) for j in range(nc)])
        ok = np.isfinite(V)
        n = ok.sum(axis=1)
        rows = np.flatnonzero(np.isfinite(x) & (n > 0))
        with np.errstate(all="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mean, sd = np.nanmean(V[rows], axis=1), np.where(n[rows] > 1, np.nanstd(V[rows], axis=1, ddof=1), 0.0)
            lo, hi = np.nanmin(V[rows], axis=1), np.nanmax(V[rows], axis=1)
        k = n[rows]
        sem = np.where(k > 1, sd / np.sqrt(k), 0.0)
        ci = np.where(k > 1, st.t.ppf(0.975, np.maximum(k - 1, 1)) * sem, 0.0)
        single = nc == 1
        out.append([{"n": int(k[i]), "mean": float(mean[i]), "sd": float(sd[i]), "sem": float(sem[i]), "ci": float(ci[i]), "min": float(lo[i]), "max": float(hi[i]),
                     "values": [float(mean[i])] if single else [float(v) for v in V[r][ok[r]]], "x": float(x[r]), "row": int(r)} for i, r in enumerate(rows)])
    return out


def summarize(table):
    """For each data set: one entry per row that has an X value and data."""
    rows, ex = table["rows"], {tuple(e) for e in table.get("excluded", [])}
    fast = summarize_fast(table, ex) if rows > 2000 else [None] * len(table["sets"])
    out = []
    for (s, (c0, nc)), f in zip(zip(table["sets"], set_columns(table)), fast):
        if f is not None:
            out.append(f)
            continue
        pts = []
        for r in range(rows):
            x = value(table, r, 0, ex)
            if x is None:
                continue
            if s["entry"] == "rep":
                vals = [value(table, r, c0 + j, ex) for j in range(nc)]
                d = describe(vals)
                if d:
                    d["values"] = [v for v in vals if v is not None]
            else:
                d = from_summary(value(table, r, c0, ex), value(table, r, c0 + 1, ex), value(table, r, c0 + 2, ex), s["entry"])
                if d:
                    d["values"] = [d["mean"]]
            if d:
                d["x"], d["row"] = x, r
                pts.append(d)
        out.append(pts)
    return out
