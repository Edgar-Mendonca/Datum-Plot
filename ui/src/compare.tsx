// 0.4.20 (B40, #61): the Comparisons page of one- and two-way ANOVA. What to compare (two-way: within rows, within data
// sets, every cell, either main effect) and how many (every pair, each against a control, chosen pairs), with a live
// diagram of the table showing exactly which means are compared, and the correction. The engine does every number.
import { For, Show, createSignal } from "solid-js";
import { Table, spans } from "./api";
import { Pick, Check } from "./ui";
import { toast } from "./store";

const FAMS: [string, string][] = [["rows", "The data sets within each row"], ["sets", "The rows within each data set (across rows)"], ["cells", "Every cell with every other"],
  ["mainsets", "The data sets' means (main effect)"], ["mainrows", "The rows' means (main effect)"]];
export const famsOf = (c: string | undefined) => c === "both" ? ["rows", "sets"] : (c || "rows").split("+").filter(f => FAMS.some(x => x[0] === f)).length ? (c || "rows").split("+").filter(f => FAMS.some(x => x[0] === f)) : ["rows"];
const pairsN = (n: number) => n * (n - 1) / 2;
/** How many comparisons the choices make (S data sets, R rows). */
const nComparisons = (two: boolean, vs: string, fams: string[], S: number, R: number, nPairs: number) => {
  const ctl = vs === "control";
  if (vs === "pairs") return nPairs;
  if (!two) return ctl ? S - 1 : pairsN(S);
  return fams.reduce((n, f) => n + ({ rows: R * (ctl ? S - 1 : pairsN(S)), sets: S * (ctl ? R - 1 : pairsN(R)), cells: ctl ? R * S - 1 : pairsN(R * S), mainsets: ctl ? S - 1 : pairsN(S), mainrows: ctl ? R - 1 : pairsN(R) } as Record<string, number>)[f], 0);
};
const letter = (k: number) => String.fromCharCode(65 + k);

/** The rows of a grouped table that hold values in any of the data sets. */
const filledRows = (t: Table, ks: number[]) => Array.from({ length: t.rows }, (_, r) => r).filter(r => ks.some(k => { const [c0, w] = spans(t)[k]; for (let c = c0; c < c0 + w; c++) if (t.cols[c]?.[r] !== null && t.cols[c]?.[r] !== undefined) return true; return false; }));

