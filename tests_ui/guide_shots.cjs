// Screenshots for the guide (docs/guide/img): the built window (ui/dist) with a sample project
// (cargo run -p datum-core --example dump guide > tests_ui/guide_fixture.json) behind the mocked bridge;
// graphs, results and the layout come from the real Python engine. Numbered markers are drawn on the page.
// Run: npm run build:ui && node tests_ui/guide_shots.cjs   (as in Datum Plan)
const { chromium } = require("playwright");
const { execFileSync } = require("child_process");
const fs = require("fs"), http = require("http"), path = require("path");
const root = path.join(__dirname, "../ui/dist"), out = path.join(__dirname, "../docs/guide/img");
const fixFile = path.join(__dirname, "guide_fixture.json");
const fix = JSON.parse(fs.readFileSync(fixFile));
// Every graph, result and layout of the project, as the engine draws them.
const py = `
import json, sys
sys.path.insert(0, sys.argv[1])
from datum import graph, analysis, console
p = json.load(open(sys.argv[2]))["state"]["project"]
T = {t["id"]: t for t in p["tables"]}
ov = lambda s: [{"kind": a["kind"], "sets": a["sets"], "options": a["options"]} for a in p["analyses"] if a["id"] in s.get("overlays", [])]
r = {"render": {g["id"]: graph.render(T[g["table"]], g["settings"], ov(g["settings"])) for g in p["graphs"]},
     "result": {a["id"]: analysis.run(a["kind"], T[a["table"]], a["sets"], a["options"]) for a in p["analyses"]},
     "page": {l["id"]: graph.page(l, {str(g["id"]): {"table": T[g["table"]], "graph": g["settings"], "overlays": ov(g["settings"])} for g in p["graphs"]}, "svg", None) for l in p["layouts"]},
     "console": console.run(p, "df = table(0)\\nprint(df.describe().round(3).iloc[:, :3])\\nplt.figure(figsize=(4, 2.6))\\nplt.plot(df.iloc[:, 0], df.iloc[:, 1], 'o-')\\nplt.xlabel('Time (h)'); plt.ylabel('OD600'); plt.tight_layout()"),
     "models": analysis.model_list()}
print(json.dumps(r, default=str))`;
const eng = JSON.parse(execFileSync(process.env.PYTHON || "python3", ["-W", "ignore", "-c", py, path.join(__dirname, "../py"), fixFile], { maxBuffer: 1 << 28 }).toString());
const types = { ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".woff2": "font/woff2", ".woff": "font/woff", ".html": "text/html" };
const srv = http.createServer((q, r) => {
  const f = path.join(root, q.url === "/" ? "index.html" : decodeURIComponent(q.url.split("?")[0]));
  fs.readFile(f, (e, b) => { if (e) { r.writeHead(404); return r.end(); } r.writeHead(200, { "content-type": types[path.extname(f)] ?? "application/octet-stream" }); r.end(b); });
});

