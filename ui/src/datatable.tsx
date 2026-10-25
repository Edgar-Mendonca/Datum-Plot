// The data table: X (hidden in column tables), then each data set's replicate (or mean/SD/N) columns, on the family
// grid engine (selection.ts, cells.ts, fmt.ts): ranges, clipboard with Excel, fill handle,
// formatting, and excluded values in blue italics.
import { For, Show, createSignal, createMemo, createEffect, onMount, onCleanup } from "solid-js";
import { Table, DataSet, spans, width, num, letter } from "./api";
import { act, call, opts, openMenu, toast, Item, openDialog, closeDialog, goto, setGoto } from "./store";
import { sortDialog, findDialog, excludeRows } from "./tools";
import * as F from "./fmt";
import { parseTsv, toTsv, transpose, series, clip } from "./cells";
import { createSel, aggregate } from "./selection";
import { Dialog, Pick, Text, Icon } from "./ui";
import { pasteSpecial as pasteDialog } from "./dialogs";
import { Help } from "./help";

const RH = 22, HW = 40, TW = 96, XW = 86, CW = 76, HEAD = 2 * RH;
const SUB: Record<string, string[]> = { msn: ["Mean", "SD", "N"], mesn: ["Mean", "SEM", "N"] };

/** Selection column k: 0 is the row title, k ≥ 1 is grid column k - 1 (0 = X). */
export const DataTable = (p: { t: Table }) => {
  const t = () => p.t, W = () => width(t());
  const ncols = () => W() + 1, nrows = () => t().rows + 10;
  /** Column tables have no X: its grid column is kept but hidden. */
  const hideX = () => t().kind === "column";
  const colW = (k: number) => (k === 0 ? TW : k === 1 ? (hideX() ? 0 : XW) : CW);
  const lefts = createMemo(() => { let x = HW; return Array.from({ length: ncols() }, (_, k) => { const l = x; x += colW(k); return l; }); });
  const total = () => lefts()[ncols() - 1] + colW(ncols() - 1);
  const ex = createMemo(() => new Set(t().excluded.map(([r, c]) => `${r}:${c}`)));
  const text = (r: number, k: number) => (k === 0 ? t().rowTitles[r] ?? "" : num(t().cols[k - 1]?.[r], opts().decimals));
  const [edit, setEdit] = createSignal<string | null>(null);
  const [top, setTop] = createSignal(0), [h, setH] = createSignal(600);
  let box!: HTMLDivElement;
  const ro = new ResizeObserver(() => setH(box.clientHeight));
  const S = createSel(() => [nrows(), ncols()], (r, c) => reveal(r, c));
  const cur = (): [number, number] => [S.cur().row, S.cur().col];
  const range = () => { const g = S.last(); return [g.r0, g.c0, g.r1, g.c1]; };
  const reveal = (r: number, c: number) => {
    if (!box) return;
    if (r * RH < box.scrollTop) box.scrollTop = r * RH; else if ((r + 2) * RH > box.scrollTop + box.clientHeight - HEAD) box.scrollTop = (r + 2) * RH - box.clientHeight + HEAD;
    const l = lefts()[c] ?? 0, w = colW(c);
    if (l - HW < box.scrollLeft) box.scrollLeft = l - HW; else if (l + w > box.scrollLeft + box.clientWidth - 16) box.scrollLeft = l + w - box.clientWidth + 16;
  };
  const key = (r: number, k: number) => `${r}:${k - 1}`;
  const fmtTarget: F.Target = {
    get: () => { const out: [string, string][] = []; S.each((r, k) => out.push([key(r, k), t().style[key(r, k)] ?? ""]), 20000); return out; },
    set: list => act({ Style: { table: t().id, cells: list } }),
    paste: (what, tr) => pasteSpecial(what, tr),
  };
  onMount(() => { ro.observe(box); F.setTarget(fmtTarget); box.focus(); });
  onCleanup(() => { ro.disconnect(); if (F.target() === fmtTarget) F.setTarget(null); });
  const put = (cells: [number, number, string][]) => act({ Cells: { table: t().id, cells: cells.map(([r, k, v]) => [r, k - 1, v]) } });
  const go = (r: number, c: number, ext = false, add = false) => S.pick(r, hideX() && c === 1 ? (c < cur()[1] ? 0 : 2) : c, ext, add);
  createEffect(() => { const g = goto(); if (g) { setGoto(null); go(g[0], g[1] + 1); box?.focus(); } });
  const commit = async (move: [number, number]) => {
    const v = edit();
    setEdit(null);
    if (v !== null && v !== text(...cur())) await put([[...cur(), v]]);
    go(cur()[0] + move[0], cur()[1] + move[1]);
    box.focus();
  };
  const selected = () => { const out: [number, number][] = []; S.each((r, k) => out.push([r, k])); return out; };
  const clear = () => { const out = selected().filter(([r, k]) => text(r, k) !== "").map(([r, k]) => [r, k, ""] as [number, number, string]); if (out.length) put(out); };
  /** Exclude (or include again) the selected values: they stay in the table but graphs skip them. */
  const exclude = () => {
    const cells = selected().filter(([r, k]) => k > 0 && r < t().rows && text(r, k) !== "").map(([r, k]) => [r, k - 1]);
    if (!cells.length) return toast("Select the values to exclude first.");
    act({ Exclude: { table: t().id, cells, on: !cells.every(([r, c]) => ex().has(`${r}:${c}`)) } });
  };
  const copyText = () => { const [r0, c0, r1, c1] = range(); return Array.from({ length: r1 - r0 + 1 }, (_, i) => Array.from({ length: c1 - c0 + 1 }, (_, j) => text(r0 + i, c0 + j))); };
  const onCopy = (e: ClipboardEvent, cut = false) => {
    if (edit() !== null) return;
    e.preventDefault();
    const [r0, c0, r1, c1] = range();
    clip.text = toTsv(copyText());
    clip.styles = Array.from({ length: r1 - r0 + 1 }, (_, i) => Array.from({ length: c1 - c0 + 1 }, (_, j) => t().style[key(r0 + i, c0 + j)] ?? ""));
    e.clipboardData?.setData("text/plain", clip.text);
    if (cut) clear();
  };
  const pasteRows = (m: string[][]) => { const [r, k] = cur(); return act({ Paste: { table: t().id, row: r, col: k - 1, rows: m } }); };
  const onPaste = (e: ClipboardEvent) => { if (edit() !== null) return; e.preventDefault(); pasteRows(parseTsv(e.clipboardData?.getData("text/plain") ?? "")); };
  const pasteSpecial = async (what: "all" | "values" | "formats", tr: boolean) => {
    const txt = clip.text || (await call<string>("read_clipboard")) || "";
    if (!txt) return toast("Copy some cells first.");
    let m = parseTsv(txt), st = clip.text === txt ? clip.styles : [];
    if (tr) { m = transpose(m); st = st.length ? transpose(st) : st; }
    const [r0, k0] = cur();
    if (what !== "formats") await pasteRows(m);
    if (what !== "values" && st.length) await act({ Style: { table: t().id, cells: st.flatMap((l, i) => l.map((v, j) => [key(r0 + i, k0 + j), v])) } });
  };
  /** Fills from the selection down (or right), continuing series as Excel does; Ctrl copies. */
  const fillRange = (r1: number, c1: number, copy = false) => {
    const [a, b, c, d] = range(), out: [number, number, string][] = [];
    if (r1 > c) for (let k = b; k <= d; k++) { const src = Array.from({ length: c - a + 1 }, (_, i) => text(a + i, k)); for (let r = c + 1; r <= r1; r++) out.push([r, k, series(src, r - c, copy)]); }
    else if (c1 > d) for (let r = a; r <= c; r++) { const src = Array.from({ length: d - b + 1 }, (_, i) => text(r, b + i)); for (let k = d + 1; k <= c1; k++) out.push([r, k, series(src, k - d, copy)]); }
    if (out.length) put(out);
    S.drag(Math.max(c, r1), Math.max(d, c1));
  };
  const [fillTo, setFillTo] = createSignal<[number, number] | null>(null);
  const fillDrag = (e: MouseEvent) => {
    e.preventDefault(); e.stopPropagation();
    const [, , r1, c1] = range();
    const mv = (m: MouseEvent) => { const [r, c] = at(m.clientX, m.clientY); const dr = r - r1, dc = (c < 0 ? c1 : c) - c1; setFillTo(dr >= dc ? [Math.max(r1, r), c1] : [r1, Math.max(c1, c)]); };
    const up = (u: MouseEvent) => { removeEventListener("mousemove", mv); removeEventListener("mouseup", up); const f = fillTo(); setFillTo(null); if (f) fillRange(f[0], f[1], u.ctrlKey); };
    addEventListener("mousemove", mv); addEventListener("mouseup", up);
  };
  const at = (cx: number, cy: number): [number, number] => {
    const b = box.getBoundingClientRect(), y = cy - b.top - HEAD + box.scrollTop, x = cx - b.left + box.scrollLeft;
    return [Math.floor(y / RH), lefts().findIndex((l, j) => x >= l && x < l + colW(j))];
  };
  const keys = (e: KeyboardEvent) => {
    const ctrl = e.ctrlKey || e.metaKey, k = e.key.toLowerCase();
    // Keys typed before the edit box has the focus still belong to the cell being typed.
    if (edit() !== null) {
      if (e.target !== box) return;
      if (e.key.length === 1 && !ctrl && !e.altKey) { e.preventDefault(); setEdit(edit() + e.key); }
      else if (e.key === "Enter" || e.key === "Tab") { e.preventDefault(); commit(e.key === "Tab" ? [0, e.shiftKey ? -1 : 1] : [e.shiftKey ? -1 : 1, 0]); }
      else if (e.key === "Escape") setEdit(null);
      return;
    }
    const g = S.ranges()[S.ranges().length - 1], [r, c] = e.shiftKey && g ? [g.r1, g.c1] : cur();
    const mv = (dr: number, dc: number) => { e.preventDefault(); go(r + dr, c + dc, e.shiftKey); };
    switch (e.key) {
      case "ArrowDown": return mv(1, 0); case "ArrowUp": return mv(-1, 0); case "ArrowLeft": return mv(0, -1); case "ArrowRight": return mv(0, 1);
      case "Tab": e.preventDefault(); return go(cur()[0], cur()[1] + (e.shiftKey ? -1 : 1));
      case "Enter": case "F2": e.preventDefault(); return setEdit(text(...cur()));
      case "Delete": case "Backspace": e.preventDefault(); return clear();
    }
    if (ctrl && e.altKey && k === "v") { e.preventDefault(); return pasteDialog(); }
    if (ctrl && k === "e") { e.preventDefault(); return exclude(); }
    if (ctrl && k === "d") { e.preventDefault(); const [a, b, c2, d] = range(); if (c2 > a) { S.setCur({ row: a, col: b }); S.setRanges([{ r0: a, c0: b, r1: a, c1: d }]); fillRange(c2, d, true); } return; }
    if (ctrl && k === "r") { e.preventDefault(); const [a, b, c2, d] = range(); if (d > b) { S.setCur({ row: a, col: b }); S.setRanges([{ r0: a, c0: b, r1: c2, c1: b }]); fillRange(c2, d, true); } return; }
    if (ctrl && ["b", "i", "u"].includes(k)) { e.preventDefault(); return F.toggle(k as "b"); }
    if (ctrl && k === "a") { e.preventDefault(); return S.all(); }
    if (ctrl && k === "f") { e.preventDefault(); return findDialog(); }
    if (!ctrl && !e.altKey && e.key.length === 1) { e.preventDefault(); setEdit(e.key); }
  };
  const down = (e: MouseEvent) => {
    if (e.button !== 0) return;
    const [r, c] = at(e.clientX, e.clientY);
    if (r < 0) return;
    if (edit() !== null) commit([0, 0]);
    if (c < 0) S.rows(r, r, e.shiftKey, e.ctrlKey); else go(r, c, e.shiftKey, e.ctrlKey);
    const mv = (m: MouseEvent) => { const [r2, c2] = at(m.clientX, m.clientY); S.drag(Math.max(0, r2), c < 0 ? ncols() - 1 : c2 < 0 ? S.last().c1 : c2); };
    const up = () => { removeEventListener("mousemove", mv); removeEventListener("mouseup", up); F.painted(); };
    addEventListener("mousemove", mv); addEventListener("mouseup", up);
  };
  const rowsSel = () => { const [a, , c] = range(); return [Math.min(a, t().rows - 1), Math.min(c, t().rows - 1)]; };
  const ctxMenu = (e: MouseEvent) => {
    const [r, c] = at(e.clientX, e.clientY);
    if (r >= 0 && c >= 0 && !S.inRange(r, c)) go(r, c);
    const [a, b] = rowsSel(), k = t().sets.length ? setAt(cur()[1]) : -1;
    const items: Item[] = [
      { label: "Cut", icon: "cut", keys: "Ctrl+X", run: () => document.execCommand("cut") }, { label: "Copy", icon: "copy", keys: "Ctrl+C", run: () => document.execCommand("copy") },
      { label: "Paste Special…", icon: "paste", keys: "Ctrl+Alt+V", run: () => pasteDialog() }, "-",
      { label: "Exclude / Include Values", icon: "exclude", keys: "Ctrl+E", run: exclude }, { label: "Clear Contents", icon: "clear", keys: "Del", run: clear }, "-",
      { label: `Insert ${b - a + 1 > 1 ? `${b - a + 1} Rows` : "Row"} Above`, icon: "addrow", run: () => act({ Rows: { table: t().id, at: a, count: b - a + 1 } }) },
      { label: `Delete ${b - a + 1 > 1 ? `${b - a + 1} Rows` : "Row"}`, icon: "delrow", run: () => act({ Rows: { table: t().id, at: a, count: -(b - a + 1) } }) }, "-",
      ...(k >= 0 ? [{ label: `Format Data Set ${letter(k)}…`, icon: "opts", run: () => setDialog(t(), k) } as Item] : []),
      { label: "Add Data Set", icon: "addset", run: () => addSet(t()) }, "-",
      { label: "Sort…", icon: "sort", run: sortDialog }, { label: "Find…", icon: "search", keys: "Ctrl+F", run: findDialog }, { label: "Exclude Rows by a Rule…", icon: "exclude", run: excludeRows },
    ];
    openMenu(e, items);
  };
  /** The data set under selection column k, or -1 for the row title and X columns. */
  const setAt = (k: number) => spans(t()).findIndex(([c0, w]) => k - 1 >= c0 && k - 1 < c0 + w);
  const vis = createMemo(() => { const f = Math.max(0, Math.floor(top() / RH) - 2); return Array.from({ length: Math.ceil(h() / RH) + 6 }, (_, j) => f + j).filter(r => r < nrows()); });
  const name = () => { const [r, k] = cur(); if (k === 0) return `Row ${r + 1} title`; if (k === 1) return `X · row ${r + 1}`; const s = setAt(k), [c0] = spans(t())[s] ?? [0]; const e = t().sets[s]?.entry; return `${letter(s)}:${e === "rep" ? `Y${k - 1 - c0 + 1}` : SUB[e!][k - 1 - c0]} · row ${r + 1}`; };
  return (
    <section class="dview">
      <TableHead t={t()} />
      <div class="fbar"><span class="fname">{name()}</span><Show when={aggregate(S, text)}>{a => <span class="agg">{a()}</span>}</Show><span class="fx" style={{ "text-align": "center", "line-height": "27px" }}>=</span>
        <input value={edit() ?? text(...cur())} onInput={e => setEdit(e.currentTarget.value)} onKeyDown={e => { if (e.key === "Enter") commit([1, 0]); if (e.key === "Escape") setEdit(null); }} /></div>
      <div class="gscroll dgrid" ref={box} tabindex="0" onFocus={() => F.setTarget(fmtTarget)} onKeyDown={keys} onMouseDown={down} onCopy={e => onCopy(e)} onCut={e => onCopy(e, true)} onPaste={onPaste}
        onScroll={() => setTop(box.scrollTop)} onDblClick={e => { if (at(e.clientX, e.clientY)[0] >= 0) setEdit(text(...cur())); }} onContextMenu={ctxMenu}>
        <div class="gsheet" style={{ width: `${total() + 40}px`, height: `${(nrows() + 2) * RH}px` }}>
          <div class="ghead dhead" style={{ height: `${HEAD}px` }}>
            <div class="hc idc" style={{ width: `${HW}px`, left: "0" }} />
            <div class="hc two" style={{ width: `${TW}px` }}>Row title</div>
            <div class="hc two xh" style={{ width: `${colW(1)}px`, display: hideX() ? "none" : undefined }} title="Double-click to rename the X column" onDblClick={e => { e.stopPropagation(); rename(t(), "xTitle", "X title"); }}><b>X</b><span>{t().xTitle}{t().xUnits ? ` (${t().xUnits})` : ""}</span></div>
            <For each={t().sets}>{(s, k) => <div class="hset" style={{ width: `${spans(t())[k()][1] * CW}px` }}>
              <div class="hc st" style={{ "--c": SETC[k() % 8] }} title="Double-click to change the data set" onMouseDown={e => { e.stopPropagation(); const [c0, w] = spans(t())[k()]; S.cols(c0 + 1, c0 + w, e.shiftKey, e.ctrlKey); box.focus(); }} onDblClick={e => { e.stopPropagation(); setDialog(t(), k()); }}>
                <b>{letter(k())}</b><span>{s.title || `Data set ${letter(k())}`}</span></div>
              <div class="subs"><For each={Array.from({ length: spans(t())[k()][1] }, (_, j) => j)}>{j => <div class="hc sub" style={{ width: `${CW}px` }}>{s.entry === "rep" ? `Y${j + 1}` : SUB[s.entry][j]}</div>}</For></div>
            </div>}</For>
            <button class="hc addset" title="Add a data set" onMouseDown={e => e.stopPropagation()} onClick={() => addSet(t())}>＋ Data set</button>
          </div>
          <div class="gbody">
            <For each={vis()}>{r => (
              <div class="row" classList={{ beyond: r >= t().rows }} style={{ top: `${r * RH}px`, height: `${RH}px`, width: `${total()}px` }}>
                <div class="c idc" style={{ width: `${HW}px` }}>{r + 1}</div>
                <For each={Array.from({ length: ncols() }, (_, k) => k)}>{k => (
                  <div class="c" classList={{ r: k > 0, rt: k === 0, xc: k === 1, in: S.inRange(r, k), at: cur()[0] === r && cur()[1] === k, ex: k > 0 && ex().has(`${r}:${k - 1}`), sep: k > 1 && spans(t()).some(([c0]) => c0 === k - 1) }}
                    style={{ width: `${colW(k)}px`, ...(k === 1 && hideX() ? { display: "none" } : {}), ...F.css(t().style[key(r, k)]) }}>{text(r, k)}</div>
                )}</For>
              </div>
            )}</For>
            <Show when={fillTo()}>{f => { const [a, b] = [Math.min(cur()[0], range()[0]), Math.min(cur()[1], range()[1])]; return <div class="fillzone" style={{ left: `${lefts()[b]}px`, top: `${a * RH}px`, width: `${lefts()[f()[1]] + colW(f()[1]) - lefts()[b]}px`, height: `${(f()[0] - a + 1) * RH}px` }} />; }}</Show>
            <Show when={edit() === null}><i class="fill" title="Drag to fill a series; hold Ctrl to copy" style={{ left: `${lefts()[range()[3]] + colW(range()[3]) - 4}px`, top: `${(range()[2] + 1) * RH - 4}px` }} onMouseDown={fillDrag} /></Show>
            <Show when={edit() !== null}>
              <input class="edit" style={{ left: `${lefts()[cur()[1]]}px`, top: `${cur()[0] * RH}px`, width: `${Math.max(colW(cur()[1]), 110)}px`, height: `${RH}px` }} value={edit()!}
                ref={el => setTimeout(() => { el.focus(); el.setSelectionRange(el.value.length, el.value.length); })} onMouseDown={e => e.stopPropagation()}
                onInput={e => setEdit(e.currentTarget.value)} onBlur={() => edit() !== null && commit([0, 0])}
                onKeyDown={e => { e.stopPropagation(); if (e.key === "Enter") { e.preventDefault(); commit([e.shiftKey ? -1 : 1, 0]); } else if (e.key === "Tab") { e.preventDefault(); commit([0, e.shiftKey ? -1 : 1]); } else if (e.key === "Escape") { setEdit(null); box.focus(); } }} />
            </Show>
          </div>
        </div>
      </div>
    </section>
  );
};
const SETC = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000"];

