// The whole app laid out: galleries for new tables, analyses and graph types, a card for every
// feature that is not built yet, the Roadmap page, and File › Import.
import { For, Show, createSignal, createMemo } from "solid-js";
import { FEATURES, AREAS, RELEASES, feature, ready, VERSION_NOW } from "./features";
import { openDialog, closeDialog, call, act, out, setOut, open, toast, setBackstage, curTable } from "./store";
import { analysisDialog, BY_ID } from "./results";
import { Dialog, Pick, Check, Icon } from "./ui";
import { C } from "./cmds";
import { num } from "./api";

const rel = (r: string) => `${r.length === 3 ? `${r}.0` : r}`;
export const Chip = (p: { id: string }) => { const f = feature(p.id)!; return ready(p.id) ? <span class="chip ok">Ready</span> : <span class="chip soon" title={RELEASES[f[2]]}>In {rel(f[2])}</span>; };

/** What a feature that is not built yet will do, and when it comes. */
export const soon = (id: string) => openDialog(() => {
  const f = feature(id);
  if (!f) return <Dialog title="Coming later"><p>This feature is planned.</p></Dialog>;
  return (
    <Dialog title={f[1]} extra={<button class="btn" onClick={() => { closeDialog(); setBackstage("roadmap"); }}>Whole roadmap</button>}>
      <div class="soonbox"><span class="fid">{f[0]}</span><Chip id={f[0]} /></div>
      <p>{f[3]}</p>
      <p class="muted">{ready(id) ? "Available now." : `Arrives in Datum Plot ${rel(f[2])}: ${RELEASES[f[2]]}.`}{f[4] ? ` Built on ${f[4]}.` : ""}</p>
    </Dialog>
  );
});

/** Help › Roadmap: every feature, what it does and when it comes. */
export const RoadmapPage = () => {
  const [q, setQ] = createSignal(""), [r, setR] = createSignal("all");
  const list = createMemo(() => FEATURES.filter(f => (r() === "all" || (r() === "ready" ? ready(f[0]) : f[2] === r())) && (f[0] + f[1] + f[3] + f[4]).toLowerCase().includes(q().toLowerCase())));
  const done = FEATURES.filter(f => ready(f[0])).length;
  return (
    <div class="roadmap"><h1>Roadmap</h1>
      <p class="muted">Everything Datum Plot will do, in the order it is being built. {done} of {FEATURES.length} features are ready in {VERSION_NOW}. Planned commands already have their place in the ribbon; clicking one tells you when it arrives.</p>
      <div class="rmbar"><input class="find" placeholder="Search features (e.g. regression, peaks, import)" value={q()} onInput={e => setQ(e.currentTarget.value)} />
        <Pick value={r()} set={setR} options={[["all", "All releases"], ["ready", "Ready now"], ...Object.entries(RELEASES).filter(([k]) => k !== "0.1").map(([k, v]) => [k, `${rel(k)} · ${v}`] as [string, string])]} /></div>
      <div class="rmrel"><For each={Object.entries(RELEASES)}>{([k, v]) => <div classList={{ now: k === VERSION_NOW || k === "0.1" }}><b>{rel(k)}</b><span>{v}</span><small>{FEATURES.filter(f => f[2] === k).length} features</small></div>}</For></div>
      <For each={Object.entries(AREAS)}>{([a, name]) => { const fs = () => list().filter(f => f[0].replace(/\d+/, "") === a); return <Show when={fs().length}>
        <h2>{a} · {name}</h2>
        <table class="tbl rmtbl"><tbody><For each={fs()}>{f => <tr><td class="fid">{f[0]}</td><td><b>{f[1]}</b><div class="muted">{f[3]}</div></td><td class="lib">{f[4]}</td><td><Chip id={f[0]} /></td></tr>}</For></tbody></table>
      </Show>; }}</For>
    </div>
  );
};