export const Comparisons = (p: { t: Table; two: boolean; o: () => Record<string, any>; put: (k: string, v: unknown) => void; sets: () => number[] }) => {
  const ks = () => p.sets().length ? p.sets() : p.t.sets.map((_, k) => k);
  const rows = () => p.two ? filledRows(p.t, ks()) : [];
  const sname = (k: number) => p.t.sets[k]?.title || `Data set ${letter(k)}`, rname = (r: number) => p.t.rowTitles?.[r] || `Row ${r + 1}`;
  const vs = () => p.o().vs ?? (p.o().posthoc === "dunnett" ? "control" : "all");
  const fams = () => famsOf(p.o().compare);
  const cs = () => ks().includes(p.o().controlSet) ? p.o().controlSet : ks()[0];
  const cr = () => rows().includes(p.o().controlRow) ? p.o().controlRow : rows()[0];
  const c1 = () => ks().includes(p.o().control) ? p.o().control : ks()[0];
  const pairs = (): number[][] => (p.o().pairs ?? []).filter((x: number[]) => Array.isArray(x) && x.length === (p.two ? 4 : 2));
  const setFam = (f: string, on: boolean) => {
    const next = FAMS.map(x => x[0]).filter(x => x === f ? on : fams().includes(x));
    if (!next.length) return toast("Keep at least one kind of comparison (or choose Correction › No comparisons).");
    p.put("compare", next.join("+"));
  };
  // each correction for the design it was made for (0.4.22: and the false discovery rate): Tukey for every pair, Dunnett against a control (one-way)
  const posts = (): [string, string][] => [...(!p.two && vs() === "all" ? [["tukey", "Tukey (recommended for every pair)"] as [string, string]] : []), ...(!p.two && vs() === "control" ? [["dunnett", "Dunnett (recommended against a control)"] as [string, string]] : []),
    ["holm", "Holm-Šidák"], ["sidak", "Šidák"], ["bonferroni", "Bonferroni"], ["fdr", "False discovery rate (Benjamini-Hochberg)"], ["lsd", "None (Fisher's LSD)"], ["none", "No comparisons"]];
  const setVs = (v: string) => {
    const keep = v === "all" ? p.o().posthoc !== "dunnett" : v === "control" ? p.o().posthoc !== "tukey" : !["tukey", "dunnett"].includes(p.o().posthoc);
    p.put("vs", v);
    if (!keep) p.put("posthoc", p.two ? "sidak" : v === "all" ? "tukey" : v === "control" ? "dunnett" : "sidak");
  };
  const count = () => nComparisons(p.two, vs(), fams(), ks().length, rows().length, pairs().length);
  // the pair being added (two-way: cells as "set:row")
  const cellOpts = (): [string, string][] => p.two ? rows().flatMap(r => ks().map(k => [`${k}:${r}`, `${rname(r)} · ${sname(k)}`] as [string, string])) : ks().map(k => [String(k), sname(k)] as [string, string]);
  const [a, setA] = createSignal(""), [b, setB] = createSignal("");
  const add = () => {
    const A = a() || cellOpts()[0]?.[0], B = b() || cellOpts()[1]?.[0];
    if (!A || !B || A === B) return toast("Choose two different " + (p.two ? "cells." : "groups."));
    const pr = p.two ? [...A.split(":").map(Number), ...B.split(":").map(Number)] : [+A, +B];
    p.put("pairs", [...pairs().filter(x => JSON.stringify(x) !== JSON.stringify(pr)), pr]);
  };
  const pairText = (x: number[]) => p.two ? `${rname(x[1])} · ${sname(x[0])} vs ${rname(x[3])} · ${sname(x[2])}` : `${sname(x[0])} vs ${sname(x[1])}`;
  return <>
    <Show when={p.two}>
      <label>What to compare</label><span class="cmpfams">
        <For each={FAMS}>{([f, l]) => <Check label={l} value={fams().includes(f)} set={v => setFam(f, v)} disabled={vs() === "pairs"} />}</For></span>
    </Show>
    <label>How many</label><span class="inline cmpinline"><Pick value={vs()} set={setVs} options={[["all", "Every pair"], ["control", "Each against a control"], ["pairs", "Only the pairs I choose"]]} />
      <Show when={vs() === "control" && !p.two}><span class="muted">control</span><Pick value={String(c1())} set={v => p.put("control", +v)} options={ks().map(k => [String(k), sname(k)] as [string, string])} /></Show>
      <Show when={vs() === "control" && p.two && fams().some(f => ["rows", "mainsets", "cells"].includes(f))}><span class="muted">control data set</span><Pick value={String(cs())} set={v => p.put("controlSet", +v)} options={ks().map(k => [String(k), sname(k)] as [string, string])} /></Show>
      <Show when={vs() === "control" && p.two && fams().some(f => ["sets", "mainrows", "cells"].includes(f))}><span class="muted">control row</span><Pick value={String(cr())} set={v => p.put("controlRow", +v)} options={rows().map(r => [String(r), rname(r)] as [string, string])} /></Show>
    </span>
    <Show when={vs() === "pairs"}>
      <label>Pairs</label><div class="cmppairs">
        <For each={pairs()}>{x => <span class="cmppair">{pairText(x)}<button class="btn sm" title="Remove this pair" onClick={() => p.put("pairs", pairs().filter(y => y !== x))}>×</button></span>}</For>
        <span class="inline cmpinline"><Pick value={a() || cellOpts()[0]?.[0] || ""} set={setA} options={cellOpts()} /><span class="muted">vs</span><Pick value={b() || cellOpts()[1]?.[0] || ""} set={setB} options={cellOpts()} /><button class="btn sm" onClick={add}>Add Pair</button></span>
      </div>
    </Show>
    <label /><Diagram t={p.t} two={p.two} ks={ks()} rows={rows()} fams={fams()} vs={vs()} cs={cs()} cr={cr()} c1={c1()} pairs={pairs()} sname={sname} rname={rname} n={count()} />
    <label>Correction</label><Pick value={p.o().posthoc} set={v => p.put("posthoc", v)} options={posts()} />
  </>;
};

