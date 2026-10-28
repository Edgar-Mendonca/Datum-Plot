"""The Python console (H1) and notebook export (H5).

The console runs the user's own code, as they type it, in one namespace that lasts until the engine
restarts. Each run sees the project's tables as pandas DataFrames, and can add new tables with
new_table(...). Nothing here runs code from a project file: opening someone else's project never runs code."""
import ast
import contextlib
import io
import json
import math
import os
import traceback
from collections.abc import Mapping

import numpy as np

from . import analysis, stats

NS = {}
LIMIT = 100_000  # characters of output sent back


def frame(t):
    """A table as a DataFrame: X (if the table has one), then each data set's columns, row titles as the index."""
    import pandas as pd
    cols = {}
    if t.get("kind", "xy") in ("xy", "survival", "matrix"):
        cols[t.get("xTitle") or "X"] = t["cols"][0] if t["cols"] else []
    sub = {"msn": ["mean", "SD", "N"], "mesn": ["mean", "SEM", "N"]}
    for k, (s, (c0, w)) in enumerate(zip(t["sets"], stats.set_columns(t))):
        name = s.get("title") or f"Data set {chr(65 + k)}"
        for j in range(w):
            key = name if w == 1 else f"{name} {sub[s['entry']][j] if s['entry'] in sub else j + 1}"
            while key in cols:
                key += "'"
            cols[key] = t["cols"][c0 + j] if c0 + j < len(t["cols"]) else []
    n = t.get("rows", 0)
    df = pd.DataFrame({k: pd.Series([np.nan if v is None else v for v in (c + [None] * (n - len(c)))[:n]], dtype=float) for k, c in cols.items()})
    titles = t.get("rowTitles") or []
    if any(titles):
        df.index = [titles[i] if i < len(titles) and titles[i] else str(i + 1) for i in range(n)]
    return df.dropna(how="all")


class Tables(Mapping):
    """tables["Name"]: each table as a DataFrame, made the first time it is used."""
    def __init__(self, raw):
        self.raw, self.done = {t.get("name") or f"Table {i + 1}": t for i, t in enumerate(raw)}, {}

    def __getitem__(self, key):
        if key not in self.raw:
            raise KeyError(f"No table is called {key!r}. Tables: {', '.join(map(repr, self.raw))}")
        if key not in self.done:
            self.done[key] = frame(self.raw[key])
        return self.done[key]

    def __iter__(self):
        return iter(self.raw)

    def __len__(self):
        return len(self.raw)

    def __repr__(self):
        return "Tables: " + ", ".join(map(repr, self.raw))


def to_table(name, data, kind):
    """A new table from a DataFrame, a dict of columns or a list of columns: the first column is X for XY tables."""
    import pandas as pd
    df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    if df.empty:
        raise ValueError("new_table needs some data.")
    kind = kind if kind in ("xy", "column", "multi", "sheet") else "xy"
    names = [str(c) for c in df.columns]
    vals = [[None if (v is None or (isinstance(v, float) and not math.isfinite(v))) else float(v) for v in pd.to_numeric(df[c], errors="coerce").tolist()] for c in df.columns]
    n = len(df)
    if kind == "xy":
        x, ys, xt = vals[0], vals[1:] or [[None] * n], names[0]
        ynames = names[1:] or ["Y"]
    else:
        x, ys, xt, ynames = [None] * n, vals, "", names
    sets = [{"title": t, "entry": "rep", "reps": 1, **({"role": "x" if i == 0 else ""} if kind == "sheet" else {})} for i, t in enumerate(ynames)]
    titles = [str(i) for i in df.index] if not isinstance(df.index, pd.RangeIndex) else []
    return {"name": str(name), "kind": kind, "xTitle": xt, "yTitle": "", "rows": n, "rowTitles": titles, "sets": sets, "cols": [x] + ys, "excluded": []}


