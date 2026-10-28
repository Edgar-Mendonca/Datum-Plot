// The graph view: the Python engine draws the graph (matplotlib SVG) and says where the plot area,
// axes and legend are, so the window can show values under the mouse and open the right page of
// Format Graph on a double-click.
import { Show, For, createSignal, createEffect, on, onCleanup } from "solid-js";
import { Graph, Render, Note, num, invoke, spans } from "./api";
import { act, call, engine, openMenu, out, toast, open, openDialog, opts } from "./store";
import { formatGraph, setG } from "./format";
import { Dialog, Pick, Check, Icon } from "./ui";
import { Help } from "./help";

export const [zoomG, setZoomG] = createSignal(1.5);
/** Format › Annotate: the kind of note the next click (text) or drag (arrow, line, box) adds. */
export const [tool, setTool] = createSignal<string | null>(null);
export const annotate = (kind: string) => { setTool(kind); toast(kind === "text" ? "Click on the graph where the text goes (Esc cancels)." : `Drag on the graph to draw the ${kind} (Esc cancels).`, true); };
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
    const tb = out()!.project.tables.find(x => x.id === p.g.table), gs = p.g.settings;
    // No crosshair where the picture has no flat X–Y plane to read (polar, 3D).
    if (!inside(px, py, R.plot) || gs.polar || (tb?.kind === "matrix" && ["surface", "wireframe"].includes(gs.column))) { setCross(null); setTip(null); return; }
    setCross([px, py]);
    const near = R.points.filter(Boolean).map(q => { const [qx, qy] = toPt(q![1], q![6] ?? q![2]); return { q: q!, d: Math.hypot(qx - px, qy - py) }; }).sort((a, b) => a.d - b.d)[0];
    if (near && near.d * k() < 12) {
      const [s, x, y, n, sd, sem] = near.q;
      setTip({ x: e.clientX, y: e.clientY, text: [tb?.sets[s]?.title || `Data set ${s + 1}`, tb?.kind === "survival" ? `X ${num(x)} · ${num(+y.toPrecision(4))}% survival` : tb?.kind === "column" || tb?.kind === "nested" ? `mean ${num(+y.toPrecision(6))}` : `X ${num(x)} · mean ${num(+y.toPrecision(6))}`, tb?.kind === "survival" ? `${n} at risk` : n > 1 ? `n ${n} · SD ${num(+sd.toPrecision(4))} · SEM ${num(+sem.toPrecision(4))}` : `n ${n}`] });
    } else { const [x, y] = toData(px, py); setTip({ x: e.clientX, y: e.clientY, text: [tb?.kind === "column" || tb?.kind === "nested" ? `Y ${num(+y.toPrecision(4))}` : `X ${num(+x.toPrecision(4))}   Y ${num(+y.toPrecision(4))}`] }); }
  };
  // ---------- working on the graph: notes, points, zoom and pan ----------
  const [sel, setSel] = createSignal<number | null>(null), [shift, setShift] = createSignal<[number, number] | null>(null);
  const [drag, setDrag] = createSignal<[number, number, number, number] | null>(null);
  const notes = () => out()?.project.graphs.find(x => x.id === p.g.id)?.settings.notes ?? [];
  const table = () => out()?.project.tables.find(x => x.id === p.g.table);
  /** The note under the mouse (any of its ends or corners), within 8 screen pixels. */
  const noteAt = (px: number, py: number) => {
    let best: number | null = null, bd = 8 / k();
    notes().forEach((n, i) => {
      const pts = [toPt(n.x, n.y), ...(n.kind === "text" ? [] : [toPt(n.x2, n.y2)]), ...(n.kind === "box" ? [toPt(n.x, n.y2), toPt(n.x2, n.y)] : n.kind === "line" ? [toPt((n.x + n.x2) / 2, (n.y + n.y2) / 2)] : [])];
      const d = Math.min(...pts.map(([a, b]) => Math.hypot(a - px, b - py)));
      if (d < bd) { bd = d; best = i; }
    });
    return best;
  };
  /** The data point under the mouse, within 12 screen pixels. */
  const pointAt = (px: number, py: number) => {
    const near = r()?.points.filter(Boolean).map(q => { const [qx, qy] = toPt(q![1], q![6] ?? q![2]); return { q: q!, d: Math.hypot(qx - px, qy - py) }; }).sort((a, b) => a.d - b.d)[0];
    return near && near.d * k() < 12 ? near.q : null;
  };
  /** Moves a note by (dx, dy) points on the graph, in data units (works on log axes too). */
  const moved = (n: Note, dx: number, dy: number): Note => {
    const mv = (x: number, y: number) => { const [a, b] = toPt(x, y); return toData(a + dx, b + dy); };
    const [x, y] = mv(n.x, n.y), [x2, y2] = n.kind === "text" ? [n.x2, n.y2] : mv(n.x2, n.y2);
    return { ...n, x, y, x2, y2 };
  };
  const editNote = (i: number) => { const t = prompt("Text", notes()[i]?.text ?? ""); if (t !== null) setG(p.g, s => { s.notes[i] = { ...s.notes[i], text: t }; return s; }); };
  const delNote = (i: number) => { setSel(null); setG(p.g, s => { s.notes.splice(i, 1); return s; }); };
  /** Leaves a point (all its replicates at that X) out of the graph and analyses: the Exclude op. */
  const excludePoint = (q: (number | undefined)[]) => {
    const t = table();
    if (!t || (t.kind !== "xy" && t.kind !== "multi")) return;
    const [c0, w] = spans(t)[q[0]!], r0 = t.kind === "multi" ? t.cols[1].findIndex((v, r) => v === q[1] && t.cols[c0]?.[r] === q[2]) : t.cols[0].findIndex(v => v === q[1]);
    const cells = Array.from({ length: w }, (_, j) => [r0, c0 + j]).filter(([r, c]) => t.cols[c]?.[r] !== null && t.cols[c]?.[r] !== undefined);
    if (r0 >= 0 && cells.length) act({ Exclude: { table: t.id, cells, on: true } }).then(ok => ok && toast("Excluded: it stays in the table in blue italics (Ctrl+E there includes it again).", true));
  };
  /** Double-click: a note edits its text; otherwise the page of Format Graph for what is under the mouse. */
  const dbl = (e: MouseEvent) => {
    if (!r() || tool()) return;
    const [px, py] = at(e), R = r()!, [x0, y0, , y1] = R.plot;
    const i = noteAt(px, py);
    if (i !== null) return editNote(i);
    if (inside(px, py, R.legend, 4)) return formatGraph(p.g, "sets");
    if (py > y1 && px >= x0 - 10) return formatGraph(p.g, "x");
    if (px < x0 && py <= y1 + 10) return formatGraph(p.g, "y");
    if (py < y0) return formatGraph(p.g, "graph");
    formatGraph(p.g, "sets");
  };
  const menu = (e: MouseEvent) => {
    const [px, py] = at(e), i = r() ? noteAt(px, py) : null, q = r() && i === null ? pointAt(px, py) : null, t = table();
    const name = q ? t?.sets[q[0]]?.title || `Data set ${q[0] + 1}` : "";
    openMenu(e, [
      ...(i !== null ? [{ label: "Edit Note Text…", icon: "rename", run: () => editNote(i) }, { label: "Delete Note", icon: "del", keys: "Del", run: () => delNote(i) }, "-" as const] : []),
      ...(q ? [...(t?.kind === "xy" || t?.kind === "multi" ? [{ label: `Exclude ${name} at X = ${num(q[1])}`, icon: "exclude", run: () => excludePoint(q) }] : []), { label: `Format ${name}…`, icon: "symbol", run: () => formatGraph(p.g, "sets") }, "-" as const] : []),
      { label: "Format Graph…", icon: "style", run: () => formatGraph(p.g, "sets") }, { label: "Format Axes…", icon: "axis", run: () => formatGraph(p.g, "x") },
      { label: "Axis Break (Gap)…", icon: "axis", run: () => formatGraph(p.g, "y") }, { label: "Zoom to a Box", icon: "zin", run: () => zoomTool("zoom") }, { label: "Zoom Out", icon: "zout", run: () => zoomOut(p.g) }, { label: "Reset Axes", icon: "fit", run: () => resetAxes(p.g) }, "-",
      { label: "Copy Picture", icon: "copy", keys: "Ctrl+C", run: () => copyGraph(p.g.id) }, { label: "Export…", icon: "export", run: () => exportGraph(p.g) }, "-",
      { label: "Go to Data Table", icon: "sheet", run: () => open("data", p.g.table) },
    ]);
  };
  const keys = (e: KeyboardEvent) => {
    if (e.key === "Escape") { setTool(null); setDrag(null); setSel(null); }
    if ((e.key === "Delete" || e.key === "Backspace") && sel() !== null) { e.preventDefault(); delNote(sel()!); }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "c") { e.preventDefault(); copyGraph(p.g.id); }
  };
  /** Mouse down: annotate (click or drag), zoom to a box, pan, or select and drag a note. */
  const down = (e: MouseEvent) => {
    if (e.button !== 0 || !r()) return;
    const kind = tool(), [px, py] = at(e), b = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const pt = (m: MouseEvent): [number, number] => [(m.clientX - b.left) / k(), (m.clientY - b.top) / k()];
    const follow = (mv: (q: [number, number]) => void, up: (q: [number, number]) => void) => {
      const m = (x: MouseEvent) => mv(pt(x)), u = (x: MouseEvent) => { removeEventListener("mousemove", m); removeEventListener("mouseup", u); up(pt(x)); };
      addEventListener("mousemove", m); addEventListener("mouseup", u);
    };
    e.preventDefault();
    if (!kind) {
      const i = noteAt(px, py);
      setSel(i);
      if (i === null) return;
      return follow(([qx, qy]) => setShift([qx - px, qy - py]), ([qx, qy]) => {
        setShift(null);
        if (Math.hypot(qx - px, qy - py) > 2) setG(p.g, s => { s.notes[i] = moved(s.notes[i], qx - px, qy - py); return s; });
      });
    }
    if (kind === "pan") return follow(([qx, qy]) => setShift([qx - px, qy - py]), ([qx, qy]) => { setShift(null); panBy(px - qx, py - qy); });
    const place = (qx: number, qy: number) => {
      setTool(null); setDrag(null);
      if (kind !== "text" && Math.hypot(qx - px, qy - py) < 3) return toast("Drag to draw it.");
      const [x, y] = toData(px, py), [x2, y2] = toData(qx, qy);
      if (kind === "zoom") return setG(p.g, s => ({ ...s, ...(["xy", "multi", "survival", "sheet"].includes(table()?.kind ?? "") ? { x: { ...s.x, auto: false, min: Math.min(x, x2), max: Math.max(x, x2) } } : {}), y: { ...s.y, auto: false, min: Math.min(y, y2), max: Math.max(y, y2) } }));
      const text = kind === "text" ? prompt("Text", "") : kind === "line" ? "" : prompt(kind === "arrow" ? "Text at the start of the arrow (optional)" : "Label (optional)", "");
      if (text === null || (kind === "text" && !text.trim())) return;
      setG(p.g, s => ({ ...s, notes: [...(s.notes ?? []), { kind, x, y, x2, y2, text, color: "", size: 0, bold: false }] }));
    };
    if (kind === "text") return place(px, py);
    follow(q => setDrag([px, py, ...q]), q => place(...q));
  };
  /** Pan: shifts both axis ranges by (dx, dy) points. */
  const panBy = (dx: number, dy: number) => {
    const R = r()!, [x0, y0, x1, y1] = R.plot, [ax, ay] = toData(x0 + dx, y1 + dy), [bx, by] = toData(x1 + dx, y0 + dy);
    setG(p.g, s => ({ ...s, ...(["xy", "multi", "survival"].includes(table()?.kind ?? "") ? { x: { ...s.x, auto: false, min: ax, max: bx } } : {}), y: { ...s.y, auto: false, min: ay, max: by } }));
  };
  onCleanup(() => { setTip(null); if (tool() === "pan" || tool() === "zoom") setTool(null); });
  return (
    <section class="gview" tabindex="0" onKeyDown={keys}>
      <div class="gpage" onWheel={e => { if (e.ctrlKey) { e.preventDefault(); setZoomG(z => Math.min(4, Math.max(0.5, z * (e.deltaY < 0 ? 1.1 : 1 / 1.1)))); } }}>
        <Show when={r()} fallback={<div class="gwait">{err() || (engine()?.error ?? engine()?.status ?? "Drawing the graph…")}</div>}>{R => (
          <div class="gpaper" classList={{ annot: !!tool() && tool() !== "pan", pan: tool() === "pan" }} style={{ width: `${R().w * k()}px`, height: `${R().h * k()}px` }} onMouseDown={down} onMouseMove={move} onMouseLeave={() => { setTip(null); setCross(null); }} onDblClick={dbl} onContextMenu={menu}>
            <GraphImg r={R()} scale={k()} />
            <Show when={drag()}>{d => { const [a, b2, c, e] = d().map(v => v * k()); return <svg class="gdrag" width={R().w * k()} height={R().h * k()}>{tool() === "box" || tool() === "zoom"
              ? <rect x={Math.min(a, c)} y={Math.min(b2, e)} width={Math.abs(c - a)} height={Math.abs(e - b2)} /> : <line x1={a} y1={b2} x2={c} y2={e} />}</svg>; }}</Show>
            <Show when={sel() !== null && notes()[sel()!]}>{n => { const [x, y] = toPt(n().x, n().y), [dx, dy] = shift() ?? [0, 0]; return <svg class="gdrag" width={R().w * k()} height={R().h * k()}>
              <rect class="nsel" x={(x + dx) * k() - 7} y={(y + dy) * k() - 7} width="14" height="14" /></svg>; }}</Show>
            <Show when={tool() === "pan" && shift()}>{d => <svg class="gdrag" width={R().w * k()} height={R().h * k()}><rect x={(R().plot[0] + d()[0]) * k()} y={(R().plot[1] + d()[1]) * k()} width={(R().plot[2] - R().plot[0]) * k()} height={(R().plot[3] - R().plot[1]) * k()} /></svg>}</Show>
            <Show when={cross()}>{c => <><i class="xh" style={{ left: `${c()[0] * k()}px`, top: `${R().plot[1] * k()}px`, height: `${(R().plot[3] - R().plot[1]) * k()}px` }} /><i class="yh" style={{ top: `${c()[1] * k()}px`, left: `${R().plot[0] * k()}px`, width: `${(R().plot[2] - R().plot[0]) * k()}px` }} /></>}</Show>
          </div>
        )}</Show>
        <Show when={err() && r()}><div class="gerr">{err()}</div></Show>
      </div>
      <div class="gfoot muted"><Icon n="graph" /><b>{p.g.name}</b><Help k="graphview" /><span>{p.g.settings.width} × {p.g.settings.height} mm · {p.g.settings.font} {p.g.settings.fontSize} pt</span><span class="grow" />
        <span>{tool() === "pan" ? "Drag to pan · Esc to stop" : "Drag a note to move it · double-click to format or edit · right-click for more"}</span></div>
      <Show when={tip()}>{t => <div class="gtip" style={{ left: `${t().x + 14}px`, top: `${t().y + 12}px` }}><For each={t().text}>{(l, i) => i() ? <span>{l}</span> : <b>{l}</b>}</For></div>}</Show>
    </section>
  );
};