/** A gallery: categories on the left, choices in the middle, details on the right. */
type Choice = { id: string; name: string; icon: string; desc: string; group: string; key?: string };
const Gallery = (p: { title: string; help?: string; items: Choice[]; ok: string; run: (c: Choice) => void | Promise<unknown>; first?: string }) => {
  const groups = [...new Set(p.items.map(i => i.group))];
  const [g, setG] = createSignal(p.items.find(i => i.id === p.first)?.group ?? groups[0]), [sel, setSel] = createSignal(p.items.find(i => i.id === p.first) ?? p.items[0]);
  const ok = () => { const f = feature(sel().id); if (f && !ready(f[0])) { soon(f[0]); return false; } p.run(sel()); };
  return (
    <Dialog title={p.title} help={p.help} wide okText={ready(sel().id) ? p.ok : `In ${rel(feature(sel().id)?.[2] ?? "")}`} ok={ok}>
      <div class="gal">
        <nav><For each={groups}>{x => <button classList={{ on: g() === x }} onClick={() => { setG(x); setSel(p.items.find(i => i.group === x)!); }}>{x}</button>}</For></nav>
        <div class="galitems"><For each={p.items.filter(i => i.group === g())}>{c => <button class="galitem" classList={{ on: sel() === c, soon: !ready(c.id) }} onClick={() => setSel(c)} onDblClick={ok}>
          <Icon n={c.icon} size={26} /><b>{c.name}</b><Chip id={c.id} /></button>}</For></div>
        <aside><h3>{sel().name}</h3><p>{sel().desc}</p><p class="muted">{feature(sel().id)?.[3]}</p><Show when={feature(sel().id)?.[4]}><p class="muted small">Python: {feature(sel().id)![4]}</p></Show></aside>
      </div>
    </Dialog>
  );
};

const TABLES: Choice[] = [
  { id: "A1", name: "XY", icon: "xy", group: "Data tables", desc: "X values (time, dose, strain, temperature…) and one or more Y data sets with replicates. Graphs as points and lines; regression and curve fitting." },
  { id: "A2", name: "Column", icon: "sheet", group: "Data tables", desc: "Each column is a group (Control, Treated…). Compare groups with t-tests and ANOVA; dot plots, bars, box plots." },
  { id: "A3", name: "Grouped", icon: "table", group: "Data tables", desc: "Two factors: rows and data sets. Two-way ANOVA and grouped bars." },
  { id: "A4", name: "Contingency", icon: "grid", group: "Data tables", desc: "Counts of outcomes per group. Chi-square and Fisher's exact test." },
  { id: "A5", name: "Survival", icon: "line", group: "Data tables", desc: "One row per subject: the time in X, and 1 (event, failure) or 0 (censored: still going at the end) in its group's column. Kaplan-Meier curves and the log-rank test." },
  { id: "A6", name: "Parts of whole", icon: "dash", group: "Data tables", desc: "Fractions of a total, such as phase or composition fractions." },
  { id: "A7", name: "Many variables", icon: "cols", group: "Data tables", desc: "One row per sample with many measured properties. Multiple regression and a correlation matrix; graphs put the first variable on X." },
  { id: "A8", name: "Nested", icon: "group", group: "Data tables", desc: "Each group's sub-columns are its subgroups (batches, animals), with replicates down the rows. Nested t-test and one-way ANOVA." },
  { id: "A9", name: "Worksheet", icon: "sheet", group: "Worksheets and 3D", desc: "Free columns, each with a role (X, Y, Y error or not plotted), a long name, units and a comment, and optional column formulas. For raw instrument data." },
  { id: "A10", name: "Matrix", icon: "grid", group: "Worksheets and 3D", desc: "Z values on an X–Y grid: X down the first column, Y values as the column titles. Contour maps, heat maps and 3D surfaces; surface fits." },
];
/** File › New table: every table type; XY is ready. */
export const newTable = () => openDialog(() => <Gallery title="New Data Table" help="newtable" items={TABLES} ok="Create" run={c => C.newTable(c.id === "A2" ? "column" : c.id === "A3" ? "grouped" : c.id === "A4" ? "contingency" : c.id === "A6" ? "parts" : c.id === "A7" ? "multi" : c.id === "A5" ? "survival" : c.id === "A8" ? "nested" : c.id === "A9" ? "sheet" : c.id === "A10" ? "matrix" : undefined)} />);

