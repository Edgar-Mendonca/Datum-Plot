// Data tools (sort, find, exclude rows by a rule), the test chooser and statistics guide, graph
// styles, colour schemes and Copy Look, and exporting every graph or the whole project to Excel.
import { For, Show, createSignal, createMemo } from "solid-js";
import { Graph, GraphSettings, Table, letter, num, spans, invoke } from "./api";
import { act, call, curTable, graph, opts, setOpts, toast, openDialog, closeDialog, P, setGoto } from "./store";
import { setG } from "./format";
import { analysisDialog, BY_ID } from "./results";
import { Dialog, Pick, Check } from "./ui";

const needT = () => { const t = curTable(); if (!t) toast("Open a data table first."); return t; };
const needG = () => { const g = graph(); if (!g) toast("Open a graph first."); return g; };
/** The grid columns of a table, as [column, name]. */
const columns = (t: Table): [string, string][] => [...(t.kind === "column" ? [] : [["0", `X: ${t.xTitle || "X"}`] as [string, string]]),
  ...t.sets.flatMap((s, k) => Array.from({ length: spans(t)[k][1] }, (_, j) => [String(spans(t)[k][0] + j), `${letter(k)}: ${s.title || `Data set ${letter(k)}`}${spans(t)[k][1] > 1 ? ` · ${s.entry === "rep" ? `Y${j + 1}` : ["Mean", "SD/SEM", "N"][j]}` : ""}`] as [string, string]))];

// ---------- sort, find, exclude rows (A17) ----------
export const sortDialog = () => {
  const t = needT();
  if (!t) return;
  openDialog(() => {
    const [col, setCol] = createSignal(columns(t)[0][0]), [desc, setDesc] = createSignal(false);
    return (
      <Dialog title="Sort" okText="Sort" ok={() => act({ Sort: { table: t.id, col: +col(), desc: desc() } })}>
        <div class="form">
          <label>Sort the rows by</label><Pick value={col()} set={setCol} options={columns(t)} />
          <label>Order</label><Pick value={desc() ? "1" : ""} set={v => setDesc(!!v)} options={[["", "Smallest first"], ["1", "Largest first"]]} />
        </div>
        <p class="muted">Whole rows move together, with their row titles, excluded values and formatting. Empty cells go last. Undo (Ctrl+Z) puts them back.</p>
      </Dialog>
    );
  });
};

export const findDialog = () => {
  const t = needT();
  if (!t) return;
  openDialog(() => {
    const [q, setQ] = createSignal("");
    const hits = createMemo(() => {
      const s = q().trim().toLowerCase();
      if (!s) return [];
      const out: [number, number, string][] = [];
      t.cols.forEach((c, j) => c.forEach((v, r) => { const x = num(v); if (x && x.toLowerCase().includes(s) && out.length < 200) out.push([r, j, x]); }));
      t.rowTitles.forEach((x, r) => { if (x && x.toLowerCase().includes(s)) out.push([r, -1, x]); });
      return out;
    });
    const name = (j: number) => (j < 0 ? "Row title" : columns(t).find(c => c[0] === String(j))?.[1] ?? `Column ${j}`);
    return (
      <Dialog title="Find" cancel="Close">
        <input class="find" placeholder="A value or part of one, e.g. 0.35" value={q()} onInput={e => setQ(e.currentTarget.value)} ref={el => setTimeout(() => el.focus())} />
        <div class="findlist"><For each={hits()} fallback={<p class="muted">{q() ? "Not found." : "Type to search the table."}</p>}>{([r, j, x]) =>
          <button onClick={() => { setGoto([r, j]); closeDialog(); }}><b>Row {r + 1}</b><span>{name(j)}</span><span class="r">{x}</span></button>}</For></div>
      </Dialog>
    );
  });
};

