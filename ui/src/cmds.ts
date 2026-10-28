// Commands shared by the ribbon, menus, shortcuts and Tell Me.
import { act, call, loadOut, out, setOut, setBackstage, toast, item, table, graph, analysis, curTable, open, P, openDialog } from "./store";
import { Out } from "./api";
import { FEATURES, ready } from "./features";
import { soon } from "./roadmap";
import { addSet, setDialog, removeSets, formulaDialog } from "./datatable";
import { copyGraph, exportGraph, newGraph, setZoomG } from "./graph";
import { formatGraph } from "./format";
import * as D from "./dialogs";
import { analyze, importFile, newTable, graphTypes, runAnalysis } from "./roadmap";
import * as T from "./tools";

const need = <T,>(v: T | undefined, what: string) => { if (!v) toast(`Open ${what} first.`); return v; };
export const C = {
  save: async (asNew = false) => { const o = await call<Out | null>("save", { asNew }); if (o) { setOut(o); toast(`Saved ${o.path}`, true); } },
  open: () => loadOut("open", { path: null }),
  undo: async () => setOut(await call<Out>("history", { redo: false })),
  redo: async () => setOut(await call<Out>("history", { redo: true })),
  print: () => setBackstage("print"),
  newTable: async (kind?: string) => { const o = await call<Out>("new_table", { kind: kind ?? null }); if (o) { setOut(o); setBackstage(null); const t = o.project.tables[o.project.tables.length - 1]; open("data", t.id); } },
  newGraph: () => { const t = need(curTable(), "a data table"); if (t) newGraph(t.id); },
  addSet: () => { const t = need(curTable(), "a data table"); if (t) addSet(t); },
  removeSets: () => { const t = need(curTable(), "a data table"); if (t) removeSets(t); },
  formatSet: (k = 0) => { const t = need(curTable(), "a data table"); if (t) setDialog(t, k); },
  rows: (count: number) => { const t = need(table(), "a data table"); if (t) act({ Rows: { table: t.id, at: count > 0 ? t.rows : Math.max(0, t.rows + count), count } }); },
  format: (page = "sets") => { const g = need(graph(), "a graph"); if (g) formatGraph(g, page); },
  exportG: (fmt = "png") => { const g = need(graph(), "a graph"); if (g) exportGraph(g, fmt); },
  copyG: () => { const g = need(graph(), "a graph"); if (g) copyGraph(g.id); },
  zoom: (f: number) => setZoomG(z => Math.min(4, Math.max(0.5, f ? z * f : 1.5))),
  rename: () => {
    const it = item(), cur = it.s === "data" ? table() : it.s === "results" ? analysis() : graph();
    if (!cur) return;
    const n = prompt("Name", cur.name);
    if (n?.trim()) act({ Rename: { id: cur.id, name: n.trim() } });
  },
  duplicate: () => { const cur = table() ?? graph() ?? analysis(); if (cur) act({ Duplicate: { id: cur.id } }); },
  del: () => {
    const cur = table() ?? graph() ?? analysis();
    if (!cur) return;
    const t = table(), gs = t ? P().graphs.filter(g => g.table === t.id).length : 0;
    if (t && P().tables.length === 1) return toast("A project keeps at least one data table.");
    if (confirm(t ? `Delete the data table “${t.name}”${gs ? ` and its ${gs} ${gs === 1 ? "graph" : "graphs"}` : ""} and its results?` : `Delete “${cur.name}”?`)) act({ Delete: { id: cur.id } });
  },
  analyze: () => analyze(),
};