/** Titles and units of the axes, above the grid. */
const TableHead = (p: { t: Table }) => {
  const set = (field: string, value: string) => act({ TableSet: { table: p.t.id, field, value } });
  return (
    <div class="thead">
      <Icon n="sheet" /><b class="tname" title="Double-click to rename" onDblClick={() => rename(p.t, "name", "Table name")}>{p.t.name}</b><Help k="table" />
      <Show when={p.t.kind !== "column"}><label>X title<input value={p.t.xTitle} onChange={e => set("xTitle", e.currentTarget.value)} /></label>
        <label>units<input class="u" value={p.t.xUnits} onChange={e => set("xUnits", e.currentTarget.value)} /></label></Show>
      <label>Y title<input value={p.t.yTitle} onChange={e => set("yTitle", e.currentTarget.value)} /></label>
      <label>units<input class="u" value={p.t.yUnits} onChange={e => set("yUnits", e.currentTarget.value)} /></label>
      <span class="grow" /><span class="muted">{p.t.kind === "column" ? "Column table · " : ""}{p.t.rows} rows · {p.t.sets.length} {p.t.kind === "column" ? (p.t.sets.length === 1 ? "group" : "groups") : `data ${p.t.sets.length === 1 ? "set" : "sets"}`}{p.t.excluded.length ? ` · ${p.t.excluded.length} excluded` : ""}</span>
    </div>
  );
};

