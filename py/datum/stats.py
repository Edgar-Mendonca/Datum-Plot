"""Summary statistics for data tables: what error bars and (later) analyses start from.

A table arrives as the engine's JSON (see crates/core/src/model.rs): `cols` is the flat list of
grid columns (column 0 is X, then each data set's sub-columns), `excluded` lists [row, col] cells.
"""
import math

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
    return float(v)


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


def summarize(table):
    """For each data set: one entry per row that has an X value and data."""
    rows, ex = table["rows"], {tuple(e) for e in table.get("excluded", [])}
    out = []
    for s, (c0, nc) in zip(table["sets"], set_columns(table)):
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
