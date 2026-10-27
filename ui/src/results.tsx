// Results: the options dialog of each analysis, and the results sheet (tabs of tables, small
// plots, and the Explain panel with the answer, checks, methods text and Python code).
import { For, Show, createSignal, createEffect, on, createResource } from "solid-js";
import { Analysis, Result, Table, invoke, letter } from "./api";
import { act, call, out, P, open, openDialog, toast, item } from "./store";
import { Dialog, Pick, Check, Tabs, Icon } from "./ui";
import { Empty } from "./nav";
import { Help } from "./help";

/** The analyses that exist, by kind: [name, catalogue id, draws on the graph: curves, or brackets on column graphs]. */
export const KINDS: Record<string, [string, string, boolean | "brackets"]> = {
  describe: ["Descriptive statistics", "B1", false], normality: ["Normality tests", "B2", false], outliers: ["Outliers", "B3", false],
  linear: ["Linear regression", "B9", true], fit: ["Nonlinear curve fit", "B10", true], arrhenius: ["Arrhenius analysis", "B28", true],
  ttest: ["t-test", "B4", "brackets"], twoway: ["Two-way ANOVA", "B15", "brackets"], contingency: ["Contingency", "B17", false], parts: ["Fractions of total", "A6", false], blandaltman: ["Bland-Altman", "B18", false], roc: ["ROC curve", "B18", false], nonparam: ["Nonparametric test", "B5", "brackets"], anova: ["One-way ANOVA", "B6", "brackets"], correlation: ["Correlation", "B16", false], power: ["Power and sample size", "B23", false],
  transform: ["Transform", "A15", false], check: ["Data checks", "A18", false], frequency: ["Frequency distribution", "D4", false], auc: ["Area under the curve", "B14", true], smooth: ["Smooth, differentiate or integrate", "B14", true],
  tensile: ["Tensile test", "B27", true], weibull: ["Weibull analysis", "B29", false],
};
/** Does this analysis draw on the graphs of table `t`? */
export const draws = (kind: string, t?: Table) => { const d = KINDS[kind]?.[2]; return d === "brackets" ? (kind === "twoway" ? t?.kind === "grouped" : t?.kind === "column") : !!d && t?.kind === "xy"; };
/** Catalogue id → analysis kind (and preset options), for the Analyze gallery and ribbon. */
export const BY_ID: Record<string, [string, Record<string, any>]> = {
  B1: ["describe", {}], B2: ["normality", {}], B3: ["outliers", {}], A16: ["outliers", {}], B9: ["linear", {}], B13: ["linear", { unknowns: "" }],
  B10: ["fit", {}], B11: ["fit", {}], B12: ["fit", { shared: "" }], B28: ["arrhenius", {}], B4: ["ttest", {}], B8: ["ttest", {}], B5: ["nonparam", {}], B6: ["anova", {}], B15: ["twoway", {}], B17: ["contingency", {}], A6: ["parts", {}], B18: ["blandaltman", {}], B18r: ["roc", {}], B7: ["anova", { posthoc: "tukey" }],
  B16: ["correlation", {}], B23: ["power", {}], A15: ["transform", {}], A18: ["check", {}], D4: ["frequency", {}], B14: ["auc", {}], B14s: ["smooth", {}], B27: ["tensile", {}], B29: ["weibull", {}],
};

