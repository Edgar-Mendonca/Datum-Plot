"""Datum Plot's Python worker: the app starts it once and sends one JSON request per line on
stdin; each answer is one JSON line on stdout ({"ok": true, ...} or {"ok": false, "error": ...})."""
import json
import logging
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logging.getLogger("matplotlib").setLevel(logging.ERROR)


def main():
    out = sys.stdout
    sys.stdout = sys.stderr  # stray prints from libraries must not break the protocol
    import matplotlib
    import numpy
    import scipy
    from datum import graph, stats

    def handle(q):
        cmd = q.get("cmd")
        if cmd == "ping":
            return {"python": sys.version.split()[0], "numpy": numpy.__version__, "scipy": scipy.__version__, "matplotlib": matplotlib.__version__}
        if cmd == "render":
            return graph.render(q["table"], q["graph"], q.get("overlays", []))
        if cmd == "export":
            return graph.export(q["table"], q["graph"], q.get("fmt", "png"), q.get("path"), q.get("dpi", 300), q.get("transparent", False), q.get("overlays", []), q.get("cmyk", False))
        if cmd == "page":
            return graph.page(q["layout"], q["panels"], q.get("fmt", "svg"), q.get("path"), q.get("dpi", 300), q.get("cmyk", False))
        if cmd == "analyze":
            from datum import analysis
            return analysis.run(q["kind"], q["table"], q.get("sets", []), q.get("options", {}))
        if cmd == "models":
            from datum import analysis
            return {"models": analysis.model_list()}
        if cmd == "read":
            from datum import io as dio
            return dio.read_file(q["path"])
        if cmd == "excel":
            from datum import io as dio
            return dio.write_excel(q["path"], q["project"], q.get("analyses", []))
        if cmd == "report":
            from datum import report
            return (report.slides if q.get("kind") == "slides" else report.word)(q["project"], q["path"])
        if cmd == "read_many":
            from datum import imports
            return {"tables": imports.read_many(q["paths"])}
        if cmd == "region":
            from datum import region
            return region.region(q["table"], q["x0"], q["x1"], q.get("y0"), q.get("y1"))
        if cmd == "formula":
            from datum import sheet
            return sheet.recalc(q["table"], q.get("k"), q.get("text"))
        if cmd == "summary":
            return {"sets": stats.summarize(q["table"])}
        raise ValueError(f"Unknown request {cmd!r}")

    # Warm up (imports, font list, first figure) before saying ready.
    graph.render({"rows": 0, "sets": [], "cols": [[]]}, {})
    out.write(json.dumps({"ok": True, "ready": True}) + "\n")
    out.flush()
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            q = json.loads(line)
            r = {"ok": True, **handle(q)}
        except Exception as e:  # report every failure to the app instead of dying
            r = {"ok": False, "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc(limit=4)}
        out.write(json.dumps(r, allow_nan=False, default=str) + "\n")
        out.flush()


if __name__ == "__main__":
    main()
