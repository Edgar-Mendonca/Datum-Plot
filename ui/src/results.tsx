// Results: the options dialog of each analysis, and the results sheet (tabs of tables, small
// plots, and the Explain panel with the answer, checks, methods text and Python code).
import { For, Show, createSignal, createEffect, on, createResource } from "solid-js";
import { Analysis, Result, Table, invoke, letter } from "./api";
import { act, call, out, P, open, openDialog, toast, item } from "./store";
import { Dialog, Pick, Check, Tabs, Icon } from "./ui";
import { Empty } from "./nav";

/** The analyses that exist, by kind: [name, catalogue id, draws a curve on the graph]. */
export const KINDS: Record<string, [string, string, boolean]> = {
  describe: ["Descriptive statistics", "B1", false], normality: ["Normality tests", "B2", false], outliers: ["Outliers", "B3", false],
  linear: ["Linear regression", "B9", true], fit: ["Nonlinear curve fit", "B10", true], arrhenius: ["Arrhenius analysis", "B28", true],
};
/** Catalogue id → analysis kind (and preset options), for the Analyze gallery and ribbon. */
export const BY_ID: Record<string, [string, Record<string, any>]> = {
  B1: ["describe", {}], B2: ["normality", {}], B3: ["outliers", {}], A16: ["outliers", {}], B9: ["linear", {}], B13: ["linear", { unknowns: "" }],
  B10: ["fit", {}], B11: ["fit", {}], B28: ["arrhenius", {}],
};

const DEFAULTS: Record<string, Record<string, any>> = {
  describe: {}, normality: { alpha: 0.05 }, outliers: { alpha: 0.05 },
  linear: { model: "line", order: 2, points: "each", weight: "none", compare: true, bands: "ci", label: true, unknowns: "" },
  fit: { model: "exp_decay", equation: "Y = A*exp(-k*X) + C", init: {}, fixed: {}, points: "each", weight: "none", bands: "ci", label: true, unknowns: "" },
  arrhenius: { tunit: "C", eunit: "kJ/mol", points: "each", label: true },
};
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
      const done = existing ? await act({ SetAnalysis: { analysis: a } }) : await act({ AddAnalysis: { analysis: a, overlay: KINDS[kind][2] } });
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
    return (
      <Dialog title={existing ? `Change · ${existing.name}` : KINDS[kind][0]} wide okText={existing ? "OK" : "Analyze"} ok={ok}>
        <div class="form">
          <label>Name</label><input value={name()} onInput={e => setName(e.currentTarget.value)} />
          <label>Data sets</label><span class="inline"><For each={t.sets}>{(s, k) => <Check label={`${letter(k())}: ${s.title || `Data set ${letter(k())}`}`} value={on(k())} set={() => toggle(k())} />}</For></span>
          <Show when={kind === "normality" || kind === "outliers"}><label>Significance level α</label><Pick value={String(o().alpha)} set={v => put("alpha", +v)} options={[["0.01", "0.01"], ["0.05", "0.05"], ["0.1", "0.10"]]} /></Show>
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
        <p class="muted">The result stays linked to “{t.name}”: change a value and it updates.{KINDS[kind][2] ? " The fitted curve is drawn on the table's graphs." : ""}</p>
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
      <div class="rhead"><Icon n="results" /><b>{p.a.name}</b><span class="muted">of <a onClick={() => open("data", p.a.table)}>{t()?.name}</a></span><span class="grow" />
        <Show when={r()?.cells.length}><button class="btn sm pri" onClick={() => act({ Exclude: { table: p.a.table, cells: r()!.cells, on: true } }).then(ok => ok && toast("Outliers excluded. They stay in the table in blue.", true))}>Exclude {r()!.cells.length} outlier{r()!.cells.length > 1 ? "s" : ""}</button></Show>
        <Show when={KINDS[p.a.kind]?.[2]}><For each={graphs()}>{g => <Check label={`Show on ${g.name}`} value={g.settings.overlays.includes(p.a.id)} set={v => act({ Overlay: { graph: g.id, analysis: p.a.id, on: v } })} />}</For></Show>
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
      <p>Results are the answers of analyses: descriptive statistics, normality, outliers, linear regression, curve fits and Arrhenius plots. Each stays linked to its table and updates when the data change.</p>
      <p><button class="btn pri" onClick={() => import("./roadmap").then(m => m.analyze())}>Analyze…</button></p>
    </Empty>}>{x => <For each={[x().id]}>{() => <ResultsView a={a()!} />}</For>}</Show>
  );
};