const DEFAULTS: Record<string, Record<string, any>> = {
  describe: {}, normality: { alpha: 0.05 }, outliers: { alpha: 0.05 },
  linear: { model: "line", order: 2, points: "each", weight: "none", compare: true, bands: "ci", label: true, unknowns: "" },
  fit: { model: "exp_decay", equation: "Y = A*exp(-k*X) + C", init: {}, fixed: {}, points: "each", weight: "none", bands: "ci", label: true, unknowns: "" },
  arrhenius: { tunit: "C", eunit: "kJ/mol", points: "each", label: true },
  ttest: { test: "unpaired", welch: true, mu: 0, alpha: 0.05, brackets: "sig", ptext: "stars" }, nonparam: { test: "mw", alpha: 0.05, brackets: "sig", ptext: "stars" },
  twoway: { posthoc: "sidak", compare: "rows", interaction: true, rowname: "", colname: "", alpha: 0.05, brackets: "sig", ptext: "stars" },
  parts: {}, blandaltman: { diff: "diff" }, roc: { direction: "higher" }, contingency: { yates: false, diagnostic: false, alpha: 0.05 },
  anova: { anova: "ordinary", posthoc: "tukey", trend: false, alpha: 0.05, brackets: "sig", ptext: "stars" }, correlation: { between: false }, power: { test: "t2", effect: "", power: 0.8, n: "", alpha: 0.05 },
  transform: { x: "none", kx: 1, y: "none", ky: 1, baseline: "none", base: 0, normalize: "none", means: false }, check: {}, frequency: { bins: "auto", width: "", y: "count", cumulative: false },
  auc: { baseline: "zero", base: 0, label: true }, smooth: { method: "sg", window: 7, order: 2, frac: 0.3, mode: "smooth", label: false }, tensile: { strain: "abs", offset: 0.2, label: true }, weibull: { method: "mle" },
};
const FUNCS: [string, string][] = [["none", "No change"], ["log10", "log10"], ["ln", "ln (natural log)"], ["recip", "1 / value"], ["sqrt", "Square root"], ["square", "Square"], ["exp10", "10 ^ value"], ["exp", "e ^ value"],
  ["mul", "Multiply by k"], ["add", "Add k"], ["c2k", "°C → kelvin"], ["k2c", "kelvin → °C"], ["pct", "Fraction → %"], ["frac", "% → fraction"]];
const [models] = createResource(() => invoke<{ models: [string, string, string, string][] }>("models").then(r => r.models).catch(() => [] as [string, string, string, string][]));

/** "A=1, k=0.5" ↔ {A: 1, k: 0.5}. */
const pairs = (s: string) => Object.fromEntries(s.split(/[,;]/).map(x => x.split("=").map(y => y.trim())).filter(x => x.length === 2 && x[0] && x[1] !== "").map(([k, v]) => [k, +v]));
const unpair = (o: Record<string, number> = {}) => Object.entries(o).map(([k, v]) => `${k}=${v}`).join(", ");
const optNum = (v: string) => (v.trim() === "" || isNaN(+v) ? null : +v);

