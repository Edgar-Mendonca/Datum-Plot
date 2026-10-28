"""Surface fits (B26): Z as a function of X and Y, from a matrix table (Z on an X–Y grid) or from three
variables of a table of many variables or a worksheet (X, Y, Z in rows). Plane, quadratic and cubic
polynomials by least squares (with the stationary point of the quadratic), and a 2D Gaussian peak."""
import math

import numpy as np
from scipy import stats as st

from . import stats
from .analysis import ALPHA, COLORS, g, name_of, pv, result, small_plot

TERMS = {"plane": ["1", "x", "y"], "quad": ["1", "x", "y", "x²", "xy", "y²"], "cubic": ["1", "x", "y", "x²", "xy", "y²", "x³", "x²y", "xy²", "y³"]}
NAMES = {"plane": "Plane", "quad": "Quadratic surface", "cubic": "Cubic surface", "gauss": "2D Gaussian peak"}


def design(x, y, model):
    cols = {"1": np.ones_like(x), "x": x, "y": y, "x²": x * x, "xy": x * y, "y²": y * y, "x³": x ** 3, "x²y": x * x * y, "xy²": x * y * y, "y³": y ** 3}
    return np.column_stack([cols[t] for t in TERMS[model]])


def gauss2d(xy, z0, a, x0, y0, sx, sy):
    x, y = xy
    return z0 + a * np.exp(-((x - x0) ** 2 / (2 * sx * sx) + (y - y0) ** 2 / (2 * sy * sy)))


def points3(table, ks):
    """(x, y, z, names) of every point: a matrix's grid, or three columns (X, Y, Z) of the other tables."""
    if table.get("kind") == "matrix":
        from .graph import matrix_grid
        x, y, Z = matrix_grid(table)
        X, Y = np.meshgrid(x, y)
        ok = np.isfinite(Z)
        return X[ok], Y[ok], Z[ok], (table.get("xTitle") or "X", "Y", table.get("yTitle") or "Z"), (x, y)
    if len(ks) < 3:
        raise ValueError("Choose three data sets: X, Y and Z (in that order), or use a matrix table.")
    ex = {tuple(e) for e in table.get("excluded", [])}
    c = stats.set_columns(table)
    rows = [[stats.value(table, r, c[k][0], ex) for k in ks[:3]] for r in range(table["rows"])]
    a = np.array([r for r in rows if all(v is not None and math.isfinite(v) for v in r)], float).reshape(-1, 3)
    return a[:, 0], a[:, 1], a[:, 2], tuple(name_of(table, k) for k in ks[:3]), None


