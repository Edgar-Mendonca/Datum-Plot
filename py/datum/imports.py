"""Importing tables (A13, A14): .pzfx project files, 96- and 384-well plate blocks found in a sheet, and
several files at once (one run per file). Each returns tables in the engine's JSON, ready to add."""
import math
import os
import xml.etree.ElementTree as ET

from .io import read_file

KINDS = {"XY": "xy", "OneWay": "column", "TwoWay": "grouped", "Contingency": "contingency", "Survival": "survival", "PartsOfWhole": "parts", "Nested": "nested", "MultipleVariables": "multi"}
ENTRY = {"SDN": "msn", "SEN": "mesn", "SD": "msn", "SE": "mesn"}


def number(s):
    if s is None:
        return None
    try:
        v = float(str(s).strip().replace(",", "."))
        return v if math.isfinite(v) else None
    except ValueError:
        return None


def _tag(e):
    return e.tag.rsplit("}", 1)[-1]


def _kids(e, name):
    return [c for c in e if _tag(c) == name]


def _text(e, name):
    k = _kids(e, name)
    return "".join(k[0].itertext()).strip() if k else ""


def read_pzfx(path):
    """Tables, titles, replicates, row titles and excluded values from a .pzfx project (its XML)."""
    root = ET.parse(path).getroot()
    tables = []
    for t in root.iter():
        if _tag(t) not in ("Table", "HugeTable"):
            continue
        kind = KINDS.get(t.get("TableType", "XY"), "xy")
        entry = ENTRY.get(t.get("YFormat", ""), "rep")
        cols, excl, sets = [], [], []

        def subcols(col):
            out = []
            for sc in _kids(col, "Subcolumn"):
                out.append([(number("".join(d.itertext())), d.get("Excluded") == "1") for d in _kids(sc, "d")])
            return out
        xcol = (_kids(t, "XColumn") or _kids(t, "XAdvancedColumn"))
        xs = subcols(xcol[0])[0] if xcol and subcols(xcol[0]) else []
        cols.append([v for v, _ in xs])
        for y in _kids(t, "YColumn"):
            subs = subcols(y)
            if entry != "rep":
                subs = (subs + [[]] * 3)[:3]
            c0 = len(cols)
            for j, sc in enumerate(subs):
                cols.append([v for v, _ in sc])
                excl += [[r, c0 + j] for r, (_, ex) in enumerate(sc) if ex]
            sets.append({"title": _text(y, "Title"), "entry": entry, "reps": max(1, len(subs)) if entry == "rep" else 3})
        if not sets:
            continue
        rt = _kids(t, "RowTitlesColumn")
        titles = ["".join(d.itertext()).strip() for sc in (_kids(rt[0], "Subcolumn") if rt else [])[:1] for d in _kids(sc, "d")]
        n = max([len(c) for c in cols] + [len(titles), 1])
        cols = [c + [None] * (n - len(c)) for c in cols]
        tables.append({"name": _text(t, "Title") or f"Table {len(tables) + 1}", "kind": kind, "xTitle": _text(xcol[0], "Title") if xcol else "", "yTitle": "",
                       "rows": n, "rowTitles": titles + [""] * (n - len(titles)), "sets": sets, "cols": cols, "excluded": excl})
    if not tables:
        raise ValueError("No data tables were found in that .pzfx file.")
    return tables


def plates(sheets):
    """96- (8 × 12) and 384-well (16 × 24) blocks: a row with 1, 2, 3… and rows below starting A, B, C…
    Each becomes a grouped table with the plate's rows as row titles and its columns as data sets."""
    out = []
    for sh in sheets:
        rows = sh["rows"]
        for r, line in enumerate(rows):
            for c in range(len(line)):
                for w, h in ((12, 8), (24, 16)):
                    if [str(v).strip() for v in line[c:c + w]] != [str(i) for i in range(1, w + 1)] or c == 0:
                        continue
                    block = rows[r + 1:r + 1 + h]
                    if len(block) < h or [str(b[c - 1]).strip().upper() if len(b) > c - 1 else "" for b in block] != [chr(65 + i) for i in range(h)]:
                        continue
                    vals = [[number(b[c + j]) if c + j < len(b) else None for b in block] for j in range(w)]
                    if sum(v is not None for col in vals for v in col) < w:
                        continue
                    out.append({"name": f"{sh['name']} plate" if len(out) == 0 else f"{sh['name']} plate {len(out) + 1}", "kind": "grouped", "xTitle": "", "yTitle": "Signal",
                                "rows": h, "rowTitles": [chr(65 + i) for i in range(h)], "sets": [{"title": str(j + 1), "entry": "rep", "reps": 1} for j in range(w)],
                                "cols": [[None] * h] + vals, "excluded": []})
    return out


def numeric_table(rows):
    """(headings or None, columns of numbers) of a sheet: a first row of words is the headings."""
    rows = [r for r in rows if any(str(c).strip() for c in r)]
    head = None
    if rows and all(number(c) is None for c in rows[0] if str(c).strip()):
        head, rows = rows[0], rows[1:]
    width = max((len(r) for r in rows), default=0)
    cols = [[number(r[j]) if j < len(r) else None for r in rows] for j in range(width)]
    keep = [j for j, c in enumerate(cols) if any(v is not None for v in c)]
    return ([head[j] if head and j < len(head) else "" for j in keep] if head else None), [cols[j] for j in keep]


def read_many(paths):
    """Several files: one data set per file (per Y column) in one XY table when they share their X values,
    otherwise one table per file."""
    runs = []
    for p in paths:
        sh = next((s for s in read_file(p)["sheets"] if s["rows"]), None)
        if not sh:
            continue
        head, cols = numeric_table(sh["rows"])
        if not cols:
            continue
        name = os.path.splitext(os.path.basename(p))[0]
        if len(cols) == 1:
            cols = [[float(i + 1) for i in range(len(cols[0]))]] + cols
            head = ["Row", *(head or [""])]
        runs.append((name, head, cols))
    if not runs:
        raise ValueError("None of those files has numbers in it.")
    same = len(runs) > 1 and all(len(r[2][0]) == len(runs[0][2][0]) and all(a == b for a, b in zip(r[2][0], runs[0][2][0])) for r in runs)
    title = lambda name, head, j, ny: name if ny == 1 else f"{name} {(head[j] if head and head[j] else f'Y{j}')}"
    if same:
        x = runs[0][2][0]
        sets, cols = [], [x]
        for name, head, c in runs:
            for j in range(1, len(c)):
                sets.append({"title": title(name, head, j, len(c) - 1), "entry": "rep", "reps": 1})
                cols.append(c[j])
        h0 = runs[0][1]
        return [{"name": "Runs", "kind": "xy", "xTitle": (h0[0] if h0 else "X") or "X", "yTitle": (h0[1] if h0 and len(h0) > 1 else "Y") or "Y", "rows": len(x),
                 "rowTitles": [], "sets": sets, "cols": cols, "excluded": []}]
    out = []
    for name, head, c in runs:
        n = max(len(v) for v in c)
        out.append({"name": name, "kind": "xy", "xTitle": (head[0] if head else "X") or "X", "yTitle": (head[1] if head and len(head) > 1 else "Y") or "Y", "rows": n, "rowTitles": [],
                    "sets": [{"title": title(name, head, j, len(c) - 1) if len(c) > 2 else (head[j] if head and head[j] else name), "entry": "rep", "reps": 1} for j in range(1, len(c))],
                    "cols": [v + [None] * (n - len(v)) for v in c], "excluded": []})
    return out