/** Zoom to a box (one drag) or pan (drag until Esc). */
export const zoomTool = (kind: "zoom" | "pan") => { setTool(kind); toast(kind === "zoom" ? "Drag a box around the part to zoom into (Esc cancels)." : "Drag the graph to pan; Esc stops.", true); };
/** Doubles both axis ranges around their middle (geometric on log axes). */
export const zoomOut = (g: Graph) => {
  const R = lastRender(g.id);
  if (!R) return;
  const wide = ([a, b]: [number, number], log: boolean) => log ? [a / Math.sqrt(b / a), b * Math.sqrt(b / a)] : [a - (b - a) / 2, b + (b - a) / 2];
  const xy = ["xy", "multi", "survival", "sheet"].includes(out()?.project.tables.find(t => t.id === g.table)?.kind ?? ""), [xa, xb] = wide(R.xlim, R.xlog), [ya, yb] = wide(R.ylim, R.ylog);
  setG(g, s => ({ ...s, ...(xy ? { x: { ...s.x, auto: false, min: xa, max: xb } } : {}), y: { ...s.y, auto: false, min: ya, max: yb } }));
};
export const resetAxes = (g: Graph) => setG(g, s => ({ ...s, x: { ...s.x, auto: true }, y: { ...s.y, auto: true } }));