/** Analyze: choose the data sets and options, then add (or change) the analysis. */
export const analysisDialog = (kind: string, t: Table | undefined, existing?: Analysis, preset: Record<string, any> = {}) => {
  if (!t) return toast("Open a data table or its graph first.");
  openDialog(() => {
    const [o, setO] = createSignal<Record<string, any>>({ ...DEFAULTS[kind], ...preset, ...(existing?.options ?? {}) });
    const [sets, setSets] = createSignal<number[]>(existing?.sets ?? []);
    const [name, setName] = createSignal(existing?.name ?? `${KINDS[kind][0]} · ${t.name}`);
    const put = (k: string, v: unknown) => setO({ ...o(), [k]: v });
    const on = (k: number) => !sets().length || sets().includes(k);
    const toggle = (k: number) => { const all = t.sets.map((_, i) => i), cur = sets().length ? sets() : all, next = on(k) ? cur.filter(x => x !== k) : [...cur, k].sort(); setSets(next.length === all.length ? [] : next); };
    const ok = async () => {
      const a = { id: existing?.id ?? 0, table: t.id, name: name(), kind, sets: sets(), options: o() };
      const done = existing ? await act({ SetAnalysis: { analysis: a } }) : await act({ AddAnalysis: { analysis: a, overlay: draws(kind, t) } });
      if (done && !existing) { const as = out()!.project.analyses; open("results", as[as.length - 1].id); }
      return done;
    };
    const Range = () => <><label>Fit X from</label><span class="inline"><input type="number" style={{ width: "100px" }} placeholder="start" value={o().xmin ?? ""} onChange={e => put("xmin", optNum(e.currentTarget.value))} /><span class="muted">to</span>
      <input type="number" style={{ width: "100px" }} placeholder="end" value={o().xmax ?? ""} onChange={e => put("xmax", optNum(e.currentTarget.value))} /><span class="muted">empty = all the data</span></span></>;
    const Points = () => <><label>Points</label><Pick value={o().points} set={v => put("points", v)} options={[["each", "Every replicate (recommended)"], ["mean", "Only the mean at each X"]]} /></>;
    const Show_ = () => <><label>On the graph</label><span class="inline"><Pick value={o().bands ?? "ci"} set={v => put("bands", v)} options={[["ci", "95% confidence band"], ["pi", "95% prediction band"], ["both", "Both bands"], ["none", "Line only"]]} />
      <Check label="Equation and R²" value={o().label !== false} set={v => put("label", v)} /></span></>;
    const Unknowns = () => <><label>Unknowns (Y values)</label><input placeholder="e.g. 0.35, 0.82 — read X off the fit" value={o().unknowns ?? ""} onChange={e => put("unknowns", e.currentTarget.value)} /></>;
    const model = () => models()?.find(m => m[0] === o().model);
    const N = (p: { k: string; w?: number; ph?: string }) => <input type="number" style={{ width: `${p.w ?? 90}px` }} placeholder={p.ph} value={o()[p.k] ?? ""} onChange={e => put(p.k, optNum(e.currentTarget.value) ?? "")} />;
    const Alpha = () => <><label>Significance level α</label><Pick value={String(o().alpha)} set={v => put("alpha", +v)} options={[["0.01", "0.01"], ["0.05", "0.05"], ["0.1", "0.10"]]} /></>;
    const Brackets = () => <Show when={t.kind === "column" || t.kind === "grouped"}><label>On the graph</label><span class="inline"><Pick value={o().brackets} set={v => put("brackets", v)} options={[["sig", "Brackets for significant pairs"], ["all", "Brackets for every pair"], ["none", "No brackets"]]} />
      <Pick value={o().ptext} set={v => put("ptext", v)} options={[["stars", "Stars (*, **, ***)"], ["p", "P values"]]} /></span></Show>;
    return (
      <Dialog title={existing ? `Change · ${existing.name}` : KINDS[kind][0]} wide help="options" okText={existing ? "OK" : "Analyze"} ok={ok}>
        <div class="form">
          <label>Name</label><input value={name()} onInput={e => setName(e.currentTarget.value)} />
          <label>Data sets</label><span class="inline"><For each={t.sets}>{(s, k) => <Check label={`${letter(k())}: ${s.title || `Data set ${letter(k())}`}`} value={on(k())} set={() => toggle(k())} />}</For></span>
          <Show when={["normality", "outliers", "ttest", "nonparam", "anova", "twoway", "contingency", "power"].includes(kind)}><Alpha /></Show>
          <Show when={kind === "ttest"}>
            <label>Test</label><Pick value={o().test} set={v => put("test", v)} options={[["unpaired", "Unpaired (two independent groups)"], ["paired", "Paired (the same items twice, row by row)"], ["ratio", "Ratio paired (ratios, not differences)"], ["one", "One sample against a value"]]} />
            <Show when={o().test === "unpaired"}><label /><Check label="Welch's correction (do not assume equal SDs; recommended)" value={!!o().welch} set={v => put("welch", v)} /></Show>
            <Show when={o().test === "one"}><label>Hypothetical value</label><N k="mu" /></Show>
            <Brackets />
          </Show>
          <Show when={kind === "twoway"}>
            <label>Factor names</label><span class="inline"><input placeholder="Rows, e.g. Alloy" value={o().rowname} onChange={e => put("rowname", e.currentTarget.value)} /><input placeholder="Data sets, e.g. Treatment" value={o().colname} onChange={e => put("colname", e.currentTarget.value)} /></span>
            <label>Model</label><Check label="Include the interaction (needs two or more values per cell)" value={o().interaction !== false} set={v => put("interaction", v)} />
            <label>Compare</label><Pick value={o().compare} set={v => put("compare", v)} options={[["rows", "The data sets within each row"], ["sets", "The rows within each data set"]]} />
            <label>Correction</label><Pick value={o().posthoc} set={v => put("posthoc", v)} options={[["sidak", "Šidák"], ["holm", "Holm-Šidák"], ["bonferroni", "Bonferroni"], ["lsd", "None (Fisher's LSD)"], ["none", "No comparisons"]]} />
            <Brackets />
          </Show>
          <Show when={kind === "blandaltman"}><label>Plot</label><Pick value={o().diff} set={v => put("diff", v)} options={[["diff", "Differences (B − A)"], ["pct", "Differences as % of the mean"], ["ratio", "Ratios (B / A)"]]} />
            <label /><p class="muted">The first two data sets are the two methods; each row is one item measured by both.</p></Show>
          <Show when={kind === "roc"}><label>Positive when</label><Pick value={o().direction} set={v => put("direction", v)} options={[["higher", "The value is high"], ["lower", "The value is low"]]} />
            <label /><p class="muted">The first data set holds the controls (negatives), the second the cases (positives).</p></Show>
          <Show when={kind === "contingency"}>
            <label>2 × 2 tables</label><span class="stackr"><Check label="Yates' continuity correction on the chi-square test" value={!!o().yates} set={v => put("yates", v)} />
              <Check label="Diagnostic test: rows are test results (positive first), data sets the true state (yes first)" value={!!o().diagnostic} set={v => put("diagnostic", v)} /></span>
          </Show>
          <Show when={kind === "nonparam"}>
            <label>Test</label><Pick value={o().test} set={v => put("test", v)} options={[["mw", "Mann-Whitney (two independent groups)"], ["wilcoxon", "Wilcoxon matched pairs (paired)"], ["ks", "Kolmogorov-Smirnov (two distributions)"], ["kw", "Kruskal-Wallis with Dunn's test (three or more groups)"], ["friedman", "Friedman (repeated measures)"]]} />
            <Brackets />
          </Show>
          <Show when={kind === "anova"}>
            <label>ANOVA</label><Pick value={o().anova} set={v => put("anova", v)} options={[["ordinary", "Ordinary (equal SDs)"], ["welch", "Welch (unequal SDs)"], ["bf", "Brown-Forsythe (unequal SDs)"], ["rm", "Repeated measures (rows are subjects)"]]} />
            <label>Multiple comparisons</label><Pick value={o().posthoc} set={v => put("posthoc", v)} options={[["tukey", "Tukey: every pair"], ["dunnett", "Dunnett: each against the first group"], ["holm", "Holm-Šidák: every pair"], ["sidak", "Šidák"], ["bonferroni", "Bonferroni"], ["lsd", "Fisher's LSD (no correction)"], ["none", "None"]]} />
            <label /><Check label="Test for a linear trend across the groups (in their order)" value={!!o().trend} set={v => put("trend", v)} />
            <Brackets />
          </Show>
          <Show when={kind === "correlation" && t.kind !== "column"}><label>Correlate</label><Pick value={o().between ? "1" : ""} set={v => put("between", !!v)} options={[["", "X with each data set's Y"], ["1", "The data sets with each other (row by row)"]]} /></Show>
          <Show when={kind === "power"}>
            <label>Test</label><Pick value={o().test} set={v => put("test", v)} options={[["t2", "Unpaired t-test"], ["paired", "Paired t-test"], ["anova", "One-way ANOVA"], ["prop", "Two proportions (Cohen's h)"]]} />
            <label>Effect size</label><span class="inline"><N k="effect" ph="from the data" /><span class="muted">Cohen's d (f for ANOVA); empty = from the chosen data sets</span></span>
            <label>Power wanted</label><Pick value={String(o().power)} set={v => put("power", +v)} options={[["0.8", "80%"], ["0.85", "85%"], ["0.9", "90%"], ["0.95", "95%"]]} />
            <label>Or: power with n</label><span class="inline"><N k="n" ph="per group" /><span class="muted">empty = find the n you need</span></span>
          </Show>
          <Show when={kind === "transform"}>
            <label>X values</label><span class="inline"><Pick value={o().x} set={v => put("x", v)} options={FUNCS} /><Show when={o().x === "mul" || o().x === "add"}><span class="muted">k</span><N k="kx" w={80} /></Show></span>
            <label>Y values</label><span class="inline"><Pick value={o().y} set={v => put("y", v)} options={FUNCS} /><Show when={o().y === "mul" || o().y === "add"}><span class="muted">k</span><N k="ky" w={80} /></Show></span>
            <label>Baseline</label><span class="inline"><Pick value={o().baseline} set={v => put("baseline", v)} options={[["none", "Keep"], ["first", "Subtract the first value"], ["min", "Subtract the smallest value"], ["value", "Subtract a value"]]} /><Show when={o().baseline === "value"}><N k="base" w={80} /></Show></span>
            <label>Normalise</label><Pick value={o().normalize} set={v => put("normalize", v)} options={[["none", "No"], ["range", "0 % = smallest, 100 % = largest"], ["max", "100 % = largest"], ["first", "100 % = first value"]]} />
            <label>Replicates</label><Check label="Replace them by mean, SD and N" value={!!o().means} set={v => put("means", v)} />
          </Show>
          <Show when={kind === "frequency"}>
            <label>Bins</label><span class="inline"><Pick value={String(o().bins)} set={v => put("bins", v)} options={[["auto", "Automatic"], ...["5", "8", "10", "15", "20", "30"].map(x => [x, `${x} bins`] as [string, string])]} /><span class="muted">or width</span><N k="width" w={80} /></span>
            <label>Show</label><span class="inline"><Pick value={o().y} set={v => put("y", v)} options={[["count", "Counts"], ["percent", "Percentages"], ["fraction", "Fractions"]]} /><Check label="Cumulative" value={!!o().cumulative} set={v => put("cumulative", v)} /></span>
          </Show>
          <Show when={kind === "auc"}>
            <label>Baseline</label><span class="inline"><Pick value={o().baseline} set={v => put("baseline", v)} options={[["zero", "Y = 0"], ["line", "Straight line from the first to the last point"], ["first", "The first Y value"], ["min", "The smallest Y value"], ["value", "Y = a value"]]} /><Show when={o().baseline === "value"}><N k="base" w={80} /></Show></span>
            <Range />
          </Show>
          <Show when={kind === "smooth"}>
            <label>Smoothing</label><span class="inline"><Pick value={o().method} set={v => put("method", v)} options={[["sg", "Savitzky-Golay"], ["lowess", "LOWESS"], ["ma", "Moving average"], ["none", "None"]]} />
              <Show when={o().method === "sg" || o().method === "ma"}><span class="muted">window</span><N k="window" w={60} /></Show><Show when={o().method === "sg"}><span class="muted">order</span><N k="order" w={50} /></Show><Show when={o().method === "lowess"}><span class="muted">fraction</span><N k="frac" w={60} /></Show></span>
            <label>Result</label><Pick value={o().mode} set={v => put("mode", v)} options={[["smooth", "The smoothed curve"], ["deriv1", "First derivative (slope)"], ["deriv2", "Second derivative"], ["integral", "Cumulative integral (area so far)"]]} />
            <Range />
          </Show>
          <Show when={kind === "tensile"}>
            <label>Strain is</label><Pick value={o().strain} set={v => put("strain", v)} options={[["abs", "Absolute (mm/mm)"], ["pct", "In percent"]]} />
            <label>Yield offset (%)</label><N k="offset" w={80} />
            <label>Modulus from strain</label><span class="inline"><input type="number" style={{ width: "100px" }} placeholder="auto" value={o().xmin ?? ""} onChange={e => put("xmin", optNum(e.currentTarget.value))} /><span class="muted">to</span>
              <input type="number" style={{ width: "100px" }} placeholder="auto" value={o().xmax ?? ""} onChange={e => put("xmax", optNum(e.currentTarget.value))} /><span class="muted">empty = 10–40 % of the UTS</span></span>
            <label /><p class="muted">X is strain; each replicate column of a data set is one specimen's stress.</p>
          </Show>
          <Show when={kind === "weibull"}><label>Method</label><Pick value={o().method} set={v => put("method", v)} options={[["mle", "Maximum likelihood (recommended, ISO 20501 / ASTM C1239)"], ["lr", "Linear regression of the Weibull plot"]]} /></Show>
          <Show when={kind === "linear"}>
            <label>Model</label><span class="inline"><Pick value={o().model} set={v => put("model", v)} options={[["line", "Straight line (least squares)"], ["origin", "Straight line through the origin"], ["poly", "Polynomial"], ["deming", "Deming (errors in X and Y)"]]} />
              <Show when={o().model === "poly"}><span class="muted">order</span><Pick value={String(o().order)} set={v => put("order", +v)} options={["2", "3", "4", "5", "6"]} /></Show></span>
            <Range /><Points />
            <label>Weighting</label><Pick value={o().weight} set={v => put("weight", v)} options={[["none", "None (ordinary least squares)"], ["1/y2", "1/Y² (relative errors)"]]} />
            <label>Compare</label><Check label="Test whether the lines of the data sets differ (slopes, then intercepts)" value={!!o().compare} set={v => put("compare", v)} />
            <Show_ /><Unknowns />
          </Show>
          <Show when={kind === "fit"}>
            <label>Model</label><Pick value={o().model} set={v => put("model", v)} options={[...(models() ?? []).map(m => [m[0], m[1]] as [string, string]), ["custom", "Your own equation…"]]} />
            <Show when={o().model === "custom"} fallback={<><label /><p class="muted eq">Y = {model()?.[2]}<br />{model()?.[3]}</p></>}>
              <label>Equation</label><input class="mono" value={o().equation} onChange={e => put("equation", e.currentTarget.value)} />
              <label /><p class="muted">Use X and any parameter names; exp, log (natural), log10, sqrt, sin, cos and ^ work. Example: Y = Ymax*(1 - exp(-k*X)).</p>
            </Show>
            <label>Starting values</label><input placeholder="optional, e.g. A=100, k=0.01" value={unpair(o().init)} onChange={e => put("init", pairs(e.currentTarget.value))} />
            <label>Fixed parameters</label><input placeholder="optional, e.g. C=0" value={unpair(o().fixed)} onChange={e => put("fixed", pairs(e.currentTarget.value))} />
            <label>Global fit</label><span class="inline"><input placeholder="shared parameters, e.g. k" value={o().shared ?? ""} onChange={e => put("shared", e.currentTarget.value)} /><span class="muted">one value for every data set, and an F test of whether it differs</span></span>
            <label>Compare with</label><span class="inline"><Pick value={o().model2 ?? ""} set={v => put("model2", v)} options={[["", "No second model"], ...(models() ?? []).filter(m => m[0] !== o().model).map(m => [m[0], m[1]] as [string, string]), ["custom", "Your own second equation…"]]} />
              <Show when={o().model2 === "custom"}><input class="mono" placeholder="Y = …" value={o().equation2 ?? ""} onChange={e => put("equation2", e.currentTarget.value)} /></Show></span>
            <Range /><Points />
            <label>Weighting</label><Pick value={o().weight} set={v => put("weight", v)} options={[["none", "None"], ["1/y2", "Relative (1/Y)"]]} />
            <Show_ /><Unknowns />
          </Show>
          <Show when={kind === "arrhenius"}>
            <label>X is temperature in</label><Pick value={o().tunit} set={v => put("tunit", v)} options={[["C", "°C"], ["K", "kelvin"]]} />
            <label>Activation energy in</label><Pick value={o().eunit} set={v => put("eunit", v)} options={["kJ/mol", "eV", "kcal/mol", "J/mol"]} />
            <Range /><Points />
            <label>On the graph</label><Check label="Show Ea on the graph" value={o().label !== false} set={v => put("label", v)} />
          </Show>
        </div>
        <p class="muted">The result stays linked to “{t.name}”: change a value and it updates.{draws(kind, t) ? (KINDS[kind][2] === "brackets" ? " Significance brackets are drawn on the table's graphs." : " The fitted curve is drawn on the table's graphs.") : ""}{kind === "transform" || kind === "frequency" || kind === "smooth" ? " Make it a new data table from the results." : ""}</p>
      </Dialog>
    );
  });
};

