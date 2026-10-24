// File › Print: settings on the left, a live preview on the right (Datum Plan's pattern). Graphs
// print at their real size (or fitted) one per page; data tables and the Info sheet print as
// flowing pages with the header and footer repeated. "Save as PDF" in the print dialog makes a PDF.
import { For, Show, Switch, Match, JSX, createSignal, createResource, onCleanup } from "solid-js";
import { Portal } from "solid-js/web";
import { createStore } from "solid-js/store";
import { Render, Table, spans, letter, num } from "./api";
import { out, opts, P, act, item, graph, table, toast, call } from "./store";
import { GraphImg, lastRender } from "./graph";
import { Pick, Check, Seg } from "./ui";

/** Paper sizes in millimetres (portrait). */
export const PAPERS: [string, number, number][] = [["A4", 210, 297], ["A3", 297, 420], ["A5", 148, 210], ["Letter", 215.9, 279.4], ["Legal", 215.9, 355.6], ["Tabloid", 279.4, 431.8]];
const MM = 96 / 25.4;
type Slots = [string, string, string];
export type PageSetup = { paper: string; landscape: boolean; margins: [number, number, number, number]; fit: boolean; which: "this" | "all"; caption: boolean; header: Slots; footer: Slots };
export const CODES: [string, string][] = [["&[Page]", "Page number"], ["&[Pages]", "Total pages"], ["&[Date]", "Today's date"], ["&[Project]", "Project name"], ["&[Item]", "Graph or table name"],
  ["&[Title]", "Info: title"], ["&[Researcher]", "Info: researcher"], ["&[Company]", "Organisation (Options)"], ["&[Logo]", "Logo (Options)"]];
const defaults = (): PageSetup => ({
  paper: opts().paper || "A4", landscape: !!opts().landscape, margins: [15, 15, 15, 15], fit: false, which: "this", caption: true,
  header: ["&[Logo]", "&[Project]", "&[Date]"], footer: ["&[Researcher]", "Page &[Page] of &[Pages]", "&[Company]"],
});
const [ps, setPs] = createStore<PageSetup>(defaults());
let loadedFor = "";
const load = () => { const k = `${out()?.path}`; if (k === loadedFor) return; loadedFor = k; setPs({ ...defaults(), ...((P().ui?.page ?? {}) as Partial<PageSetup>) }); };
const save = () => { if (JSON.stringify(P().ui?.page ?? {}) !== JSON.stringify(ps)) act({ Ui: { key: "page", value: JSON.parse(JSON.stringify(ps)) } }, true); };

const codes = (t: string, page: number, pages: number, name: string) => {
  const i = P().info, d = new Date();
  return t.replace(/&\[Page\]/g, String(page)).replace(/&\[Pages\]/g, String(pages)).replace(/&\[Date\]/g, d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }))
    .replace(/&\[Project\]/g, P().name).replace(/&\[Item\]/g, name).replace(/&\[Title\]/g, i.title).replace(/&\[Researcher\]/g, i.researcher).replace(/&\[Company\]/g, opts().company || i.organisation);
};
const Slot = (p: { t: string; page: number; pages: number; name: string; h: number }) => (
  <For each={p.t.split(/(&\[Logo\])/)}>{part => part === "&[Logo]" ? (opts().logo && <img src={opts().logo} style={{ "max-height": `${p.h}px`, "max-width": "45%" }} />) : <span style={{ "white-space": "pre-line" }}>{codes(part, p.page, p.pages, p.name)}</span>}</For>
);
const HeadFoot = (p: { k: "header" | "footer"; page: number; pages: number; name: string }) => (
  <div class={p.k === "header" ? "phead" : "pfoot"}><For each={[0, 1, 2]}>{i => <div class={`ps${i}`}><Slot t={ps[p.k][i]} page={p.page} pages={p.pages} name={p.name} h={30} /></div>}</For></div>
);

/** What File › Print prints: the open graph(s), the open table, or the Info sheet. */
const kind = () => (item().s === "graphs" ? "graph" : item().s === "data" ? "table" : "info");
const paper = () => { const p = PAPERS.find(x => x[0] === ps.paper) ?? PAPERS[0]; return ps.landscape ? [p[2], p[1]] : [p[1], p[2]]; };
const graphIds = () => (ps.which === "all" ? P().graphs.map(g => g.id) : graph() ? [graph()!.id] : []);

