// UI tests: the built window (ui/dist) in Chromium, with the engine's real output for a sample
// project (cargo run -p datum-core --example dump > tests_ui/fixture.json) and a real graph from the
// Python engine, behind a mocked Tauri bridge. Run: npm run test:ui
const { chromium } = require("playwright");
const { execFileSync } = require("child_process");
const fs = require("fs"), http = require("http"), path = require("path");
const root = path.join(__dirname, "../ui/dist"), fix = JSON.parse(fs.readFileSync(path.join(__dirname, "fixture.json")));
const P = fix.state.project;
// The graph as the Python engine draws it (numpy, scipy, matplotlib must be installed).
const py = `import json,sys; sys.path.insert(0, sys.argv[1]); from datum import graph; p = json.load(open(sys.argv[2]))["state"]["project"]; print(json.dumps(graph.render(p["tables"][0], p["graphs"][0]["settings"])))`;
const render = JSON.parse(execFileSync(process.env.PYTHON || "python3", ["-c", py, path.join(__dirname, "../py"), path.join(__dirname, "fixture.json")], { maxBuffer: 1 << 26 }).toString());
// A real linear regression of the sample's first data set, for the results sheet.
const pyr = `import json,sys; sys.path.insert(0, sys.argv[1]); from datum import analysis; p = json.load(open(sys.argv[2]))["state"]["project"]; print(json.dumps({"result": analysis.run("linear", p["tables"][0], [], {"xmax": 10}), "models": analysis.model_list()}))`;
const lin = JSON.parse(execFileSync(process.env.PYTHON || "python3", ["-c", pyr, path.join(__dirname, "../py"), path.join(__dirname, "fixture.json")], { maxBuffer: 1 << 26 }).toString());
const types = { ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".woff2": "font/woff2", ".woff": "font/woff", ".html": "text/html" };
const srv = http.createServer((q, r) => {
  const f = path.join(root, q.url === "/" ? "index.html" : decodeURIComponent(q.url.split("?")[0]));
  fs.readFile(f, (e, b) => { if (e) { r.writeHead(404); return r.end(); } r.writeHead(200, { "content-type": types[path.extname(f)] ?? "application/octet-stream" }); r.end(b); });
});
let failed = 0;
const check = (name, ok, info = "") => { console.log(`${ok ? "ok  " : "FAIL"} ${name}${ok ? "" : "  " + info}`); if (!ok) failed++; };