def run(project, code):
    """Runs `code`; returns {"out": text, "figures": [svg], "tables": [new tables], "error": bool}."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    import scipy
    from scipy import stats as sst
    tables = project.get("tables", [])
    pending = []

    def table(which):
        """A table by its name or its position (0 = the first)."""
        t = tables[which] if isinstance(which, int) else next((t for t in tables if t.get("name") == which), None)
        if t is None:
            raise KeyError(f"No table is called {which!r}. Tables: {', '.join(repr(t.get('name')) for t in tables)}")
        return frame(t)

    def result(name):
        """An analysis's result (as on its results sheet) by its name."""
        a = next((a for a in project.get("analyses", []) if a.get("name") == name), None)
        if a is None:
            raise KeyError(f"No analysis is called {name!r}. Analyses: {', '.join(repr(a.get('name')) for a in project.get('analyses', []))}")
        t = next(t for t in tables if t["id"] == a["table"])
        return analysis.run(a["kind"], t, a.get("sets", []), a.get("options", {}))

    def new_table(name, data, kind="xy"):
        """Adds a table to the project when the code has run: a DataFrame or {column: values}; for XY the first column is X."""
        pending.append(to_table(name, data, kind))
        return f"Table {name!r} will be added."

    if not NS:
        NS.update({"__name__": "__console__", "np": np, "pd": pd, "scipy": scipy, "stats": sst, "plt": plt})
    NS.update({"tables": Tables(tables), "table": table, "result": result, "new_table": new_table})
    buf, err = io.StringIO(), False
    plt.close("all")
    try:
        tree = ast.parse(code, "<console>", "exec")
        last = tree.body.pop() if tree.body and isinstance(tree.body[-1], ast.Expr) else None
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf), np.errstate(all="ignore"):
            exec(compile(tree, "<console>", "exec"), NS)
            if last is not None:
                v = eval(compile(ast.Expression(last.value), "<console>", "eval"), NS)
                if v is not None:
                    print(v if isinstance(v, (str, np.generic)) else repr(v))  # 2.33, not np.float64(2.33)
    except SyntaxError as e:
        err = True
        buf.write(f"Line {e.lineno}: {e.msg}\n{(e.text or '').rstrip()}\n{' ' * max((e.offset or 1) - 1, 0)}^\n")
    except (Exception, SystemExit) as e:  # the user's own code: report it and keep the engine alive
        err = True
        frames = [f for f in traceback.extract_tb(e.__traceback__) if f.filename == "<console>"]
        where = f"Line {frames[-1].lineno}: " if frames else ""
        buf.write(f"{where}{type(e).__name__}: {e}\n")
    figs = []
    for n in plt.get_fignums()[:6]:
        f = plt.figure(n)
        s = io.StringIO()
        f.savefig(s, format="svg", bbox_inches="tight", metadata={"Date": None})
        figs.append(s.getvalue())
    plt.close("all")
    out = buf.getvalue()
    if len(out) > LIMIT:
        out = out[:LIMIT] + f"\n… ({len(out) - LIMIT} more characters not shown)"
    return {"out": out, "figures": figs, "tables": pending, "error": err}


def reset():
    NS.clear()
    return {"out": "The console was cleared: variables and imports start again.", "figures": [], "tables": [], "error": False}


# ---------- notebook export (H5) ----------
def notebook(project, path):
    """The project as a Jupyter notebook: its tables as DataFrames (large ones in CSV files beside it), each
    analysis's answer and the Python behind it, and a graph of each table."""
    cells = []
    md = lambda s: cells.append({"cell_type": "markdown", "metadata": {}, "source": s})
    code = lambda s: cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s})
    info = project.get("info") or {}
    md(f"# {info.get('title') or project.get('name') or 'Datum Plot project'}\n\n{info.get('experiment') or ''}\n\nExported from Datum Plot.")
    code("import numpy as np\nimport pandas as pd\nimport matplotlib.pyplot as plt\nfrom scipy import stats")
    import pandas as pd
    base, names = os.path.splitext(path)[0], {}
    for i, t in enumerate(project.get("tables", [])):
        df = frame(t)
        var = f"t{i + 1}"
        names[t["id"]] = var
        md(f"## {t.get('name') or var}")
        if df.size > 5000:
            csv = f"{base}-{var}.csv"
            df.to_csv(csv, index=not isinstance(df.index, pd.RangeIndex))
            code(f"{var} = pd.read_csv({os.path.basename(csv)!r})\n{var}.head()")
        else:
            code(f"{var} = pd.DataFrame({json.dumps({c: [None if v != v else v for v in df[c].tolist()] for c in df.columns})})\n{var}")
        if df.shape[1] > 1 and t.get("kind", "xy") == "xy":
            code(f"{var}.plot(x={df.columns[0]!r}, style='o-')\nplt.show()")
    for a in project.get("analyses", []):
        t = next((t for t in project.get("tables", []) if t["id"] == a["table"]), None)
        if not t:
            continue
        try:
            r = analysis.run(a["kind"], t, a.get("sets", []), a.get("options", {}))
        except Exception as e:  # noqa: BLE001
            r = {"answer": f"Could not be worked out: {e}", "code": "", "methods": ""}
        var = names[t["id"]]
        md(f"## {a.get('name') or a['kind']}\n\n{r.get('answer', '')}\n\n*{r.get('methods', '')}*")
        if r.get("code"):
            code(f"# Data: {var}; x is its first column, y the next (adapt as needed)\nx, y = {var}.iloc[:, 0].to_numpy(), {var}.iloc[:, 1].to_numpy()\n" + "\n".join(l for l in r["code"].splitlines() if "[...]" not in l))  # the snippets' placeholders would overwrite the data
    nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    return {"path": path, "cells": len(cells)}