/** A small picture of the table: a circle for each mean, and a line for each comparison (shown for at most 3 × 3 cells). */
const Diagram = (p: { t: Table; two: boolean; ks: number[]; rows: number[]; fams: string[]; vs: string; cs: number; cr: number; c1: number; pairs: number[][]; sname: (k: number) => string; rname: (r: number) => string; n: number }) => <>{() => {
  // drawn inside a function so it is drawn again whenever a choice (a prop) changes
  const pick = <T,>(xs: T[], must: T, n: number) => xs.length <= n ? xs : xs.slice(0, n).includes(must) ? xs.slice(0, n) : [...xs.slice(0, n - 1), must];
  const ctl = p.vs === "control";
  const S = pick(p.ks, p.two ? p.cs : p.c1, p.two ? 3 : 5), R = p.two ? pick(p.rows, p.cr, 3) : [0];
  const X = (j: number) => 96 + j * 74, Y = (i: number) => 40 + i * 38, rad = 10;
  const mainS = p.two && p.vs !== "pairs" && p.fams.includes("mainsets"), mainR = p.two && p.vs !== "pairs" && p.fams.includes("mainrows");
  const W = X(S.length - 1) + (mainR ? 110 : 50), H = Y(R.length - 1) + (mainS ? 64 : 26);
  type L = [number, number, number, number, number];  // x1 y1 x2 y2 bend
  const lines: L[] = [];
  const pr = <T,>(xs: T[], c: T): [T, T][] => ctl ? xs.filter(x => x !== c).map(x => [c, x]) : xs.flatMap((x, i) => xs.slice(i + 1).map(y => [x, y] as [T, T]));
  const cell = (k: number, r: number): [number, number] => [X(S.indexOf(k)), Y(R.indexOf(r))];
  const join = (u: [number, number], v: [number, number], bend = 0) => lines.push([...u, ...v, bend]);
  if (!p.two) {
    const ps: [number, number][] = p.vs === "pairs" ? p.pairs.filter(x => S.includes(x[0]) && S.includes(x[1])).map(x => [x[0], x[1]]) : pr(S, p.c1);
    ps.forEach(([a, b]) => join(cell(a, 0), cell(b, 0), -14 * Math.abs(S.indexOf(b) - S.indexOf(a))));
  } else if (p.vs === "pairs") {
    p.pairs.filter(x => S.includes(x[0]) && S.includes(x[2]) && R.includes(x[1]) && R.includes(x[3])).forEach(x => join(cell(x[0], x[1]), cell(x[2], x[3])));
  } else {
    if (p.fams.includes("rows")) R.forEach(r => pr(S, p.cs).forEach(([a, b]) => join(cell(a, r), cell(b, r), Math.abs(S.indexOf(b) - S.indexOf(a)) > 1 ? -12 : 0)));
    if (p.fams.includes("sets")) S.forEach(k => pr(R, p.cr).forEach(([a, b]) => join(cell(k, a), cell(k, b), Math.abs(R.indexOf(b) - R.indexOf(a)) > 1 ? -14 : 0)));
    if (p.fams.includes("cells")) { const all = R.flatMap(r => S.map(k => `${k}:${r}`)); pr(all, `${p.cs}:${p.cr}`).forEach(([a, b]) => { const [ka, ra] = a.split(":").map(Number), [kb, rb] = b.split(":").map(Number); join(cell(ka, ra), cell(kb, rb), ra === rb && Math.abs(S.indexOf(kb) - S.indexOf(ka)) > 1 ? -12 : ka === kb && Math.abs(R.indexOf(rb) - R.indexOf(ra)) > 1 ? -14 : 0); }); }
    if (mainS) { const y = Y(R.length - 1) + 44; pr(S, p.cs).forEach(([a, b]) => join([X(S.indexOf(a)), y], [X(S.indexOf(b)), y], Math.abs(S.indexOf(b) - S.indexOf(a)) > 1 ? 12 : 0)); }
    if (mainR) { const x = X(S.length - 1) + 74; pr(R, p.cr).forEach(([a, b]) => join([x, Y(R.indexOf(a))], [x, Y(R.indexOf(b))], Math.abs(R.indexOf(b) - R.indexOf(a)) > 1 ? 14 : 0)); }
  }
  /** A line between two circles (ends pulled back to their edges), bent sideways when it would cross another circle. */
  const path = ([x1, y1, x2, y2, bend]: L) => {
    const dx = x2 - x1, dy = y2 - y1, d = Math.hypot(dx, dy) || 1, ux = dx / d, uy = dy / d;
    const a = [x1 + ux * (rad + 2), y1 + uy * (rad + 2)], b = [x2 - ux * (rad + 2), y2 - uy * (rad + 2)];
    const mx = (x1 + x2) / 2 - uy * bend * 1.6, my = (y1 + y2) / 2 + ux * bend * 1.6;
    return bend ? `M${a[0]},${a[1]} Q${mx},${my} ${b[0]},${b[1]}` : `M${a[0]},${a[1]} L${b[0]},${b[1]}`;
  };
  const isCtl = (k: number, r: number) => ctl && (p.two ? (p.fams.includes("cells") ? k === p.cs && r === p.cr : (p.fams.includes("rows") && k === p.cs) || (p.fams.includes("sets") && r === p.cr)) : k === p.c1);
  const cut = (s: string) => s.length > 10 ? s.slice(0, 9) + "…" : s;
  return <div class="cmpdiag">
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Which means are compared">
      <defs><marker id="cmparrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L8,4 L0,8 z" class="cmpa" /></marker></defs>
      <For each={S}>{(k, j) => <text x={X(j())} y={14} text-anchor="middle" class="cmph">{cut(p.sname(k))}</text>}</For>
      <Show when={p.two}><For each={R}>{(r, i) => <text x={8} y={Y(i()) + 4} class="cmph">{cut(p.rname(r))}</text>}</For></Show>
      <For each={lines}>{l => <path d={path(l)} class="cmpl" marker-start="url(#cmparrow)" marker-end="url(#cmparrow)" />}</For>
      <For each={R}>{(r, i) => <For each={S}>{(k, j) => <circle cx={X(j())} cy={Y(i())} r={rad} classList={{ cmpc: true, ctl: isCtl(k, r) }} />}</For>}</For>
      <Show when={mainS}><For each={S}>{(k, j) => <><circle cx={X(j())} cy={Y(R.length - 1) + 44} r={rad} classList={{ cmpc: true, main: true, ctl: ctl && k === p.cs }} /></>}</For><text x={8} y={Y(R.length - 1) + 48} class="cmph">Mean</text></Show>
      <Show when={mainR}><For each={R}>{(r, i) => <circle cx={X(S.length - 1) + 74} cy={Y(i())} r={rad} classList={{ cmpc: true, main: true, ctl: ctl && r === p.cr }} />}</For><text x={X(S.length - 1) + 74} y={14} text-anchor="middle" class="cmph">Mean</text></Show>
    </svg>
    <span class="muted">{p.n} comparison{p.n === 1 ? "" : "s"}{p.two && (p.ks.length > 3 || p.rows.length > 3) ? " (the picture shows part of the table)" : ""}{ctl ? `; the filled circle${p.two && p.fams.length > 1 ? "s are the controls" : " is the control"}` : ""}.</span>
  </div>;
}}</>;