const ANALYSES: Choice[] = [
  { id: "B1", name: "Descriptive statistics", icon: "sigma", group: "Statistics", desc: "Summarise each data set." },
  { id: "B2", name: "Normality tests", icon: "check", group: "Statistics", desc: "Is the data consistent with a normal distribution?" },
  { id: "B3", name: "Outliers", icon: "exclude", group: "Statistics", desc: "Find values that do not belong." },
  { id: "A6", name: "Fractions of total", icon: "dash", group: "Statistics", desc: "Each part as a percentage of its whole, with 95% confidence intervals for counts." },
  { id: "D4", name: "Frequency distribution", icon: "table", group: "Statistics", desc: "Histogram and cumulative distribution of the values." },
  { id: "A18", name: "Data checks", icon: "check", group: "Statistics", desc: "Look for missing X values, missing N, typing mistakes and values a log axis cannot show." },
  { id: "A15", name: "Transform", icon: "fx", group: "Statistics", desc: "A new table of transformed values: log, 1/X, °C → K, baseline subtracted, normalised." },
  { id: "B9", name: "Linear regression", icon: "line", group: "Regression and fitting", desc: "Fit a straight line (or a polynomial) and get slope, intercept, R² with confidence intervals; compare lines." },
  { id: "B10", name: "Nonlinear curve fit", icon: "curve", group: "Regression and fitting", desc: "Fit an equation from the model library or your own." },
  { id: "B12", name: "Global fit and model comparison", icon: "curve", group: "Regression and fitting", desc: "Share parameters between data sets; choose between two models." },
  { id: "B13", name: "Interpolate a standard curve", icon: "xy", group: "Regression and fitting", desc: "Read unknown samples off a calibration curve." },
  { id: "B28", name: "Arrhenius / activation energy", icon: "log", group: "Regression and fitting", desc: "Rates at several temperatures give the activation energy and the pre-factor." },
  { id: "B14", name: "Area under the curve", icon: "graph", group: "Regression and fitting", desc: "Total area, positive and negative areas and peaks above a baseline (DSC enthalpy, AUC)." },
  { id: "B14", key: "B14s", name: "Smooth, derivative, integral", icon: "curve", group: "Regression and fitting", desc: "Savitzky-Golay, LOWESS or moving-average smoothing; first and second derivatives; cumulative integral." },
  { id: "B27", name: "Tensile test", icon: "line", group: "Materials", desc: "Young's modulus, 0.2 % offset yield, UTS, elongation at break and toughness of each specimen, with mean ± SD." },
  { id: "B29", name: "Weibull analysis", icon: "sigma", group: "Materials", desc: "Weibull modulus and characteristic strength (maximum likelihood or regression) with the Weibull plot." },
  { id: "B4", name: "t-tests", icon: "err", group: "Compare groups", desc: "Compare two groups' means: unpaired, paired, ratio or one-sample." },
  { id: "B5", name: "Nonparametric tests", icon: "err", group: "Compare groups", desc: "Compare groups without assuming a normal distribution." },
  { id: "B6", name: "One-way ANOVA", icon: "table", group: "Compare groups", desc: "Compare three or more groups." },
  { id: "B7", name: "Multiple comparisons", icon: "list", group: "Compare groups", desc: "Which groups differ after ANOVA: Tukey, Dunnett, Holm-Šidák…" },
  { id: "B8", name: "Effect sizes", icon: "sigma", group: "Compare groups", desc: "Cohen's d and Hedges' g with the t-test; η² and ω² with ANOVA." },
  { id: "B15", name: "Two-way ANOVA", icon: "table", group: "Compare groups", desc: "Two factors at once, such as alloy and temperature." },
  { id: "B16", name: "Correlation", icon: "xy", group: "Relationships", desc: "How strongly two variables move together." },
  { id: "B17", name: "Contingency", icon: "grid", group: "Relationships", desc: "Tests on counts." },
  { id: "B18", name: "Bland-Altman", icon: "err", group: "Relationships", desc: "Agreement of two measuring methods: bias and limits of agreement, with the Bland-Altman plot." },
  { id: "B18", key: "B18r", name: "ROC curve", icon: "curve", group: "Relationships", desc: "How well a test separates two groups: the ROC curve, AUC and the best cut-off." },
  { id: "B21", name: "Multiple and logistic regression", icon: "cols", group: "Relationships", desc: "Several predictors at once: linear for measurements, logistic for 0/1 outcomes, Poisson for counts." },
  { id: "B22", name: "PCA and clustering", icon: "group", group: "Relationships", desc: "Patterns in many variables: principal components with a biplot; groups of similar rows by hierarchical or k-means clustering." },
  { id: "B19", name: "Survival and reliability", icon: "line", group: "Survival", desc: "Kaplan-Meier survival, median survival with its 95% CI, the log-rank test and hazard ratios (Cox)." },
  { id: "B24", name: "Peak analysis", icon: "curve", group: "Signals and spectra", desc: "Baselines, peaks, widths, areas and multi-peak fits (XRD, Raman, chromatograms)." },
  { id: "B25", name: "Signal processing", icon: "graph", group: "Signals and spectra", desc: "Fourier spectrum, low-, high- and band-pass filters, resampling." },
  { id: "B26", name: "Surface fitting", icon: "grid", group: "Signals and spectra", desc: "Fit Z = f(X, Y): a plane, quadratic or cubic surface, or a 2D Gaussian peak." },
  { id: "B23", name: "Power and sample size", icon: "sigma", group: "Planning", desc: "How many specimens you need." },
];
/** Analyze: every analysis; the ready ones open their options. */
export const analyze = (first?: string) => openDialog(() => <Gallery title="Analyze Data" help="analyze" items={ANALYSES} ok="Next…" first={first} run={c => { setTimeout(() => runAnalysis(c.key ?? c.id)); }} />);
/** Opens the options of the analysis behind a catalogue id, for the open table. */
export const runAnalysis = (id: string) => { const [kind, preset] = BY_ID[id] ?? []; if (kind) analysisDialog(kind, curTable(), undefined, preset); else soon(id); };

