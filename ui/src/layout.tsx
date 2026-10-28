// Page layouts (F1, F2, G3): graphs and text placed on a page in millimetres, with panel letters,
// journal sizes, arranging in a grid, and export of the whole page at its real size. The engine draws
// the page; the window only shows boxes over it to move and resize the items.
import { For, Show, createSignal, createEffect, on, onCleanup } from "solid-js";
import { Layout, LayoutItem, Render, invoke } from "./api";
import { act, call, out, P, item, open, openMenu, openDialog, toast, opts, Item } from "./store";
import { Dialog, Pick, Check, Icon } from "./ui";
import { Empty } from "./nav";
import { Help } from "./help";

/** Journal and page sizes in millimetres (width, height). */
export const PAGES: [string, number, number][] = [["Single column (85 mm)", 85, 100], ["1.5 columns (114 mm)", 114, 110], ["Double column (174 mm)", 174, 130], ["Nature double (183 mm)", 183, 150],
  ["A4 page (210 × 297)", 210, 297], ["Letter page (216 × 279)", 216, 279], ["Slide 16:9 (254 × 143)", 254, 143],
  ["Slide 4:3 (254 × 190)", 254, 190], ["Poster A1 (594 × 841)", 594, 841], ["Poster A0 (841 × 1189)", 841, 1189]];
const GAP = 3;
const layout = () => P().layouts?.find(l => l.id === item().id);
const set = (l: Layout) => act({ LayoutSet: { layout: l } });

/** Places the graph items in a grid of `cols` columns (rows follow), filling the page. */
export const arrange = (l: Layout, cols: number) => {
  const gs = l.items.filter(i => i.kind === "graph"), rest = l.items.filter(i => i.kind !== "graph");
  if (!gs.length) return toast("Add graphs to the layout first.");
  const rows = Math.ceil(gs.length / cols), cap = rest.length ? 12 : 0;
  const w = (l.width - GAP * (cols - 1)) / cols, h = (l.height - cap - GAP * (rows - 1)) / rows;
  const items = gs.map((it, i) => ({ ...it, x: (i % cols) * (w + GAP), y: Math.floor(i / cols) * (h + GAP), w, h }))
    .concat(rest.map((it, i) => ({ ...it, x: 0, y: l.height - cap + i * 5, w: l.width, h: 10 })));
  set({ ...l, items });
};

/** Layout › Poster or Slide (F3): a page with a title and the project's graphs in a grid below it, in sizes
 * that read from across a room (A0 poster: 72 pt title, 24 pt text; 16:9 slide: 28 pt title, 14 pt text). */
export const templateLayout = async (kind: "poster" | "slide") => {
  const poster = kind === "poster", [W, H] = poster ? [841, 1189] : [254, 143], m = poster ? 30 : 8, top = poster ? 110 : 26, foot = poster ? 50 : 0;
  const ids = P().graphs.slice(0, poster ? 6 : 2).map(g => g.id), cols = poster ? 2 : Math.max(ids.length, 1), rows = Math.max(1, Math.ceil(ids.length / cols)), gap = poster ? 20 : 6;
  const w = (W - 2 * m - gap * (cols - 1)) / cols, h = (H - top - foot - m - gap * (rows - 1)) / rows;
  const t = (text: string, y: number, hh: number, size: number, bold: boolean) => ({ kind: "text", graph: 0, x: m, y, w: W - 2 * m, h: hh, text, size, bold });
  const items = [t(P().info?.title || P().name || "Title", m * 0.6, poster ? 60 : 14, poster ? 72 : 28, true),
    ...ids.map((g, i) => ({ kind: "graph", graph: g, x: m + (i % cols) * (w + gap), y: top + Math.floor(i / cols) * (h + gap), w, h, text: "", size: 0, bold: false })),
    ...(poster ? [t([P().info?.researcher, P().info?.organisation].filter(Boolean).join(" · ") || "Authors · Organisation", H - foot, 30, 28, false)] : [])];
  const l: Layout = { id: 0, name: poster ? "Poster" : "Slide", width: W, height: H, letters: poster ? "A" : "none", letterSize: poster ? 40 : 14, font: "Arial", fontSize: poster ? 24 : 14, items };
  if (await act({ AddLayout: { layout: l } })) {
    const ls = out()!.project.layouts;
    open("layouts", ls[ls.length - 1].id);
    toast(poster ? "An A0 poster with your graphs: click the title to change it; File › Export Page saves it as PDF." : "A 16:9 slide with your graphs: Tools › PowerPoint makes a deck of every graph.", true);
  }
};

