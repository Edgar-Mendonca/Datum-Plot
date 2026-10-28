// Title bar, quick access toolbar, Tell Me and the ribbon (Data, Analyze, Graph, Format, View, Help).
import { For, Show, JSX, createSignal, createMemo, onMount } from "solid-js";
import { call, toast, out, tab, setTab, setBackstage, openMenu, Item, closeDialog, openDialog, theme, setTheme, item, graph, table, navOpen, setNavOpen, open as openView, curTable, thumbs, setThumbs } from "./store";
import { C, ALL_CMDS } from "./cmds";
import * as D from "./dialogs";
import { Icon } from "./ui";
import * as F from "./fmt";
import { setG, ERRORS, SIZES, MATRIX, FONTS as GFONTS } from "./format";
import { GraphSettings } from "./api";
import { feature } from "./features";
import { formulaDialog } from "./datatable";
import { soon, newTable, analyze, graphTypes, importFile, importFiles, runAnalysis } from "./roadmap";
import * as T from "./tools";
import * as L from "./layout";
import { Layout } from "./api";
import { annotate, zoomTool, zoomOut, resetAxes } from "./graph";
import { Help, helpCard, HELP } from "./help";

const GH = "https://github.com/Edgar-Mendonca/Datum-Plot";
export const FONTS = ["Arial", "Calibri", "Segoe UI", "Tahoma", "Verdana", "Times New Roman", "Cambria", "Georgia", "Consolas", "IBM Plex Sans"];
const COLORS: [string, string][] = [["Red", "#C0392B"], ["Orange", "#E67E22"], ["Amber", "#B7950B"], ["Green", "#1E8449"], ["Blue", "#0E8C7F"], ["Dark Blue", "#0C1A2B"], ["Purple", "#7D3C98"], ["Grey", "#7F8C8D"]];
const FILLS: [string, string][] = [["Yellow", "#FFF2CC"], ["Green", "#E2F0D9"], ["Blue", "#DDEBF7"], ["Red", "#FADBD8"], ["Orange", "#FCE4D6"], ["Purple", "#E8DAEF"], ["Grey", "#EDEDED"]];
const pickColor = (k: "c" | "f") => { const i = document.createElement("input"); i.type = "color"; i.value = F.current()[k] || (k === "c" ? "#000000" : "#ffffff"); i.onchange = () => F.setProp(k, i.value); i.click(); };
const colorMenu = (k: "c" | "f"): Item[] => [{ label: k === "c" ? "Automatic" : "No Fill", run: () => F.setProp(k, undefined) }, ...(k === "c" ? COLORS : FILLS).map(([l, v]) => ({ label: l, run: () => F.setProp(k, v), on: F.current()[k] === v })), "-", { label: "More Colors…", run: () => pickColor(k) }];
/** Excel-style Font and Alignment controls; they act on the selected cells of the task sheet or a sheet tab. */
const Font = () => {
  const s = () => F.current(), [last, setLast] = createSignal<[string, string]>(["#C0392B", "#FFF2CC"]);
  const T = (p: { k: "b" | "i" | "u" | "s"; l: string; t: string; st: JSX.CSSProperties }) => <button class="rb fb" classList={{ on: !!s()[p.k] }} title={p.t} onClick={() => F.toggle(p.k)}><span style={p.st}>{p.l}</span></button>;
  const A = (p: { a: string; i: string; t: string }) => <button class="rb fb" classList={{ on: (s().a || "") === p.a }} title={p.t} onClick={() => F.setProp("a", p.a || undefined)}><Icon n={p.i} /></button>;
  return <>
    <G l="Font" h="font"><div class="fontg">
      <div><select class="ffam" title="Font" value={s().n || ""} onChange={e => F.setProp("n", e.currentTarget.value || undefined)}><option value="">Default font</option><For each={FONTS}>{f => <option value={f} style={{ "font-family": `'${f}'` }}>{f}</option>}</For></select>
        <select class="fsize" title="Font size" value={String(s().z || 12)} onChange={e => F.setProp("z", +e.currentTarget.value === 12 ? undefined : +e.currentTarget.value)}><For each={[8, 9, 10, 11, 12, 13, 14]}>{z => <option value={z}>{z}</option>}</For></select>
        <button class="rb fb" title="Increase font size" onClick={() => F.setProp("z", Math.min(14, (s().z || 12) + 1))}><span>A<sup>+</sup></span></button><button class="rb fb" title="Decrease font size" onClick={() => F.setProp("z", Math.max(8, (s().z || 12) - 1))}><span>A<sup>−</sup></span></button></div>
      <div><T k="b" l="B" t="Bold (Ctrl+B)" st={{ "font-weight": 700 }} /><T k="i" l="I" t="Italic (Ctrl+I)" st={{ "font-style": "italic" }} /><T k="u" l="U" t="Underline (Ctrl+U)" st={{ "text-decoration": "underline" }} /><T k="s" l="S" t="Strikethrough" st={{ "text-decoration": "line-through" }} />
        <span class="fcol"><button class="rb fb" title="Font color" onClick={() => F.setProp("c", last()[0])}><span class="ca">A<i style={{ background: last()[0] }} /></span></button><button class="rb split" onClick={e => openMenu(e, colorMenu("c").map(x => x === "-" || !x.run ? x : { ...x, run: () => { x.run!(); const v = F.current().c; if (v) setLast([v, last()[1]]); } }))}>▾</button></span>
        <span class="fcol"><button class="rb fb" title="Fill color" onClick={() => F.setProp("f", last()[1])}><span class="ca"><Icon n="bucket" /><i style={{ background: last()[1] }} /></span></button><button class="rb split" onClick={e => openMenu(e, colorMenu("f").map(x => x === "-" || !x.run ? x : { ...x, run: () => { x.run!(); const v = F.current().f; if (v) setLast([last()[0], v]); } }))}>▾</button></span></div>
    </div></G>
    <G l="Alignment" h="alignment"><div class="fontg"><div><A a="" i="al" t="Align left" /><A a="c" i="ac" t="Center" /><A a="r" i="ar" t="Align right" /></div><div><button class="rb fb" title="Clear Formatting" onClick={F.clearFmt}><Icon n="clear" /></button></div></div></G>
  </>;
};

