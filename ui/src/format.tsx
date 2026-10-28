// Format Graph: data sets, axes and the whole graph. Every change applies at once (with undo),
// so the graph behind the dialog shows it.
import { For, Show, createSignal } from "solid-js";
import { Graph, GraphSettings, Axis, SetStyle, Note, letter } from "./api";
import { act, out, openDialog } from "./store";
import { Dialog, Tabs, Pick, Check } from "./ui";
import { PALETTES } from "./tools";

export const OKABE_ITO = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000"];
export const SYMBOLS: [string, string][] = [["circle", "● Circle"], ["square", "■ Square"], ["triangle", "▲ Triangle"], ["down", "▼ Down triangle"], ["diamond", "◆ Diamond"], ["pentagon", "⬟ Pentagon"], ["hexagon", "⬢ Hexagon"], ["star", "★ Star"], ["none", "No symbol"]];
export const FONTS = ["Arial", "Helvetica", "Calibri", "Segoe UI", "Verdana", "Times New Roman", "Georgia", "Cambria"];
export const ERRORS: [string, string][] = [["sd", "Mean ± SD"], ["sem", "Mean ± SEM"], ["ci", "Mean ± 95% CI"], ["range", "Mean and range"], ["none", "Mean only"]];
/** Journal column widths in mm. */
export const SIZES: [string, number, number][] = [["Single column (85 mm)", 85, 64], ["1.5 columns (114 mm)", 114, 80], ["Double column (174 mm)", 174, 110], ["Square (80 mm)", 80, 80], ["Slide (240 × 135 mm)", 240, 135]];

const DEF_SET: SetStyle = { show: true, color: "", symbol: "", size: 6, filled: true, line: null, width: 1, right: false };
/** Applies a change to the graph's settings. */
export const setG = (g: Graph, f: (s: GraphSettings) => GraphSettings) => {
  const now = out()!.project.graphs.find(x => x.id === g.id)?.settings ?? g.settings;
  return act({ GraphSet: { graph: g.id, settings: f(structuredClone(now)) } });
};
const num = (v: string) => (v.trim() === "" || isNaN(+v) ? null : +v);