const POST: Record<string, string> = { tukey: "Tukey", dunnett: "Dunnett", holm: "Holm-Šidák", sidak: "Šidák", bonferroni: "Bonferroni", fdr: "the false discovery rate (Benjamini-Hochberg)", lsd: "no correction (Fisher's LSD)" };
const DESIGN: Record<string, string> = {
  none: "Ordinary two-way ANOVA: every value is a different subject", rows: "Two-way repeated-measures ANOVA: each sub-column is one subject, measured in every row",
  sets: "Two-way repeated-measures ANOVA: each row's sub-column is one subject, measured in every data set", both: "Two-way repeated-measures ANOVA: each sub-column is one subject, measured in every row and data set" };
const ONEWAY: Record<string, string> = { ordinary: "Ordinary one-way ANOVA (equal SDs)", welch: "Welch's ANOVA (the SDs may differ)", bf: "Brown-Forsythe ANOVA (the SDs may differ)", rm: "Repeated-measures one-way ANOVA (each row is one subject)" };
const FAMTXT: Record<string, string> = { rows: "the data sets within each row", sets: "the rows within each data set", cells: "every cell with every other", mainsets: "the data sets' means", mainrows: "the rows' means" };

/** 0.4.22 (#61): "What will be done", in plain words from every choice in the window, kept up to date as they change. */
export const Plan = (p: { t: Table; two: boolean; o: () => Record<string, any>; sets: () => number[] }) => {
  const lines = () => {
    const o = p.o(), ks = p.sets().length ? p.sets() : p.t.sets.map((_, k) => k), rows = p.two ? filledRows(p.t, ks) : [];
    const sname = (k: number) => p.t.sets[k]?.title || `Data set ${letter(k)}`, rname = (r: number) => p.t.rowTitles?.[r] || `Row ${r + 1}`;
    const vs = o.vs ?? (o.posthoc === "dunnett" ? "control" : "all"), fams = famsOf(o.compare), nP = (o.pairs ?? []).length;
    let post = o.posthoc ?? (p.two ? "sidak" : "tukey");
    if ((post === "tukey" && vs !== "all") || (post === "dunnett" && vs !== "control") || (o.anova === "rm" && ["tukey", "dunnett"].includes(post))) post = "holm";
    const out: string[] = [];
    if (p.two) {
      const rm = o.rm ?? "none";
      out.push(`${DESIGN[rm] ?? DESIGN.none}${rm === "none" ? (o.interaction !== false ? ", with the interaction of the two factors." : ", main effects only (no interaction).") : `${o.gg !== false ? "; Geisser-Greenhouse correction for sphericity" : ""}; a mixed-effects model if values are missing.`}`);
    } else out.push(`${ONEWAY[o.anova ?? "ordinary"] ?? ONEWAY.ordinary}, ${ks.length} groups.`);
    if (post === "none") out.push("No multiple comparisons.");
    else {
      const n = nComparisons(p.two, vs, fams, ks.length, rows.length, nP);
      const what = vs === "pairs" ? `only the ${nP} pair${nP === 1 ? "" : "s"} you chose` : p.two ? fams.map(f => FAMTXT[f]).join(", ") : vs === "control" ? "each group" : "every pair of groups";
      const ctl = vs !== "control" ? "" : p.two ? `, each against ${fams.every(f => ["sets", "mainrows"].includes(f)) ? rname(rows.includes(o.controlRow) ? o.controlRow : rows[0]) : fams.includes("cells") ? `${rname(rows.includes(o.controlRow) ? o.controlRow : rows[0])} · ${sname(ks.includes(o.controlSet) ? o.controlSet : ks[0])}` : sname(ks.includes(o.controlSet) ? o.controlSet : ks[0])}` : ` against ${sname(ks.includes(o.control) ? o.control : ks[0])}`;
      out.push(`Compare ${what}${p.two && vs === "all" ? ", every pair" : ""}${ctl}: ${n} comparison${n === 1 ? "" : "s"}, corrected by ${POST[post] ?? post}${p.two && fams.length > 1 && vs !== "pairs" ? " (each kind on its own)" : ""}.`);
    }
    if (!p.two && o.trend) out.push("A test for a linear trend across the groups in their order.");
    if (!p.two && o.bayes) out.push("A Bayes factor beside the P value.");
    out.push(o.brackets === "none" || post === "none" ? "No brackets on the graph." : `Brackets with ${o.ptext === "p" ? "P values" : o.ptext === "stars4" ? "stars (up to ****)" : "stars"} on the graph for ${o.brackets === "all" ? "every pair compared" : "the significant pairs"}.`);
    if (o.resplots) out.push("Residual plots (residuals, spread, normal QQ) on the results sheet.");
    return out;
  };
  return <div class="plan"><b>What will be done</b><ul><For each={lines()}>{l => <li>{l}</li>}</For></ul></div>;
};