export const excludeRows = () => {
  const t = needT();
  if (!t) return;
  openDialog(() => {
    const [col, setCol] = createSignal(columns(t)[0][0]), [rule, setRule] = createSignal("lt"), [a, setA] = createSignal(""), [b, setB] = createSignal("");
    const rows = () => {
      const c = t.cols[+col()] ?? [], x = +a(), y = +b();
      if (a() === "" || isNaN(x)) return [];
      return c.map((v, r) => [v, r] as [number | null, number]).filter(([v]) => v !== null && (rule() === "lt" ? v! < x : rule() === "gt" ? v! > x : rule() === "eq" ? v === x : rule() === "out" ? v! < x || v! > y : v! >= x && v! <= y)).map(([, r]) => r);
    };
    const ok = () => {
      const rs = rows();
      if (!rs.length) { toast("No rows match."); return false; }
      const cells = rs.flatMap(r => t.cols.map((_, j) => [r, j] as [number, number]).filter(([, j]) => j > 0 && t.cols[j][r] !== null));
      return act({ Exclude: { table: t.id, cells, on: true } }).then(done => { if (done) toast(`${rs.length} row${rs.length > 1 ? "s" : ""} excluded. Select them and press Ctrl+E to include them again.`, true); return done; });
    };
    return (
      <Dialog title="Exclude Rows" okText="Exclude" ok={ok}>
        <div class="form">
          <label>Where</label><Pick value={col()} set={setCol} options={columns(t)} />
          <label>is</label><span class="inline"><Pick value={rule()} set={setRule} options={[["lt", "less than"], ["gt", "greater than"], ["eq", "equal to"], ["in", "between"], ["out", "outside"]]} />
            <input type="number" style={{ width: "100px" }} value={a()} onInput={e => setA(e.currentTarget.value)} /><Show when={rule() === "in" || rule() === "out"}><span class="muted">and</span><input type="number" style={{ width: "100px" }} value={b()} onInput={e => setB(e.currentTarget.value)} /></Show></span>
        </div>
        <p class="muted">{rows().length} row{rows().length === 1 ? "" : "s"} match. Their values stay in the table (blue italics) but graphs and analyses leave them out.</p>
      </Dialog>
    );
  });
};

