// Calls into the Rust shell and the shapes it returns.
declare global {
  interface Window { __TAURI__?: { core: { invoke: (cmd: string, args?: object) => Promise<any> }; event: { listen: (e: string, f: (x: { payload: any }) => void) => Promise<() => void> } } }
}

export const invoke = <T = any>(cmd: string, args?: object): Promise<T> =>
  window.__TAURI__ ? window.__TAURI__.core.invoke(cmd, args) : Promise.reject("Datum Plot must run inside its desktop window.");
export const listen = (e: string, f: (p: any) => void) => window.__TAURI__?.event.listen(e, x => f(x.payload));

export type Entry = "rep" | "msn" | "mesn";
export interface DataSet { title: string; entry: Entry; reps: number; role?: string; units?: string; comment?: string; formula?: string }
export interface Table {
  id: number; name: string; kind: string; xTitle: string; xUnits: string; yTitle: string; yUnits: string; rows: number; rowTitles: string[];
  sets: DataSet[]; cols: (number | null)[][]; excluded: [number, number][]; style: Record<string, string>; notes: string;
}
export interface Axis { title: string; scale: "lin" | "log"; auto: boolean; min: number | null; max: number | null; step: number | null; minor: boolean; grid: boolean; breakFrom?: number | null; breakTo?: number | null }
export interface SetStyle { show: boolean; color: string; symbol: string; size: number; filled: boolean; line: boolean | null; width: number; right?: boolean }
export interface GraphSettings {
  error: string; errorDir: string; points: string; line: boolean; cap: number; width: number; height: number; font: string; fontSize: number; boldTitles: boolean;
  style: string; title: string; showTitle: boolean; legend: { show: boolean; loc: string }; x: Axis; y: Axis; sets: SetStyle[]; overlays: number[];
  /** Column tables: scatter, bars, box, violin, paired or mean. */ column: string; /** Colour scheme name or "#hex, #hex…". */ palette: string; /** The right Y axis. */ y2: Axis; /** Annotations. */ notes: Note[];
  /** XY: polar axes. Matrix: contour levels and the 3D view. */ polar?: boolean; levels?: number; elev?: number; azim?: number;
}
/** An annotation in data coordinates: text at (x, y); an arrow from (x, y) to (x2, y2); a line; a box with those corners. */
export interface Note { kind: string; x: number; y: number; x2: number; y2: number; text: string; color: string; size: number; bold: boolean }
export interface Graph { id: number; table: number; name: string; settings: GraphSettings }
export interface Analysis { id: number; table: number; name: string; kind: string; sets: number[]; options: Record<string, any> }
/** An analysis's results from Python (py/datum/analysis.py). */
export interface ResultTable { title: string; columns: string[]; rows: string[][] }
export interface Result {
  title: string; answer: string; tabs: { name: string; tables: ResultTable[] }[]; checks: [boolean | null, string][]; methods: string; legend: string; code: string;
  plots: { title: string; svg: string }[]; curves: unknown[]; cells: [number, number][];
  /** [set, set, P] over column graphs. */ brackets?: [number, number, number][];
  /** A new data table the result can become (transforms, histograms, smoothing). */ table?: Partial<Table>;
}
export interface Info { title: string; experiment: string; researcher: string; organisation: string; date: string; notes: string }
/** A page layout: items placed in millimetres from the page's top-left. */
export interface LayoutItem { kind: string; graph: number; x: number; y: number; w: number; h: number; text: string; size: number; bold: boolean; inset?: boolean; hideX?: boolean }
export interface Layout { id: number; name: string; width: number; height: number; letters: string; letterSize: number; font: string; fontSize: number; align?: boolean; items: LayoutItem[] }
export interface Project { format: number; name: string; info: Info; tables: Table[]; graphs: Graph[]; analyses: Analysis[]; layouts: Layout[]; nextId: number; ui: any }
export interface Out { project: Project; path: string | null; dirty: boolean; undo: boolean; redo: boolean; rev: number }
/** A graph drawn by the Python engine: SVG and where things are, in points from the top-left. */
export interface Render {
  svg: string; w: number; h: number; plot: [number, number, number, number]; all: [number, number, number, number]; legend: [number, number, number, number] | null;
  xlim: [number, number]; ylim: [number, number]; xlog: boolean; ylog: boolean; points: ([number, number, number, number, number, number, number?] | null)[];
}
export interface Options {
  theme: string; autosave: number; beta: boolean; openLast: boolean; decimals: number; reps: number; entry: string; error: string; width: number; height: number;
  font: string; fontSize: number; style: string; dpi: number; paper: string; landscape: boolean; company: string; logo: string;
  /** Graph styles the user saved: name → settings. */ styles: Record<string, Partial<GraphSettings>>;
}

/** Spreadsheet-style column letters: A, B, … Z, AA. */
export const letter = (k: number): string => (k < 26 ? String.fromCharCode(65 + k) : letter(Math.floor(k / 26) - 1) + letter(k % 26));
/** Grid columns of each data set: [first column, width]. */
export const spans = (t: Table) => { let c = 1; return t.sets.map(s => { const w = s.entry === "rep" ? Math.max(1, s.reps) : 3; const v: [number, number] = [c, w]; c += w; return v; }); };
/** A data set with no values yet (left out of graphs and analyses). */
export const isEmpty = (t: Table, k: number) => { const [c0, w] = spans(t)[k] ?? [0, 0]; return t.cols.slice(c0, c0 + w).every(c => !c || c.every(v => v === null)); };
export const width = (t: Table) => 1 + t.sets.reduce((a, s) => a + (s.entry === "rep" ? Math.max(1, s.reps) : 3), 0);
/** A number for a table cell: as typed (up to 10 significant digits) or with fixed decimals. */
export const num = (v: number | null | undefined, decimals = -1) => v === null || v === undefined ? "" : decimals >= 0 ? v.toFixed(decimals) : String(+v.toPrecision(10));

/** Days since 1970-01-01 (local) and ISO dates, for the fill handle's date series. */
export const dayDate = (d: number) => { const x = new Date(1970, 0, 1); x.setDate(x.getDate() + Math.floor(d)); return x; };
export const dateDay = (x: Date) => Math.round((Date.UTC(x.getFullYear(), x.getMonth(), x.getDate()) - Date.UTC(1970, 0, 1)) / 864e5);
export const iso = (d: number) => { const x = dayDate(d); return `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, "0")}-${String(x.getDate()).padStart(2, "0")}`; };
