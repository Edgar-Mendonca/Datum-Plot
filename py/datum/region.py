"""Region tools (E5): drag over part of a graph for the statistics, area, straight-line fit and highest
point of each curve between two X values."""
import math

import numpy as np
from scipy import stats as st

from .analysis import g, name_of, points


def view(table):
    """Worksheets and tables of many variables seen as XY tables, as their graphs draw them."""
    if table.get("kind") == "sheet":
        from .sheet import sheet_view
        return sheet_view(table)
    if table.get("kind") == "multi":
        from .regress import xy_view
        return xy_view(table)
    return table


def region(table, x0, x1, y0=None, y1=None):
    t = view(table)
    lo, hi = sorted((float(x0), float(x1)))
    rows = []
    for k in range(len(t["sets"])):
        if k in t.get("hidden", []) or (t.get("fromMulti") and k == 0):
            continue
        x, y, _ = points(t, k, {"points": "each", "xmin": lo, "xmax": hi})
        if y0 is not None and y1 is not None:
            a, b = sorted((float(y0), float(y1)))
            m = (y >= a) & (y <= b)
            x, y = x[m], y[m]
        if not len(x):
            continue
        i = np.argsort(x, kind="stable")
        x, y = x[i], y[i]
        n = len(y)
        ux, uy = (np.unique(x), np.array([y[x == v].mean() for v in np.unique(x)])) if n > 1 else (x, y)
        area = float(np.trapezoid(uy, ux)) if len(ux) > 1 else 0.0
        fit = st.linregress(x, y) if n > 2 and np.ptp(x) > 0 else None
        j = int(np.argmax(y))
        rows.append([name_of(t, k), g(n), g(float(y.mean()), 5), g(float(y.std(ddof=1)), 4) if n > 1 else "—", f"{g(float(y.min()), 4)} to {g(float(y.max()), 4)}", g(area, 5),
                     f"{g(fit.slope, 4)} (R² {g(fit.rvalue ** 2, 3)})" if fit else "—", f"{g(float(y[j]), 4)} at {g(float(x[j]), 4)}"])
    return {"x0": lo, "x1": hi, "columns": ["Data set", "Points", "Mean Y", "SD", "Range of Y", "Area", "Slope", "Highest"], "rows": rows}