/** Copies the graph to the Windows clipboard as a picture (through Rust; WebView2 blocks the
 *  browser clipboard), for Word and PowerPoint. */
export const copyGraph = async (id: number) => {
  try { await invoke("copy_graph", { id, dpi: Math.min(600, opts().dpi) }); toast("Graph copied as a picture. Paste it into Word, PowerPoint or an email.", true); }
  catch (e) { toast(`Could not copy the picture: ${e}`); }
};

const FORMATS: [string, string][] = [["png", "PNG picture"], ["tiff", "TIFF picture (journals)"], ["svg", "SVG vector (editable text)"], ["pdf", "PDF vector"], ["eps", "EPS vector"]];
/** Export: format, resolution and background, then a Save dialog. */
export const exportGraph = (g: Graph, fmt0 = "png") => openDialog(() => {
  const [fmt, setFmt] = createSignal(fmt0), [dpi, setDpi] = createSignal(String(opts().dpi)), [tr, setTr] = createSignal(false), [cmyk, setCmyk] = createSignal(false);
  const raster = () => fmt() === "png" || fmt() === "tiff";
  return (
    <Dialog title={`Export · ${g.name}`} help="export" okText="Export…" ok={async () => { const p = await call<string | null>("export_graph", { id: g.id, fmt: fmt(), dpi: +dpi(), transparent: tr(), cmyk: cmyk() }); if (p) toast(`Saved ${p}`, true); }}>
      <div class="form">
        <label>Format</label><Pick value={fmt()} set={setFmt} options={FORMATS} />
        <Show when={raster()}><label>Resolution</label><Pick value={dpi()} set={setDpi} options={[["150", "150 dpi (screen)"], ["300", "300 dpi (print, most journals)"], ["600", "600 dpi (line art)"], ["1200", "1200 dpi"]]} /></Show>
        <label>Background</label><Check label="Transparent" value={tr()} set={setTr} />
        <Show when={fmt() === "tiff"}><label>Colour</label><Check label="CMYK for print (journals; LZW compressed)" value={cmyk()} set={setCmyk} /></Show>
      </div>
      <p class="muted">The size is the graph's size ({g.settings.width} × {g.settings.height} mm). Vector files keep text as text, so it stays editable in Illustrator or Inkscape.</p>
    </Dialog>
  );
});

export const newGraph = (table: number) => act({ AddGraph: { table, settings: null } }).then(ok => { if (ok) { const gs = out()!.project.graphs; open("graphs", gs[gs.length - 1].id); } });