// ---------- test chooser (C4) ----------
type Q = { q: string; a: [string, string][] };
const QUESTIONS: Record<string, Q> = {
  goal: { q: "What do you want to know?", a: [["compare", "Whether groups differ (control vs treated, alloy A vs B…)"], ["relate", "Whether two measurements move together"], ["fit", "A line or curve through X–Y data"], ["describe", "How the values are spread"], ["materials", "Material properties (modulus, strength, activation energy)"], ["plan", "How many samples I need"]] },
  groups: { q: "How many groups?", a: [["2", "Two"], ["3", "Three or more"]] },
  paired: { q: "Are the groups matched?", a: [["no", "No: different items in each group"], ["yes", "Yes: the same items measured each time (before/after, row by row)"]] },
  normal: { q: "Are the values roughly normally distributed?", a: [["yes", "Yes, or n ≥ 15 per group (the usual case)"], ["no", "No: skewed, ranked or with outliers"]] },
  fit: { q: "What shape?", a: [["line", "A straight line"], ["curve", "A curve (exponential, sigmoid, peak…)"], ["std", "A standard curve to read unknowns from"]] },
  describe: { q: "What do you need?", a: [["stats", "Mean, SD, CI, median…"], ["normal", "Whether they are normally distributed"], ["hist", "A histogram"], ["out", "Values that do not belong"]] },
  materials: { q: "Which test?", a: [["tensile", "A tensile test (stress–strain)"], ["weibull", "Strengths of brittle specimens (Weibull)"], ["arrhenius", "Rates at several temperatures (Arrhenius)"]] },
};
const pick = (a: Record<string, string>): [string, Record<string, any>, string] | null => {
  const g = a.goal;
  if (g === "compare") {
    if (!a.groups || !a.paired || !a.normal) return null;
    const two = a.groups === "2", pair = a.paired === "yes", norm = a.normal === "yes";
    if (two) return norm ? ["ttest", { test: pair ? "paired" : "unpaired", welch: true }, pair ? "Paired t-test" : "Unpaired t-test with Welch's correction"] : ["nonparam", { test: pair ? "wilcoxon" : "mw" }, pair ? "Wilcoxon matched-pairs test" : "Mann-Whitney test"];
    return norm ? ["anova", { anova: pair ? "rm" : "ordinary", posthoc: "tukey" }, pair ? "Repeated measures one-way ANOVA" : "One-way ANOVA with Tukey's multiple comparisons"] : ["nonparam", { test: pair ? "friedman" : "kw" }, pair ? "Friedman test" : "Kruskal-Wallis test with Dunn's multiple comparisons"];
  }
  if (g === "relate") return ["correlation", {}, "Correlation (Pearson, Spearman and Kendall)"];
  if (g === "plan") return ["power", {}, "Power and sample size"];
  if (g === "fit") return !a.fit ? null : a.fit === "line" ? ["linear", {}, "Linear regression"] : a.fit === "curve" ? ["fit", {}, "Nonlinear curve fit"] : ["linear", { unknowns: "" }, "Linear regression with unknowns read off the line"];
  if (g === "describe") return !a.describe ? null : ({ stats: ["describe", {}, "Descriptive statistics"], normal: ["normality", {}, "Normality tests"], hist: ["frequency", {}, "Frequency distribution"], out: ["outliers", {}, "Outliers (Grubbs)"] } as Record<string, [string, Record<string, any>, string]>)[a.describe];
  if (g === "materials") return !a.materials ? null : ({ tensile: ["tensile", {}, "Tensile test analysis"], weibull: ["weibull", {}, "Weibull analysis"], arrhenius: ["arrhenius", {}, "Arrhenius analysis"] } as Record<string, [string, Record<string, any>, string]>)[a.materials];
  return null;
};
export const testChooser = () => openDialog(() => {
  const [a, setA] = createSignal<Record<string, string>>({});
  const order = () => { const g = a().goal; return ["goal", ...(g === "compare" ? ["groups", "paired", "normal"] : g === "fit" ? ["fit"] : g === "describe" ? ["describe"] : g === "materials" ? ["materials"] : [])]; };
  const res = () => pick(a());
  const go = () => { const r = res(); if (!r) return false; closeDialog(); setTimeout(() => analysisDialog(r[0], curTable(), undefined, r[1])); };
  return (
    <Dialog title="Test Chooser" wide okText="Open this analysis" ok={go}>
      <div class="chooser"><For each={order()}>{k => <div class="cq"><b>{QUESTIONS[k].q}</b><div class="stackr">{QUESTIONS[k].a.map(([v, l]) =>
        <label class="chk"><input type="radio" name={k} checked={a()[k] === v} onChange={() => setA(k === "goal" ? { goal: v } : { ...a(), [k]: v })} />{l}</label>)}</div></div>}</For></div>
      <div class="cans"><Show when={res()} fallback={<p class="muted">Answer the questions to see the analysis.</p>}>{r => <p>Use <b>{r()[2]}</b>. {r()[0] === "nonparam" || r()[0] === "ttest" || r()[0] === "anova" ? "Put each group in a column of a column table (New Table › Column)." : ""}</p>}</Show>
        <p class="muted small">Help › Statistics Guide explains each test and what its answer means.</p></div>
    </Dialog>
  );
});

// ---------- statistics guide (J3) ----------
const GUIDE: [string, string[]][] = [
  ["Which test when", ["Two groups of different items: unpaired t-test (with Welch's correction); if the values are skewed or ranked, Mann-Whitney.", "The same items measured twice: paired t-test, or Wilcoxon.", "Three or more groups: one-way ANOVA, then Tukey's test to see which pairs differ (Dunnett's to compare each with a control); Kruskal-Wallis with Dunn's test if not normal.", "Two measurements that move together: correlation. One that depends on the other: regression.", "Help › Test Chooser asks a few questions and opens the right analysis."]],
  ["P values", ["P is the chance of a difference at least this large if there were really no difference. It is not the chance that the result is wrong, nor a measure of how big or important the effect is.", "P < 0.05 is a convention, not a law. Report the exact P and the effect with its confidence interval.", "With many comparisons, some P values fall below 0.05 by chance: use multiplicity-adjusted P values (Tukey, Holm-Šidák) after ANOVA."]],
  ["Confidence intervals", ["A 95% CI is the range of values for the true effect that are compatible with the data. Narrow means precise.", "If the CI of a difference excludes zero, P < 0.05 for that difference. The CI tells you more: how big the effect could be."]],
  ["SD or SEM?", ["SD shows how much the values vary; use it to describe the data.", "SEM (SD/√n) shows how precisely the mean is known and shrinks with more samples; use a 95% CI instead to show precision.", "Always say which one your error bars show."]],
  ["Regression and fits", ["R² says how much of the variation the line explains; it does not say the model is right. Look at the residuals: they should scatter randomly (the runs test checks this).", "Fit only the range where the model holds, such as the elastic part of a stress–strain curve.", "Compare models with the F test or AICc (Curve Fit › Compare with), not by R² alone."]],
  ["Materials testing", ["Report the modulus, yield and UTS as mean ± SD of specimens, with the number of specimens.", "Weibull modulus m describes scatter in strength: higher m means more reliable. Standards ask for about 30 specimens.", "Activation energies come from ln(k) against 1/T with T in kelvin; check the Arrhenius plot is straight."]],
  ["Common mistakes", ["Treating repeated readings of one specimen as independent replicates (pseudo-replication).", "Running many t-tests instead of one ANOVA with multiple comparisons.", "Deleting outliers without a reason: exclude them (they stay in the table), and say so.", "Concluding 'no difference' from P > 0.05 with few samples: check the power (Analyze › Power)."]],
];
export const statsGuide = () => openDialog(() => (
  <Dialog title="Statistics Guide" wide>
    <div class="guide"><For each={GUIDE}>{([h, ps]) => <><h4>{h}</h4><ul><For each={ps}>{p => <li>{p}</li>}</For></ul></>}</For></div>
  </Dialog>
));