/** Tell Me: [label, run, keys]. */
export const ALL_CMDS: [string, () => void, string?][] = [
  ["Save", () => C.save(), "Ctrl+S"], ["Save As", () => C.save(true), "Ctrl+Shift+S"], ["Open", C.open, "Ctrl+O"], ["New project (File › Home)", () => setBackstage("home"), "Ctrl+N"],
  ["Print or save as PDF", C.print, "Ctrl+P"], ["Undo", C.undo, "Ctrl+Z"], ["Redo", C.redo, "Ctrl+Y"],
  ["New XY data table", () => C.newTable()], ["New graph of this table", C.newGraph], ["Add data set", C.addSet], ["Format data set", () => C.formatSet()], ["Add 10 rows", () => C.rows(10)],
  ["Format graph", () => C.format("sets")], ["Format X axis", () => C.format("x")], ["Format Y axis", () => C.format("y")], ["Graph size and font", () => C.format("graph")],
  ["Export graph as PNG", () => C.exportG("png")], ["Export graph as TIFF", () => C.exportG("tiff")], ["Export graph as SVG", () => C.exportG("svg")], ["Export graph as PDF", () => C.exportG("pdf")], ["Copy graph as picture", C.copyG],
  ["Info sheet", () => open("info")], ["Show data table", () => open("data")], ["Show graph", () => open("graphs")],
  ["Rename", C.rename], ["Duplicate", C.duplicate], ["Delete table or graph", C.del],
  ["Options", () => setBackstage("options")], ["Check for updates", () => setBackstage("about")], ["Keyboard shortcuts", D.shortcuts, "F1"], ["Getting started", D.gettingStarted], ["Glossary", D.glossary],
  ["Import CSV, TXT or Excel", importFile], ["Linear regression", () => runAnalysis("B9")], ["Curve fit (nonlinear regression)", () => runAnalysis("B10")], ["Descriptive statistics", () => runAnalysis("B1")],
  ["Normality tests", () => runAnalysis("B2")], ["Outliers (Grubbs)", () => runAnalysis("B3")], ["Arrhenius / activation energy", () => runAnalysis("B28")], ["Interpolate unknowns from a standard curve", () => runAnalysis("B13")], ["New data table (choose a kind)", newTable], ["Graph type", graphTypes], ["Analyze data", analyze], ["Roadmap: what comes when", () => setBackstage("roadmap")],
  ["New column table (groups)", () => C.newTable("column")], ["New grouped table (two factors)", () => C.newTable("grouped")], ["Two-way ANOVA", () => runAnalysis("B15")], ["New contingency table (counts)", () => C.newTable("contingency")], ["New table of many variables", () => C.newTable("multi")], ["Multiple, logistic or Poisson regression", () => runAnalysis("B21")], ["Principal component analysis (PCA)", () => runAnalysis("B22")], ["Cluster analysis (hierarchical, k-means)", () => runAnalysis("B22c")], ["New survival table", () => C.newTable("survival")], ["New nested table (subgroups)", () => C.newTable("nested")], ["Nested t-test or one-way ANOVA", () => runAnalysis("B20")], ["Peak analysis (find and fit peaks)", () => runAnalysis("B24")], ["New worksheet (free columns)", () => C.newTable("sheet")], ["New matrix (Z on an X–Y grid)", () => C.newTable("matrix")], ["Surface fit (Z = f(X, Y))", () => runAnalysis("B26")], ["Import several files (one run per file)", () => import("./roadmap").then(m => m.importFiles())], ["Statistics of a region (drag on the graph)", () => import("./graph").then(m => m.zoomTool("region"))], ["Slides of every graph (.pptx)", () => import("./tools").then(m => m.exportReport("slides"))], ["Word report (.docx)", () => import("./tools").then(m => m.exportReport("word"))], ["Poster (A0)", () => import("./layout").then(m => m.templateLayout("poster"))], ["Slide layout (16:9)", () => import("./layout").then(m => m.templateLayout("slide"))], ["Column formula", () => { const t = need(curTable(), "a data table"); if (t) formulaDialog(t); }], ["Signal processing (Fourier spectrum, filters, resampling)", () => runAnalysis("B25")], ["Thermal analysis (DSC, TGA)", () => runAnalysis("B31")], ["S–N fatigue curve (Basquin)", () => runAnalysis("B30")], ["Survival analysis (Kaplan-Meier, log-rank)", () => runAnalysis("B19")], ["New parts-of-whole table (pie chart)", () => C.newTable("parts")], ["Fractions of total", () => runAnalysis("A6")], ["Add text to the graph", () => import("./graph").then(m => m.annotate("text"))], ["Add an arrow to the graph", () => import("./graph").then(m => m.annotate("arrow"))], ["Edit notes on the graph", () => C.format("notes")], ["Zoom to a box", () => import("./graph").then(m => m.zoomTool("zoom"))], ["Pan the graph", () => import("./graph").then(m => m.zoomTool("pan"))], ["Reset axes", () => { const g = graph(); if (g) import("./graph").then(m => m.resetAxes(g)); }], ["Axis break", () => C.format("y")], ["Second Y axis (right)", () => C.format("sets")], ["Bland-Altman (agreement of two methods)", () => runAnalysis("B18")], ["ROC curve", () => runAnalysis("B18r")], ["Chi-square and Fisher's exact test", () => runAnalysis("B17")], ["t-test", () => runAnalysis("B4")], ["One-way ANOVA", () => runAnalysis("B6")], ["Multiple comparisons (Tukey, Dunnett)", () => runAnalysis("B7")],
  ["Nonparametric tests (Mann-Whitney, Kruskal-Wallis)", () => runAnalysis("B5")], ["Effect sizes", () => runAnalysis("B8")], ["Correlation", () => runAnalysis("B16")], ["Power and sample size", () => runAnalysis("B23")],
  ["Transform (log, normalise, baseline)", () => runAnalysis("A15")], ["Check data", () => runAnalysis("A18")], ["Frequency distribution (histogram)", () => runAnalysis("D4")], ["Area under the curve", () => runAnalysis("B14")],
  ["Smooth, derivative or integral", () => runAnalysis("B14s")], ["Global fit and model comparison", () => runAnalysis("B12")], ["Tensile test analysis", () => runAnalysis("B27")], ["Weibull analysis", () => runAnalysis("B29")],
  ["New page layout", () => import("./layout").then(m => m.newLayout())], ["Remove data sets", () => C.removeSets()], ["Sort rows", T.sortDialog], ["Find", T.findDialog, "Ctrl+F"], ["Exclude rows by a rule", T.excludeRows], ["Test chooser", T.testChooser], ["Statistics guide", T.statsGuide], ["Significance brackets", T.significance],
  ["Graph styles (Nature, IEEE, presentation…)", () => import("./store").then(m => m.openMenu({ x: 300, y: 120 }, T.styleMenu()))], ["Copy look to other graphs", T.copyLook], ["Colour schemes", T.paletteDialog],
  ["Export all graphs", T.exportAll], ["Export to Excel workbook", T.exportExcel],
  ...FEATURES.filter(f => !ready(f[0])).map(f => [`${f[1]} (${f[2]})`, () => soon(f[0])] as [string, () => void]),
];
export { out, openDialog };
