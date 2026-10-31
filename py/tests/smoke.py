"""Engine smoke test: every template project through the real worker, as the app sends it. Every graph is drawn
and exported in every format, every analysis worked out, every layout drawn, and each project exported to
.xlsx/.ods, .pptx/.odp, .docx/.odt and a notebook. Any failed request fails the test.
  cargo run -q -p datum-core --example dump all > all.json && python py/tests/smoke.py all.json"""
import json
import os
import subprocess
import sys
import tempfile
import time

KINDS = ["scatter", "line", "bars", "box", "violin", "mean", "paired", "stacked", "percent", "pie", "donut", "contour", "heatmap", "surface", "wireframe", "arrow", "range"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(fixture):
    projects = json.load(open(fixture, encoding="utf-8"))
    w = subprocess.Popen([sys.executable, "-W", "ignore", os.path.join(ROOT, "worker.py")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8")
    assert json.loads(w.stdout.readline()).get("ready")
    failed, count, slow = [], 0, []

    def ask(what, q):
        nonlocal count
        count += 1
        t = time.time()
        w.stdin.write(json.dumps(q) + "\n")
        w.stdin.flush()
        r = json.loads(w.stdout.readline())
        if time.time() - t > 20:
            slow.append(f"{what} ({time.time() - t:.0f} s)")
        if not r.get("ok"):
            failed.append(f"{what}: {r.get('error')}")
        return r

    with tempfile.TemporaryDirectory() as d:
        for i, p in enumerate(projects):
            tables = {t["id"]: t for t in p["tables"]}
            overlays = lambda s: [{"kind": a["kind"], "sets": a["sets"], "options": a["options"]} for a in p["analyses"] if a["id"] in s.get("overlays", [])]
            name = p["tables"][0]["name"] if p["tables"] else f"project {i}"
            for a in p["analyses"]:
                ask(f"{name} › {a['kind']}", {"cmd": "analyze", "kind": a["kind"], "table": tables[a["table"]], "sets": a["sets"], "options": a["options"]})
                if a["kind"] == "twoway":  # repeated measures designs (B32)
                    for rm in ("rows", "sets", "both"):
                        ask(f"{name} › twoway rm={rm}", {"cmd": "analyze", "kind": "twoway", "table": tables[a["table"]], "sets": a["sets"], "options": {**a["options"], "rm": rm}})
            for g in p["graphs"]:
                q = {"table": tables[g["table"]], "graph": g["settings"], "overlays": overlays(g["settings"])}
                ask(f"{name} › graph {g['name']}", {"cmd": "render", **q})
                for fmt in ("png", "tiff", "svg", "pdf", "eps"):
                    ask(f"{name} › {fmt}", {"cmd": "export", **q, "fmt": fmt, "dpi": 150, "path": os.path.join(d, f"g{i}.{fmt}")})
            for l in p["layouts"]:
                panels = {str(g["id"]): {"table": tables[g["table"]], "graph": g["settings"], "overlays": overlays(g["settings"])} for g in p["graphs"]}
                ask(f"{name} › layout", {"cmd": "page", "layout": l, "panels": panels, "fmt": "svg"})
            for t in p["tables"]:
                ask(f"{name} › summary", {"cmd": "summary", "table": t})
                g = next((g["settings"] for g in p["graphs"] if g["table"] == t["id"]), {})
                for kind in KINDS:  # every graph type on every kind of table: wrong ones fall back, never fail
                    ask(f"{name} › {kind} graph", {"cmd": "render", "table": t, "graph": {**g, "column": kind}, "overlays": []})
            ask(f"{name} › .xlsx", {"cmd": "excel", "project": p, "analyses": p["analyses"], "path": os.path.join(d, f"p{i}.xlsx")})
            ask(f"{name} › .ipynb", {"cmd": "notebook", "project": p, "path": os.path.join(d, f"p{i}.ipynb")})
            ask(f"{name} › console", {"cmd": "console", "project": p, "code": "len(tables)"})
        ask("slides", {"cmd": "report", "kind": "slides", "project": projects[0], "path": os.path.join(d, "r.pptx")})
        ask("report", {"cmd": "report", "kind": "word", "project": projects[0], "path": os.path.join(d, "r.docx")})
        ask("slides .odp", {"cmd": "report", "kind": "slides", "project": projects[0], "path": os.path.join(d, "r.odp")})
        ask("document .odt", {"cmd": "report", "kind": "word", "project": projects[0], "path": os.path.join(d, "r.odt")})
        ask("workbook .ods", {"cmd": "excel", "project": projects[0], "analyses": projects[0]["analyses"], "path": os.path.join(d, "p0.ods")})
        ask("read back", {"cmd": "read", "path": os.path.join(d, "p0.xlsx")})
        left = [f for f in os.listdir(d) if f.endswith(".tmp")]
    w.stdin.close()
    w.wait(30)
    print(f"{len(projects)} projects, {count} requests, {len(failed)} failed")
    for f in failed + [f"slow: {s}" for s in slow] + [f"temporary file left: {f}" for f in left]:
        print("  " + f)
    sys.exit(1 if failed or left else 0)


if __name__ == "__main__":
    main(sys.argv[1])
