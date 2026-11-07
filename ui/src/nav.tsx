// The sidebar (Info, Data, Results, Graphs, Layouts), the navigator next to it, and
// the Info sheet and empty pages.
import { For, Show, JSX, createSignal } from "solid-js";
import { Info } from "./api";
import { P, item, open, Section, navOpen, act, openMenu, thumbs, setThumbs, graph } from "./store";
import { C } from "./cmds";
import { newGraph, useRender, GraphImg, copyGraph, copyEmbedded, exportGraph } from "./graph";
import { Icon } from "./ui";
import { Help } from "./help";
import { analyze, newTable, importFile } from "./roadmap";
import { newLayout, copyPage, exportLayout } from "./layout";

export const SIDE: [Section, string, string][] = [["info", "infosheet", "Info"], ["data", "sheet", "Data"], ["results", "results", "Results"], ["graphs", "graph", "Graphs"], ["layouts", "layout", "Layouts"]];

export const Side = () => (
  <nav class="side"><For each={SIDE}>{([s, i, l], k) => <>{k() === 1 && <hr />}<button classList={{ on: item().s === s }} onClick={() => open(s)} title={l}><Icon n={i} /><span>{l}</span></button></>}</For></nav>
);

const Head = (p: { l: string; h?: string; add?: (e: MouseEvent) => void; title?: string }) => <div class="nhead"><span>{p.l}{p.h && <Help k={p.h} />}</span>{p.add && <button title={p.title} onClick={p.add}>＋</button>}</div>;
/** 0.3.15 (#21): the panel can be dragged wider (kept in this browser profile), so long names show in full. */
const [navW, setNavW] = createSignal((() => { try { return Math.min(560, Math.max(160, +(localStorage.getItem("navw") ?? 190) || 190)); } catch { return 190; } })());
const keepW = (w: number) => { setNavW(w); try { localStorage.setItem("navw", String(Math.round(w))); } catch { /* private window */ } };
const widen = (e: MouseEvent) => {
  e.preventDefault();
  const x0 = e.clientX, w0 = navW();
  const move = (m: MouseEvent) => setNavW(Math.min(560, Math.max(160, w0 + m.clientX - x0)));
  const up = () => { removeEventListener("mousemove", move); removeEventListener("mouseup", up); keepW(navW()); };
  addEventListener("mousemove", move); addEventListener("mouseup", up);
};
/** 0.3.16 (#31, #32): organising the navigator. Folders and name colours live in the project (ui.nav, undoable):
 *  `folder` maps an item's id to its folder's name (folders are per section), `color` to a colour. Selection
 *  (Ctrl/Shift+click), collapsed folders and the family view are this window's state only. */
type NavUi = { folder?: Record<string, string>; color?: Record<string, string> };
const navUi = (): NavUi => (P().ui?.nav ?? {}) as NavUi;
const setNav = (f: (n: NavUi) => NavUi) => act({ Ui: { key: "nav", value: f(structuredClone({ folder: {}, color: {}, ...navUi() })) } });
const COLOURS: [string, string][] = [["", "No colour"], ["#D55E00", "Red"], ["#E69F00", "Orange"], ["#009E73", "Green"], ["#0072B2", "Blue"], ["#CC79A7", "Pink"], ["#8A94A6", "Grey"]];
const [sel, setSel] = createSignal<number[]>([]), [anchor, setAnchor] = createSignal<number | null>(null);
const [shut, setShut] = createSignal<string[]>([]);
export const [family, setFamily] = createSignal<number | null>(null);
type Entry = { id: number; name: string; icon: string };

