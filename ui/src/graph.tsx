// The graph view: the Python engine draws the graph (matplotlib SVG) and says where the plot area,
// axes and legend are, so the window can show values under the mouse and open the right page of
// Format Graph on a double-click.
import { Show, For, createSignal, createEffect, on, onCleanup } from "solid-js";
import { Graph, Render, num, invoke } from "./api";
import { act, call, engine, openMenu, out, toast, open, openDialog, opts } from "./store";
import { formatGraph } from "./format";
import { Dialog, Pick, Check, Icon } from "./ui";

export const [zoomG, setZoomG] = createSignal(1.5);
/** The last render of each graph, by id (also used by File › Print). */
const renders = new Map<number, Render>();
export const lastRender = (id: number) => renders.get(id);
const svgUrl = (r: Render) => `data:image/svg+xml;charset=utf-8,${encodeURIComponent(r.svg)}`;
export const GraphImg = (p: { r: Render; scale: number }) => <img class="gimg" src={svgUrl(p.r)} width={p.r.w * p.scale} height={p.r.h * p.scale} alt="" draggable={false} />;

/** Renders a graph whenever the project changes (the shell caches unchanged graphs). */
export const useRender = (id: () => number | undefined) => {
  const [r, setR] = createSignal<Render | null>(null), [err, setErr] = createSignal("");
  let n = 0;
  createEffect(on([id, () => out()?.rev], ([g]) => {
    if (!g) return;
    const k = ++n;
    invoke<Render>("render", { id: g }).then(x => { if (k === n) { renders.set(g, x); setR(x); setErr(""); } }).catch(e => { if (k === n) setErr(String(e)); });
  }));
  return [r, err] as const;
};

export const GraphView = (p: { g: Graph }) => {
  const [r, err] = useRender(() => p.g.id);
  const [tip, setTip] = createSignal<{ x: number; y: number; text: string[] } | null>(null);
  const [cross, setCross] = createSignal<[number, number] | null>(null);
  const k = () => zoomG() * 96 / 72;
  /** Points (from the image's top-left) ↔ data values, for linear and log axes. */
  const toData = (px: number, py: number) => {
    const R = r()!, [x0, y0, x1, y1] = R.plot, f = (t: number, [a, b]: [number, number], log: boolean) => log ? 10 ** (Math.log10(a) + t * (Math.log10(b) - Math.log10(a))) : a + t * (b - a);
    return [f((px - x0) / (x1 - x0), R.xlim, R.xlog), f((y1 - py) / (y1 - y0), R.ylim, R.ylog)];
  };
  const toPt = (x: number, y: number) => {
    const R = r()!, [x0, y0, x1, y1] = R.plot, t = (v: number, [a, b]: [number, number], log: boolean) => log ? (Math.log10(v) - Math.log10(a)) / (Math.log10(b) - Math.log10(a)) : (v - a) / (b - a);
    return [x0 + t(x, R.xlim, R.xlog) * (x1 - x0), y1 - t(y, R.ylim, R.ylog) * (y1 - y0)];
  };
  const at = (e: MouseEvent) => { const b = (e.currentTarget as HTMLElement).getBoundingClientRect(); return [(e.clientX - b.left) / k(), (e.clientY - b.top) / k()]; };
  const inside = (px: number, py: number, b: number[] | null, pad = 0) => !!b && px >= b[0] - pad && px <= b[2] + pad && py >= b[1] - pad && py <= b[3] + pad;
  const move = (e: MouseEvent) => {
    if (!r()) return;
    const [px, py] = at(e), R = r()!;
    if (!inside(px, py, R.plot)) { setCross(null); setTip(null); return; }
    setCross([px, py]);
    const tb = out()!.project.tables.find(x => x.id === p.g.table);
    const near = R.points.filter(Boolean).map(q => { const [qx, qy] = toPt(q![1], q![2]); return { q: q!, d: Math.hypot(qx - px, qy - py) }; }).sort((a, b) => a.d - b.d)[0];
    if (near && near.d * k() < 12) {
      const [s, x, y, n, sd, sem] = near.q;
      setTip({ x: e.clientX, y: e.clientY, text: [tb?.sets[s]?.title || `Data set ${s + 1}`, `X ${num(x)} · mean ${num(+y.toPrecision(6))}`, n > 1 ? `n ${n} · SD ${num(+sd.toPrecision(4))} · SEM ${num(+sem.toPrecision(4))}` : `n ${n}`] });
    } else { const [x, y] = toData(px, py); setTip({ x: e.clientX, y: e.clientY, text: [`X ${num(+x.toPrecision(4))}   Y ${num(+y.toPrecision(4))}`] }); }
  };
  /** Double-click opens the page of Format Graph for what is under the mouse. */
  const dbl = (e: MouseEvent) => {
    if (!r()) return;
    const [px, py] = at(e), R = r()!, [x0, y0, , y1] = R.plot;
    if (inside(px, py, R.legend, 4)) return formatGraph(p.g, "sets");
    if (py > y1 && px >= x0 - 10) return formatGraph(p.g, "x");
    if (px < x0 && py <= y1 + 10) return formatGraph(p.g, "y");
    if (py < y0) return formatGraph(p.g, "graph");
    formatGraph(p.g, "sets");
  };
  const menu = (e: MouseEvent) => openMenu(e, [
    { label: "Format Graph…", icon: "style", run: () => formatGraph(p.g, "sets") }, { label: "Format Axes…", icon: "axis", run: () => formatGraph(p.g, "x") }, "-",
    { label: "Copy Picture", icon: "copy", keys: "Ctrl+C", run: () => copyGraph(p.g.id) }, { label: "Export…", icon: "export", run: () => exportGraph(p.g) }, "-",
    { label: "Go to Data Table", icon: "sheet", run: () => open("data", p.g.table) },
  ]);
  const keys = (e: KeyboardEvent) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "c") { e.preventDefault(); copyGraph(p.g.id); } };
  onCleanup(() => setTip(null));
  return (
    <section class="gview" tabindex="0" onKeyDown={keys}>
      <div class="gpage" onWheel={e => { if (e.ctrlKey) { e.preventDefault(); setZoomG(z => Math.min(4, Math.max(0.5, z * (e.deltaY < 0 ? 1.1 : 1 / 1.1)))); } }}>
        <Show when={r()} fallback={<div class="gwait">{err() || (engine()?.error ?? "Drawing the graph…")}</div>}>{R => (
          <div class="gpaper" style={{ width: `${R().w * k()}px`, height: `${R().h * k()}px` }} onMouseMove={move} onMouseLeave={() => { setTip(null); setCross(null); }} onDblClick={dbl} onContextMenu={menu}>
            <GraphImg r={R()} scale={k()} />
            <Show when={cross()}>{c => <><i class="xh" style={{ left: `${c()[0] * k()}px`, top: `${R().plot[1] * k()}px`, height: `${(R().plot[3] - R().plot[1]) * k()}px` }} /><i class="yh" style={{ top: `${c()[1] * k()}px`, left: `${R().plot[0] * k()}px`, width: `${(R().plot[2] - R().plot[0]) * k()}px` }} /></>}</Show>
          </div>
        )}</Show>
        <Show when={err() && r()}><div class="gerr">{err()}</div></Show>
      </div>
      <div class="gfoot muted"><Icon n="graph" /><b>{p.g.name}</b><span>{p.g.settings.width} × {p.g.settings.height} mm · {p.g.settings.font} {p.g.settings.fontSize} pt</span><span class="grow" />
        <span>Double-click an axis, the legend or the data to format it · right-click for more</span></div>
      <Show when={tip()}>{t => <div class="gtip" style={{ left: `${t().x + 14}px`, top: `${t().y + 12}px` }}><For each={t().text}>{(l, i) => i() ? <span>{l}</span> : <b>{l}</b>}</For></div>}</Show>
    </section>
  );
};