const B = (p: { i: string; l: string; run?: (e: MouseEvent) => void; big?: boolean; on?: boolean; off?: boolean; dd?: (e: MouseEvent) => void; title?: string; soon?: boolean }) => p.big && p.run && p.dd ? (
  // MS Project split button: the picture runs the command, the label opens the menu.
  <div class="rbw big splitbig" classList={{ on: p.on }}>
    <button class="rb top" title={p.title ?? p.l} onClick={e => p.run!(e)}><Icon n={p.i} /></button>
    <button class="rb bot" title={`${p.l} options`} onClick={e => p.dd!(e)}><span>{p.l}</span><b class="car">▾</b></button>
  </div>
) : (
  <div class="rbw" classList={{ big: p.big }}>
    <button class="rb" classList={{ big: p.big, on: p.on, soonb: p.soon }} disabled={p.off} title={p.title ?? p.l} onClick={e => (p.run ?? p.dd)?.(e)}><Icon n={p.i} />{p.big ? <span>{p.l}{p.dd && !p.run ? " ▾" : ""}</span> : <span>{p.l}</span>}{!p.big && p.dd && !p.run && <b class="car">▾</b>}</button>
    {p.run && p.dd && <button class="rb split" onClick={e => p.dd!(e)}>▾</button>}
  </div>
);
const G = (p: { l: string; h?: string; children: JSX.Element }) => <div class="grp"><div class="items">{p.children}</div><div class="cap">{p.l}{p.h && <Help k={p.h} />}</div></div>;
const S = (p: { children: JSX.Element }) => <div class="stack">{p.children}</div>;
/** A planned command: it has its place now and says when it arrives (feature catalogue id). */
const N = (p: { i: string; l: string; id: string; big?: boolean }) => { const f = feature(p.id); return <B i={p.i} l={p.l} big={p.big} soon title={`${p.l}: arrives in ${f?.[2]} (${p.id})`} run={() => soon(p.id)} />; };

/** Tell Me / command search (Ctrl+K, Alt+Q). */
export const palette = () => openDialog(() => {
  const [q, setQ] = createSignal(""), [k, setK] = createSignal(0);
  const list = createMemo(() => { const s = q().toLowerCase(); return ALL_CMDS.filter(c => c[0].toLowerCase().includes(s)).slice(0, 14); });
  const go = (i: number) => { const c = list()[i]; if (c) { closeDialog(); setTimeout(() => c[1]()); } };
  let input!: HTMLInputElement;
  onMount(() => input.focus());
  return (
    <div class="ov top" onMouseDown={e => e.target === e.currentTarget && closeDialog()}>
      <div class="pal">
        <input ref={input} placeholder="Tell me what you want to do" value={q()} onInput={e => { setQ(e.currentTarget.value); setK(0); }}
          onKeyDown={e => { if (e.key === "ArrowDown") { e.preventDefault(); setK(Math.min(list().length - 1, k() + 1)); } else if (e.key === "ArrowUp") { e.preventDefault(); setK(Math.max(0, k() - 1)); } else if (e.key === "Enter") { e.preventDefault(); go(k()); } else if (e.key === "Escape") closeDialog(); }} />
        <div class="pl"><For each={list()}>{(c, i) => <button classList={{ on: i() === k() }} onMouseEnter={() => setK(i())} onClick={() => go(i())}><span>{c[0]}</span>{c[2] && <kbd>{c[2]}</kbd>}</button>}</For></div>
      </div>
    </div>
  );
});