/** One graph page at real size, or scaled to fit the space between header and footer. */
const GraphPage = (p: { id: number; r: Render; n: number; pages: number }) => {
  const [pw, ph] = paper(), g = () => P().graphs.find(x => x.id === p.id);
  const W = () => (pw - ps.margins[1] - ps.margins[3]) * MM, H = () => (ph - ps.margins[0] - ps.margins[2]) * MM - 90;
  const k = () => { const k0 = 96 / 72, fit = Math.min(W() / (p.r.w * k0), H() / (p.r.h * k0)); return k0 * (ps.fit ? fit : Math.min(1, fit)); };
  return (
    <div class="ppage" style={{ width: `${pw * MM}px`, height: `${ph * MM}px` }}>
      <div class="pin" style={{ left: `${ps.margins[3] * MM}px`, top: `${ps.margins[0] * MM}px`, width: `${W()}px`, height: `${(ph - ps.margins[0] - ps.margins[2]) * MM}px` }}>
        <HeadFoot k="header" page={p.n} pages={p.pages} name={g()?.name ?? ""} />
        <div class="pgraph"><GraphImg r={p.r} scale={k()} /><Show when={ps.caption}><p class="pcap"><b>{g()?.name}</b>{caption(p.id)}</p></Show></div>
        <HeadFoot k="footer" page={p.n} pages={p.pages} name={g()?.name ?? ""} />
      </div>
    </div>
  );
};
/** A figure-legend line: what the points and bars show. */
const caption = (id: number) => {
  const g = P().graphs.find(x => x.id === id), t = P().tables.find(x => x.id === g?.table);
  if (!g || !t) return "";
  const e = { sd: "mean ± SD", sem: "mean ± SEM", ci: "mean ± 95% CI", range: "mean and range", none: "mean" }[g.settings.error] ?? "mean";
  const reps = t.sets.filter(s => s.entry === "rep").map(s => s.reps);
  return `. ${g.settings.points === "each" ? "Each replicate is shown" : `Points show the ${e}`}${reps.length ? `, ${Math.max(...reps) > 1 ? `n = ${[...new Set(reps)].join("–")} replicates per point` : "single values"}` : ""}.`;
};

/** A data table for printing (flowing pages). */
const TablePrint = (p: { t: Table }) => (
  <table class="ptable"><thead>
    <tr><th rowspan="2">Row</th><th rowspan="2">{p.t.xTitle}{p.t.xUnits ? ` (${p.t.xUnits})` : ""}</th><For each={p.t.sets}>{(s, k) => <th colspan={spans(p.t)[k()][1]}>{letter(k())}: {s.title}</th>}</For></tr>
    <tr><For each={p.t.sets}>{s => <For each={Array.from({ length: s.entry === "rep" ? s.reps : 3 }, (_, j) => j)}>{j => <th>{s.entry === "rep" ? `Y${j + 1}` : (s.entry === "msn" ? ["Mean", "SD", "N"] : ["Mean", "SEM", "N"])[j]}</th>}</For>}</For></tr>
  </thead><tbody>
    <For each={Array.from({ length: p.t.rows }, (_, r) => r).filter(r => p.t.cols.some(c => c[r] !== null) || p.t.rowTitles[r])}>{r => <tr><td>{p.t.rowTitles[r] || r + 1}</td>
      <For each={p.t.cols}>{(c, k) => <td class="r" classList={{ ex: p.t.excluded.some(([a, b]) => a === r && b === k()) }}>{num(c[r], opts().decimals)}</td>}</For></tr>}</For>
  </tbody></table>
);
const InfoPrint = () => (
  <div class="pinfo"><h1>{P().info.title || P().name}</h1>
    <For each={[["Experiment", P().info.experiment], ["Researcher", P().info.researcher], ["Organisation", P().info.organisation], ["Date", P().info.date]].filter(x => x[1])}>{([l, v]) => <p><b>{l}: </b>{v}</p>}</For>
    <Show when={P().info.notes}><h3>Notes</h3><p style={{ "white-space": "pre-wrap" }}>{P().info.notes}</p></Show>
  </div>
);
/** Flowing document: the header and footer repeat through thead/tfoot; page numbers come from @page. */
const Flow = (p: { children: JSX.Element; name: string }) => (
  <table class="pflow"><thead><tr><td><HeadFoot k="header" page={1} pages={1} name={p.name} /></td></tr></thead>
    <tbody><tr><td>{p.children}</td></tr></tbody><tfoot><tr><td><HeadFoot k="footer" page={1} pages={1} name={p.name} /></td></tr></tfoot></table>
);
const FlowDoc = () => <Flow name={table()?.name ?? "Info"}>{kind() === "table" && table() ? <TablePrint t={table()!} /> : <InfoPrint />}</Flow>;