export const formatGraph = (g0: Graph, page = "sets") => openDialog(() => {
  const [tab, setTab] = createSignal(page);
  const g = () => out()!.project.graphs.find(x => x.id === g0.id) ?? g0, s = () => g().settings;
  const t = () => out()!.project.tables.find(x => x.id === g().table);
  const set = (f: (s: GraphSettings) => void) => setG(g(), x => { f(x); return x; });
  const setStyle = (k: number, patch: Partial<SetStyle>) => set(x => { while (x.sets.length <= k) x.sets.push({ ...DEF_SET }); x.sets[k] = { ...x.sets[k], ...patch }; });
  const st = (k: number) => ({ ...DEF_SET, ...(s().sets[k] ?? {}) });
  const AxisPage = (p: { k: "x" | "y" | "y2" }) => {
    const a = () => s()[p.k] ?? { title: "", scale: "lin", auto: true, min: null, max: null, step: null, minor: false, grid: false }, put = (patch: Partial<Axis>) => set(x => { x[p.k] = { ...a(), ...patch } as Axis; });
    const auto = () => p.k === "y2" ? "the titles of the right-axis data sets" : `${p.k === "x" ? t()?.xTitle : t()?.yTitle}${(p.k === "x" ? t()?.xUnits : t()?.yUnits) ? ` (${p.k === "x" ? t()?.xUnits : t()?.yUnits})` : ""}`;
    return <div class="form">
      <label>Title</label><input value={a().title} placeholder={`From the table: ${auto()}`} onChange={e => put({ title: e.currentTarget.value })} />
      <label>Scale</label><Pick value={a().scale} set={v => put({ scale: v as Axis["scale"] })} options={[["lin", "Linear"], ["log", "Logarithmic (log10)"]]} />
      <label>Range</label><span class="inline"><Check label="Automatic" value={a().auto} set={v => put({ auto: v })} />
        <Show when={!a().auto}><span class="muted">from</span><input type="number" style={{ width: "90px" }} value={a().min ?? ""} onChange={e => put({ min: num(e.currentTarget.value) })} /><span class="muted">to</span><input type="number" style={{ width: "90px" }} value={a().max ?? ""} onChange={e => put({ max: num(e.currentTarget.value) })} /></Show></span>
      <Show when={a().scale === "lin"}><label>Major ticks every</label><input type="number" placeholder="Automatic" value={a().step ?? ""} onChange={e => put({ step: num(e.currentTarget.value) && num(e.currentTarget.value)! > 0 ? num(e.currentTarget.value) : null })} /></Show>
      <label>Ticks and grid</label><span class="inline"><Check label="Minor ticks" value={a().minor} set={v => put({ minor: v })} /><Check label="Gridlines" value={a().grid} set={v => put({ grid: v })} /></span>
      <Show when={p.k !== "y2" && t()?.kind === "xy" && a().scale === "lin"}><label>Axis break</label><span class="inline"><span class="muted">leave out from</span><input type="number" style={{ width: "90px" }} value={a().breakFrom ?? ""} onChange={e => put({ breakFrom: num(e.currentTarget.value) })} />
        <span class="muted">to</span><input type="number" style={{ width: "90px" }} value={a().breakTo ?? ""} onChange={e => put({ breakTo: num(e.currentTarget.value) })} /><span class="muted">empty = no break</span></span></Show>
    </div>;
  };
  return (
    <Dialog title={`Format Graph · ${g().name}`} side help="format" cancel="Close">
      <Tabs tabs={[["sets", "Data Sets"], ["x", "X Axis"], ["y", "Y Axis"], ...(s().sets.some(x => x?.right) ? [["y2", "Right Y Axis"] as [string, string]] : []), ["graph", "Graph"], ["notes", `Notes${s().notes?.length ? ` (${s().notes.length})` : ""}`]]} on={tab()} set={setTab} />
      <div class="fmtpage">
        <Show when={tab() === "sets"}>
          <div class="form">
            <Show when={t()?.kind === "survival"}><label>Confidence band</label><Check label="Shade the 95% CI of each curve" value={s().error === "ci"} set={v => set(x => { x.error = v ? "ci" : "none"; })} /></Show>
            <Show when={t()?.kind === "nested"}><label>Error bars</label><Pick value={s().error} set={v => set(x => { x.error = v; })} options={ERRORS} /></Show>
            <Show when={t()?.kind !== "xy" && t()?.kind !== "multi" && t()?.kind !== "survival" && t()?.kind !== "nested"}><label>Graph</label><span class="inline"><Pick value={s().column || (t()?.kind === "column" ? "scatter" : t()?.kind === "parts" ? "pie" : "bars")} set={v => set(x => { x.column = v; })} options={t()?.kind === "parts" ? [["pie", "Pie"], ["donut", "Donut"], ["percent", "Bars stacked to 100%"]] : t()?.kind !== "column"
                ? [["bars", "Grouped bars"], ["stacked", "Stacked bars"], ["percent", "Stacked to 100%"], ["scatter", "Grouped dots"], ["lines", "Lines (interaction plot)"], ["heatmap", "Heat map"]] : [["scatter", "Scatter dot plot"], ["bars", "Bars"], ["box", "Box and whiskers"], ["violin", "Violin"], ["mean", "Mean ± error only"], ["paired", "Before–after"]]} />
              <Check label="Show each value" value={s().points === "each"} set={v => set(x => { x.points = v ? "each" : "mean"; })} /></span>
              <label>Error bars</label><Pick value={s().error} set={v => set(x => { x.error = v; })} options={ERRORS} /></Show>
            <Show when={t()?.kind === "xy"}><label>Show</label><Pick value={s().points} set={v => set(x => { x.points = v; })} options={[["mean", "Mean with error bars"], ["each", "Each replicate"]]} /></Show>
            <label>Colours</label><span class="inline"><Pick value={s().palette.includes("#") ? "own" : s().palette || "okabe"} set={v => v !== "own" && set(x => { x.palette = v; x.sets = x.sets.map(q => ({ ...q, color: "" })); })} options={[...PALETTES.map(p => [p[0], p[1]] as [string, string]), ...(s().palette.includes("#") ? [["own", "Your colours"] as [string, string]] : [])]} />
              <button class="btn sm" onClick={() => import("./tools").then(m => m.paletteDialog())}>Colour schemes…</button></span>
            <Show when={s().points === "mean" && t()?.kind === "xy"}>
              <label>Error bars</label><span class="inline"><Pick value={s().error} set={v => set(x => { x.error = v; })} options={ERRORS} />
                <Pick value={s().errorDir} set={v => set(x => { x.errorDir = v; })} options={[["both", "Both directions"], ["up", "Above only"], ["down", "Below only"]]} />
                <span class="muted">caps</span><input type="number" min="0" max="12" step="0.5" style={{ width: "60px" }} value={s().cap} onChange={e => set(x => { x.cap = Math.max(0, +e.currentTarget.value); })} /></span>
            </Show>
            <Show when={t()?.kind === "xy"}><label>Connect the points</label><Check label="Line through the means of every data set" value={s().line} set={v => set(x => { x.line = v; })} /></Show>
          </div>
          <div class="setwrap"><table class="tbl setfmt"><thead><tr><th /><th>Data set</th><th>Show</th><th>Symbol</th><th>Colour</th><th>Size</th><th>Filled</th><th>Line</th><th>Width</th><Show when={t()?.kind === "xy"}><th title="Draw against a second Y axis on the right">Right Y</th></Show></tr></thead><tbody>
            <For each={t()?.sets ?? []}>{(d, k) => <tr>
              <td><b>{letter(k())}</b></td><td>{d.title || `Data set ${letter(k())}`}</td>
              <td><input type="checkbox" checked={st(k()).show} onChange={e => setStyle(k(), { show: e.currentTarget.checked })} /></td>
              <td><Pick value={st(k()).symbol || SYMBOLS[k() % 8][0]} set={v => setStyle(k(), { symbol: v })} options={SYMBOLS} /></td>
              <td><span class="inline"><input type="color" value={st(k()).color || OKABE_ITO[k() % 8]} onChange={e => setStyle(k(), { color: e.currentTarget.value })} />
                <span class="swset"><For each={OKABE_ITO}>{c => <button style={{ background: c }} title={c} onClick={() => setStyle(k(), { color: c })} />}</For></span></span></td>
              <td><input type="number" min="1" max="20" style={{ width: "54px" }} value={st(k()).size} onChange={e => setStyle(k(), { size: +e.currentTarget.value })} /></td>
              <td><input type="checkbox" checked={st(k()).filled} onChange={e => setStyle(k(), { filled: e.currentTarget.checked })} /></td>
              <td><Pick value={st(k()).line === null ? "" : st(k()).line ? "1" : "0"} set={v => setStyle(k(), { line: v === "" ? null : v === "1" })} options={[["", "As the graph"], ["1", "Line"], ["0", "No line"]]} /></td>
              <td><input type="number" min="0.25" max="6" step="0.25" style={{ width: "58px" }} value={st(k()).width} onChange={e => setStyle(k(), { width: +e.currentTarget.value })} /></td>
              <Show when={t()?.kind === "xy"}><td><input type="checkbox" checked={!!st(k()).right} onChange={e => setStyle(k(), { right: e.currentTarget.checked })} /></td></Show>
            </tr>}</For>
          </tbody></table></div>
          <p class="muted">Empty colours follow the colour scheme (Okabe-Ito by default, readable with colour-blindness); other empty settings follow the data set's position.</p>
        </Show>
        <Show when={tab() === "x"}><AxisPage k="x" /></Show>
        <Show when={tab() === "y"}><AxisPage k="y" /></Show>
        <Show when={tab() === "y2"}><AxisPage k="y2" /></Show>
        <Show when={tab() === "notes"}>
          <p class="inline"><For each={[["text", "Text"], ["arrow", "Arrow"], ["line", "Line"], ["box", "Box"]]}>{([k, l]) => <button class="btn sm" onClick={() => import("./graph").then(m => m.annotate(k))}>＋ {l}</button>}</For></p>
          <Show when={s().notes?.length} fallback={<p class="muted">No notes yet. Add one with the buttons above (then click or drag on the graph), or Format › Annotate.</p>}>
            <table class="tbl setfmt"><thead><tr><th>Kind</th><th>Text</th><th>X</th><th>Y</th><th>To X</th><th>To Y</th><th>Colour</th><th>Size</th><th>Bold</th><th /></tr></thead><tbody>
              <For each={s().notes}>{(n, i) => { const put = (patch: Partial<Note>) => set(x => { x.notes[i()] = { ...x.notes[i()], ...patch }; }); const N = (q: { k: "x" | "y" | "x2" | "y2" }) =>
                <input type="number" style={{ width: "70px" }} value={+n[q.k].toPrecision(5)} onChange={e => { const v = num(e.currentTarget.value); if (v !== null) put({ [q.k]: v }); }} />;
                return <tr><td>{n.kind}</td><td><input value={n.text} onChange={e => put({ text: e.currentTarget.value })} /></td><td><N k="x" /></td><td><N k="y" /></td>
                  <td>{n.kind !== "text" && <N k="x2" />}</td><td>{n.kind !== "text" && <N k="y2" />}</td><td><input type="color" value={n.color || "#222222"} onChange={e => put({ color: e.currentTarget.value })} /></td>
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
            <label>Legend</label><span class="inline"><Check label="Show" value={s().legend.show} set={v => set(x => { x.legend.show = v; })} />
              <Pick value={s().legend.loc} set={v => set(x => { x.legend.loc = v; })} options={[["best", "Best place"], ["upper left", "Top left"], ["upper right", "Top right"], ["lower left", "Bottom left"], ["lower right", "Bottom right"], ["outside", "Outside, right"]]} /></span>
          </div>
        </Show>
      </div>
    </Dialog>
  );
});