export const rename = (t: Table, field: string, label: string) => openDialog(() => {
  const [v, setV] = createSignal(String((t as any)[field] ?? ""));
  return <Dialog title={`Rename · ${label}`} ok={() => act({ TableSet: { table: t.id, field, value: v() } })}><div class="form"><label>{label}</label><Text value={v()} set={setV} /></div></Dialog>;
});

export const addSet = (t: Table) => {
  const last = t.sets[t.sets.length - 1];
  return act({ SetDef: { table: t.id, k: null, set: { title: `Data set ${letter(t.sets.length)}`, entry: last?.entry ?? "rep", reps: last?.reps ?? 3 } } });
};

/** Format Data Set: title, how values are entered, replicates; or delete it. */
export const setDialog = (t: Table, k: number) => openDialog(() => {
  const s = t.sets[k];
  const [v, setV] = createSignal<DataSet>({ ...s });
  return (
    <Dialog title={`Data set ${letter(k)}`} help="dataset" ok={() => act({ SetDef: { table: t.id, k, set: { ...v(), reps: Math.max(1, Math.min(50, Math.round(v().reps))) } } })}
      extra={<button class="btn" disabled={t.sets.length < 2} onClick={() => { if (confirm(`Delete data set ${letter(k)} and its values?`)) act({ SetDef: { table: t.id, k, set: null } }).then(ok => { if (ok) closeDialog(); }); }}>Delete data set</button>}>
      <div class="form">
        <label>Title</label><Text value={v().title} set={x => setV({ ...v(), title: x })} />
        <label>Enter values as</label><Pick value={v().entry} set={x => setV({ ...v(), entry: x as DataSet["entry"] })} options={[["rep", "Replicate values (Y1, Y2, …)"], ["msn", "Mean, SD and N"], ["mesn", "Mean, SEM and N"]]} />
        <Show when={v().entry === "rep"}><label>Replicates</label><input type="number" min="1" max="50" value={v().reps} onChange={e => setV({ ...v(), reps: +e.currentTarget.value })} /></Show>
      </div>
      <p class="muted">Fewer replicates drop the values in the last columns. Switching to mean/SD/N keeps the first three columns as they are.</p>
    </Dialog>
  );
});
