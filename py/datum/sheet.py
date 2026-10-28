"""Worksheets (A9) and column formulas (A11).

A worksheet is a table whose data sets are single columns, each with a role: "x", "" (Y), "yerr"
(the error of the Y column before it) or "skip". Graphs and XY analyses see it through `sheet_view`.

A column formula fills a data set (one value per row) from the others: A, B, C… are the data sets
(each row's mean when they have replicates), X the X column, i the row number, col("Title") a data set
by its title. Arithmetic (+ − × ÷ ^ %), comparisons, if(test, a, b), and the functions in FUNCS.
Formulas are checked node by node before they run: only names, numbers and those calls are allowed."""
import ast
import math
import re

import numpy as np

from . import stats


def letter(k):
    s = ""
    k += 1
    while k:
        k, r = divmod(k - 1, 26)
        s = chr(65 + r) + s
    return s


def _agg(f):
    return lambda v: np.full_like(np.asarray(v, float), f(np.asarray(v, float)))


FUNCS = {
    "abs": np.abs, "sqrt": np.sqrt, "exp": np.exp, "ln": np.log, "log": np.log10, "log10": np.log10, "log2": np.log2,
    "sin": np.sin, "cos": np.cos, "tan": np.tan, "asin": np.arcsin, "acos": np.arccos, "atan": np.arctan,
    "round": lambda v, n=0: np.round(v, int(n)), "floor": np.floor, "ceil": np.ceil, "sign": np.sign,
    "mean": _agg(np.nanmean), "sd": _agg(lambda v: np.nanstd(v, ddof=1)), "sem": _agg(lambda v: np.nanstd(v, ddof=1) / math.sqrt(np.sum(np.isfinite(v)))),
    "sum": _agg(np.nansum), "min": _agg(np.nanmin), "max": _agg(np.nanmax), "median": _agg(np.nanmedian), "count": _agg(lambda v: float(np.sum(np.isfinite(v)))),
    "cumsum": lambda v: np.nancumsum(np.asarray(v, float)),
    "diff": lambda v: np.concatenate([[np.nan], np.diff(np.asarray(v, float))]),
    "if": lambda c, a, b: np.where(c, a, b),
    "radians": np.radians, "degrees": np.degrees,
}
CONSTS = {"pi": math.pi, "e": math.e}
OPS = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Compare, ast.BoolOp, ast.Call, ast.Name, ast.Load, ast.Constant,
       ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.USub, ast.UAdd, ast.Lt, ast.Gt, ast.LtE, ast.GtE, ast.Eq, ast.NotEq, ast.And, ast.Or)


def columns(table):
    """Each data set's values by row (the mean of its sub-columns), NaN where empty."""
    out = []
    for s, (c0, w) in zip(table["sets"], stats.set_columns(table)):
        w = w if s["entry"] == "rep" else 1
        rows = []
        for r in range(table["rows"]):
            v = [stats.value(table, r, c) for c in range(c0, c0 + w)]
            v = [x for x in v if x is not None]
            rows.append(float(np.mean(v)) if v else np.nan)
        out.append(np.array(rows, float))
    return out


