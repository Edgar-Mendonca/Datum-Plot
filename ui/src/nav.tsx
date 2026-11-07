// The sidebar (Info, Data, Results, Graphs, Layouts), the navigator next to it, and
// the Info sheet and empty pages.
import { For, Show, JSX, createSignal } from "solid-js";
import { Info } from "./api";
import { P, item, open, Section, navOpen, act, openMenu, thumbs, setThumbs, graph } from "./store";
import { C } from "./cmds";
import { newGraph, useRender, GraphImg, copyGraph, exportGraph } from "./graph";
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
export const Navigator = () => {
  const ctx = (e: MouseEvent, id: number, s: Section) => { e.preventDefault(); e.stopPropagation(); open(s, id); openMenu(e, [
    ...(s === "data" ? [{ label: "New Graph of This Table", icon: "graph", run: () => newGraph(id) }, "-" as const] : []),
    ...(s === "graphs" ? [{ label: "Copy Picture", icon: "copy", run: () => copyGraph(id) }, { label: "Export…", icon: "export", run: () => { const g = P().graphs.find(x => x.id === id); if (g) exportGraph(g); } },
      { label: "New Layout with This Graph", icon: "layout", run: () => newLayout([id]) }, { label: thumbs() ? "Hide Previews" : "Show Previews", icon: "image", run: () => setThumbs(!thumbs()) }, "-" as const] : []),
    ...(s === "layouts" ? [{ label: "Copy Picture", icon: "copy", run: () => copyPage(id) }, { label: "Export…", icon: "export", run: () => { const l = P().layouts?.find(x => x.id === id); if (l) exportLayout(l); } }, "-" as const] : []),
    { label: "Rename…", icon: "rename", run: C.rename },
    ...(s === "data" ? [{ label: "Duplicate with Graphs and Results", icon: "copy", run: () => C.duplicate(false) }, { label: "Duplicate Table Only", icon: "copy", run: () => C.duplicate(true) }] : [{ label: "Duplicate", icon: "copy", run: () => C.duplicate() }]),
    { label: "Delete", icon: "del", run: C.del },
  ]); };
  /** 0.3.15 (#29): the Graphs ＋ asks: a new graph of a table, or a copy of the open graph with all its formatting. */
  const addGraph = (e: MouseEvent) => openMenu(e, [
    ...(graph() ? [{ label: `Duplicate “${graph()!.name}” (keeps its formatting)`, icon: "copy", run: () => C.duplicate() }, "-" as const] : []),
    ...P().tables.map(t => ({ label: `New Graph of “${t.name}”`, icon: "graph", run: () => newGraph(t.id) })),
  ]);
  return (
    <Show when={navOpen()}>
      <aside class="nav" style={{ width: `${navW()}px` }}>
        <button class="nitem" classList={{ on: item().s === "info" }} onClick={() => open("info")}><Icon n="infosheet" /><span>{P().info.title || "Project info"}</span></button>
        <Head l="Data tables" h="navigator" add={newTable} title="New data table" />
        <For each={P().tables}>{t => <button class="nitem" classList={{ on: item().s === "data" && item().id === t.id }} onClick={() => open("data", t.id)} onContextMenu={e => ctx(e, t.id, "data")} onDblClick={C.rename}><Icon n={t.kind === "column" ? "table" : "sheet"} /><span title={t.name}>{t.name}</span></button>}</For>
        <Head l="Results" h="results" add={() => analyze()} title="Analyze data" />
        <For each={P().analyses ?? []} fallback={<p class="nnone">Analyze… adds results here</p>}>{a => <button class="nitem" classList={{ on: item().s === "results" && item().id === a.id }} onClick={() => open("results", a.id)} onContextMenu={e => ctx(e, a.id, "results")} onDblClick={C.rename}><Icon n="results" /><span title={a.name}>{a.name}</span></button>}</For>
        <Head l="Graphs" h="graphview" add={addGraph} title="A new graph of a table, or a copy of this graph" />
        {/* 0.3.14 (a user's request): each graph's preview sits under its name; View › Thumbnails or a right-click hides them. */}
        <For each={P().graphs}>{g => <>
          <button class="nitem" classList={{ on: item().s === "graphs" && item().id === g.id }} onClick={() => open("graphs", g.id)} onContextMenu={e => ctx(e, g.id, "graphs")} onDblClick={C.rename}><Icon n="graph" /><span title={g.name}>{g.name}</span></button>
          <Show when={thumbs()}><div class="nthumbs" onContextMenu={e => ctx(e, g.id, "graphs")}><Thumb id={g.id} on={item().s === "graphs" && item().id === g.id} /></div></Show>
        </>}</For>
        <Head l="Layouts" h="layouts" add={() => newLayout()} title="New layout of the graphs" />
        <For each={P().layouts ?? []} fallback={<p class="nnone">＋ arranges graphs on a page</p>}>{l => <button class="nitem" classList={{ on: item().s === "layouts" && item().id === l.id }} onClick={() => open("layouts", l.id)} onContextMenu={e => ctx(e, l.id, "layouts")} onDblClick={C.rename}><Icon n="layout" /><span title={l.name}>{l.name}</span></button>}</For>
      </aside>
      <i class="navrsz" title="Drag to widen the panel; double-click for the usual width" onMouseDown={widen} onDblClick={() => keepW(190)} />
    </Show>
  );
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