/** Copies a PNG of the graph to the clipboard, for Word and PowerPoint. */
export const copyGraph = async (id: number) => {
  const b64 = await call<string>("graph_png", { id, dpi: Math.min(600, opts().dpi) });
  if (!b64) return;
  try {
    const blob = await (await fetch(`data:image/png;base64,${b64}`)).blob();
    await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
    toast("Graph copied as a picture. Paste it into Word, PowerPoint or an email.", true);
  } catch (e) { toast(`Could not copy the picture: ${e}`); }
};

const FORMATS: [string, string][] = [["png", "PNG picture"], ["tiff", "TIFF picture (journals)"], ["svg", "SVG vector (editable text)"], ["pdf", "PDF vector"], ["eps", "EPS vector"]];
/** Export: format, resolution and background, then a Save dialog. */
export const exportGraph = (g: Graph, fmt0 = "png") => openDialog(() => {
  const [fmt, setFmt] = createSignal(fmt0), [dpi, setDpi] = createSignal(String(opts().dpi)), [tr, setTr] = createSignal(false);
  const raster = () => fmt() === "png" || fmt() === "tiff";
  return (
    <Dialog title={`Export · ${g.name}`} okText="Export…" ok={async () => { const p = await call<string | null>("export_graph", { id: g.id, fmt: fmt(), dpi: +dpi(), transparent: tr() }); if (p) toast(`Saved ${p}`, true); }}>
      <div class="form">
        <label>Format</label><Pick value={fmt()} set={setFmt} options={FORMATS} />
        <Show when={raster()}><label>Resolution</label><Pick value={dpi()} set={setDpi} options={[["150", "150 dpi (screen)"], ["300", "300 dpi (print, most journals)"], ["600", "600 dpi (line art)"], ["1200", "1200 dpi"]]} /></Show>
        <label>Background</label><Check label="Transparent" value={tr()} set={setTr} />
      </div>
      <p class="muted">The size is the graph's size ({g.settings.width} × {g.settings.height} mm). Vector files keep text as text, so it stays editable in Illustrator or Inkscape.</p>
    </Dialog>
  );
});

export const newGraph = (table: number) => act({ AddGraph: { table, settings: null } }).then(ok => { if (ok) { const gs = out()!.project.graphs; open("graphs", gs[gs.length - 1].id); } });
