// Format Graph: data sets, axes and the whole graph. Every change applies at once (with undo),
// so the graph behind the dialog shows it.
import { For, Show, createSignal, createEffect, on, JSX } from "solid-js";
import { Graph, GraphSettings, Axis, SetStyle, Note, letter, isEmpty, invoke, dateText } from "./api";
import { act, out, openDialog, closeDialog, dialogs, toast, item } from "./store";
import { Dialog, Tabs, Pick, Check } from "./ui";
import { PALETTES, ORDERED, paletteName } from "./tools";
import { lastRender } from "./graph";

export const OKABE_ITO = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000"];
export const SYMBOLS: [string, string][] = [["circle", "● Circle"], ["square", "■ Square"], ["triangle", "▲ Triangle"], ["down", "▼ Down triangle"], ["diamond", "◆ Diamond"], ["pentagon", "⬟ Pentagon"], ["hexagon", "⬢ Hexagon"], ["star", "★ Star"], ["none", "No symbol"]];
export const FONTS = ["Arial", "Helvetica", "Calibri", "Segoe UI", "Verdana", "Times New Roman", "Georgia", "Cambria"];
export const MATRIX: [string, string][] = [["contour", "Contour map"], ["heatmap", "Heat map"], ["surface", "3D surface"], ["wireframe", "3D wireframe"]];
export const ERRORS: [string, string][] = [["sd", "Mean ± SD"], ["sem", "Mean ± SEM"], ["ci", "Mean ± 95% CI"], ["range", "Mean and range"], ["median_iqr", "Median and interquartile range"], ["median_range", "Median and range"], ["median_ci", "Median ± 95% CI"], ["none", "Mean only"]];
/** Journal column widths in mm. */
export const SIZES: [string, number, number][] = [["Single column (85 mm)", 85, 64], ["1.5 columns (114 mm)", 114, 80], ["Double column (174 mm)", 174, 110], ["Square (80 mm)", 80, 80], ["Slide (240 × 135 mm)", 240, 135]];

const DEF_SET: SetStyle = { show: true, color: "", symbol: "", size: 6, filled: true, line: null, width: 1, right: false };
/** Applies a change to the graph's settings. */
export const setG = (g: Graph, f: (s: GraphSettings) => GraphSettings) => {
  const now = out()!.project.graphs.find(x => x.id === g.id)?.settings ?? g.settings;
  return act({ GraphSet: { graph: g.id, settings: f(structuredClone(now)) } });
};
const num = (v: string) => (v.trim() === "" || isNaN(+v) ? null : +v);

/** The open Format Graph window: 0.3.12 reuses it (switching to the page asked for) instead of stacking another;
 *  0.3.14 makes it follow the graph on screen (a user edited a graph they could no longer see) and close without one. */