export const TitleBar = (p: { update: string | null }) => (
  <header class="top">
    <div class="bar">
      <div class="qat">
        <img src="logo.svg" alt="" class="logo" />
        <button title="Save (Ctrl+S)" onClick={() => C.save()}><Icon n="save" /></button>
        <button title="Undo (Ctrl+Z)" disabled={!out()?.undo} onClick={C.undo}><Icon n="undo" /></button>
        <button title="Redo (Ctrl+Y)" disabled={!out()?.redo} onClick={C.redo}><Icon n="redo" /></button>
        <button title="Print (Ctrl+P)" onClick={C.print}><Icon n="print" /></button>
      </div>
      <div class="title">{out() ? `${out()!.project.name}${out()!.dirty ? " •" : ""} — Datum Plot` : "Datum Plot"}</div>
      <button class="search" onClick={palette} title="Tell me what you want to do (Alt+Q)"><Icon n="search" /><span>Tell me what you want to do</span><kbd>Ctrl+K</kbd></button>
      <Show when={p.update}><button class="upd" onClick={() => setBackstage("about")}>Update {p.update} available</button></Show>
      <button class="theme" title="Theme: Auto follows Windows" onClick={() => setTheme(theme() === "auto" ? "light" : theme() === "light" ? "dark" : "auto")}>Theme · {theme()}</button>
    </div>
    <nav class="tabs">
      <button class="file" onClick={() => setBackstage("home")}>File</button>
      <For each={[["data", "Data"], ["analyze", "Analyze"], ["graph", "Graph"], ["layout", "Layout"], ["tools", "Tools"], ["view", "View"], ["help", "Help"]]}>{([k, l]) => <button classList={{ on: tab() === k }} onClick={() => setTab(k)}>{l}</button>}</For>
      <Show when={item().s === "graphs"}><div class="ctxgrp"><small>Graph Tools</small><button classList={{ on: tab() === "format" }} onClick={() => setTab("format")}>Format</button></div></Show>
    </nav>
  </header>
);

/** Shrinks the ribbon in steps (labels of small buttons, then of big ones) instead of scrolling sideways. */
const fitRibbon = (el: HTMLElement) => {
  // Tighten everything first, then fold groups from the right: small-button labels, then big-button labels.
  const fit = () => {
    const gs = [...el.querySelectorAll<HTMLElement>(":scope > .grp")];
    el.dataset.fit = "0"; gs.forEach(g => delete g.dataset.fit);
    const over = () => el.scrollWidth > el.clientWidth + 1;
    if (!over()) return;
    el.dataset.fit = "1";
    for (const lvl of ["2", "3"]) for (let i = gs.length - 1; i >= 0 && over(); i--) gs[i].dataset.fit = lvl;
  };
  new ResizeObserver(fit).observe(el);
  new MutationObserver(() => requestAnimationFrame(fit)).observe(el, { childList: true, subtree: false });
};
const gs = (): GraphSettings | undefined => graph()?.settings;
const setGS = (f: (s: GraphSettings) => void) => { const g = graph(); if (!g) return toast("Open a graph first."); setG(g, s => { f(s); return s; }); };
const errorMenu = (): Item[] => ERRORS.map(([k, l]) => ({ label: l, on: gs()?.error === k && gs()?.points !== "each", run: () => setGS(s => { s.error = k; s.points = "mean"; }) }));
const sizeMenu = (): Item[] => SIZES.map(([l, w, h]) => ({ label: l, on: gs()?.width === w && gs()?.height === h, run: () => setGS(s => { s.width = w; s.height = h; }) }));
const COLUMNS: [string, string][] = [["scatter", "Scatter dot plot (mean ± error)"], ["bars", "Bars (mean ± error)"], ["box", "Box and whiskers"], ["violin", "Violin"], ["mean", "Mean ± error only"], ["paired", "Before–after (rows joined)"]];
const GROUPED: [string, string][] = [["bars", "Grouped bars"], ["stacked", "Stacked bars"], ["percent", "Stacked to 100%"], ["scatter", "Grouped dots (mean ± error)"], ["lines", "Lines (interaction plot)"], ["heatmap", "Heat map of the means"]];
const PARTS: [string, string][] = [["pie", "Pie"], ["donut", "Donut"], ["percent", "Bars stacked to 100%"]];
const columnMenu = (): Item[] => curTable()?.kind === "matrix" ? MATRIX.map(([k, l]) => ({ label: l, on: (gs()?.column || "contour") === k, run: () => setGS(s => { s.column = k; }) })) : curTable()?.kind === "parts" ? PARTS.map(([k, l]) => ({ label: l, on: (gs()?.column || "pie") === k, run: () => setGS(s => { s.column = k; }) })) : curTable()?.kind === "grouped" || curTable()?.kind === "contingency" ? [...GROUPED.map(([k, l]) => ({ label: l, on: (gs()?.column || "bars") === k, run: () => setGS(s => { s.column = k; }) })), "-",
  { label: "Show Each Value", on: gs()?.points === "each", run: () => setGS(s => { s.points = s.points === "each" ? "mean" : "each"; }) }] : [...COLUMNS.map(([k, l]) => ({ label: l, on: (gs()?.column || "scatter") === k, run: () => setGS(s => { s.column = k; }) })), "-",
  { label: "Show Each Value", on: gs()?.points === "each", run: () => setGS(s => { s.points = s.points === "each" ? "mean" : "each"; }) }];
