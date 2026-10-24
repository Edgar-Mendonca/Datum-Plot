// Commands shared by the ribbon, menus, shortcuts and Tell Me.
import { act, call, loadOut, out, setOut, setBackstage, toast, item, table, graph, curTable, open, P, openDialog } from "./store";
import { Out } from "./api";
import { FEATURES, ready } from "./features";
import { soon } from "./roadmap";
import { addSet, setDialog } from "./datatable";
import { copyGraph, exportGraph, newGraph, setZoomG } from "./graph";
import { formatGraph } from "./format";
import * as D from "./dialogs";
import { analyze, importFile, newTable, graphTypes } from "./roadmap";

const need = <T,>(v: T | undefined, what: string) => { if (!v) toast(`Open ${what} first.`); return v; };
export const C = {
  save: async (asNew = false) => { const o = await call<Out | null>("save", { asNew }); if (o) { setOut(o); toast(`Saved ${o.path}`, true); } },
  open: () => loadOut("open", { path: null }),
  undo: async () => setOut(await call<Out>("history", { redo: false })),
  redo: async () => setOut(await call<Out>("history", { redo: true })),
  print: () => setBackstage("print"),
  newTable: async () => { const o = await call<Out>("new_table"); if (o) { setOut(o); const t = o.project.tables[o.project.tables.length - 1]; open("data", t.id); } },
  newGraph: () => { const t = need(curTable(), "a data table"); if (t) newGraph(t.id); },
  addSet: () => { const t = need(curTable(), "a data table"); if (t) addSet(t); },
  formatSet: (k = 0) => { const t = need(curTable(), "a data table"); if (t) setDialog(t, k); },
  rows: (count: number) => { const t = need(table(), "a data table"); if (t) act({ Rows: { table: t.id, at: count > 0 ? t.rows : Math.max(0, t.rows + count), count } }); },
  format: (page = "sets") => { const g = need(graph(), "a graph"); if (g) formatGraph(g, page); },
  exportG: (fmt = "png") => { const g = need(graph(), "a graph"); if (g) exportGraph(g, fmt); },
  copyG: () => { const g = need(graph(), "a graph"); if (g) copyGraph(g.id); },
  zoom: (f: number) => setZoomG(z => Math.min(4, Math.max(0.5, f ? z * f : 1.5))),
  rename: () => {
    const it = item(), cur = it.s === "data" ? table() : graph();
    if (!cur) return;
    const n = prompt("Name", cur.name);
    if (n?.trim()) act({ Rename: { id: cur.id, name: n.trim() } });
  },
  duplicate: () => { const cur = table() ?? graph(); if (cur) act({ Duplicate: { id: cur.id } }); },
  del: () => {
    const cur = table() ?? graph();
    if (!cur) return;
    const t = table(), gs = t ? P().graphs.filter(g => g.table === t.id).length : 0;
    if (t && P().tables.length === 1) return toast("A project keeps at least one data table.");
    if (confirm(t ? `Delete the data table “${t.name}”${gs ? ` and its ${gs} ${gs === 1 ? "graph" : "graphs"}` : ""}?` : `Delete the graph “${cur.name}”?`)) act({ Delete: { id: cur.id } });
  },
  analyze: () => analyze(),
};

/** Tell Me: [label, run, keys]. */
export const ALL_CMDS: [string, () => void, string?][] = [
  ["Save", () => C.save(), "Ctrl+S"], ["Save As", () => C.save(true), "Ctrl+Shift+S"], ["Open", C.open, "Ctrl+O"], ["New project (File › Home)", () => setBackstage("home"), "Ctrl+N"],
  ["Print or save as PDF", C.print, "Ctrl+P"], ["Undo", C.undo, "Ctrl+Z"], ["Redo", C.redo, "Ctrl+Y"],
  ["New XY data table", C.newTable], ["New graph of this table", C.newGraph], ["Add data set", C.addSet], ["Format data set", () => C.formatSet()], ["Add 10 rows", () => C.rows(10)],
  ["Format graph", () => C.format("sets")], ["Format X axis", () => C.format("x")], ["Format Y axis", () => C.format("y")], ["Graph size and font", () => C.format("graph")],
  ["Export graph as PNG", () => C.exportG("png")], ["Export graph as TIFF", () => C.exportG("tiff")], ["Export graph as SVG", () => C.exportG("svg")], ["Export graph as PDF", () => C.exportG("pdf")], ["Copy graph as picture", C.copyG],
  ["Info sheet", () => open("info")], ["Show data table", () => open("data")], ["Show graph", () => open("graphs")],
  ["Rename", C.rename], ["Duplicate", C.duplicate], ["Delete table or graph", C.del],
  ["Options", () => setBackstage("options")], ["Check for updates", () => setBackstage("about")], ["Keyboard shortcuts", D.shortcuts, "F1"], ["Getting started", D.gettingStarted], ["Glossary", D.glossary],
  ["Import CSV, TXT or Excel", importFile], ["New data table (choose a kind)", newTable], ["Graph type", graphTypes], ["Analyze data", analyze], ["Roadmap: what comes when", () => setBackstage("roadmap")],
  ...FEATURES.filter(f => !ready(f[0])).map(f => [`${f[1]} (${f[2]})`, () => soon(f[0])] as [string, () => void]),
];
export { out, openDialog };