/** A new layout of the project's graphs (up to four, two per row), or of the given graph. */
export const newLayout = async (graphs?: number[]) => {
  const ids = graphs ?? P().graphs.slice(0, 4).map(g => g.id), wide = ids.length > 1;
  const l: Layout = { id: 0, name: "", width: wide ? 174 : 85, height: wide ? (ids.length > 2 ? 130 : 70) : 70, letters: wide ? "A" : "none", letterSize: 10, font: "Arial", fontSize: 8,
    items: ids.map(g => ({ kind: "graph", graph: g, x: 0, y: 0, w: 80, h: 60, text: "", size: 0, bold: false })) };
  if (await act({ AddLayout: { layout: l } })) {
    const ls = out()!.project.layouts;
    const made = ls[ls.length - 1];
    open("layouts", made.id);
    if (ids.length) arrange(made, wide ? 2 : 1);
  }
};

const addGraph = (l: Layout, g: number) => set({ ...l, items: [...l.items, { kind: "graph", graph: g, x: 0, y: 0, w: Math.min(80, l.width), h: Math.min(60, l.height), text: "", size: 0, bold: false }] });
const addText = (l: Layout) => { const t = prompt("Text (a caption or a label)", "Figure 1. "); if (t) set({ ...l, items: [...l.items, { kind: "text", graph: 0, x: 2, y: Math.max(0, l.height - 10), w: l.width - 4, h: 8, text: t, size: 0, bold: false }] }); };
export const graphMenu = (l: Layout): Item[] => P().graphs.length ? P().graphs.map(g => ({ label: g.name, run: () => addGraph(l, g.id) })) : [{ label: "No graphs yet", off: true }];
export const arrangeMenu = (l: Layout): Item[] => [...[[1, "One column"], [2, "Two columns"], [3, "Three columns"], [4, "Four columns"]].map(([c, t]) => ({ label: t as string, run: () => arrange(l, c as number) })),
  "-", { label: "Stack, sharing the X axis", run: () => stack(l) }, { label: "Line Up the Axes", on: l.align !== false, run: () => set({ ...l, align: l.align === false }) }];
/** One column with no gaps; only the bottom graph keeps its X axis title and numbers (D12). */
export const stack = (l: Layout) => {
  const gs = l.items.filter(i => i.kind === "graph" && !i.inset), rest = l.items.filter(i => i.kind !== "graph" || i.inset);
  if (gs.length < 2) return toast("Stacking needs two or more graphs.");
  const cap = l.items.some(i => i.kind === "text") ? 12 : 0, h = (l.height - cap) / gs.length;
  set({ ...l, align: true, items: [...gs.map((it, i) => ({ ...it, x: 0, y: i * h, w: l.width, h, hideX: i < gs.length - 1 })), ...rest] });
};
/** A small graph on a white card in the top-right of a graph panel (D12). */
const addInset = (l: Layout, at: LayoutItem, g: number) => set({ ...l, items: [...l.items, { kind: "graph", graph: g, x: at.x + at.w * 0.52, y: at.y + 2, w: at.w * 0.45, h: at.h * 0.45, text: "", size: 0, bold: false, inset: true }] });
export const sizeMenu = (l: Layout): Item[] => PAGES.map(([t, w, h]) => ({ label: t, on: l.width === w && l.height === h, run: () => set({ ...l, width: w, height: h }) }));
export const letterMenu = (l: Layout): Item[] => [["A", "A, B, C"], ["a", "a, b, c"], ["(a)", "(a), (b), (c)"], ["none", "No letters"]].map(([k, t]) => ({ label: t, on: l.letters === k, run: () => set({ ...l, letters: k }) }));