def surface(table, ks, o):
    model, alpha = o.get("model", "quad"), float(o.get("alpha", ALPHA))
    x, y, z, (nx, ny, nz), grid = points3(table, ks)
    n = len(z)
    k = 6 if model == "gauss" else len(TERMS.get(model, TERMS["quad"]))
    if n < k + 2:
        raise ValueError(f"A {NAMES.get(model, model).lower()} needs at least {k + 2} points with X, Y and Z; there are {n}.")
    checks, extra = [], []
    if model == "gauss":
        from scipy.optimize import curve_fit
        i = int(np.argmax(np.abs(z - np.median(z))))
        p0 = [float(np.median(z)), float(z[i] - np.median(z)), float(x[i]), float(y[i]), float(np.ptp(x) / 4 or 1), float(np.ptp(y) / 4 or 1)]
        try:
            p, cov = curve_fit(gauss2d, (x, y), z, p0=p0, maxfev=20000)
        except Exception as e:
            raise ValueError(f"The 2D Gaussian did not converge ({e}); try a quadratic surface.")
        se = np.sqrt(np.diag(cov))
        fit = gauss2d((x, y), *p)
        names = ["Baseline z0", "Height A", "Centre x0", "Centre y0", "Width σx", "Width σy"]
        q = st.t.ppf(1 - alpha / 2, n - 6)
        rows = [[nm, g(v, 5), g(s, 3), f"{g(v - q * s, 4)} to {g(v + q * s, 4)}", "—"] for nm, v, s in zip(names, p, se)]
        f_eval = lambda X, Y: gauss2d((X, Y), *p)
        eq = "z = z0 + A·exp(−((x−x0)²/2σx² + (y−y0)²/2σy²))"
        ans = f"Peak of height {g(p[1], 4)} at x = {g(p[2], 4)}, y = {g(p[3], 4)} (widths σx {g(abs(p[4]), 3)}, σy {g(abs(p[5]), 3)})"
    else:
        import statsmodels.api as sm
        model = model if model in TERMS else "quad"
        D = design(x, y, model)
        f = sm.OLS(z, D).fit()
        p = f.params
        fit = f.fittedvalues
        q = st.t.ppf(1 - alpha / 2, f.df_resid)
        rows = [[t, g(v, 5), g(s, 3), f"{g(v - q * s, 4)} to {g(v + q * s, 4)}", pv(pp)] for t, v, s, pp in zip(TERMS[model], p, f.bse, f.pvalues)]
        f_eval = lambda X, Y: design(X.ravel(), Y.ravel(), model).dot(p).reshape(X.shape)
        eq = "z = b0 + " + " + ".join(f"b{i}·{t}" for i, t in enumerate(TERMS[model]) if t != "1")
        ans = f"{NAMES[model]}: R² = {g(f.rsquared, 4)}"
        if model == "quad":
            H = np.array([[2 * p[3], p[4]], [p[4], 2 * p[5]]])
            try:
                xs, ys = np.linalg.solve(H, [-p[1], -p[2]])
                zs = float(design(np.array([xs]), np.array([ys]), "quad").dot(p)[0])
                ev = np.linalg.eigvalsh(H)
                kind = "maximum" if np.all(ev < 0) else "minimum" if np.all(ev > 0) else "saddle point"
                inside = x.min() <= xs <= x.max() and y.min() <= ys <= y.max()
                extra.append({"title": "Stationary point", "columns": ["", "Value"], "rows": [["Kind", kind], ["x", g(xs, 5)], ["y", g(ys, 5)], ["z", g(zs, 5)], ["Inside the data", "yes" if inside else "no"]]})
                ans += f"; {kind} z = {g(zs, 4)} at x = {g(xs, 4)}, y = {g(ys, 4)}" + ("" if inside else " (outside the data: an extrapolation)")
            except np.linalg.LinAlgError:
                pass
    res = z - fit
    ss = float(np.sum(res ** 2))
    r2 = 1 - ss / float(np.sum((z - z.mean()) ** 2)) if np.ptp(z) else float("nan")
    adj = 1 - (1 - r2) * (n - 1) / max(n - k, 1)
    fitrows = [["Points", g(n)], ["R²", g(r2, 4)], ["Adjusted R²", g(adj, 4)], ["Residual SD", g(math.sqrt(ss / max(n - k, 1)), 4)]]
    if model != "gauss":
        fitrows.insert(2, ["F (P value)", f"{g(f.fvalue, 4)} ({pv(f.f_pvalue)})"])
    out = {}
    if grid is not None:
        gx, gy = np.linspace(grid[0].min(), grid[0].max(), 40), np.linspace(grid[1].min(), grid[1].max(), 40)
        GX, GY = np.meshgrid(gx, gy)
        out["surface"] = {"x": gx.tolist(), "y": gy.tolist(), "z": np.asarray(f_eval(GX, GY), float).tolist()}
    c = COLORS[0]
    plots = [small_plot("Residuals", lambda ax: (ax.axhline(0, color="#8D9AAB", lw=0.8), ax.plot(fit, res, "o", ms=3, color=c), ax.set_xlabel("Fitted z"), ax.set_ylabel("Residual"))),
             small_plot("Fitted vs actual", lambda ax: (ax.plot(fit, z, "o", ms=3, color=c), ax.axline((float(z.mean()),) * 2, slope=1, color="#8D9AAB", lw=0.8), ax.set_xlabel("Fitted"), ax.set_ylabel("Actual")))]
    if n < 3 * k:
        checks.append((False, f"{n} points for {k} parameters: few for a surface; the coefficients may be unstable."))
    checks.append((None, f"x = {nx}, y = {ny}, z = {nz}."))
    return result(f"Surface fit: {NAMES.get(model, model)}", ans + ".", [{"name": "Summary", "tables": [{"title": eq, "columns": ["Parameter", "Value", "Std. error", f"{100 * (1 - alpha):g}% CI", "P value"], "rows": rows},
                                                                                {"title": "Goodness of fit", "columns": ["", "Value"], "rows": fitrows}, *extra]}],
                  checks, plots=plots, legend=f"{NAMES.get(model, model)} fitted to {nz} over {nx} and {ny} (n = {n}).",
                  methods=f"A {NAMES.get(model, model).lower()} ({eq}) was fitted to {n} points by least squares in Datum Plot ({'SciPy' if model == 'gauss' else 'statsmodels'}).",
                  code="import numpy as np\nD = np.column_stack([np.ones_like(x), x, y, x*x, x*y, y*y])\nb, *_ = np.linalg.lstsq(D, z, rcond=None)", **out)