// ---------- graph styles (D13), colour schemes (D16), copy look (D14) ----------
type Look = Partial<GraphSettings> & { xa?: Partial<GraphSettings["x"]>; ya?: Partial<GraphSettings["y"]> };
export const STYLES: [string, Look][] = [
  ["Prism", { font: "Arial", fontSize: 10, style: "prism", boldTitles: true, palette: "okabe", cap: 3, xa: { minor: false, grid: false }, ya: { minor: false, grid: false } }],
  ["Origin", { font: "Arial", fontSize: 10, style: "frame", boldTitles: false, palette: "bright", cap: 3, xa: { minor: true }, ya: { minor: true } }],
  ["Nature (89 mm)", { font: "Arial", fontSize: 7, width: 89, height: 66, style: "prism", boldTitles: false, palette: "okabe", cap: 2 }],
  ["Science (57 mm)", { font: "Helvetica", fontSize: 7, width: 57, height: 45, style: "prism", boldTitles: false, palette: "okabe", cap: 2 }],
  ["ACS (82.5 mm)", { font: "Arial", fontSize: 8, width: 82.5, height: 62, style: "frame", boldTitles: false, palette: "okabe", cap: 2 }],
  ["IEEE (88.9 mm)", { font: "Times New Roman", fontSize: 8, width: 88.9, height: 66, style: "frame", boldTitles: false, palette: "grey", cap: 2 }],
  ["Presentation", { font: "Arial", fontSize: 18, width: 240, height: 135, style: "prism", boldTitles: true, palette: "tableau", cap: 6 }],
  ["Greyscale", { palette: "grey" }],
];
const LOOK_KEYS: (keyof GraphSettings)[] = ["font", "fontSize", "width", "height", "style", "boldTitles", "palette", "cap", "error", "column"];
export const applyStyle = (g: Graph, l: Look) => setG(g, s => {
  const { xa, ya, ...rest } = l;
  return { ...s, ...rest, x: { ...s.x, ...(xa ?? {}) }, y: { ...s.y, ...(ya ?? {}) } };
});
export const saveStyle = () => {
  const g = needG();
  if (!g) return;
  const name = prompt("Name of the style", "My style")?.trim();
  if (!name) return;
  const s = g.settings, look: Look = { ...Object.fromEntries(LOOK_KEYS.map(k => [k, s[k]])), xa: { minor: s.x.minor, grid: s.x.grid }, ya: { minor: s.y.minor, grid: s.y.grid } };
  const o = { ...opts(), styles: { ...(opts().styles ?? {}), [name]: look } };
  setOpts(o);
  invoke("set_options", { opts: o }).then(() => toast(`Style “${name}” saved. It is in Graph › Styles.`, true)).catch(e => toast(String(e)));
};
export const styleMenu = () => {
  const g = graph();
  const saved = Object.entries(opts().styles ?? {}) as [string, Look][];
  return [...STYLES, ...saved].map(([l, v]) => ({ label: l, run: () => g ? applyStyle(g, v) : toast("Open a graph first.") }) as const)
    .concat([{ label: "Save This Graph's Style…", run: saveStyle } as any, ...(saved.length ? [{ label: "Delete Saved Styles", run: () => { const o = { ...opts(), styles: {} }; setOpts(o); invoke("set_options", { opts: o }); } } as any] : [])]);
};