export const Navigator = () => {
  const one = (id: number) => P().tables.find(t => t.id === id) ?? P().graphs.find(g => g.id === id) ?? P().analyses?.find(a => a.id === id) ?? P().layouts?.find(l => l.id === id);
  const picked = (id: number) => (sel().includes(id) ? sel() : [id]);
  const folders = (s: Section) => [...new Set(list(s).map(e => navUi().folder?.[e.id]).filter((f): f is string => !!f))];
  const moveTo = (ids: number[], folder: string) => setNav(n => { ids.forEach(i => { if (folder) n.folder![i] = folder; else delete n.folder![i]; }); return n; });
  const colour = (ids: number[], c: string) => setNav(n => { ids.forEach(i => { if (c) n.color![i] = c; else delete n.color![i]; }); return n; });
  const organise = (ids: number[], s: Section) => [
    { label: "Move to Folder", icon: "folder", sub: [
      ...folders(s).map(f => ({ label: f, run: () => moveTo(ids, f) })),
      { label: "New Folder…", run: () => { const f = prompt("Folder name", ""); if (f?.trim()) moveTo(ids, f.trim().slice(0, 80)); } },
      ...(ids.some(i => navUi().folder?.[i]) ? [{ label: "Out of the Folder", run: () => moveTo(ids, "") }] : []),
    ] },
    { label: "Colour", icon: "paint", sub: COLOURS.map(([c, l]) => ({ label: l, on: ids.every(i => (navUi().color?.[i] ?? "") === c), run: () => colour(ids, c) })) },
  ];
  const delMany = (ids: number[]) => {
    const names = ids.map(i => one(i)?.name).filter(Boolean);
    const graphs = P().graphs.filter(g => ids.includes(g.table) && !ids.includes(g.id)).length;
    if (confirm(`Delete ${names.length} items (${names.slice(0, 6).join(", ")}${names.length > 6 ? "…" : ""})${graphs ? ` and the ${graphs} graphs and results of the tables among them` : ""}?`)) {
      // Graphs and results first, tables last: deleting a table takes its own graphs, and a second delete would fail.
      const isT = (i: number) => P().tables.some(t => t.id === i);
      act({ Batch: [...ids.filter(i => !isT(i)), ...ids.filter(isT)].map(id => ({ Delete: { id } })) }).then(ok => ok && setSel([]));
    }
  };
  const ctx = (e: MouseEvent, id: number, s: Section) => {
    e.preventDefault(); e.stopPropagation();
    const ids = picked(id);
    if (ids.length > 1) return openMenu(e, [...organise(ids, s), "-", { label: `Delete ${ids.length} Items`, icon: "del", run: () => delMany(ids) }, { label: "Clear the Selection", run: () => setSel([]) }]);
    setSel([]); open(s, id); openMenu(e, [
      ...(s === "data" ? [{ label: "New Graph of This Table", icon: "graph", run: () => newGraph(id) }, { label: "Show Only This Family", icon: "list", run: () => setFamily(id) }, "-" as const] : []),
      ...(s === "graphs" ? [{ label: "Copy Picture", icon: "copy", run: () => copyGraph(id) }, { label: "Copy Embedded", icon: "copy", run: () => copyEmbedded(id) }, { label: "Export…", icon: "export", run: () => { const g = P().graphs.find(x => x.id === id); if (g) exportGraph(g); } },
        { label: "New Layout with This Graph", icon: "layout", run: () => newLayout([id]) }, { label: thumbs() ? "Hide Previews" : "Show Previews", icon: "image", run: () => setThumbs(!thumbs()) }, "-" as const] : []),
      ...(s === "layouts" ? [{ label: "Copy Picture", icon: "copy", run: () => copyPage(id) }, { label: "Export…", icon: "export", run: () => { const l = P().layouts?.find(x => x.id === id); if (l) exportLayout(l); } }, "-" as const] : []),
      ...organise([id], s), "-" as const,
      { label: "Rename…", icon: "rename", run: C.rename },
      ...(s === "data" ? [{ label: "Duplicate with Graphs and Results", icon: "copy", run: () => C.duplicate(false) }, { label: "Duplicate Table Only", icon: "copy", run: () => C.duplicate(true) }] : [{ label: "Duplicate", icon: "copy", run: () => C.duplicate() }]),
      { label: "Delete", icon: "del", run: C.del },
    ]);
  };
  /** Click opens; Ctrl+click adds to the selection; Shift+click selects a run within the section. */
  const click = (e: MouseEvent, id: number, s: Section) => {
    if (e.ctrlKey || e.metaKey) { const cur = sel().length ? sel() : item().s === s && item().id ? [item().id] : []; setSel(cur.includes(id) ? cur.filter(x => x !== id) : [...cur, id]); setAnchor(id); return; }
    if (e.shiftKey && anchor() !== null) { const ids = list(s).map(x => x.id), a = ids.indexOf(anchor()!), b = ids.indexOf(id); if (a >= 0 && b >= 0) { setSel(ids.slice(Math.min(a, b), Math.max(a, b) + 1)); return; } }
    setSel([]); setAnchor(id); open(s, id);
  };
  const folderMenu = (e: MouseEvent, s: Section, f: string) => { e.preventDefault(); openMenu(e, [
    { label: "Rename Folder…", icon: "rename", run: () => { const n = prompt("Folder name", f); if (n?.trim()) setNav(x => { Object.keys(x.folder!).forEach(i => { if (x.folder![i] === f && list(s).some(y => String(y.id) === i)) x.folder![i] = n.trim().slice(0, 80); }); return x; }); } },
    { label: "Remove Folder (keeps its items)", icon: "del", run: () => moveTo(list(s).filter(x => navUi().folder?.[x.id] === f).map(x => x.id), "") },
  ]); };
  /** 0.3.15 (#29): the Graphs ＋ asks: a new graph of a table, or a copy of the open graph with all its formatting. */
  const addGraph = (e: MouseEvent) => openMenu(e, [
    ...(graph() ? [{ label: `Duplicate “${graph()!.name}” (keeps its formatting)`, icon: "copy", run: () => C.duplicate() }, "-" as const] : []),
    ...P().tables.map(t => ({ label: `New Graph of “${t.name}”`, icon: "graph", run: () => newGraph(t.id) })),
  ]);
  const Row = (q: { e: Entry; s: Section }) => (
    <button class="nitem" classList={{ on: item().s === q.s && item().id === q.e.id, sel: sel().includes(q.e.id), infold: !!navUi().folder?.[q.e.id] }} style={{ color: navUi().color?.[q.e.id] || undefined }}
      onClick={e => click(e, q.e.id, q.s)} onContextMenu={e => ctx(e, q.e.id, q.s)} onDblClick={C.rename}><Icon n={q.e.icon} /><span title={q.e.name}>{q.e.name}</span></button>
  );
  const Items = (q: { s: Section; none?: string }) => {
    const loose = () => list(q.s).filter(e => !navUi().folder?.[e.id]);
    const Each = (r: { e: Entry }) => <><Row e={r.e} s={q.s} />
      <Show when={q.s === "graphs" && thumbs()}><div class="nthumbs" classList={{ infold: !!navUi().folder?.[r.e.id] }} onContextMenu={e => ctx(e, r.e.id, "graphs")}><Thumb id={r.e.id} on={item().s === "graphs" && item().id === r.e.id} /></div></Show></>;
    return <>
      <For each={folders(q.s)}>{f => { const key = `${q.s}:${f}`, open_ = () => !shut().includes(key); return <>
        <button class="nfolder" onClick={() => setShut(open_() ? [...shut(), key] : shut().filter(x => x !== key))} onContextMenu={e => folderMenu(e, q.s, f)} title="Click to open or close; right-click to rename or remove">
          <span class="caret">{open_() ? "▾" : "▸"}</span><Icon n="folder" /><span>{f}</span><small>{list(q.s).filter(e => navUi().folder?.[e.id] === f).length}</small></button>
        <Show when={open_()}><For each={list(q.s).filter(e => navUi().folder?.[e.id] === f)}>{e => <Each e={e} />}</For></Show>
      </>; }}</For>
      <For each={loose()} fallback={folders(q.s).length || !q.none ? null : <p class="nnone">{q.none}</p>}>{e => <Each e={e} />}</For>
    </>;
  };
  const keys = (e: KeyboardEvent) => { if (e.key === "Delete" && sel().length > 1) { e.preventDefault(); delMany(sel()); } if (e.key === "Escape") setSel([]); };
  return (
    <Show when={navOpen()}>
      <aside class="nav" style={{ width: `${navW()}px` }} tabindex="-1" onKeyDown={keys}>
        <Show when={family() !== null && P().tables.some(t => t.id === family())}>
          <div class="nfamily"><span>Family of <b>{P().tables.find(t => t.id === family())?.name}</b></span><button class="btn sm" onClick={() => setFamily(null)}>Show All</button></div>
        </Show>
        <Show when={sel().length > 1}><div class="nfamily"><span><b>{sel().length}</b> selected · right-click for more</span><button class="btn sm" onClick={() => setSel([])}>Clear</button></div></Show>
        <button class="nitem" classList={{ on: item().s === "info" }} onClick={() => open("info")}><Icon n="infosheet" /><span>{P().info.title || "Project info"}</span></button>
        <Head l="Data tables" h="navigator" add={newTable} title="New data table" />
        <Items s="data" />
        <Head l="Results" h="results" add={() => analyze()} title="Analyze data" />
        <Items s="results" none="Analyze… adds results here" />
        <Head l="Graphs" h="graphview" add={addGraph} title="A new graph of a table, or a copy of this graph" />
        <Items s="graphs" />
        <Head l="Layouts" h="layouts" add={() => newLayout()} title="New layout of the graphs" />
        <Items s="layouts" none="＋ arranges graphs on a page" />
      </aside>
      <i class="navrsz" title="Drag to widen the panel; double-click for the usual width" onMouseDown={widen} onDblClick={() => keepW(190)} />
    </Show>
  );
};