/** Export: format, resolution and CMYK for journals; the page at its real size. */
export const exportLayout = (l: Layout, tiff = false) => openDialog(() => {
  const [fmt, setFmt] = createSignal(tiff ? "tiff" : "pdf"), [dpi, setDpi] = createSignal(String(tiff ? 600 : opts().dpi)), [cmyk, setCmyk] = createSignal(tiff);
  return (
    <Dialog title={`Export · ${l.name}`} okText="Export…" ok={async () => { const p = await call<string | null>("export_page", { id: l.id, fmt: fmt(), dpi: +dpi(), cmyk: cmyk() }); if (p) toast(`Saved ${p}`, true); }}>
      <div class="form">
        <label>Format</label><Pick value={fmt()} set={setFmt} options={[["pdf", "PDF vector (most journals)"], ["tiff", "TIFF picture"], ["png", "PNG picture"], ["svg", "SVG vector (editable text)"], ["eps", "EPS vector"]]} />
        <Show when={fmt() === "png" || fmt() === "tiff"}><label>Resolution</label><Pick value={dpi()} set={setDpi} options={[["300", "300 dpi (photos, colour)"], ["600", "600 dpi (graphs with text)"], ["1200", "1200 dpi (line art)"]]} /></Show>
        <Show when={fmt() === "tiff"}><label>Colour</label><Check label="CMYK for print (LZW compressed)" value={cmyk()} set={setCmyk} /></Show>
      </div>
      <p class="muted">The page is {l.width} × {l.height} mm, exported at that size. Check the journal's instructions: many ask for 300–600 dpi TIFF or a vector PDF, with column widths of about 85 or 174 mm.</p>
    </Dialog>
  );
});

/** The Layouts section: the open layout with its items, or how to make one. */
export const LayoutsPage = () => (
  <Show when={layout()} fallback={<Empty icon="layout" title="Layouts">
    <p>A layout is a page that arranges several graphs and text, with panel letters A, B, C, at a journal's column width, ready for a paper, a report or a slide.</p>
    <p><button class="btn pri" disabled={!P().graphs.length} onClick={() => newLayout()}>New Layout of the graphs</button></p>
    <p class="muted">{P().graphs.length ? "It starts with up to four graphs of the project, two per row; add, move and resize them afterwards." : "Make a graph first: every data table has one (Graphs in the navigator)."}</p>
  </Empty>}>{l => <For each={[l().id]}>{() => <LayoutView />}</For>}</Show>
);

