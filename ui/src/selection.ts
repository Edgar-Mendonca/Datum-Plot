// The selection model shared by the task sheet and the Sheets tabs (one grid engine, two views):
// several ranges (Ctrl+click), extend (Shift), whole rows and columns, Ctrl+A, and the status-bar
// Sum / Average / Count of the selected numbers.
import { Accessor, batch, createSignal } from "solid-js";

export type Range = { r0: number; c0: number; r1: number; c1: number };
export type Cell = { row: number; col: number };
export const norm = (g: Range): Range => ({ r0: Math.min(g.r0, g.r1), r1: Math.max(g.r0, g.r1), c0: Math.min(g.c0, g.c1), c1: Math.max(g.c0, g.c1) });

export type Sel = ReturnType<typeof createSel>;
/**
 * `size` gives (rows, columns) for clamping; `reveal` scrolls a cell into view. The signals can be
 * passed in (the task sheet keeps its selection in the store, for the Gantt chart and commands).
 */
export const createSel = (size: () => [number, number], reveal: (row: number, col: number) => void,
  sig?: { ranges: Accessor<Range[]>; setRanges: (v: Range[]) => void; cur: Accessor<Cell>; setCur: (v: Cell) => void }) => {
  const own = sig ? null : { r: createSignal<Range[]>([{ r0: 0, c0: 0, r1: 0, c1: 0 }]), c: createSignal<Cell>({ row: 0, col: 0 }) };
  const ranges = sig?.ranges ?? own!.r[0], setRanges = sig?.setRanges ?? own!.r[1], cur = sig?.cur ?? own!.c[0], setCur = sig?.setCur ?? own!.c[1];
  const last = () => norm(ranges()[ranges().length - 1] ?? { r0: cur().row, c0: cur().col, r1: cur().row, c1: cur().col });
  const inRange = (r: number, c: number) => ranges().some(g => r >= Math.min(g.r0, g.r1) && r <= Math.max(g.r0, g.r1) && c >= Math.min(g.c0, g.c1) && c <= Math.max(g.c0, g.c1));
  /** Moves the active cell; `extend` grows the last range to it, `add` starts another range. */
  const pick = (row: number, col: number, extend = false, add = false) => {
    const [nr, nc] = size();
    row = Math.max(0, Math.min(nr, row)); col = Math.max(0, Math.min(nc - 1, col));
    batch(() => {
      if (extend && ranges().length) setRanges([...ranges().slice(0, -1), { ...ranges()[ranges().length - 1], r1: row, c1: col }]);
      else { setCur({ row, col }); setRanges([...(add ? ranges() : []), { r0: row, c0: col, r1: row, c1: col }]); }
    });
    reveal(row, col);
  };
  /** Grows the last range while dragging. */
  const drag = (row: number, col: number) => { const g = ranges()[ranges().length - 1]; if (g) setRanges([...ranges().slice(0, -1), { ...g, r1: Math.max(0, row), c1: Math.max(0, col) }]); };
  const rows = (r0: number, r1: number, extend = false, add = false) => { const [, nc] = size(); setRanges([...(extend || add ? ranges().slice(0, extend ? -1 : undefined) : []), { r0: extend ? last().r0 : r0, c0: 0, r1, c1: nc - 1 }]); if (!extend) setCur({ row: r0, col: cur().col }); };
  const cols = (c0: number, c1: number, extend = false, add = false) => { const [nr] = size(); setRanges([...(extend || add ? ranges().slice(0, extend ? -1 : undefined) : []), { r0: 0, c0: extend ? last().c0 : c0, r1: Math.max(0, nr - 1), c1 }]); if (!extend) setCur({ row: 0, col: c0 }); };
  const all = () => { const [nr, nc] = size(); setRanges([{ r0: 0, c0: 0, r1: Math.max(0, nr - 1), c1: nc - 1 }]); };
  const wholeRows = () => ranges().length > 0 && ranges().every(g => norm(g).c0 === 0 && norm(g).c1 === size()[1] - 1);
  /** Calls `f` for every selected cell (up to `limit`). */
  const each = (f: (r: number, c: number) => void, limit = 50000) => { let n = 0; for (const g of ranges()) { const x = norm(g); for (let r = x.r0; r <= x.r1; r++) for (let c = x.c0; c <= x.c1; c++) { if (n++ >= limit) return; f(r, c); } } };
  return { ranges, setRanges, cur, setCur, last, inRange, pick, drag, rows, cols, all, wholeRows, each };
};

const num = (s: string) => { const v = parseFloat(s.replace(/[^\d.\-]/g, "")); return /\d/.test(s) && !/[a-z]{3,}-/i.test(s) ? v : NaN; };
/** "Sum 12 · Average 4 · Count 3" for a selection of more than one cell, as in Excel's status bar. */
export const aggregate = (sel: Sel, text: (r: number, c: number) => string) => {
  const vals: number[] = []; let cells = 0;
  sel.each((r, c) => { cells++; const v = num(text(r, c) ?? ""); if (!isNaN(v)) vals.push(v); }, 5000 * 30);
  if (cells < 2 || !vals.length) return "";
  const sum = vals.reduce((a, b) => a + b, 0);
  return `Sum ${+sum.toFixed(2)} · Average ${+(sum / vals.length).toFixed(2)} · Count ${vals.length}`;
};