/** The items of a section, filtered to one table's family when that view is on. */
const list = (s: Section): Entry[] => {
  const f = family() !== null && P().tables.some(t => t.id === family()) ? family() : null;
  const fg = f === null ? [] : P().graphs.filter(g => g.table === f).map(g => g.id);
  if (s === "data") return P().tables.filter(t => f === null || t.id === f).map(t => ({ id: t.id, name: t.name, icon: t.kind === "column" ? "table" : "sheet" }));
  if (s === "results") return (P().analyses ?? []).filter(a => f === null || a.table === f).map(a => ({ id: a.id, name: a.name, icon: "results" }));
  if (s === "graphs") return P().graphs.filter(g => f === null || g.table === f).map(g => ({ id: g.id, name: g.name, icon: "graph" }));
  if (s === "layouts") return (P().layouts ?? []).filter(l => f === null || l.items.some(i => i.kind === "graph" && fg.includes(i.graph))).map(l => ({ id: l.id, name: l.name, icon: "layout" }));
  return [];
};

/** A small picture of a graph (E7); the shell keeps recent renders, so unchanged graphs cost nothing. */
const Thumb = (p: { id: number; on: boolean }) => {
  const [r] = useRender(() => p.id);
  return <button class="nthumb" classList={{ on: p.on }} title={P().graphs.find(g => g.id === p.id)?.name} onClick={() => open("graphs", p.id)}>
    <Show when={r()} fallback={<span class="muted">…</span>}>{x => <GraphImg r={x()} scale={Math.min(150 / x().w, 100 / x().h)} />}</Show></button>;
};