const tsv = (t: { columns: string[]; rows: string[][] }) => [t.columns, ...t.rows].map(r => r.join("\t")).join("\n");
const ICON: Record<string, string> = { true: "✓", false: "⚠", null: "ℹ" };

/** The results sheet of the open analysis. */
export const ResultsView = (p: { a: Analysis }) => {
  const [r, setR] = createSignal<Result | null>(null), [err, setErr] = createSignal(""), [tab, setTab] = createSignal("Summary");
  createEffect(on(() => [p.a.id, out()?.rev], () => { invoke<Result>("result", { id: p.a.id }).then(x => { setR(x); setErr(""); if (!x.tabs.some(t => t.name === tab())) setTab(x.tabs[0]?.name ?? "Summary"); }).catch(e => setErr(String(e))); }));
  const t = () => P().tables.find(x => x.id === p.a.table);
  const graphs = () => P().graphs.filter(g => g.table === p.a.table);
  const copy = (text: string, what: string) => call("copy_text", { text }).then(() => toast(`${what} copied.`, true));
  const code = () => openDialog(() => <Dialog title="Python code"><p class="muted">The same calculation in Python (numpy, SciPy, statsmodels, lmfit), to check it outside Datum Plot.</p><pre class="code">{r()?.code}</pre>
    <p><button class="btn sm" onClick={() => copy(r()!.code, "Code")}>Copy</button></p></Dialog>);
  return (
    <section class="rview">
      <div class="rhead"><Icon n="results" /><b>{p.a.name}</b><Help k="results" /><span class="muted">of <a onClick={() => open("data", p.a.table)}>{t()?.name}</a></span><span class="grow" />
        <Show when={r()?.cells.length}><button class="btn sm pri" onClick={() => act({ Exclude: { table: p.a.table, cells: r()!.cells, on: true } }).then(ok => ok && toast("Outliers excluded. They stay in the table in blue.", true))}>Exclude {r()!.cells.length} outlier{r()!.cells.length > 1 ? "s" : ""}</button></Show>
        <Show when={r()?.table}><button class="btn sm pri" title="A new data table (with its graph) from these values" onClick={() => act({ NewTable: { table: r()!.table, graph: {} } }).then(ok => { if (ok) { const ts = out()!.project.tables; open("data", ts[ts.length - 1].id); toast("New data table made from the result.", true); } })}>New table from result</button></Show>
        <Show when={draws(p.a.kind, t())}><For each={graphs()}>{g => <Check label={`Show on ${g.name}`} value={g.settings.overlays.includes(p.a.id)} set={v => act({ Overlay: { graph: g.id, analysis: p.a.id, on: v } })} />}</For></Show>
        <button class="btn sm" onClick={() => analysisDialog(p.a.kind, t(), p.a)}>Change…</button><button class="btn sm" onClick={code}>Python code</button>
      </div>
      <Show when={r()} fallback={<div class="gwait">{err() || "Calculating…"}</div>}>{res => (
        <div class="rbody">
          <div class="rmain">
            <Tabs tabs={res().tabs.map(x => [x.name, x.name] as [string, string])} on={tab()} set={setTab} />
            <For each={res().tabs.find(x => x.name === tab())?.tables ?? []}>{tb => (
              <div class="rtable"><div class="rtt"><b>{tb.title}</b><button class="btn sm" title="Copy as a table for Excel or Word" onClick={() => copy(tsv(tb), "Table")}>Copy</button></div>
                <table class="tbl"><thead><tr><For each={tb.columns}>{c => <th>{c}</th>}</For></tr></thead>
                  <tbody><For each={tb.rows}>{row => <tr><For each={row}>{(c, i) => <td classList={{ r: i() > 0, sub: i() === 0 && c.startsWith("  ") }}>{c}</td>}</For></tr>}</For></tbody></table></div>
            )}</For>
            <Show when={tab() === res().tabs[0]?.name && res().plots.length}><div class="rplots"><For each={res().plots}>{pl => <figure><img src={`data:image/svg+xml;charset=utf-8,${encodeURIComponent(pl.svg)}`} /><figcaption>{pl.title}</figcaption></figure>}</For></div></Show>
          </div>
          <aside class="explain">
            <h4>Answer</h4><p class="ans">{res().answer}</p>
            <Show when={res().checks.length}><h4>Checks</h4><ul class="checks"><For each={res().checks}>{([ok, text]) => <li classList={{ ok: ok === true, bad: ok === false }}><i>{ICON[String(ok)]}</i>{text}</li>}</For></ul></Show>
            <h4>Methods</h4><p class="small">{res().methods}</p><button class="btn sm" onClick={() => copy(res().methods + (res().legend ? `\n\n${res().legend}` : ""), "Methods text")}>Copy methods text</button>
            <Show when={res().legend}><h4>Figure legend</h4><p class="small">{res().legend}</p></Show>
          </aside>
        </div>
      )}</Show>
    </section>
  );
};

/** The Results section: the open analysis, or what results are when there are none yet. */
export const ResultsPage = () => {
  const a = () => P().analyses?.find(x => x.id === item().id);
  return (
    <Show when={a()} fallback={<Empty icon="results" title="Results">
      <p>Results are the answers of analyses: statistics, t-tests and ANOVA, regression and curve fits, tensile, Weibull and Arrhenius analyses, transforms and more. Each stays linked to its table and updates when the data change.</p>
      <p><button class="btn pri" onClick={() => import("./roadmap").then(m => m.analyze())}>Analyze…</button></p>
    </Empty>}>{x => <For each={[x().id]}>{() => <ResultsView a={a()!} />}</For>}</Show>
  );
};
