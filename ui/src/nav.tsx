// The sidebar (Info, Data, Results, Graphs, Layouts), the Prism-style navigator next to it, and
// the Info sheet and empty pages.
import { For, Show, JSX } from "solid-js";
import { Info } from "./api";
import { P, item, open, Section, navOpen, act, openMenu, setBackstage, thumbs } from "./store";
import { C } from "./cmds";
import { newGraph, useRender, GraphImg } from "./graph";
import { Icon } from "./ui";
import { analyze, soon, newTable } from "./roadmap";

export const SIDE: [Section, string, string][] = [["info", "infosheet", "Info"], ["data", "sheet", "Data"], ["results", "results", "Results"], ["graphs", "graph", "Graphs"], ["layouts", "layout", "Layouts"]];

export const Side = () => (
  <nav class="side"><For each={SIDE}>{([s, i, l], k) => <>{k() === 1 && <hr />}<button classList={{ on: item().s === s }} onClick={() => open(s)} title={l}><Icon n={i} /><span>{l}</span></button></>}</For></nav>
);

const Head = (p: { l: string; add?: () => void; title?: string }) => <div class="nhead"><span>{p.l}</span>{p.add && <button title={p.title} onClick={p.add}>＋</button>}</div>;
export const Navigator = () => {
  const ctx = (e: MouseEvent, id: number, s: Section) => { open(s, id); openMenu(e, [
    ...(s === "data" ? [{ label: "New Graph of This Table", icon: "graph", run: () => newGraph(id) }, "-" as const] : []),
    { label: "Rename…", icon: "rename", run: C.rename }, { label: "Duplicate", icon: "copy", run: C.duplicate }, { label: "Delete", icon: "del", run: C.del },
  ]); };
  return (
    <Show when={navOpen()}>
      <aside class="nav">
        <button class="nitem" classList={{ on: item().s === "info" }} onClick={() => open("info")}><Icon n="infosheet" /><span>{P().info.title || "Project info"}</span></button>
        <Head l="Data tables" add={newTable} title="New data table" />
        <For each={P().tables}>{t => <button class="nitem" classList={{ on: item().s === "data" && item().id === t.id }} onClick={() => open("data", t.id)} onContextMenu={e => ctx(e, t.id, "data")} onDblClick={C.rename}><Icon n={t.kind === "column" ? "table" : "sheet"} /><span>{t.name}</span></button>}</For>
        <Head l="Results" add={() => analyze()} title="Analyze data" />
        <For each={P().analyses ?? []} fallback={<p class="nnone">Analyze… adds results here</p>}>{a => <button class="nitem" classList={{ on: item().s === "results" && item().id === a.id }} onClick={() => open("results", a.id)} onContextMenu={e => ctx(e, a.id, "results")} onDblClick={C.rename}><Icon n="results" /><span>{a.name}</span></button>}</For>
        <Head l="Graphs" add={C.newGraph} title="New graph of the open table" />
        <For each={P().graphs}>{g => <button class="nitem" classList={{ on: item().s === "graphs" && item().id === g.id }} onClick={() => open("graphs", g.id)} onContextMenu={e => ctx(e, g.id, "graphs")} onDblClick={C.rename}><Icon n="graph" /><span>{g.name}</span></button>}</For>
        <Show when={thumbs() && P().graphs.length}><div class="nthumbs"><For each={P().graphs}>{g => <Thumb id={g.id} on={item().s === "graphs" && item().id === g.id} />}</For></div></Show>
        <Head l="Layouts" add={() => soon("F1")} title="New layout (0.2.3)" />
        <p class="nnone">Page layouts arrive in 0.2.3</p>
      </aside>
    </Show>
  );
};

/** A small picture of a graph (E7); the shell keeps recent renders, so unchanged graphs cost nothing. */
const Thumb = (p: { id: number; on: boolean }) => {
  const [r] = useRender(() => p.id);
  return <button class="nthumb" classList={{ on: p.on }} title={P().graphs.find(g => g.id === p.id)?.name} onClick={() => open("graphs", p.id)}>
    <Show when={r()} fallback={<span class="muted">…</span>}>{x => <GraphImg r={x()} scale={Math.min(150 / x().w, 100 / x().h)} />}</Show></button>;
};

/** Prism's Info sheet: what the experiment is. Fields can go into page headers. */
export const InfoPage = () => {
  const put = (k: keyof Info, v: string) => act({ Info: { info: { ...P().info, [k]: v } } });
  const F = (p: { k: keyof Info; l: string; hint: string; area?: boolean }) => <div class="opt"><div><b>{p.l}</b><small>{p.hint}</small></div><div class="ctl">{p.area
    ? <textarea rows="8" value={P().info[p.k]} onChange={e => put(p.k, e.currentTarget.value)} /> : <input value={P().info[p.k]} onChange={e => put(p.k, e.currentTarget.value)} />}</div></div>;
  return (
    <div class="page infopage"><div class="options">
      <h1>Info</h1>
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

export const Empty = (p: { icon: string; title: string; children: JSX.Element }) => (
  <div class="page emptypage"><div class="emptybox"><Icon n={p.icon} size={42} /><h1>{p.title}</h1>{p.children}</div></div>
);
export const LayoutsPage = () => (
  <Empty icon="layout" title="Layouts">
    <p>A layout is a page that arranges several graphs, tables and text, with panel letters A, B, C, ready for a paper or a poster.</p>
    <p class="muted">Layouts arrive in 0.2.3. Until then, print each graph from File › Print, or export it and arrange it in your document.</p>
    <p><button class="btn" onClick={() => setBackstage("print")}>Print a graph</button></p>
  </Empty>
);
