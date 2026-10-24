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