export const PALETTES: [string, string, string[]][] = [
  ["okabe", "Okabe-Ito (colour-blind safe)", ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000"]],
  ["bright", "Bright (Tol, colour-blind safe)", ["#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377", "#BBBBBB"]],
  ["muted", "Muted (Tol, colour-blind safe)", ["#332288", "#88CCEE", "#44AA99", "#117733", "#999933", "#DDCC77", "#CC6677", "#882255"]],
  ["tableau", "Tableau", ["#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F", "#EDC948", "#B07AA1", "#FF9DA7"]],
  ["dark", "Dark (ColorBrewer)", ["#1B9E77", "#D95F02", "#7570B3", "#E7298A", "#66A61E", "#E6AB02", "#A6761D", "#666666"]],
  ["pastel", "Paired pastel", ["#A6CEE3", "#B2DF8A", "#FB9A99", "#FDBF6F", "#CAB2D6", "#FFFF99", "#1F78B4", "#33A02C"]],
  ["viridis", "Viridis (ordered)", ["#440154", "#414487", "#2A788E", "#22A884", "#7AD151", "#FDE725"]],
  ["cividis", "Cividis (ordered, colour-blind safe)", ["#00224E", "#35456C", "#666970", "#948E77", "#C8B866", "#FEE838"]],
  ["magma", "Magma (ordered)", ["#000004", "#3B0F70", "#8C2981", "#DE4968", "#FE9F6D", "#FCFDBF"]],
  ["grey", "Greyscale", ["#000000", "#333333", "#555555", "#777777", "#999999"]],
];
/** Simulated colour-vision deficiency (Machado 2009, full severity, applied in linear RGB). */
const CVD: Record<string, number[]> = {
  deutan: [0.367, 0.861, -0.228, 0.280, 0.673, 0.047, -0.012, 0.043, 0.969], protan: [0.152, 1.053, -0.205, 0.115, 0.786, 0.099, -0.004, -0.048, 1.052], tritan: [1.256, -0.077, -0.179, -0.078, 0.931, 0.148, 0.005, 0.691, 0.304],
};
const simulate = (hex: string, m: number[]) => {
  const lin = (v: number) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4), gam = (v: number) => Math.round(255 * Math.min(1, Math.max(0, v <= 0.0031308 ? 12.92 * v : 1.055 * v ** (1 / 2.4) - 0.055)));
  const [r, g, b] = [1, 3, 5].map(i => lin(parseInt(hex.slice(i, i + 2), 16) / 255));
  return `rgb(${gam(m[0] * r + m[1] * g + m[2] * b)},${gam(m[3] * r + m[4] * g + m[5] * b)},${gam(m[6] * r + m[7] * g + m[8] * b)})`;
};
export const paletteDialog = () => {
  const g = needG();
  if (!g) return;
  openDialog(() => {
    const cur = () => P().graphs.find(x => x.id === g.id)?.settings.palette || "okabe";
    const [own, setOwn] = createSignal(cur().includes("#") ? cur() : "#0E8C7F, #F2B233, #C0392B, #3A4655");
    const cols = (p: string) => PALETTES.find(x => x[0] === p)?.[2] ?? p.split(",").map(c => c.trim()).filter(c => /^#[0-9a-fA-F]{6}$/.test(c));
    const Sw = (p: { c: string[]; m?: number[] }) => <span class="pal">{p.c.map(c => <i style={{ background: p.m ? simulate(c, p.m) : c }} />)}</span>;
    return (
      <Dialog title="Colour Schemes" wide cancel="Close">
        <table class="tbl paltbl"><thead><tr><th>Scheme</th><th>Colours</th><th>Red-blind (protan)</th><th>Green-blind (deutan)</th><th>Blue-blind (tritan)</th></tr></thead><tbody>
          <For each={PALETTES}>{([k, l, c]) => <tr classList={{ on: cur() === k }} onClick={() => setG(g, s => ({ ...s, palette: k, sets: s.sets.map(x => ({ ...x, color: "" })) }))}><td>{l}</td><td><Sw c={c} /></td><td><Sw c={c} m={CVD.protan} /></td><td><Sw c={c} m={CVD.deutan} /></td><td><Sw c={c} m={CVD.tritan} /></td></tr>}</For>
          <tr classList={{ on: cur().includes("#") }}><td><input class="mono" value={own()} onInput={e => setOwn(e.currentTarget.value)} /></td><td><Sw c={cols(own())} /></td><td><Sw c={cols(own())} m={CVD.protan} /></td><td><Sw c={cols(own())} m={CVD.deutan} /></td>
            <td><button class="btn sm" disabled={!cols(own()).length} onClick={() => setG(g, s => ({ ...s, palette: cols(own()).join(", "), sets: s.sets.map(x => ({ ...x, color: "" })) }))}>Use my colours</button></td></tr>
        </tbody></table>
        <p class="muted">Click a scheme to use it on “{g.name}”; colours set by hand for single data sets are reset. The three columns on the right show how people with colour-blindness see the colours: pick a scheme whose colours stay apart.</p>
      </Dialog>
    );
  });
};

export const copyLook = () => {
  const g = needG();
  if (!g) return;
  const others = P().graphs.filter(x => x.id !== g.id);
  if (!others.length) return toast("There is no other graph to copy the look to.");
  openDialog(() => {
    const [to, setTo] = createSignal<number[]>(others.map(x => x.id));
    return (
      <Dialog title={`Copy Look of “${g.name}”`} okText="Apply" ok={() => act({ CopyLook: { from: g.id, to: to() } }).then(ok => { if (ok) toast(`Look copied to ${to().length} graph${to().length > 1 ? "s" : ""}.`, true); return ok; })}>
        <div class="stackr"><For each={others}>{x => <Check label={x.name} value={to().includes(x.id)} set={v => setTo(v ? [...to(), x.id] : to().filter(i => i !== x.id))} />}</For></div>
        <p class="muted">Copies fonts, sizes, axis style, colours, symbols and error bars. Each graph keeps its own title, axis titles and ranges and fitted curves.</p>
      </Dialog>
    );
  });
};

// ---------- export every graph (G4), Excel workbook (G6) ----------
export const exportAll = () => {
  if (!P().graphs.length) return toast("This project has no graphs.");
  openDialog(() => {
    const [fmt, setFmt] = createSignal("png"), [dpi, setDpi] = createSignal(String(opts().dpi));
    return (
      <Dialog title="Export All Graphs" okText="Choose a folder…" ok={async () => { const r = await call<string | null>("export_all", { fmt: fmt(), dpi: +dpi() }); if (r) toast(r, true); }}>
        <div class="form">
          <label>Format</label><Pick value={fmt()} set={setFmt} options={[["png", "PNG picture"], ["tiff", "TIFF picture (journals)"], ["svg", "SVG vector"], ["pdf", "PDF vector"], ["eps", "EPS vector"]]} />
          <Show when={fmt() === "png" || fmt() === "tiff"}><label>Resolution</label><Pick value={dpi()} set={setDpi} options={[["150", "150 dpi"], ["300", "300 dpi"], ["600", "600 dpi"], ["1200", "1200 dpi"]]} /></Show>
        </div>
        <p class="muted">Each of the {P().graphs.length} graphs is saved under its own name, at its own size.</p>
      </Dialog>
    );
  });
};
export const exportExcel = async () => { const p = await call<string | null>("export_excel"); if (p) toast(`Saved ${p}`, true); };

/** Graph › Significance: brackets come from a t-test (two groups) or a one-way ANOVA. */
export const significance = () => {
  const t = curTable();
  if (!t) return toast("Open a column graph first.");
  if (t.kind === "grouped") return analysisDialog("twoway", t, undefined, {});
  if (t.kind !== "column") return toast("Significance brackets go on column and grouped graphs. Make a column table (New Table › Column) for groups.");
  const [kind, preset] = BY_ID[t.sets.length === 2 ? "B4" : "B6"];
  analysisDialog(kind, t, undefined, preset);
};