let open1: { id: () => number; set: (id: number) => void; d: () => JSX.Element; tab: (p: string) => void } | null = null;
export const formatGraph = (g0: Graph, page = "sets") => {
  if (open1 && dialogs().includes(open1.d)) { open1.set(g0.id); return open1.tab(page); }
  const [tab, setTab] = createSignal(page), [gid, setGid] = createSignal(g0.id);
  const d = () => fmtWindow(g0, gid, setGid, tab, setTab, () => closeDialog(d));
  open1 = { id: gid, set: setGid, d, tab: setTab };
  openDialog(d);
};
const fmtWindow = (g0: Graph, gid: () => number, setGid: (id: number) => void, tab: () => string, setTab: (p: string) => void, close: () => void) => {
  createEffect(on(item, it => { if (it.s !== "graphs" || !out()?.project.graphs.some(x => x.id === it.id)) close(); else { setGid(it.id); if (tab() === "y2") setTab("y"); } }, { defer: true }));
  let last: Graph | undefined = g0;  // a deleted graph: keep showing it until the window closes
  const g = () => (last = out()!.project.graphs.find(x => x.id === gid()) ?? last)!, s = () => g().settings;
  const t = () => out()!.project.tables.find(x => x.id === g().table);
  const set = (f: (s: GraphSettings) => void) => setG(g(), x => { f(x); return x; });
  const setStyle = (k: number, patch: Partial<SetStyle>) => set(x => { while (x.sets.length <= k) x.sets.push({ ...DEF_SET }); x.sets[k] = { ...x.sets[k], ...patch }; });
  const st = (k: number) => ({ ...DEF_SET, ...(s().sets[k] ?? {}) });
  /** The colour each data set is drawn in (the engine's answer), and the scheme's colours to pick from. */
  const drawn = (k: number) => st(k).color || lastRender(g().id)?.colors?.[k] || OKABE_ITO[k % 8];
  const scheme = () => { const p = s().palette || "okabe"; return p.includes("#") ? p.split(",").map(c => c.trim()).filter(c => /^#[0-9a-fA-F]{6}$/.test(c)) : (!ORDERED.includes(p) && PALETTES.find(x => x[0] === p)?.[2]) || (lastRender(g().id)?.colors ?? OKABE_ITO); };
  const AxisPage = (p: { k: "x" | "y" | "y2" }) => {
    const a = () => s()[p.k] ?? { title: "", scale: "lin", auto: true, min: null, max: null, step: null, minor: false, grid: false }, put = (patch: Partial<Axis>) => set(x => { x[p.k] = { ...a(), ...patch } as Axis; });
    /** 0.3.11: a date X axis takes its limits as typed dates (read by the engine's own date rules). */
    const isDate = () => p.k === "x" && !!t()?.xFormat;
    const asDate = async (text: string, k: "min" | "max") => { const v = text.trim() ? await invoke<number | null>("date_number", { text }) : null; if (text.trim() && v === null) return toast(`“${text}” is not a date: type it as 2026-11-05 or 5 Nov 2026.`); put({ [k]: v }); };
    const auto = () => p.k === "y2" ? "the titles of the right-axis data sets" : `${p.k === "x" ? t()?.xTitle : t()?.yTitle}${(p.k === "x" ? t()?.xUnits : t()?.yUnits) ? ` (${p.k === "x" ? t()?.xUnits : t()?.yUnits})` : ""}`;
    const breaks = () => p.k !== "y2" && a().scale === "lin" && !s().polar && (["xy", "sheet"].includes(t()?.kind ?? "") || (p.k === "y" && ["column", "grouped", "contingency", "nested"].includes(t()?.kind ?? "") && !["heatmap", "percent"].includes(s().column)));
    return <div class="form">
      <label>Title</label><input value={a().title} placeholder={`From the table: ${auto()}`} onChange={e => put({ title: e.currentTarget.value })} />
      <label>Scale</label><Pick value={a().scale} set={v => put({ scale: v as Axis["scale"] })} options={[["lin", "Linear"], ["log", "Logarithmic (log10)"]]} />
      <label>Range</label><span class="inline"><Check label="Automatic" value={a().auto} set={v => put({ auto: v })} />
        <Show when={!a().auto && !isDate()}><span class="muted">from</span><input type="number" style={{ width: "90px" }} value={a().min ?? ""} onChange={e => put({ min: num(e.currentTarget.value) })} /><span class="muted">to</span><input type="number" style={{ width: "90px" }} value={a().max ?? ""} onChange={e => put({ max: num(e.currentTarget.value) })} /></Show>
        <Show when={!a().auto && isDate()}><span class="muted">from</span><input style={{ width: "110px" }} value={dateText(a().min, "iso")} onChange={e => asDate(e.currentTarget.value, "min")} /><span class="muted">to</span><input style={{ width: "110px" }} value={dateText(a().max, "iso")} onChange={e => asDate(e.currentTarget.value, "max")} /></Show></span>
      <Show when={isDate()}><label>Tick labels</label><Pick value={a().dates || "auto"} set={v => put({ dates: v })} options={[["auto", "Automatic (the year once, then months or days)"], ["daymonth", "Day and month (05 Nov)"], ["monthyear", "Month and year (Nov 2026)"], ["iso", "ISO (2026-11-05)"], ["week", "Week number (W45)"]]} /></Show>
      <Show when={isDate()}><label>Major ticks every</label><Pick value={a().dateStep || ""} set={v => put({ dateStep: v })} options={[["", "Automatic"], ["d1", "Day"], ["w1", "Week (Mondays)"], ["w2", "2 weeks"], ["m1", "Month"], ["m3", "3 months"], ["y1", "Year"]]} /></Show>
      <Show when={a().scale === "lin" && !isDate()}><label>Major ticks every</label><input type="number" placeholder="Automatic" value={a().step ?? ""} onChange={e => put({ step: num(e.currentTarget.value) && num(e.currentTarget.value)! > 0 ? num(e.currentTarget.value) : null })} /></Show>
      <label>Ticks and grid</label><span class="inline"><Check label="Minor ticks" value={a().minor} set={v => put({ minor: v })} /><Check label="Gridlines" value={a().grid} set={v => put({ grid: v })} /></span>
      <Show when={breaks()} fallback={<Show when={p.k !== "y2"}><label>Axis break</label><span class="muted">{a().scale !== "lin" ? "Breaks need a linear axis." : "Breaks are for the Y axis of XY, column, grouped and nested graphs, and the X axis of XY graphs."}</span></Show>}><label>Axis break</label><span class="inline"><span class="muted">leave out from</span><input type="number" style={{ width: "90px" }} value={a().breakFrom ?? ""} onChange={e => put({ breakFrom: num(e.currentTarget.value) })} />
        <span class="muted">to</span><input type="number" style={{ width: "90px" }} value={a().breakTo ?? ""} onChange={e => put({ breakTo: num(e.currentTarget.value) })} /><span class="muted">empty = no break</span></span>
        <Show when={a().breakFrom != null && a().breakTo != null}>
          <label>Break position</label><span class="inline"><span class="muted">{p.k === "x" ? "the part before the break takes" : "the part below the break takes"}</span>
            <input type="number" min="10" max="90" step="5" style={{ width: "70px" }} placeholder="69" value={a().breakRatio != null ? Math.round(a().breakRatio! * 100) : ""} onChange={e => { const v = num(e.currentTarget.value); put({ breakRatio: v === null ? null : Math.min(90, Math.max(10, v)) / 100 }); }} /><span class="muted">% of the axis</span></span>
          <label>Ticks beyond the break</label><span class="inline"><input type="number" style={{ width: "90px" }} placeholder="Automatic" value={a().breakStep ?? ""} onChange={e => { const v = num(e.currentTarget.value); put({ breakStep: v !== null && v > 0 ? v : null }); }} /><span class="muted">{p.k === "x" ? "after the break; before it, Major ticks every above" : "above the break; below it, Major ticks every above"}</span></span>
        </Show></Show>
    </div>;
  };
  /** 0.3.15 (#20, #23): lines belong to XY-like graphs; the others take fill and border colours and their own order. */
  const lined = () => ["xy", "survival", "sheet", "multi"].includes(t()?.kind ?? "xy");
  const ordered = () => ["column", "grouped", "parts", "nested"].includes(t()?.kind ?? "");
  const rows = () => { const n = t()?.sets.length ?? 0, ks = Array.from({ length: n }, (_, k) => k), o = s().order ?? [];
    return ordered() ? ks.sort((a, b) => (o.includes(a) ? o.indexOf(a) : o.length + a) - (o.includes(b) ? o.indexOf(b) : o.length + b)) : ks; };
  const move = (k: number, d: number) => { const r = rows(), i = r.indexOf(k), j = i + d; if (j < 0 || j >= r.length) return; [r[i], r[j]] = [r[j], r[i]]; set(x => { x.order = r; }); };
  /** 0.3.12: a vertical line at a typed X value or date, with an optional label. */
  const lineAt = async () => {
    const date = !!t()?.xFormat, at = prompt(date ? "Date of the line (2026-11-05 or 5 Nov 2026)" : "X value of the line", "");
    if (!at?.trim()) return;
    const x = date ? await invoke<number | null>("date_number", { text: at }) : num(at);
    if (x === null || x === undefined) return toast(`“${at}” is not ${date ? "a date" : "a number"}.`);
    const text = prompt("Label (optional)", "") ?? "";
    set(s => { s.notes = [...(s.notes ?? []), { kind: "vline", x, y: 0, x2: x, y2: 0, text, color: "#222222", size: 0, bold: false }]; });
  };
  return (
    <Dialog title={`Format Graph · ${g().name}`} side help="format" cancel="Close">
      <Tabs tabs={[["sets", "Data Sets"], ["x", "X Axis"], ["y", "Y Axis"], ...(s().sets.some(x => x?.right) ? [["y2", "Right Y Axis"] as [string, string]] : []), ["graph", "Graph"], ["notes", `Notes${s().notes?.length ? ` (${s().notes.length})` : ""}`]]} on={tab()} set={setTab} />
      <div class="fmtpage">
        <Show when={tab() === "sets"}>
          <div class="form">
            <Show when={t()?.kind === "survival"}><label>Confidence band</label><Check label="Shade the 95% CI of each curve" value={s().error === "ci"} set={v => set(x => { x.error = v ? "ci" : "none"; })} /></Show>
            <Show when={t()?.kind === "nested"}><label>Error bars</label><Pick value={s().error} set={v => set(x => { x.error = v; })} options={ERRORS} /></Show>
            <Show when={t()?.kind === "matrix"}>
              <label>Graph</label><Pick value={["contour", "heatmap", "surface", "wireframe"].includes(s().column) ? s().column : "contour"} set={v => set(x => { x.column = v; })} options={MATRIX} />
              <Show when={s().column === "contour" || !["heatmap", "surface", "wireframe"].includes(s().column)}><label>Contour levels</label><span class="inline"><input type="number" min="0" max="60" style={{ width: "70px" }} value={s().levels || ""} placeholder="12" onChange={e => set(x => { x.levels = Math.max(0, Math.round(+e.currentTarget.value)); })} /><span class="muted">empty = 12</span></span></Show>
              <Show when={s().column === "surface" || s().column === "wireframe"}><label>View</label><span class="inline"><span class="muted">tilt</span><input type="number" min="-90" max="90" style={{ width: "70px" }} value={s().elev ?? 28} onChange={e => set(x => { x.elev = +e.currentTarget.value; })} />
                <span class="muted">turn</span><input type="number" min="-180" max="180" style={{ width: "70px" }} value={s().azim ?? -60} onChange={e => set(x => { x.azim = +e.currentTarget.value; })} /><span class="muted">degrees</span></span></Show>
              <label>Colours</label><Pick value={["viridis", "cividis", "magma", "grey"].includes(s().palette) ? s().palette : "viridis"} set={v => set(x => { x.palette = v; })} options={[["viridis", "Viridis"], ["cividis", "Cividis (colour-blind safe)"], ["magma", "Magma"], ["grey", "Greys"]]} />
            </Show>
            <Show when={["xy", "sheet"].includes(t()?.kind ?? "")}><label>Graph</label><span class="inline"><Pick value={s().column === "waterfall" ? "waterfall" : "scatter"} set={v => set(x => { x.column = v; })} options={[["scatter", "Points and lines"], ["waterfall", "Waterfall"]]} />
              <Show when={s().column === "waterfall"}><span class="muted">lift</span><input type="number" min="0" step="any" style={{ width: "80px" }} title="Distance between the curves in Y units; 0 = automatic" value={s().offset ?? 0} onChange={e => set(x => { x.offset = Math.max(0, +e.currentTarget.value || 0); })} /></Show></span></Show>
            <Show when={t()?.kind === "multi"}><label>Graph</label><span class="inline"><Pick value={["ternary", "bubble", "scatter3d", "vector"].includes(s().column) ? s().column : "scatter"} set={v => set(x => { x.column = v; })} options={[["scatter", "Scatter (first variable on X)"], ["ternary", "Ternary (first three variables)"], ["bubble", "Bubble (X, Y, size, colour)"], ["scatter3d", "3D scatter (X, Y, Z, colour)"], ["vector", "Vector field (X, Y, U, V)"]]} />
              <Show when={s().column === "scatter3d"}><span class="muted">tilt</span><input type="number" min="-90" max="90" style={{ width: "60px" }} value={s().elev ?? 28} onChange={e => set(x => { x.elev = +e.currentTarget.value; })} /><span class="muted">turn</span><input type="number" min="-180" max="180" style={{ width: "60px" }} value={s().azim ?? -60} onChange={e => set(x => { x.azim = +e.currentTarget.value; })} /></Show></span></Show>
            <Show when={["xy", "sheet"].includes(t()?.kind ?? "")}><label>Axes</label><Check label="Polar: X is the angle in degrees, Y the radius" value={!!s().polar} set={v => set(x => { x.polar = v; })} /></Show>
            <Show when={!["xy", "multi", "survival", "nested", "sheet", "matrix"].includes(t()?.kind ?? "")}><label>Graph</label><span class="inline"><Pick value={s().column || (t()?.kind === "column" ? "scatter" : t()?.kind === "parts" ? "pie" : "bars")} set={v => set(x => { x.column = v; })} options={t()?.kind === "parts" ? [["pie", "Pie"], ["donut", "Donut"], ["percent", "Bars stacked to 100%"]] : t()?.kind !== "column"
                ? [["bars", "Grouped bars"], ["stacked", "Stacked bars"], ["percent", "Stacked to 100%"], ["scatter", "Grouped dots"], ["lines", "Lines (interaction plot)"], ["heatmap", "Heat map"], ["radar", "Radar"]] : [["scatter", "Scatter dot plot"], ["bars", "Bars"], ["box", "Box and whiskers"], ["violin", "Violin"], ["mean", "Mean ± error only"], ["paired", "Before–after"]]} />
              <Check label="Show each value" value={s().points === "each"} set={v => set(x => { x.points = v ? "each" : "mean"; })} /></span>
              <label>Error bars</label><Pick value={s().error} set={v => set(x => { x.error = v; })} options={ERRORS} /></Show>
            <Show when={t()?.kind === "xy"}><label>Show</label><Pick value={s().points} set={v => set(x => { x.points = v; })} options={[["mean", "Mean with error bars"], ["each", "Each replicate"]]} /></Show>
            <label>Colours</label><span class="inline"><Pick value={s().palette.includes("#") ? "own" : s().palette || "okabe"} set={v => v !== "own" && set(x => { x.palette = v; x.sets = x.sets.map(q => ({ ...q, color: "" })); })} options={[...PALETTES.map(p => [p[0], paletteName(p)] as [string, string]), ...(s().palette.includes("#") ? [["own", "Your colours"] as [string, string]] : [])]} />
              <button class="btn sm" onClick={() => import("./tools").then(m => m.paletteDialog())}>Colour schemes…</button></span>
            <Show when={s().points === "mean" && (t()?.kind === "xy" || t()?.kind === "sheet")}>
              <label>Error bars</label><span class="inline"><Pick value={s().error} set={v => set(x => { x.error = v; })} options={ERRORS} />
                <Pick value={s().errorDir} set={v => set(x => { x.errorDir = v; })} options={[["both", "Both directions"], ["up", "Above only"], ["down", "Below only"]]} />
                <span class="muted">caps</span><input type="number" min="0" max="12" step="0.5" style={{ width: "60px" }} value={s().cap} onChange={e => set(x => { x.cap = Math.max(0, +e.currentTarget.value); })} /></span>
            </Show>
            <Show when={t()?.kind === "xy"}><label>Connect the points</label><Check label="Line through the means of every data set" value={s().line} set={v => set(x => { x.line = v; })} /></Show>
          </div>
          <div class="setwrap"><table class="tbl setfmt"><thead><tr><th /><th>Data set</th><Show when={ordered()}><th title="The order along the graph; the table keeps its own">Order</th></Show><th>Show</th><th>Symbol</th><th>Colour</th><th>Size</th><th>Filled</th>
            <Show when={lined()} fallback={<><th title="The fill of bars, boxes and violins (empty: the data set's colour)">Fill</th><th title="Their border (empty: the data set's colour)">Border</th></>}><th title="Connect the points of this data set with a line">Connect</th><th title="Thickness of that line, in points">Line width</th></Show>
            <Show when={t()?.kind === "xy"}><th title="Draw against a second Y axis on the right">Right Y</th></Show></tr></thead><tbody>
            <For each={rows()}>{k0 => { const k = () => k0, d = () => t()!.sets[k0], at = () => rows().indexOf(k0); return <tr classList={{ dimset: !!t() && isEmpty(t()!, k()) }}>
              <td><b>{letter(k())}</b></td><td>{d()?.title || `Data set ${letter(k())}`}{t() && isEmpty(t()!, k()) ? " (empty)" : ""}</td>
              <Show when={ordered()}><td class="nowrap"><button class="btn sm" title="Earlier on the graph" disabled={at() === 0} onClick={() => move(k0, -1)}>▲</button><button class="btn sm" title="Later on the graph" disabled={at() === rows().length - 1} onClick={() => move(k0, 1)}>▼</button></td></Show>
              <td><input type="checkbox" checked={st(k()).show} onChange={e => setStyle(k(), { show: e.currentTarget.checked })} /></td>
              <td><Pick value={st(k()).symbol || SYMBOLS[k() % 8][0]} set={v => setStyle(k(), { symbol: v })} options={SYMBOLS} /></td>
              <td><span class="inline"><input type="color" value={drawn(k())} onChange={e => setStyle(k(), { color: e.currentTarget.value })} />
                <span class="swset"><For each={scheme()}>{c => <button style={{ background: c }} title={c} onClick={() => setStyle(k(), { color: c })} />}</For></span></span></td>
              <td><input type="number" min="1" max="20" style={{ width: "54px" }} value={st(k()).size} onChange={e => setStyle(k(), { size: +e.currentTarget.value })} /></td>
              <td><input type="checkbox" checked={st(k()).filled} onChange={e => setStyle(k(), { filled: e.currentTarget.checked })} /></td>
              <Show when={lined()} fallback={<><td><input type="color" value={st(k()).fill || drawn(k())} title="Fill" onChange={e => setStyle(k(), { fill: e.currentTarget.value })} /></td>
                <td><input type="color" value={st(k()).edge || drawn(k())} title="Border" onChange={e => setStyle(k(), { edge: e.currentTarget.value })} /></td></>}>
              <td><Pick value={st(k()).line === null ? "" : st(k()).line ? "1" : "0"} set={v => setStyle(k(), { line: v === "" ? null : v === "1" })} options={[["", "As the graph"], ["1", "Line"], ["0", "No line"]]} /></td>
              <td><input type="number" min="0.25" max="6" step="0.25" style={{ width: "58px" }} value={st(k()).width} onChange={e => setStyle(k(), { width: +e.currentTarget.value })} /></td></Show>
              <Show when={t()?.kind === "xy"}><td><input type="checkbox" checked={!!st(k()).right} onChange={e => setStyle(k(), { right: e.currentTarget.checked })} /></td></Show>
            </tr>; }}</For>
          </tbody></table></div>
          <p class="muted">Order changes this graph only; the table keeps its own. Empty colours follow the colour scheme (Okabe-Ito by default, readable with colour-blindness); other empty settings follow the data set's position.</p>
        </Show>
        <Show when={tab() === "x"}><AxisPage k="x" /></Show>
        <Show when={tab() === "y"}><AxisPage k="y" /></Show>
        <Show when={tab() === "y2"}><AxisPage k="y2" /></Show>
        <Show when={tab() === "notes"}>
          <p class="inline"><For each={[["text", "Text"], ["arrow", "Arrow"], ["line", "Line"], ["box", "Box"]]}>{([k, l]) => <button class="btn sm" onClick={() => import("./graph").then(m => m.annotate(k))}>＋ {l}</button>}</For>
            <button class="btn sm" title="A dashed vertical line across the graph at an X value (on a date axis: a date)" onClick={lineAt}>＋ Line at {t()?.xFormat ? "a date" : "an X value"}…</button></p>
          <Show when={s().notes?.length} fallback={<p class="muted">No notes yet. Add one with the buttons above (then click or drag on the graph), or Format › Annotate.</p>}>
            <table class="tbl setfmt"><thead><tr><th>Kind</th><th>Text</th><th>X</th><th>Y</th><th>To X</th><th>To Y</th><th>Colour</th><th>Size</th><th>Bold</th><th /></tr></thead><tbody>
              <For each={s().notes}>{(n, i) => { const put = (patch: Partial<Note>) => set(x => { x.notes[i()] = { ...x.notes[i()], ...patch }; }); const N = (q: { k: "x" | "y" | "x2" | "y2" }) =>
                <input type="number" style={{ width: "70px" }} value={+n[q.k].toPrecision(5)} onChange={e => { const v = num(e.currentTarget.value); if (v !== null) put({ [q.k]: v }); }} />;
                const vl = n.kind === "vline", D = () => <input style={{ width: "96px" }} value={dateText(n.x, "iso")} onChange={async e => { const v = await invoke<number | null>("date_number", { text: e.currentTarget.value }); if (v !== null) put({ x: v, x2: v }); }} />;
                return <tr><td>{vl ? "line at X" : n.kind}</td><td><input value={n.text} onChange={e => put({ text: e.currentTarget.value })} /></td><td>{vl && t()?.xFormat ? <D /> : <N k="x" />}</td><td>{!vl && <N k="y" />}</td>
                  <td>{n.kind !== "text" && !vl && <N k="x2" />}</td><td>{n.kind !== "text" && !vl && <N k="y2" />}</td><td><input type="color" value={n.color || "#222222"} onChange={e => put({ color: e.currentTarget.value })} /></td>
                  <td><input type="number" min="0" max="48" style={{ width: "54px" }} value={n.size} title="0 = the graph's size" onChange={e => put({ size: +e.currentTarget.value })} /></td>
                  <td><input type="checkbox" checked={n.bold} onChange={e => put({ bold: e.currentTarget.checked })} /></td><td><button class="btn sm" onClick={() => set(x => { x.notes.splice(i(), 1); })}>Delete</button></td></tr>; }}</For>
            </tbody></table>
          </Show>
          <p class="muted">Positions are in the units of the axes, so notes stay on their data when the graph is resized or exported.</p>
        </Show>
        <Show when={tab() === "graph"}>
          <div class="form">
            <label>Title</label><span class="inline"><input value={s().title} placeholder="No title" onChange={e => set(x => { x.title = e.currentTarget.value; })} /><Check label="Show" value={s().showTitle} set={v => set(x => { x.showTitle = v; })} /></span>
            <label>Size (mm)</label><span class="inline"><input type="number" min="10" max="1000" style={{ width: "80px" }} value={s().width} onChange={e => set(x => { x.width = +e.currentTarget.value; })} /><span class="muted">×</span>
              <input type="number" min="10" max="1000" style={{ width: "80px" }} value={s().height} onChange={e => set(x => { x.height = +e.currentTarget.value; })} />
              <Pick value="" set={v => { const z = SIZES.find(q => q[0] === v); if (z) set(x => { x.width = z[1]; x.height = z[2]; }); }} options={[["", "Journal sizes…"], ...SIZES.map(z => [z[0], z[0]] as [string, string])]} /></span>
            <label>Font</label><span class="inline"><Pick value={s().font} set={v => set(x => { x.font = v; })} options={FONTS} /><input type="number" min="5" max="36" step="0.5" style={{ width: "64px" }} value={s().fontSize} onChange={e => set(x => { x.fontSize = +e.currentTarget.value; })} /><span class="muted">pt</span>
              <Check label="Bold axis titles" value={s().boldTitles} set={v => set(x => { x.boldTitles = v; })} /></span>
            <label>Axes</label><Pick value={s().style} set={v => set(x => { x.style = v; })} options={[["prism", "Open (left and bottom, ticks out)"], ["frame", "Framed box (ticks in)"]]} />
            <label>Legend</label><span class="inline"><Check label="Show" value={t()?.kind === "column" ? !!s().legend.groups : s().legend.show} set={v => set(x => { if (t()?.kind === "column") { x.legend.groups = v; if (v) x.legend.show = true; } else x.legend.show = v; })} />
              <Pick value={s().legend.loc} set={v => set(x => { x.legend.loc = v; })} options={[["best", "Best place"], ["upper left", "Top left"], ["upper right", "Top right"], ["lower left", "Bottom left"], ["lower right", "Bottom right"], ["outside", "Outside, right"]]} /></span>
          </div>
        </Show>
      </div>
    </Dialog>
  );
};