const GRAPHS: Choice[] = [
  { id: "D1", name: "XY: points and lines", icon: "xy", group: "XY", desc: "Means with error bars or every replicate, joined or not." },
  { id: "D5", name: "Fitted curve", icon: "curve", group: "XY", desc: "Data with a fitted line or curve and its bands." },
  { id: "D4", name: "Histogram and QQ", icon: "table", group: "Distributions", desc: "How the values are spread." },
  { id: "D2", name: "Column graphs", icon: "err", group: "Groups", desc: "Dot plots, bars, box plots, violins." },
  { id: "D6", name: "Grouped bars and heat map", icon: "grid", group: "Groups", desc: "Two factors in one graph." },
  { id: "D7", name: "Pie and donut", icon: "dash", group: "Groups", desc: "Parts of a whole." },
  { id: "D9", name: "Survival curve", icon: "line", group: "Special", desc: "Kaplan-Meier staircase." },
  { id: "D10", name: "Volcano, forest, ROC", icon: "xy", group: "Special", desc: "Special-purpose graphs." },
  { id: "D11", name: "3D, contour and polar", icon: "grid", group: "Worksheets and 3D", desc: "Contour and heat maps and 3D surfaces of a matrix; polar graphs of XY data." },
  { id: "D12", name: "Multi-panel and insets", icon: "layout", group: "Worksheets and 3D", desc: "Several plots in one figure." },
];
/** Graph › Graph Type: every kind of graph; XY is ready. */
export const graphTypes = () => openDialog(() => <Gallery title="Graph Type" help="graphtype" items={GRAPHS} ok="Use" first={curTable()?.kind === "matrix" ? "D11" : curTable()?.kind === "survival" ? "D9" : curTable()?.kind === "parts" ? "D7" : curTable()?.kind === "column" ? "D2" : curTable()?.kind === "grouped" || curTable()?.kind === "contingency" ? "D6" : "D1"} run={c => {
  const t = curTable();
  if (c.id === "D4") { setTimeout(() => runAnalysis("D4")); return; }
  if (c.id === "D7") return t?.kind === "parts" ? toast("This is a parts-of-whole graph: Graph › Column Graph picks pie, donut or bars stacked to 100%.", true) : toast("Pie and donut charts show parts-of-whole tables: File › New Table › Parts of whole.");
  if (c.id === "D6") return t?.kind === "grouped" || t?.kind === "contingency" ? toast("This is a grouped graph: Graph › Column Graph picks grouped bars, stacked bars, dots, lines or a heat map.", true) : toast("Grouped graphs show grouped tables: File › New Table › Grouped.");
  if (c.id === "D11") return t?.kind === "matrix" ? toast("This is a matrix graph: Graph › Column Graph picks a contour map, heat map, 3D surface or wireframe.", true) : t?.kind === "xy" ? toast("Format Graph › Data Sets › Polar draws this XY graph on polar axes; matrices (File › New Table › Matrix) give contours and 3D surfaces.", true) : toast("Contours and 3D surfaces show matrix tables: File › New Table › Matrix.");
  if (c.id === "D9") return t?.kind === "survival" ? toast("This is a survival graph: Format Graph › Confidence band shades the 95% CI.", true) : toast("Survival curves show survival tables: File › New Table › Survival.");
  if (c.id === "D2") return t?.kind === "column" ? toast("This is a column graph: Graph › Column Graph picks dots, bars, box plots or violins.", true) : toast("Column graphs show column tables: File › New Table › Column.");
  toast(t?.kind === "survival" ? "This survival table draws Kaplan-Meier curves." : t?.kind === "column" ? "XY graphs show XY tables: File › New Table › XY." : "This graph is already an XY graph.", true);
}} />);