(async () => {
  fs.mkdirSync(out, { recursive: true });
  await new Promise(ok => srv.listen(0, ok));
  const b = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  const p = await b.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.5 });
  await p.addInitScript(([f, e]) => {
    try { localStorage.setItem("guide-hint", "1"); } catch { /* none */ }
    const opts = { theme: "light", autosave: 0, beta: false, openLast: false, decimals: -1, reps: 3, entry: "rep", error: "sd", width: 80, height: 60, font: "Arial", fontSize: 10, style: "prism", dpi: 300, paper: "A4", landscape: false, company: "", logo: "", styles: {} };
    const m = { state: f.state, options: opts, startup_file: null, recovery: null, check_update: null, templates: f.templates, recent: [{ path: "C:\\Users\\you\\Documents\\Strain study.dplot", name: "Strain study", saved: "today" }], version: "0.3.2",
      engine: { versions: { python: "3.13", numpy: "2.3", scipy: "1.16", matplotlib: "3.10" }, error: null }, models: { models: e.models }, new_project: f.state,
      console: { ...e.console, state: f.state } };
    window.__TAURI__ = { core: { invoke: async (c, a) => {
      if (c === "render") return e.render[a.id];
      if (c === "result") return e.result[a.id];
      if (c === "render_page") return e.page[a.id];
      if (c in m) return m[c];
      if (c === "apply" || c === "history") return f.state;
      return null;
    } }, event: { listen: async () => () => {} } };
  }, [fix, eng]);
  await p.goto(`http://localhost:${srv.address().port}/`);
  await p.waitForTimeout(900);

  const wait = ms => p.waitForTimeout(ms);
  const tab = async t => { await p.click(`.tabs button:text-is('${t}')`); await wait(250); };
  const nav = async k => { await p.click(`.nav .nitem >> nth=${k}`); await wait(900); };
  /** Numbered markers: [selector or {x,y,w,h}, number, optional nth match, optional place]. */
  const mark = marks => p.evaluate(ms => {
    document.querySelectorAll(".gmark").forEach(e => e.remove());
    for (const [s, n, k, pos] of ms) {
      // "grp:Insert" is the ribbon group with that caption; "text:Tell me" the smallest element with that text.
      const find = q => q.startsWith("grp:") ? [...document.querySelectorAll(".ribbon .grp")].find(g => (g.querySelector(".cap")?.textContent ?? "").replace("?", "").trim().toLowerCase() === q.slice(4).toLowerCase())
        : q.startsWith("text:") ? [...document.querySelectorAll("body *")].filter(e => e.textContent.includes(q.slice(5)) && e.getBoundingClientRect().width > 0).sort((a, b) => a.textContent.length - b.textContent.length)[0]
        : document.querySelectorAll(q)[k ?? 0];
      const el = typeof s === "string" ? find(s) : null;
      const r = el ? el.getBoundingClientRect() : s;
      if (!r || !r.width) { console.log("no marker target", s); continue; }
      const box = document.createElement("div");
      box.className = "gmark";
      Object.assign(box.style, { position: "fixed", left: `${r.x - 3}px`, top: `${r.y - 3}px`, width: `${r.width + 6}px`, height: `${r.height + 6}px`, border: "3px solid #E4572E", borderRadius: "6px", zIndex: 99999, pointerEvents: "none", boxShadow: "0 0 0 2px rgba(255,255,255,.85)" });
      const dot = document.createElement("div");
      dot.textContent = n;
      const where = pos ?? (r.x < 14 || r.y < 14 ? "right" : "corner");
      const at = { corner: ["-14px", "-14px"], right: [`${r.width + 10}px`, `${Math.min(r.height / 2 - 10, 40)}px`], in: ["6px", "6px"], below: ["0px", `${r.height + 10}px`] }[where];
      Object.assign(dot.style, { position: "absolute", left: at[0], top: at[1], width: "26px", height: "26px", borderRadius: "13px", background: "#E4572E", color: "#fff", font: "700 14px/26px 'IBM Plex Sans', sans-serif", textAlign: "center", boxShadow: "0 1px 3px rgba(0,0,0,.35)" });
      box.append(dot);
      document.body.append(box);
    }
  }, marks);
  p.on("console", m => { if (m.text().startsWith("no marker")) console.log("  ", m.text()); });
  /** `clip`: part of the window (x, y, width, height), or a selector to frame with a margin. */
  const shot = async (name, marks = [], clip) => {
    await mark(marks); await wait(150);
    if (typeof clip === "string") clip = await p.evaluate(s => { const r = document.querySelector(s).getBoundingClientRect(); return { x: Math.max(0, r.x - 24), y: Math.max(0, r.y - 24), width: Math.min(r.width + 48, 1440), height: Math.min(r.height + 48, 900) }; }, clip);
    await p.screenshot({ path: path.join(out, `${name}.png`), clip });
    await mark([]); console.log("shot", name);
  };
  const TOP = { x: 0, y: 0, width: 1440, height: 200 };

  // 1. Home: blank table, samples, import, guide.
  await shot("home", [[".home .tile", 1, 0], [".home .tile", 2, 1], [".bs aside", 3, 0, "in"]]);
  await p.click(".bs aside .back"); await wait(600);
  // Navigator order: info, 4 tables, 4 results, 4 graphs, 1 layout.
  await nav(9);
  const tabsBox = await p.evaluate(() => { const t = [...document.querySelectorAll(".tabs > button")]; const a = t[0].getBoundingClientRect(), z = t[t.length - 1].getBoundingClientRect(); return { x: a.x + 2, y: a.y + 2, width: z.right - a.x - 2, height: a.height - 4 }; });
  await shot("window", [[tabsBox, 1, 0, "right"], [".ribbon", 2], [".side", 3, 0, "in"], [".nav", 4], [".gpaper", 5]]);
  await tab("Graph"); await shot("graph-tab", [["grp:Graph", 1], ["grp:Axes", 2], ["grp:Style", 3], ["grp:Share", 4]], TOP);
  await p.click('.ribbon .rb.big:has-text("Format Axes")'); await wait(400);
  await shot("format", [[".dlg .dtabs", 1], [".dlg .fmtpage", 2], [".gpaper", 3]]);
  await p.keyboard.press("Escape"); await wait(200);
  // 2. The data table.
  await nav(1);
  await tab("Data"); await shot("table", [["grp:Insert", 1], [".dhead", 2], [".dgrid", 3, 0, "in"]], { x: 0, y: 0, width: 1440, height: 640 });
  await p.click('.ribbon .rb:has-text("New Table")'); await wait(400);
  await shot("new-table", [[".dlg .gal nav, .dlg nav", 1], [".galitem", 2, 0]], ".dlg");
  await p.keyboard.press("Escape"); await wait(200);
  // 3. Analyze.
  await tab("Analyze"); await shot("analyze-tab", [["grp:Analyze", 1]], TOP);
  await p.click('.ribbon .rb:has-text("Analyze…")'); await wait(400);
  await shot("analyze", [[".dlg nav", 1], [".dlg .galitem", 2, 0]], ".dlg");
  await p.keyboard.press("Escape"); await wait(200);
  await nav(5); await wait(600);
  await shot("results", [[".rview .rtable", 1, 0], [".explain .ans", 2, 0, "below"], [".explain .checks", 3, 0, "below"]]);
  await nav(6); await wait(400); await shot("anova-results");
  // 4. Other graphs.
  await nav(10); await shot("anova", [[".gpaper", 1]]);
  await nav(11); await shot("contour", [[".gpaper", 1]]);
  await nav(12); await shot("survival");
  // 5. Layout.
  await nav(13); await wait(600);
  await tab("Layout"); await shot("layout", [["grp:Layout", 1], [".lpaper", 2]]);
  // 6. Tools: the Python console.
  await tab("Tools"); await shot("tools-tab", [["grp:Python", 1]], TOP);
  await p.click('.ribbon .rb:has-text("Python Console")'); await wait(400);
  await p.evaluate(() => { const t = document.querySelector(".concode"); t.value = "df = table(0)\nprint(df.describe().round(3).iloc[:, :3])\nplt.figure(figsize=(4, 2.6))\nplt.plot(df.iloc[:, 0], df.iloc[:, 1], 'o-')\nplt.xlabel('Time (h)'); plt.ylabel('OD600'); plt.tight_layout()"; t.dispatchEvent(new Event("input", { bubbles: true })); });
  await p.click('.conbar .btn:has-text("Run")'); await wait(700);
  await shot("console", [[".concode", 1], [".conbar .btn.pri", 2], [".conlog", 3], ["text:ⓘ How to use", 4]], ".dlg");
  await p.keyboard.press("Escape"); await wait(200);
  // 7. Help and the guide.
  await tab("Help"); await shot("help-tab", [["grp:Learn", 1], ["grp:Updates", 2]], TOP);
  await p.click(".ribbon .rb:has-text('Guide')"); await wait(400);
  await shot("guide-dialog", [[".guidecards", 1]], ".dlg");
  await p.keyboard.press("Escape"); await wait(200);
  // 8. File › Export (of the open graph).
  await nav(9);
  await p.click(".tabs .file"); await wait(300);
  await p.click(".bs aside button:has-text('Export')"); await wait(500);
  await shot("export", [[".bs aside", 1, 0, "in"], [".bs .tile", 2, 0]]);
  await p.click(".bs aside button:has-text('Updates')"); await wait(400);
  await shot("updates", [], { x: 0, y: 0, width: 1440, height: 420 });
  await b.close();
  srv.close();
})();
