"""Reading data files for File › Import: CSV, TSV, TXT and Excel workbooks. Every cell comes back
as text (numbers without trailing zeros, dates as ISO), the Rust engine parses the numbers."""
import csv
import datetime
import io
import os
import re

MAX_ROWS, MAX_COLS = 200_000, 500
DECIMAL_COMMA = re.compile(r"^-?\d+,\d+$")


def cell(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(v).upper()
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() and abs(v) < 1e15 else repr(v)
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    return str(v).strip()


def read_text(path):
    """A delimited text file: the delimiter is guessed; 1,5 becomes 1.5 when ; separates columns."""
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    sample = "\n".join(text.splitlines()[:50])
    try:
        delim = csv.Sniffer().sniff(sample, delimiters=",;\t| ").delimiter
    except csv.Error:
        delim = "\t" if "\t" in sample else ","
    rows = []
    for r in csv.reader(io.StringIO(text), delimiter=delim, skipinitialspace=delim == " "):
        if len(rows) >= MAX_ROWS:
            break
        r = [c.strip() for c in r[:MAX_COLS]]
        if delim == ";":
            r = [c.replace(",", ".") if DECIMAL_COMMA.match(c) else c for c in r]
        rows.append(r)
    while rows and not any(rows[-1]):
        rows.pop()
    return [{"name": os.path.splitext(os.path.basename(path))[0], "rows": rows, "delimiter": delim}]


def read_excel(path):
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True, data_only=True)
    out = []
    for ws in wb.worksheets:
        rows = []
        for r in ws.iter_rows(values_only=True, max_col=MAX_COLS):
            if len(rows) >= MAX_ROWS:
                break
            rows.append([cell(v) for v in r])
        while rows and not any(rows[-1]):
            rows.pop()
        width = max((max((i + 1 for i, c in enumerate(r) if c), default=0) for r in rows), default=0)
        out.append({"name": ws.title, "rows": [r[:width] for r in rows]})
    wb.close()
    return out


def read_file(path):
    """{"sheets": [{"name", "rows": [[text]]}]} for a CSV, TSV, TXT or XLSX file."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm"):
        sheets = read_excel(path)
    elif ext in (".csv", ".tsv", ".txt", ".dat", ".prn"):
        sheets = read_text(path)
    else:
        raise ValueError(f"Datum Plot cannot read {ext or 'this kind of'} files yet. Use CSV, TXT or Excel (.xlsx).")
    return {"sheets": sheets}


def write_excel(path, project, analyses):
    """File › Export › Excel workbook: a sheet per data table and one per result (G6)."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from . import analysis, stats
    wb = Workbook()
    wb.remove(wb.active)
    bold, head = Font(bold=True), PatternFill("solid", fgColor="E3F5F2")
    used = set()

    def sheet(name):
        base = re.sub(r"[\[\]:*?/\\]", " ", name).strip()[:28] or "Sheet"
        n, k = base, 2
        while n.lower() in used:
            n, k = f"{base[:25]} ({k})", k + 1
        used.add(n.lower())
        return wb.create_sheet(n)

    for t in project.get("tables", []):
        ws = sheet(t["name"])
        xy = t.get("kind", "xy") in ("xy", "survival", "matrix")
        grouped = t.get("kind") in ("grouped", "contingency", "parts", "multi", "sheet")
        heads = ([f"{t.get('xTitle') or 'X'}{' (' + t['xUnits'] + ')' if t.get('xUnits') else ''}"] if xy else ["Row"] if grouped else [])
        sub = {"msn": ["Mean", "SD", "N"], "mesn": ["Mean", "SEM", "N"]}
        for s, (c0, w) in zip(t["sets"], stats.set_columns(t)):
            heads += [f"{s['title']}" + (f" {sub[s['entry']][j]}" if s["entry"] != "rep" else f" Y{j + 1}" if w > 1 else "") for j in range(w)]
        ws.append(heads)
        for c in ws[1]:
            c.font, c.fill = bold, head
        ex = {tuple(e) for e in t.get("excluded", [])}
        first = 0 if xy else 1
        for r in range(t["rows"]):
            row = [t["cols"][c][r] if c < len(t["cols"]) and r < len(t["cols"][c]) else None for c in range(first, len(t["cols"]))]
            if any(v is not None for v in row):
                lead = [(t.get("rowTitles") or [""] * t["rows"])[r] or f"Row {r + 1}"] if grouped else []
                ws.append(lead + row)
                for j, c in enumerate(ws[ws.max_row][len(lead):]):
                    if (r, j + first) in ex:
                        c.font = Font(italic=True, color="1F6FD0")
        ws.freeze_panes = "A2"
    for a in analyses:
        t = next((x for x in project.get("tables", []) if x["id"] == a["table"]), None)
        if t is None:
            continue
        ws = sheet(a["name"])
        try:
            res = analysis.run(a["kind"], t, a.get("sets", []), a.get("options", {}))
        except Exception as e:
            ws.append([a["name"]]); ws.append([f"Could not calculate: {e}"]); continue
        ws.append([res["title"]]); ws["A1"].font = Font(bold=True, size=13)
        ws.append([res["answer"]]); ws.append([])
        for tab in res["tabs"]:
            for tb in tab["tables"]:
                ws.append([f"{tab['name']} · {tb['title']}" if tb["title"] else tab["name"]]); ws.cell(ws.max_row, 1).font = bold
                ws.append(tb["columns"])
                for c in ws[ws.max_row]:
                    c.font, c.fill = bold, head
                for row in tb["rows"]:
                    ws.append([num(v) for v in row])
                ws.append([])
        ws.append(["Methods"]); ws.cell(ws.max_row, 1).font = bold
        ws.append([res["methods"]])
        ws.column_dimensions["A"].width = 34
    wb.save(path)
    return {"path": path, "sheets": len(wb.sheetnames)}


def num(v):
    """Result cells are text; plain numbers go to Excel as numbers."""
    try:
        return float(v) if re.fullmatch(r"-?\d+(\.\d+)?(e[-+]?\d+)?", v.strip()) else v
    except (AttributeError, ValueError):
        return v