const ZOOM = (): Item[] => [{ label: "Statistics of a Region", icon: "sigma", run: () => zoomTool("region") }, { label: "Zoom to a Box", icon: "zin", run: () => zoomTool("zoom") }, { label: "Pan (drag)", run: () => zoomTool("pan") }, { label: "Zoom Out", icon: "zout", run: () => { const g = graph(); if (g) zoomOut(g); } },
  { label: "Reset Axes", icon: "fit", run: () => { const g = graph(); if (g) resetAxes(g); } }];
const ANNOT = (): Item[] => [...[["text", "Text"], ["arrow", "Arrow"], ["line", "Line"], ["box", "Box"]].map(([k, l]) => ({ label: l, run: () => annotate(k) })), "-", { label: "Edit Notes…", run: () => C.format("notes") }];
/** Runs `f` on the open layout (or says how to get one). */
const lay = (f: (l: Layout) => void) => { const it = item(), l = it.s === "layouts" ? out()?.project.layouts?.find(x => x.id === it.id) : undefined; if (l) f(l); else toast(out()?.project.layouts?.length ? "Open a layout first (Layouts in the navigator)." : "Make a layout first: New Layout."); };
const exportMenu = (): Item[] => [["Export…", "png"], ["PNG picture", "png"], ["TIFF picture", "tiff"], ["SVG vector", "svg"], ["PDF vector", "pdf"], ["EPS vector", "eps"]].map(([l, f], i) => ({ label: l, icon: i ? undefined : "export", run: () => C.exportG(f) }));
export const Ribbon = () => (
  <section class="ribbon" ref={fitRibbon}>
    <Show when={tab() === "data"}>
      <G l="Clipboard" h="clipboard"><B big i="paste" l="Paste" run={() => document.execCommand("paste")} dd={e => openMenu(e, [{ label: "Paste", icon: "paste", run: () => document.execCommand("paste"), keys: "Ctrl+V" }, { label: "Paste Special…", icon: "paste", run: () => D.pasteSpecial(), keys: "Ctrl+Alt+V" }, "-", { label: "Paste Values", run: () => F.target()?.paste?.("values", false) }, { label: "Paste Formatting", icon: "paint", run: () => F.target()?.paste?.("formats", false) }, { label: "Transpose", run: () => F.target()?.paste?.("all", true) }])} />
        <S><B i="cut" l="Cut" run={() => document.execCommand("cut")} /><B i="copy" l="Copy" run={() => document.execCommand("copy")} /><B i="paint" l="Format Painter" run={F.paint} on={F.painter() !== null} /></S></G>
      <Font />
      <G l="Insert" h="insert"><B big i="sheet" l="New Table" title="Choose a kind of data table" run={newTable} /><B big i="import" l="Import" title="A CSV, TXT, .xlsx or .pzfx file; plate-reader sheets become plates" run={importFile} /><B big i="folder" l="Several Files" title="Several runs at once: one data set per file" run={importFiles} /><S><B i="addset" l="Add Data Set" run={C.addSet} /><B i="del" l="Remove Data Set" title="Delete data sets (columns) and their values" run={C.removeSets} /></S><S><B i="addrow" l="Add 10 Rows" run={() => C.rows(10)} /><B i="delrow" l="Remove Last Row" run={() => C.rows(-1)} /></S></G>
      <G l="Transform" h="transform"><S><B i="fx" l="Transform" title="A new table of log, 1/X, normalised… values" run={() => runAnalysis("A15")} /><B i="fx" l="Column Formula" title="Fill a data set from the others: log10(A), (B - mean(B)) / sd(B)…" run={() => { const t = curTable(); if (t) formulaDialog(t); else toast("Open a data table first."); }} /><B i="sort" l="Sort" run={T.sortDialog} /></S>
        <S><B i="find" l="Find" title="Ctrl+F" run={T.findDialog} /><B i="filter" l="Exclude Rows" title="Exclude rows by a rule" run={T.excludeRows} /><B i="check" l="Check Data" run={() => runAnalysis("A18")} /></S><S><B i="exclude" l="Find Outliers" run={() => runAnalysis("A16")} /></S></G>
      <G l="Values" h="values"><S><B i="exclude" l="Exclude / Include" title="Leave the selected values out of graphs (Ctrl+E)" run={() => document.querySelector(".dgrid")?.dispatchEvent(new KeyboardEvent("keydown", { key: "e", ctrlKey: true, bubbles: true }))} /><B i="opts" l="Format Data Set" run={() => C.formatSet()} /><B i="filldown" l="Fill Down" title="Ctrl+D" run={() => document.querySelector(".dgrid")?.dispatchEvent(new KeyboardEvent("keydown", { key: "d", ctrlKey: true, bubbles: true }))} /></S></G>
      <G l="Graph" h="graph"><B big i="graph" l="New Graph" run={C.newGraph} /><B big i="xy" l="Show Graph" run={() => openView("graphs")} /></G>
      <G l="Item" h="item"><S><B i="rename" l="Rename" run={C.rename} /><B i="copy" l="Duplicate" run={C.duplicate} /><B i="del" l="Delete" run={C.del} /></S></G>
    </Show>
    <Show when={tab() === "analyze"}>
      <G l="Analyze" h="analyze"><B big i="sigma" l="Analyze…" title="Choose an analysis" run={() => analyze()} /><B big i="search" l="Test Chooser" title="A few questions open the right analysis" run={T.testChooser} /></G>
      <G l="Statistics" h="statistics"><S><B i="sigma" l="Descriptive" run={() => runAnalysis("B1")} /><B i="check" l="Normality" run={() => runAnalysis("B2")} /><B i="exclude" l="Outliers" run={() => runAnalysis("B3")} /></S>
        <S><B i="table" l="Frequency" title="Histogram and cumulative distribution" run={() => runAnalysis("D4")} /><B i="dash" l="Fractions" title="Parts as a percentage of the whole" run={() => runAnalysis("A6")} /><B i="xy" l="Correlation" run={() => runAnalysis("B16")} /></S><S><B i="sigma" l="Power" title="Power and sample size" run={() => runAnalysis("B23")} /><B i="err" l="Bland-Altman" title="Agreement of two methods" run={() => runAnalysis("B18")} /><B i="curve" l="ROC Curve" title="How well a test separates two groups" run={() => runAnalysis("B18r")} /></S></G>
      <G l="Compare Groups" h="compare"><B big i="err" l="t-test" run={() => runAnalysis("B4")} /><B big i="table" l="One-way ANOVA" run={() => runAnalysis("B6")} />
        <S><B i="err" l="Nonparametric" run={() => runAnalysis("B5")} /><B i="list" l="Multiple Comparisons" run={() => runAnalysis("B7")} /><B i="sigma" l="Effect Sizes" run={() => runAnalysis("B8")} /></S><S><B i="group" l="Nested" title="Nested t-test or one-way ANOVA: subgroups (batches, animals) within groups" run={() => runAnalysis("B20")} /></S></G>
      <G l="Regression" h="regression"><B big i="line" l="Linear Regression" run={() => runAnalysis("B9")} /><B big i="curve" l="Curve Fit" run={() => runAnalysis("B10")} />
        <S><B i="xy" l="Interpolate" run={() => runAnalysis("B13")} /><B i="curve" l="Global Fit" title="Shared parameters; compare models" run={() => runAnalysis("B12")} /><B i="graph" l="Area" title="Area under the curve and peaks" run={() => runAnalysis("B14")} /></S>
        <S><B i="curve" l="Smooth" title="Smooth, differentiate or integrate" run={() => runAnalysis("B14s")} /><B i="grid" l="Surface Fit" title="Fit Z = f(X, Y): plane, quadratic, cubic or a 2D Gaussian peak" run={() => runAnalysis("B26")} /><B i="cols" l="Multiple" title="Multiple, logistic or Poisson regression: several predictors at once" run={() => runAnalysis("B21")} /></S></G>
      <G l="Materials" h="materials"><B big i="line" l="Tensile Test" title="Modulus, yield, UTS, elongation and toughness" run={() => runAnalysis("B27")} />
        <S><B i="sigma" l="Weibull" title="Weibull modulus and characteristic strength" run={() => runAnalysis("B29")} /><B i="log" l="Arrhenius" title="Activation energy from rates at several temperatures" run={() => runAnalysis("B28")} /><B i="line" l="S–N Curves" title="Fatigue: Basquin fit of stress against cycles to failure, with run-outs" run={() => runAnalysis("B30")} /></S></G>
      <G l="More"><S><B i="table" l="Two-way ANOVA" title="Two factors: a grouped table" run={() => runAnalysis("B15")} /><B i="grid" l="Contingency" title="Chi-square and Fisher's exact test on counts" run={() => runAnalysis("B17")} /><B i="line" l="Survival" title="Kaplan-Meier curves, median survival, log-rank test and hazard ratios" run={() => runAnalysis("B19")} /></S><S><B i="group" l="PCA" title="Principal component analysis: the main patterns in many variables" run={() => runAnalysis("B22")} /><B i="group" l="Clusters" title="Group similar rows: hierarchical or k-means clustering" run={() => runAnalysis("B22c")} /><B i="curve" l="Peaks" title="Find peaks above a baseline: positions, widths, areas; fit Gaussian, Lorentzian or Voigt peaks" run={() => runAnalysis("B24")} /><B i="graph" l="Signal" title="Fourier spectrum, low-, high- and band-pass filters, resampling" run={() => runAnalysis("B25")} /><B i="curve" l="DSC / TGA" title="Thermal analysis: DSC onsets, peaks and enthalpies; TGA steps and mass loss" run={() => runAnalysis("B31")} /></S></G>
    </Show>
    <Show when={tab() === "graph"}>
      <G l="Graph" h="graphtab"><B big i="graph" l="New Graph" run={C.newGraph} /><B big i="xy" l="Graph Type" run={graphTypes} /><B big i="sheet" l="Data Table" run={() => openView("data", graph()?.table ?? table()?.id ?? 0)} /></G>
      <G l="Data" h="gdata"><B big i="err" l="Error Bars" dd={e => openMenu(e, errorMenu())} /><S><B i="symbol" l="Each Replicate" on={gs()?.points === "each"} run={() => setGS(s => { s.points = s.points === "each" ? "mean" : "each"; })} /><B i="line" l="Connect Points" on={!!gs()?.line} run={() => setGS(s => { s.line = !s.line; })} /><B i="legend" l="Legend" on={!!gs()?.legend.show} run={() => setGS(s => { s.legend.show = !s.legend.show; })} /></S></G>
      <G l="Axes" h="axes"><S><B i="log" l="Log X Axis" on={gs()?.x.scale === "log"} run={() => setGS(s => { s.x.scale = s.x.scale === "log" ? "lin" : "log"; })} /><B i="log" l="Log Y Axis" on={gs()?.y.scale === "log"} run={() => setGS(s => { s.y.scale = s.y.scale === "log" ? "lin" : "log"; })} /><B i="frame" l="Framed Axes" on={gs()?.style === "frame"} run={() => setGS(s => { s.style = s.style === "frame" ? "prism" : "frame"; })} /></S>
        <B big i="axis" l="Format Axes" run={() => C.format("x")} /><S><B i="axis" l="Axis Break" title="Leave a gap in the X or Y axis (Format Graph › X Axis or Y Axis)" run={() => C.format("y")} /></S></G>
      <G l="Size" h="size"><B big i="size" l="Size" dd={e => openMenu(e, sizeMenu())} /></G>
      <Show when={curTable() && curTable()!.kind !== "xy" && curTable()!.kind !== "multi" && curTable()!.kind !== "survival" && curTable()!.kind !== "nested" && curTable()!.kind !== "sheet"}><G l="Columns" h="columns"><B big i="err" l="Column Graph" dd={e => openMenu(e, columnMenu())} /></G></Show>
      <G l="Add" h="add"><S><B i="curve" l="Fit a Curve" title="Linear regression or a curve fit, drawn on this graph" run={() => analyze("B9")} /><B i="err" l="Significance" title="Stars over the groups, from a t-test or ANOVA" run={e => T.significance(e)} /><B i="note" l="Annotation" title="Text, arrows, lines and boxes on the graph" dd={e => openMenu(e, ANNOT())} /></S></G>
      <G l="Style" h="style"><B big i="style" l="Styles" dd={e => openMenu(e, T.styleMenu())} /><S><B i="paint" l="Copy Look" title="Give other graphs this graph's look" run={T.copyLook} /><B i="bucket" l="Colour Schemes" run={T.paletteDialog} /></S></G>
      <G l="Share" h="share"><B big i="export" l="Export" run={() => C.exportG()} dd={e => openMenu(e, exportMenu())} /><S><B i="copy" l="Copy Picture" run={C.copyG} /><B i="print" l="Print" run={C.print} /></S></G>
    </Show>
    <Show when={tab() === "format"}>
      <G l="Format" h="format"><B big i="style" l="Format Graph" run={() => C.format("sets")} /><S><B i="symbol" l="Data Sets" run={() => C.format("sets")} /><B i="axis" l="X Axis" run={() => C.format("x")} /><B i="axis" l="Y Axis" run={() => C.format("y")} /></S></G>
      <G l="Text" h="text"><div class="fontg"><div><select class="ffam" title="Graph font" value={gs()?.font ?? "Arial"} onChange={e => { const v = e.currentTarget.value; setGS(s => { s.font = v; }); }}><For each={GFONTS}>{f => <option value={f} style={{ "font-family": `'${f}'` }}>{f}</option>}</For></select>
        <select class="fsize" title="Font size (pt)" value={String(gs()?.fontSize ?? 10)} onChange={e => { const v = +e.currentTarget.value; setGS(s => { s.fontSize = v; }); }}><For each={[6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20, 24]}>{z => <option value={z}>{z}</option>}</For></select></div>
        <div><button class="rb fb" classList={{ on: !!gs()?.boldTitles }} title="Bold axis titles" onClick={() => setGS(s => { s.boldTitles = !s.boldTitles; })}><span style={{ "font-weight": 700 }}>B</span></button>
          <button class="rb fb" title="Increase font size" onClick={() => setGS(s => { s.fontSize = Math.min(36, s.fontSize + 1); })}><span>A<sup>+</sup></span></button><button class="rb fb" title="Decrease font size" onClick={() => setGS(s => { s.fontSize = Math.max(5, s.fontSize - 1); })}><span>A<sup>−</sup></span></button></div></div></G>
      <G l="Annotate" h="annotate"><S><B i="note" l="Text" run={() => annotate("text")} /><B i="line" l="Arrow" run={() => annotate("arrow")} /><B i="frame" l="Box" run={() => annotate("box")} /></S><S><B i="dash" l="Line" run={() => annotate("line")} /><B i="list" l="Edit Notes" run={() => C.format("notes")} /></S></G>
      <G l="Axes" h="axes"><S><B i="axis" l="Axis Break" title="Leave out a stretch of the Y axis (Format Graph › Y Axis)" run={() => C.format("y")} /><B i="axis" l="Second Y Axis" title="Tick “Right Y” for a data set (Format Graph › Data Sets)" run={() => { C.format("sets"); toast("Tick “Right Y” for the data sets that belong on a second axis.", true); }} /><B i="zin" l="Zoom and Pan" dd={e => openMenu(e, ZOOM())} /></S></G>
      <G l="Layout" h="glayout"><B big i="size" l="Size" dd={e => openMenu(e, sizeMenu())} /><S><B i="legend" l="Legend" on={!!gs()?.legend.show} run={() => setGS(s => { s.legend.show = !s.legend.show; })} /><B i="frame" l="Framed Axes" on={gs()?.style === "frame"} run={() => setGS(s => { s.style = s.style === "frame" ? "prism" : "frame"; })} /><B i="opts" l="Graph Options" run={() => C.format("graph")} /></S></G>
    </Show>
    <Show when={tab() === "layout"}>
      <G l="Layout" h="layouts"><B big i="layout" l="New Layout" title="Arrange graphs on a page" run={() => L.newLayout()} />
        <S><B i="list" l="Panel Letters" dd={e => lay(l => openMenu(e, L.letterMenu(l)))} /><B i="cols" l="Arrange" dd={e => lay(l => openMenu(e, L.arrangeMenu(l)))} /><B i="size" l="Journal Figure" dd={e => lay(l => openMenu(e, L.sizeMenu(l)))} /></S>
        <S><B i="graph" l="Add Graph" dd={e => lay(l => openMenu(e, L.graphMenu(l)))} /></S></G>
      <G l="Templates"><B big i="layout" l="Poster" title="An A0 poster with a title and your graphs" run={() => L.templateLayout("poster")} /><B big i="layout" l="Slide" title="A 16:9 slide with a title and your graphs" run={() => L.templateLayout("slide")} /></G>
      <G l="Export" h="exportall"><B big i="export" l="Export Layout" title="PDF, TIFF, PNG, SVG or EPS at the page's real size" run={() => lay(l => L.exportLayout(l))} /><B big i="image" l="TIFF for Journals" title="CMYK, LZW, 600 dpi" run={() => lay(l => L.exportLayout(l, true))} /></G>
    </Show>
    <Show when={tab() === "tools"}>
      <G l="Python"><N big i="fx" l="Python Console" id="H1" /><S><N i="fx" l="My Analyses" id="H2" /><N i="report" l="Notebook" id="H5" /></S></G>
      <G l="Automate"><N big i="repeat" l="Analysis Template" id="H3" /><N big i="folder" l="Batch Process" id="H4" /></G>
      <G l="Export" h="exportall"><B big i="export" l="Export All Graphs" run={T.exportAll} /><B big i="table" l="Excel Workbook" title="Data tables and results as an Excel workbook" run={T.exportExcel} /><S><B i="report" l="PowerPoint" title="Every graph on its own slide, and the results (.pptx)" run={() => T.exportReport("slides")} /><B i="report" l="Word Report" title="A report with the graphs, the results and the methods text (.docx)" run={() => T.exportReport("word")} /></S></G>
      <G l="Engine" h="engine"><B big i="update" l="Restart Engine" title="Restart the Python engine" run={() => call("restart_engine").then(() => toast("The Python engine restarted.", true))} /></G>
    </Show>
    <Show when={tab() === "view"}>
      <G l="Show" h="show"><B big i="infosheet" l="Info" run={() => openView("info")} /><B big i="sheet" l="Data" run={() => openView("data")} /><B big i="graph" l="Graphs" run={() => openView("graphs")} /><S><B i="list" l="Navigator" on={navOpen()} run={() => setNavOpen(!navOpen())} /><B i="image" l="Thumbnails" title="Small pictures of the graphs in the navigator" on={thumbs()} run={() => setThumbs(!thumbs())} /></S></G>
      <G l="Zoom" h="zoom"><S><B i="zin" l="Zoom In" run={() => C.zoom(1.15)} /><B i="zout" l="Zoom Out" run={() => C.zoom(1 / 1.15)} /><B i="fit" l="Normal Size" run={() => C.zoom(0)} /></S></G>
      <G l="Theme" h="theme"><S><For each={[["auto", "Auto (Windows)"], ["light", "Light"], ["dark", "Dark"]]}>{([k, l]) => <B i="style" l={l} on={theme() === k} run={() => setTheme(k)} />}</For></S></G>
    </Show>
    <Show when={tab() === "help"}>
      <G l="Learn"><B big i="report" l="Getting Started" run={() => D.gettingStarted()} /><B big i="list" l="Roadmap" title="Everything Datum Plot will do, and when" run={() => setBackstage("roadmap")} /><B big i="info" l="Glossary" title="SD, SEM, CI, replicate and other terms" run={() => D.glossary()} /><B big i="help" l="What Is This Tool?" title="Every tool explained: click a ? beside a tool, or pick one here" dd={e => openMenu(e, Object.entries(HELP).map(([k, h]) => ({ label: h.t, run: () => helpCard(k) })))} /><B big i="report" l="Statistics Guide" title="Which test when, P values, confidence intervals, common mistakes" run={T.statsGuide} /><B big i="search" l="Test Chooser" run={T.testChooser} /><B big i="keys" l="Shortcuts" run={() => D.shortcuts()} /><B big i="search" l="Tell Me" run={palette} /></G>
      <G l="Datum Plot on GitHub"><B big i="github" l="GitHub" title="The project and its code" run={() => call("open_url", { url: GH })} /><B big i="tag" l="Releases" title="Every version and its change log" run={() => call("open_url", { url: `${GH}/releases` })} /><B big i="bug" l="Report an Issue" run={() => call("open_url", { url: `${GH}/issues/new` })} /></G>
      <G l="Updates"><B big i="upd" l="Check for Updates" run={() => setBackstage("about")} /></G>
    </Show>
  </section>
);