const [printing, setPrinting] = createSignal(false);
export const PrintPage = () => {
  load();
  onCleanup(save);
  const [zoomP, setZoomP] = createSignal(0.6);
  /** Renders of the graphs to print (the open one is usually cached already). */
  const [rs] = createResource(() => [graphIds().join(","), out()?.rev], async () => {
    const list: [number, Render][] = [];
    for (const id of graphIds()) { const r = lastRender(id) ?? (await call<Render>("render", { id })); if (r) list.push([id, r]); }
    return list;
  });
  const printNow = () => {
    save();
    if (kind() === "graph" && !rs()?.length) return toast("Nothing to print yet.");
    const [pw, ph] = paper(), css = document.createElement("style"), flow = kind() !== "graph";
    css.textContent = flow ? `@page { size: ${pw}mm ${ph}mm; margin: ${ps.margins.map(m => `${m}mm`).join(" ")}; @bottom-center { content: "Page " counter(page) " of " counter(pages); font: 9pt 'IBM Plex Sans', sans-serif; color: #55606E; } }` : `@page { size: ${pw}mm ${ph}mm; margin: 0 }`;
    document.head.append(css);
    setPrinting(true);
    document.documentElement.classList.add("printing");
    setTimeout(() => { window.print(); document.documentElement.classList.remove("printing"); css.remove(); setPrinting(false); }, 300);
  };
  const Slots = (p: { k: "header" | "footer"; label: string }) => (
    <div class="pslots"><b>{p.label}</b><For each={["Left", "Center", "Right"]}>{(l, i) => <label><span>{l}</span><textarea rows="2" value={ps[p.k][i()]} onInput={e => setPs(p.k, i(), e.currentTarget.value)} /></label>}</For></div>
  );
  const Pages = () => (
    <Switch>
      <Match when={kind() === "graph"}><For each={rs() ?? []}>{([id, r], i) => <GraphPage id={id} r={r} n={i() + 1} pages={rs()!.length} />}</For></Match>
      <Match when={true}><FlowDoc /></Match>
    </Switch>
  );
  const [tab, setTab] = createSignal("page");
  return (
    <div class="printpage">
      <div class="pset">
        <h1>Print</h1>
        <p class="pwhat">Printing: <b>{kind() === "graph" ? (ps.which === "all" ? `All graphs (${P().graphs.length})` : graph()?.name) : kind() === "table" ? table()?.name : "Info sheet"}</b><br /><span class="muted">Open another graph or table first to print it.</span></p>
        <div class="pbtns"><button class="btn pri big" onClick={printNow}><svg class="ic"><use href="#i-print" /></svg> Print / Save as PDF</button></div>
        <p class="muted">In the print window choose your printer, or <b>Save as PDF</b>. {ps.paper} {ps.landscape ? "landscape" : "portrait"}.</p>
        <h4>Settings</h4>
        <Show when={kind() === "graph"}><label class="pl">Graphs</label><Seg value={ps.which} set={v => setPs("which", v as "this")} options={[["this", "This graph"], ["all", "All graphs, one per page"]]} />
          <Check label="Scale graphs up to fill the page" value={ps.fit} set={v => setPs("fit", v)} /><Check label="Caption under each graph (name, what the points show)" value={ps.caption} set={v => setPs("caption", v)} /></Show>
        <div class="prow"><label>Paper<Pick value={ps.paper} set={v => setPs("paper", v)} options={PAPERS.map(p => p[0])} /></label><label>Orientation<Pick value={ps.landscape ? "1" : "0"} set={v => setPs("landscape", v === "1")} options={[["0", "Portrait"], ["1", "Landscape"]]} /></label></div>
        <h4>Page Setup</h4>
        <Seg value={tab()} set={setTab} options={[["page", "Margins"], ["header", "Header"], ["footer", "Footer"]]} />
        <div class="ptab">
          <Show when={tab() === "page"}><div class="prow">{(["Top", "Right", "Bottom", "Left"] as const).map((l, i) => <label>{l} (mm)<input type="number" min="0" max="60" value={ps.margins[i]} onChange={e => setPs("margins", i, +e.currentTarget.value)} /></label>)}</div></Show>
          <Show when={tab() === "header"}><Slots k="header" label="Header" /></Show>
          <Show when={tab() === "footer"}><Slots k="footer" label="Footer" /></Show>
          <Show when={tab() !== "page"}><p class="muted pcodes">Codes: <For each={CODES}>{([c, l]) => <code title={l} onClick={() => call("copy_text", { text: c }).then(() => toast(`${c} copied: paste it into a box.`, true))}>{c}</code>}</For></p></Show>
        </div>
        <p><button class="btn sm" onClick={() => setPs(defaults())}>Reset to defaults</button></p>
      </div>
      <div class="pprev">
        <div class="pzoom"><span class="muted">Preview</span><input type="range" min="0.25" max="1.2" step="0.05" value={zoomP()} onInput={e => setZoomP(+e.currentTarget.value)} /><span class="muted">{Math.round(zoomP() * 100)}%</span></div>
        <Show when={kind() === "graph"} fallback={<div class="pwrap pflowprev" style={{ width: `${paper()[0] * MM * zoomP()}px` }}><div style={{ zoom: zoomP(), padding: ps.margins.map(m => `${m * MM}px`).join(" "), width: `${paper()[0] * MM}px` }}><FlowDoc /></div></div>}>
          <Show when={rs()?.length} fallback={<p class="pempty">{rs.loading ? "Preparing pages…" : "Open a graph to print it."}</p>}>
            <For each={rs()}>{([id, r], i) => <div class="pwrap" style={{ width: `${paper()[0] * MM * zoomP()}px`, height: `${paper()[1] * MM * zoomP()}px` }}><div style={{ transform: `scale(${zoomP()})`, "transform-origin": "0 0" }}><GraphPage id={id} r={r} n={i() + 1} pages={rs()!.length} /></div><small>Page {i() + 1} of {rs()!.length}</small></div>}</For>
          </Show>
        </Show>
      </div>
      <Show when={printing()}><Portal mount={document.body}><div id="printroot" classList={{ flow: kind() !== "graph" }}><Pages /></div></Portal></Show>
    </div>
  );
};