/** File › Import: a CSV, TXT or Excel file into a new XY table. */
/** Adds ready tables (a .pzfx project, plates, several runs) and opens the first. */
const addTables = async (tables: any[], what: string) => {
  const o = await call<any>("import_tables", { tables });
  if (!o) return false;
  setOut(o);
  const ts = o.project.tables;
  open("data", ts[ts.length - tables.length].id);
  toast(`Imported: ${what}.`, true);
  return true;
};
/** File › Import Several Files: one run per file, in one table when they share X (A14). */
export const importFiles = async () => {
  const o = await call<any>("import_files");
  if (o) { setOut(o); const ts = o.project.tables; open("data", ts[ts.length - 1].id); toast("Imported the files.", true); }
};
export const importFile = async () => {
  const r = await call<{ name: string; sheets: { name: string; rows: string[][] }[]; tables?: any[]; plates?: any[] } | null>("import_file");
  if (!r) return;
  if (r.tables?.length) return addTables(r.tables, `${r.tables.length} table${r.tables.length > 1 ? "s" : ""} from ${r.name}`);
  if (!r.sheets.some(s => s.rows.length)) return toast("That file has no data.");
  openDialog(() => {
    const [k, setK] = createSignal(Math.max(0, r.sheets.findIndex(s => s.rows.length))), rows = () => r.sheets[k()].rows;
    const words = (l: string[] = []) => l.some(c => c.trim()) && l.every(c => !c.trim() || isNaN(+c));
    /** Headings like "Sample 1, , , Sample 2, , " mean 3 replicates per data set. */
    const guess = () => { const h = rows()[0] ?? [], at = h.map((c, j) => (j > 0 && c.trim() ? j : -1)).filter(j => j > 0), gaps = at.slice(1).map((j, i) => j - at[i]); return gaps.length && gaps.every(g => g === gaps[0]) ? gaps[0] : 1; };
    const [head, setHead] = createSignal(words(rows()[0])), [x, setX] = createSignal(0), [reps, setReps] = createSignal(words(rows()[0]) ? guess() : 1), [entry, setEntry] = createSignal("rep");
    const [name, setName] = createSignal(r.sheets.length > 1 ? `${r.name} ${r.sheets[k()].name}` : r.name);
    const ncols = () => Math.max(...rows().map(l => l.length), 0);
    const order = () => [x(), ...Array.from({ length: ncols() }, (_, j) => j).filter(j => j !== x())];
    const arranged = () => rows().map(l => order().map(j => l[j] ?? ""));
    const [plate, setPlate] = createSignal(!!r.plates?.length);
    const go = async () => {
      if (plate() && r.plates?.length) return addTables(r.plates, `${r.plates.length > 1 ? `${r.plates.length} plates` : "The plate"} as a grouped table (rows ${r.plates[0].rowTitles[0]}–${r.plates[0].rowTitles[r.plates[0].rows - 1]})`);
      const ok = await act({ Import: { name: name() || "Imported", entry: entry(), reps: entry() === "rep" ? reps() : 3, header: head(), rows: arranged(), graph: null } });
      if (ok) { const p = out()!.project; open("data", p.tables[p.tables.length - 1].id); toast(`Imported ${rows().length - (head() ? 1 : 0)} rows.`, true); }
      return ok;
    };
    return (
      <Dialog title={`Import · ${r.name}`} help="import" wide okText="Import" ok={go}>
        <div class="form">
          <Show when={r.plates?.length}><label>Plate reader</label><Check label={`Import the ${r.plates![0].sets.length * r.plates![0].rows}-well plate as a grouped table (rows ${r.plates![0].rowTitles[0]}–${r.plates![0].rowTitles[r.plates![0].rows - 1]}, columns 1–${r.plates![0].sets.length}); untick to import the sheet as it is`} value={plate()} set={setPlate} /></Show>
          <Show when={r.sheets.length > 1}><label>Sheet</label><Pick value={String(k())} set={v => { setK(+v); setHead(words(rows()[0])); setX(0); setReps(words(rows()[0]) ? guess() : 1); }} options={r.sheets.map((s, i) => [String(i), `${s.name} (${s.rows.length} rows)`] as [string, string])} /></Show>
          <label>Table name</label><input value={name()} onInput={e => setName(e.currentTarget.value)} />
          <label>Headings</label><Check label="The first row holds the column titles" value={head()} set={setHead} />
          <label>X column</label><Pick value={String(x())} set={v => setX(+v)} options={Array.from({ length: ncols() }, (_, j) => [String(j), `${j + 1}: ${head() ? rows()[0][j] || "(no title)" : rows()[0][j] ?? ""}`] as [string, string])} />
          <label>The other columns are</label><span class="inline"><Pick value={entry()} set={setEntry} options={[["rep", "Replicate values"], ["msn", "Mean, SD, N (3 columns per data set)"], ["mesn", "Mean, SEM, N"]]} />
            <Show when={entry() === "rep"}><input type="number" min="1" max="50" style={{ width: "60px" }} value={reps()} onChange={e => setReps(Math.max(1, Math.min(50, +e.currentTarget.value)))} /><span class="muted">per data set</span></Show></span>
        </div>
        <div class="impprev"><table class="tbl"><tbody><For each={arranged().slice(0, 14)}>{(l, i) => <tr classList={{ hd: head() && i() === 0 }}><For each={l.slice(0, 12)}>{(c, j) => <td classList={{ xcol: j() === 0, r: !isNaN(+c) && c !== "" }}>{!isNaN(+c) && c !== "" ? num(+c) : c}</td>}</For></tr>}</For></tbody></table></div>
        <p class="muted">{rows().length} rows × {ncols()} columns. The first column of the preview becomes X; text that is not a number is left empty.</p>
      </Dialog>
    );
  });
};