/** The Info sheet: what the experiment is. Fields can go into page headers. */
export const InfoPage = () => {
  const put = (k: keyof Info, v: string) => act({ Info: { info: { ...P().info, [k]: v } } });
  const F = (p: { k: keyof Info; l: string; hint: string; area?: boolean }) => <div class="opt"><div><b>{p.l}</b><small>{p.hint}</small></div><div class="ctl">{p.area
    ? <textarea rows="8" value={P().info[p.k]} onChange={e => put(p.k, e.currentTarget.value)} /> : <input value={P().info[p.k]} onChange={e => put(p.k, e.currentTarget.value)} />}</div></div>;
  return (
    <div class="page infopage"><div class="options">
      <h1>Info <Help k="info" /></h1>
      <p class="muted">What this project is about. It is saved with the project, and the fields can go into printed headers and footers (File › Print).</p>
      <section class="osec">
        <F k="title" l="Title" hint="Printed with &[Title]." />
        <F k="experiment" l="Experiment" hint="What was measured, and how." />
        <F k="researcher" l="Researcher" hint="Printed with &[Researcher]." />
        <F k="organisation" l="Organisation" hint="Lab, department or company." />
        <F k="date" l="Date" hint="When the experiment was done." />
        <F k="notes" l="Notes" hint="Protocol, reagents, instrument settings, anything to remember." area />
      </section>
    </div></div>
  );
};

/** 0.3.15: a project with no data table yet (the empty start, or after deleting the last table). */
export const EmptyProject = () => (
  <Empty icon={item().s === "graphs" ? "graph" : "sheet"} title={P().tables.length ? "Graphs" : "An empty project"}>
    <p>{P().tables.length ? "Graphs show a data table: make one from a table." : "Start with a data table: type or paste your values, or import a file. Graphs and analyses follow from the table."}</p>
    <p class="inline"><button class="btn pri" onClick={() => newTable()}>New Table…</button><button class="btn" onClick={() => importFile()}>Import Data…</button>
      <Show when={P().tables.length}><button class="btn" onClick={() => newGraph(P().tables[0].id)}>New Graph</button></Show></p>
  </Empty>
);
export const Empty = (p: { icon: string; title: string; children: JSX.Element }) => (
  <div class="page emptypage"><div class="emptybox"><Icon n={p.icon} size={42} /><h1>{p.title}</h1>{p.children}</div></div>
);