(async () => {
  await new Promise(ok => srv.listen(0, ok));
  const url = `http://localhost:${srv.address().port}/`;
  const b = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  p.on("pageerror", e => errors.push(e.message));
  await p.addInitScript(([f, rd, ln]) => {
    f.state.project.analyses = [{ id: 99, table: f.state.project.tables[0].id, name: "Growth fit", kind: "linear", sets: [], options: { xmax: 10 } }];
    const opts = { theme: "light", autosave: 0, beta: false, openLast: false, decimals: -1, reps: 3, entry: "rep", error: "sd", width: 80, height: 60, font: "Arial", fontSize: 10, style: "prism", dpi: 300, paper: "A4", landscape: false, company: "", logo: "" };
    const m = { state: f.state, options: opts, startup_file: null, recovery: null, check_update: null, templates: f.templates, recent: [], version: "test", render: rd, result: ln.result, models: { models: ln.models }, engine: { versions: { python: "3", numpy: "2" }, error: null }, new_project: f.state,
      import_file: { name: "tensile", sheets: [{ name: "tensile", rows: [["Strain", "Sample 1", "", "Sample 2", ""], ["0", "0", "0.2", "0", "0.1"], ["0.002", "140", "138", "150", "148"]] }] } };
    window.__calls = [];
    window.__TAURI__ = { core: { invoke: async (c, a) => { window.__calls.push([c, a]); if (c in m) return m[c]; if (c === "apply" || c === "history") return f.state; return null; } }, event: { listen: async () => () => {} } };
  }, [fix, render, lin]);
  const calls = (c) => p.evaluate(c => window.__calls.filter(x => x[0] === c).map(x => x[1]), c);
  const ops = async () => (await calls("apply")).map(a => a.op);
  const reset = () => p.evaluate(() => { window.__calls = []; });
  await p.goto(url);
  await p.waitForTimeout(700);

  // 1. Home: the samples from the engine, and the updates card.
  check("Home shows the blank table, five samples, open, import and roadmap", (await p.$$(".home .tile")).length === 9, String((await p.$$(".home .tile")).length));
  check("updates card names the app", (await p.textContent(".card .brand")).includes("Datum Plot"));
  await p.click(".home .tile:nth-child(2)");
  await p.waitForTimeout(600);
  check("a sample opens on its graph", !!(await p.$(".gpaper img.gimg")) && !(await p.$(".bs")));
  check("the graph image is the engine's SVG at its size", await p.evaluate(() => { const i = document.querySelector(".gimg"); return i.src.startsWith("data:image/svg+xml") && i.width > 200; }));

  // 2. Double-click on the X axis opens Format Graph on the X Axis page; changes apply at once.
  const plot = await p.evaluate(() => { const r = document.querySelector(".gpaper").getBoundingClientRect(); return [r.left, r.top]; });
  const k = 1.5 * 96 / 72, [x0, , x1, y1] = render.plot;
  await p.mouse.dblclick(plot[0] + (x0 + x1) / 2 * k, plot[1] + (y1 + 12) * k);
  await p.waitForTimeout(300);
  check("double-click on the X axis opens Format Graph › X Axis", (await p.textContent(".dlg .dtabs button.on").catch(() => "")).includes("X Axis"));
  await reset();
  await p.selectOption(".dlg .fmtpage select", "log");
  await p.waitForTimeout(200);
  const gs = (await ops()).find(o => o.GraphSet);
  check("choosing a log scale sends the graph's settings", gs && gs.GraphSet.settings.x.scale === "log" && gs.GraphSet.graph === P.graphs[0].id, JSON.stringify(gs));
  check("Format Graph is docked so the graph stays visible", await p.evaluate(() => { const d = document.querySelector(".dlg").getBoundingClientRect(), g = document.querySelector(".gpaper").getBoundingClientRect(); return g.right <= d.left + 1; }));
  await p.keyboard.press("Escape");

  // 3. Hovering a point shows its values.
  const pt = render.points.find(Boolean);
  const toPx = (x, y) => { const [a, b] = render.xlim, [c, d] = render.ylim, [px0, py0, px1, py1] = render.plot; return [plot[0] + (px0 + (x - a) / (b - a) * (px1 - px0)) * k, plot[1] + (py1 - (y - c) / (d - c) * (py1 - py0)) * k]; };
  const [hx, hy] = toPx(pt[1], pt[2]);
  await p.mouse.move(hx, hy);
  await p.waitForTimeout(150);
  check("hovering a point shows its data set, mean and n", ((await p.textContent(".gtip").catch(() => "")) || "").includes("mean"), await p.textContent(".gtip").catch(() => "none"));

  // 4. The data table: headings over their columns, typing, ranges, exclude, paste.
  await p.click(".nav .nitem:nth-of-type(2)");
  await p.waitForTimeout(300);
  check("the navigator opens the data table", !!(await p.$(".dgrid")));
  const align = await p.evaluate(() => {
    const subs = [...document.querySelectorAll(".dhead .hc.sub")], row = document.querySelector(".gbody .row").children;
    const x = document.querySelector(".dhead .xh").getBoundingClientRect().left - row[2].getBoundingClientRect().left;
    return [x, ...subs.map((h, i) => h.getBoundingClientRect().left - row[3 + i].getBoundingClientRect().left)].map(Math.abs);
  });
  check("headings line up with their columns", align.length > 4 && Math.max(...align) < 1, JSON.stringify(align));
  const cell = (r, c) => p.evaluate(([r, c]) => { const e = document.querySelectorAll(".gbody .row")[r].children[c + 1].getBoundingClientRect(); return [e.left + e.width / 2, e.top + e.height / 2]; }, [r, c]);
  await reset();
  let [cx, cy] = await cell(1, 2);
  await p.mouse.click(cx, cy);
  await p.keyboard.type("4.25");
  await p.keyboard.press("Enter");
  await p.waitForTimeout(150);
  const typed = (await ops()).find(o => o.Cells);
  check("typing sets the cell (row 1, data column 1 = A:Y1)", typed && JSON.stringify(typed.Cells.cells) === JSON.stringify([[1, 1, "4.25"]]), JSON.stringify(typed));
  const [ax, ay] = await cell(2, 2), [bx, by] = await cell(4, 4);
  await p.mouse.move(ax, ay); await p.mouse.down(); await p.mouse.move(bx, by, { steps: 5 }); await p.mouse.up();
  check("dragging selects a 3×3 block", (await p.$$(".gbody .c.in")).length === 9, String((await p.$$(".gbody .c.in")).length));
  check("Sum, Average and Count of the selection", (await p.textContent(".fbar")).includes("Count 9"));
  await reset();
  await p.keyboard.press("Control+e");
  await p.waitForTimeout(150);
  const ex = (await ops()).find(o => o.Exclude);
  check("Ctrl+E excludes the selected values", ex && ex.Exclude.on === true && ex.Exclude.cells.length === 9, JSON.stringify(ex));
  await reset();
  [cx, cy] = await cell(0, 1);
  await p.mouse.click(cx, cy);
  await p.evaluate(() => { const d = new DataTransfer(); d.setData("text/plain", "Time\tA\tB\n1\t2\t3\n"); document.querySelector(".dgrid").dispatchEvent(new ClipboardEvent("paste", { clipboardData: d, bubbles: true })); });
  await p.waitForTimeout(150);
  const pa = (await ops()).find(o => o.Paste);
  check("paste from Excel sends the rows with their headings", pa && pa.Paste.row === 0 && pa.Paste.col === 0 && pa.Paste.rows.length === 2 && pa.Paste.rows[0][0] === "Time", JSON.stringify(pa));
  check("excluded values are shown struck through in blue", (await p.$$(".gbody .c.ex")).length === P.tables[0].excluded.length);

  // 5. Ribbon: every tab fits without a sideways scrollbar; Analyze explains what comes next.
  for (const w of [1280, 1600]) {
    await p.setViewportSize({ width: w, height: 900 });
    for (const t of ["Data", "Analyze", "Graph", "Layout", "Tools", "View", "Help"]) {
      await p.click(`.tabs button:text-is("${t}")`);
      await p.waitForTimeout(80);
      const over = await p.evaluate(() => { const r = document.querySelector(".ribbon"); return r.scrollWidth - r.clientWidth; });
      if (over > 1) check(`ribbon ${t} fits at ${w}px`, false, `${over}px too wide`);
    }
  }
  check("ribbon tabs fit at 1280 and 1600 px", true);
  await p.setViewportSize({ width: 1440, height: 900 });
  await p.click('.tabs button:text-is("Analyze")');
  await p.click('.ribbon .rb:has-text("t-tests")');
  await p.waitForTimeout(150);
  check("a planned command opens its card with its ID and release", ((await p.textContent(".dlg")) || "").includes("B4") && (await p.textContent(".dlg")).includes("0.3"));
  await p.keyboard.press("Escape");
  check("planned commands are marked in the ribbon", (await p.$$(".ribbon .rb.soonb")).length >= 10);
  await p.click('.ribbon .rb:has-text("Analyze…")');
  await p.waitForTimeout(150);
  check("Analyze lists every family of analyses", (await p.$$(".gal nav button")).length >= 6 && (await p.$$(".galitem")).length >= 3);
  await p.click('.gal nav button:has-text("Regression")');
  check("the gallery shows regression analyses with their release", ((await p.textContent(".galitems")) || "").includes("Linear regression"));
  await p.keyboard.press("Escape");
  await p.waitForTimeout(100);

  // 5a. Analyses: the gallery leads to the options; OK adds a linked analysis drawn on the graph.
  await p.click('.tabs button:text-is("Analyze")');
  await reset();
  await p.click('.ribbon .rb.big:has-text("Linear Regression")');
  await p.waitForTimeout(200);
  check("Linear Regression opens its options", ((await p.textContent(".dlg header")) || "").includes("Linear regression"));
  await p.fill('.dlg input[placeholder="end"]', "10");
  await p.press('.dlg input[placeholder="end"]', "Tab");
  await p.click(".dlg .btn.pri");
  await p.waitForTimeout(200);
  const add = (await ops()).find(o => o.AddAnalysis);
  check("OK adds the analysis with its fit range, drawn on the graph", add && add.AddAnalysis.analysis.kind === "linear" && add.AddAnalysis.analysis.options.xmax === 10 && add.AddAnalysis.overlay === true, JSON.stringify(add));
  await p.click('.ribbon .rb.big:has-text("Curve Fit")');
  await p.waitForTimeout(200);
  check("Curve Fit lists the model library", (await p.$$eval(".dlg select option", os => os.map(o => o.textContent))).some(t => t.includes("Exponential decay")));
  await p.keyboard.press("Escape");

  // 5b. Import: the file comes back from Python; headings with gaps mean replicates; one Import op.
  await p.click('.tabs button:text-is("Data")');
  await reset();
  await p.click('.ribbon .rb.big:has-text("Import")');
  await p.waitForTimeout(250);
  check("Import guesses 2 replicates from the headings", (await p.inputValue('.dlg input[type=number]').catch(() => "")) === "2");
  await p.click('.dlg .btn.pri');
  await p.waitForTimeout(150);
  const im = (await ops()).find(o => o.Import);
  check("Import sends the rows, headings and replicates", im && im.Import.reps === 2 && im.Import.header === true && im.Import.rows.length === 3 && im.Import.rows[0][0] === "Strain", JSON.stringify(im));
  await p.keyboard.press("Escape");

  // 5c. Copy Picture goes through Rust (WebView2 blocks the browser clipboard).
  await p.click(".side button:nth-of-type(4)");
  await p.waitForTimeout(300);
  await reset();
  await p.click('.tabs button:text-is("Graph")');
  await p.click('.ribbon .rb:has-text("Copy Picture")');
  await p.waitForTimeout(150);
  check("Copy Picture asks the shell to copy the graph", (await calls("copy_graph")).length === 1);

  // 6. Info sheet edits go to the engine; File › Print previews the graph page; Options line up.
  await p.click(".side button:nth-of-type(1)");
  await p.waitForTimeout(150);
  await reset();
  await p.fill(".infopage .opt:nth-of-type(3) input", "Dr Lee");
  await p.press(".infopage .opt:nth-of-type(3) input", "Tab");
  await p.waitForTimeout(150);
  const info = (await ops()).find(o => o.Info);
  check("Info sheet fields are saved in the project", info && info.Info.info.researcher === "Dr Lee", JSON.stringify(info));
  await p.click(".side button:nth-of-type(4)");
  await p.waitForTimeout(300);
  await p.keyboard.press("Control+p");
  await p.waitForTimeout(500);
  check("Print shows a page with the graph, header and footer", !!(await p.$(".pprev .ppage .pgraph img")) && !!(await p.$(".pprev .ppage .phead")));
  check("the printed caption says what the points show", ((await p.textContent(".pprev .pcap").catch(() => "")) || "").includes("mean ± SD"));
  await p.click('.bs aside button:has-text("Roadmap")');
  await p.waitForTimeout(200);
  check("the Roadmap lists every feature with its status", (await p.$$(".rmtbl tr")).length >= 90 && (await p.$$(".rmtbl .chip.ok")).length >= 8);
  await p.fill(".roadmap .find", "regression");
  await p.waitForTimeout(100);
  check("the Roadmap can be searched", (await p.$$(".rmtbl tr")).length >= 2 && (await p.$$(".rmtbl tr")).length < 10);
  await p.click('.bs aside button:has-text("Options")');
  await p.waitForTimeout(200);
  const optRows = await p.evaluate(() => [...document.querySelectorAll(".options .opt")].map(o => o.children.length));
  check("Options: every row has a name and a control", optRows.length > 10 && optRows.every(n => n === 2), JSON.stringify(optRows));
  await p.click(".bs aside .back");

  // 7. A results sheet: tables, the answer, checks and methods; outliers would offer to exclude.
  await p.click('.nav .nitem:has-text("Growth fit")');
  await p.waitForTimeout(300);
  check("the results sheet shows the summary tables", (await p.$$(".rview .rtable")).length >= 2);
  check("the Explain panel gives the answer and the checks", ((await p.textContent(".explain .ans")) || "").includes("slope") && (await p.$$(".explain .checks li")).length >= 1);
  check("residual plots are shown", (await p.$$(".rplots img")).length >= 1);
  await reset();
  await p.click('.explain .btn:has-text("Copy methods text")');
  await p.waitForTimeout(100);
  check("Copy methods text uses the Windows clipboard", ((await calls("copy_text"))[0]?.text || "").includes("least squares"));
  check("no script errors", errors.length === 0, errors.join(" | "));
  await b.close(); srv.close();
  console.log(failed ? `\n${failed} failed` : "\nall passed");
  process.exit(failed ? 1 : 0);
})();