/** 0.4.22 (#61): which values belong to one subject under repeated measures, outlined on a small picture of the table. */
export const Layout = (p: { t: Table; mode: string; sets: () => number[] }) => <>{() => {
  const two = p.mode !== "oneway", ks = (p.sets().length ? p.sets() : p.t.sets.map((_, k) => k)).slice(0, two ? 2 : 3);
  const R = two ? 3 : 4, W = two ? 3 : 1, cw = 22, ch = 15, gx = 12, x0 = 54, y0 = 30;
  const X = (j: number, s: number) => x0 + j * (W * cw + gx) + s * cw, Y = (r: number) => y0 + r * ch;
  const on = (j: number, r: number, s: number) => s === 0 && (p.mode === "rows" ? j === 0 : p.mode === "sets" ? r === 0 : p.mode === "both" ? true : r === 0);
  const cells = ks.flatMap((_, j) => Array.from({ length: R }, (_, r) => Array.from({ length: W }, (_, s) => [j, r, s]))).flat() as [number, number, number][];
  const hit = cells.filter(c => on(...c));
  const order = [...hit].sort((a, b) => p.mode === "sets" || p.mode === "oneway" ? a[0] - b[0] || a[1] - b[1] : a[0] - b[0] || a[1] - b[1]);
  const w = X(ks.length - 1, W - 1) + cw + 10, h = Y(R - 1) + ch + 8;
  const cut = (s: string) => s.length > 9 ? s.slice(0, 8) + "…" : s;
  return <div class="cmpdiag rmlayout">
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} role="img" aria-label="Which values belong to one subject">
      <For each={ks}>{(k, j) => <text x={X(j(), 0) + W * cw / 2} y={12} text-anchor="middle" class="cmph">{cut(p.t.sets[k]?.title || `Data set ${letter(k)}`)}</text>}</For>
      <Show when={two}><For each={ks}>{(_, j) => <For each={Array.from({ length: W }, (_, s) => s)}>{s => <text x={X(j(), s) + cw / 2} y={24} text-anchor="middle" class="cmph">{s + 1}</text>}</For>}</For></Show>
      <For each={Array.from({ length: R }, (_, r) => r)}>{r => <text x={6} y={Y(r) + 11} class="cmph">{two ? (p.t.rowTitles?.[r] ? cut(p.t.rowTitles[r]) : `Row ${r + 1}`) : `Row ${r + 1}`}</text>}</For>
      <For each={cells}>{([j, r, s]) => <rect x={X(j, s) + 1} y={Y(r) + 1} width={cw - 2} height={ch - 2} classList={{ rmc: true, on: on(j, r, s) }} />}</For>
      <polyline points={order.map(([j, r, s]) => `${X(j, s) + cw / 2},${Y(r) + ch / 2}`).join(" ")} class="rml" />
    </svg>
    <span class="muted">Outlined: the values of one subject, matched {p.mode === "rows" ? "down the rows" : p.mode === "sets" ? "across the data sets" : p.mode === "both" ? "across rows and data sets" : "across the groups"}.</span>
  </div>;
}}</>;