const LayoutView = () => {
  const l = () => layout()!;
  const [r, setR] = createSignal<Render | null>(null), [err, setErr] = createSignal(""), [sel, setSel] = createSignal<number | null>(null);
  const [zoom, setZoom] = createSignal(1);
  const [live, setLive] = createSignal<LayoutItem | null>(null);
  let n = 0;
  createEffect(on([() => l().id, () => out()?.rev], ([id]) => { const k = ++n; invoke<Render>("render_page", { id }).then(x => { if (k === n) { setR(x); setErr(""); } }).catch(e => { if (k === n) setErr(String(e)); }); }));
  /** Screen pixels per millimetre. */
  const s = () => zoom() * 96 / 25.4;
  const put = (i: number, it: LayoutItem) => set({ ...l(), items: l().items.map((x, j) => (j === i ? it : x)) });
  const remove = (i: number) => { setSel(null); set({ ...l(), items: l().items.filter((_, j) => j !== i) }); };
  /** Drag to move; drag the corner to resize; snaps to whole millimetres and stays on the page. */
  const drag = (e: MouseEvent, i: number, resize: boolean) => {
    e.preventDefault(); e.stopPropagation();
    setSel(i);
    const it = l().items[i], x0 = e.clientX, y0 = e.clientY;
    const at = (m: MouseEvent): LayoutItem => {
      const dx = Math.round((m.clientX - x0) / s()), dy = Math.round((m.clientY - y0) / s());
      return resize ? { ...it, w: Math.max(10, Math.min(l().width - it.x, it.w + dx)), h: Math.max(6, Math.min(l().height - it.y, it.h + dy)) }
        : { ...it, x: Math.max(0, Math.min(l().width - it.w, it.x + dx)), y: Math.max(0, Math.min(l().height - it.h, it.y + dy)) };
    };
    const mv = (m: MouseEvent) => setLive(at(m));
    const up = (m: MouseEvent) => { removeEventListener("mousemove", mv); removeEventListener("mouseup", up); setLive(null); const v = at(m); if (v.x !== it.x || v.y !== it.y || v.w !== it.w || v.h !== it.h) put(i, v); };
    addEventListener("mousemove", mv); addEventListener("mouseup", up);
  };
  const keys = (e: KeyboardEvent) => { if ((e.key === "Delete" || e.key === "Backspace") && sel() !== null) { e.preventDefault(); remove(sel()!); } if (e.key === "Escape") setSel(null); };
  const name = (it: LayoutItem) => it.kind === "graph" ? P().graphs.find(g => g.id === it.graph)?.name ?? "Graph" : it.text;
  const itemMenu = (e: MouseEvent, i: number) => {
    e.preventDefault(); e.stopPropagation(); setSel(i);
    const it = l().items[i];
    openMenu(e, [...(it.kind === "graph" ? [
      { label: "Add an Inset Here", sub: P().graphs.map(g => ({ label: g.name, run: () => addInset(l(), it, g.id) })) } as Item,
      { label: "Inset (white card, small text)", on: !!it.inset, run: () => put(i, { ...it, inset: !it.inset }) },
      { label: "Hide X Axis Title and Numbers", on: !!it.hideX, run: () => put(i, { ...it, hideX: !it.hideX }) }, { label: "Open the Graph", icon: "graph", run: () => open("graphs", it.graph) }, "-" as const] : [{ label: "Edit Text…", icon: "rename", run: () => editText(i) }, "-" as const]),
      { label: "Bring to Front", run: () => set({ ...l(), items: [...l().items.filter((_, j) => j !== i), it] }) }, { label: "Delete", icon: "del", keys: "Del", run: () => remove(i) }]);
  };
  const editText = (i: number) => { const it = l().items[i]; if (it.kind !== "text") return open("graphs", it.graph); const t = prompt("Text", it.text); if (t !== null) put(i, { ...it, text: t }); };
  onCleanup(() => setSel(null));
  return (
    <section class="lview" tabindex="0" onKeyDown={keys} onMouseDown={() => setSel(null)}>
      <div class="lbar"><Icon n="layout" /><b>{l().name}</b><Help k="layouts" />
        <button class="btn sm" onClick={e => openMenu(e, graphMenu(l()))}>＋ Graph ▾</button><button class="btn sm" onClick={() => addText(l())}>＋ Text</button>
        <button class="btn sm" onClick={e => openMenu(e, arrangeMenu(l()))}>Arrange ▾</button><button class="btn sm" onClick={e => openMenu(e, letterMenu(l()))}>Letters ▾</button>
        <button class="btn sm" onClick={e => openMenu(e, sizeMenu(l()))}>Page size ▾</button>
        <span class="inline"><input type="number" min="20" max="2000" style={{ width: "64px" }} value={l().width} onChange={e => set({ ...l(), width: +e.currentTarget.value })} /><span class="muted">×</span>
          <input type="number" min="20" max="2000" style={{ width: "64px" }} value={l().height} onChange={e => set({ ...l(), height: +e.currentTarget.value })} /><span class="muted">mm</span></span>
        <span class="grow" /><button class="btn sm" onClick={() => setZoom(z => Math.max(0.4, z / 1.2))}>−</button><span class="muted">{Math.round(zoom() * 100)}%</span><button class="btn sm" onClick={() => setZoom(z => Math.min(3, z * 1.2))}>＋</button>
        <button class="btn sm pri" onClick={() => exportLayout(l())}>Export…</button></div>
      <div class="lpage">
        <div class="lpaper" style={{ width: `${l().width * s()}px`, height: `${l().height * s()}px` }}>
          <Show when={r()} fallback={<div class="gwait">{err() || "Drawing the page…"}</div>}>{R => <img class="gimg" src={`data:image/svg+xml;charset=utf-8,${encodeURIComponent(R().svg)}`} width={l().width * s()} height={l().height * s()} alt="" draggable={false} />}</Show>
          <For each={l().items}>{(it0, i) => { const it = () => (live() && sel() === i() ? live()! : it0); return (
            <div class="litem" classList={{ on: sel() === i(), text: it0.kind === "text", inset: !!it0.inset }} style={{ left: `${it().x * s()}px`, top: `${it().y * s()}px`, width: `${it().w * s()}px`, height: `${it().h * s()}px` }}
              title={`${name(it0)} · ${Math.round(it().w)} × ${Math.round(it().h)} mm · drag to move, corner to resize, double-click to ${it0.kind === "text" ? "edit" : "open the graph"}, Delete to remove`}
              onMouseDown={e => drag(e, i(), false)} onDblClick={() => editText(i())} onContextMenu={e => itemMenu(e, i())}>
              <Show when={sel() === i()}><span class="lname">{name(it0)} · {Math.round(it().w)} × {Math.round(it().h)} mm</span><i class="lsize" onMouseDown={e => drag(e, i(), true)} /></Show>
            </div>); }}</For>
        </div>
      </div>
      <div class="gfoot muted"><span>{l().items.filter(x => x.kind === "graph").length} graphs · {l().width} × {l().height} mm · panel letters {l().letters === "none" ? "off" : l().letters}</span><span class="grow" /><span>Drag to move · corner to resize · Delete removes</span></div>
    </section>
  );
};