def evaluate(table, text):
    """The formula's value on every row (a list, None where it has no value)."""
    src = (text or "").strip().lstrip("=").replace("^", "**").replace("×", "*").replace("÷", "/").replace("−", "-")
    if not src:
        raise ValueError("Type a formula, such as log10(A) or (B - mean(B)) / sd(B).")
    src = re.sub(r"\bif\s*\(", "if_(", src)  # if is a Python word
    try:
        tree = ast.parse(src, mode="eval")
    except SyntaxError:
        raise ValueError(f"The formula “{text}” is not complete or has a typing mistake.")
    cols = columns(table)
    n = table["rows"]
    env = {letter(k): v for k, v in enumerate(cols)}
    env.update(CONSTS)
    env["i"] = np.arange(1, n + 1, dtype=float)
    if table.get("kind", "xy") in ("xy", "survival"):
        env["X"] = np.array([np.nan if v is None else v for v in [stats.value(table, r, 0) for r in range(n)]], float)
    titles = {(s.get("title") or "").strip().lower(): cols[k] for k, s in enumerate(table["sets"])}
    funcs = {**FUNCS, "if_": FUNCS["if"], "col": lambda name: titles[str(name).strip().lower()] if str(name).strip().lower() in titles else _unknown(name)}
    names = {id(a) for c in ast.walk(tree) if isinstance(c, ast.Call) and getattr(c.func, "id", "") == "col" for a in c.args}
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
            node.value = float(node.value)  # whole numbers would let 10^10^10 run for ever
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in names:
            raise ValueError(f"Text in “{text}” can only name a column, as in col(\"Strength\").")
        if not isinstance(node, OPS):
            raise ValueError(f"“{text}” uses something formulas cannot: only numbers, columns (A, B…, X, i), arithmetic and functions such as log10, mean or if.")
        if isinstance(node, ast.Call) and not (isinstance(node.func, ast.Name) and node.func.id in funcs):
            raise ValueError(f"Unknown function in “{text}”. Functions: {', '.join(sorted(k for k in FUNCS))}, col.")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float, str)):
            raise ValueError(f"“{text}” has a value formulas cannot use.")
        if isinstance(node, ast.Name) and node.id not in env and node.id not in funcs:
            raise ValueError(f"“{node.id}” is not a column. Columns are A, B, C…" + (", X" if "X" in env else "") + " and i (the row number).")
    try:
        with np.errstate(all="ignore"):
            v = eval(compile(tree, "<formula>", "eval"), {"__builtins__": {}}, {**env, **funcs})
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"“{text}” could not be worked out ({e}).")
    v = np.broadcast_to(np.asarray(v, float), (n,)) if np.ndim(v) == 0 or np.size(v) == n else None
    if v is None:
        raise ValueError("The formula must give one value per row.")
    return [float(f"{x:.15g}") if math.isfinite(x) else None for x in v]  # no 421.34999999999997


def _unknown(name):
    raise ValueError(f"No data set is called “{name}”.")


def recalc(table, k=None, text=None):
    """Every formula column in order (left to right, each seeing the ones before), after setting data set k's
    formula to `text` when given: {"sets": [[k, values], …]}."""
    t = {**table, "sets": [dict(s) for s in table["sets"]], "cols": [list(c) for c in table["cols"]]}
    if k is not None:
        t["sets"][k]["formula"] = text or ""
    out = []
    for j, s in enumerate(t["sets"]):
        f = (s.get("formula") or "").strip()
        if not f:
            continue
        if s["entry"] != "rep" or s["reps"] != 1:
            raise ValueError(f"A formula fills a data set with one value per row; {s.get('title') or letter(j)} has {s['reps'] if s['entry'] == 'rep' else 3} columns.")
        vals = evaluate(t, f)
        c0 = stats.set_columns(t)[j][0]
        t["cols"][c0] = vals
        out.append([j, vals])
    return {"sets": out}


def sheet_view(table):
    """A worksheet seen as an XY table, keeping every data set in place: the first X column becomes X, a
    Y column followed by a Y-error column becomes mean ± SD, and X, error and skipped columns are hidden
    (`hidden`)."""
    sets, cols, hidden = [], [], []
    roles = [s.get("role", "") for s in table["sets"]]
    src = [c0 for c0, _ in stats.set_columns(table)]
    xk = next((k for k, r in enumerate(roles) if r == "x"), None)
    n = table["rows"]
    col = lambda k: list(table["cols"][src[k]]) + [None] * (n - len(table["cols"][src[k]])) if src[k] < len(table["cols"]) else [None] * n
    cols.append(col(xk) if xk is not None else [float(r + 1) for r in range(n)])
    ex = {(r, c) for r, c in table.get("excluded", [])}
    vex = []
    for k, s in enumerate(table["sets"]):
        err = k + 1 < len(roles) and roles[k + 1] == "yerr" and roles[k] == ""
        c0 = len(cols)
        if err:
            sets.append({**s, "entry": "msn", "reps": 3})
            cols += [col(k), col(k + 1), [None] * n]
        else:
            sets.append({**s, "entry": "rep", "reps": 1})
            cols.append(col(k))
        vex += [[r, c0] for r in range(n) if (r, src[k]) in ex]
        if roles[k] != "":
            hidden.append(k)
    xs = table["sets"][xk] if xk is not None else {}
    return {**table, "kind": "xy", "fromSheet": True, "sets": sets, "cols": cols, "excluded": vex, "hidden": hidden,
            "xTitle": (xs.get("title") or "X") if xk is not None else "Row", "xUnits": xs.get("units", "") if xk is not None else "",
            "yTitle": table.get("yTitle") or next((s.get("title") for s, r in zip(table["sets"], roles) if r == ""), "Y"),
            "yUnits": table.get("yUnits") or next((s.get("units", "") for s, r in zip(table["sets"], roles) if r == ""), "")}
