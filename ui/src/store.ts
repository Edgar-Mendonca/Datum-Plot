// Window state: the open project, the item shown (Info, a table or a graph), menus, dialogs, toasts.
import { createSignal, batch, JSX } from "solid-js";
import { invoke, Out, Options, Table, Graph } from "./api";

export const [out, setOutRaw] = createSignal<Out | null>(null);
export const [tick, setTick] = createSignal(0);
export const setOut = (o: Out | null | undefined) => { if (o) batch(() => { setOutRaw(o); setTick(t => t + 1); fixItem(); }); };
export const P = () => out()!.project;

/** auto, light or dark; auto follows Windows. */
export const [theme, setThemeRaw] = createSignal("auto");
const darkMq = typeof matchMedia === "function" ? matchMedia("(prefers-color-scheme: dark)") : null;
export const applyTheme = () => { document.documentElement.dataset.theme = theme() === "auto" ? (darkMq?.matches ? "dark" : "light") : theme(); };
darkMq?.addEventListener("change", () => theme() === "auto" && applyTheme());
export const setTheme = (t: string) => { setThemeRaw(t); applyTheme(); setOpts({ ...opts(), theme: t }); invoke("set_options", { opts: opts() }).catch(() => {}); };
export const [opts, setOpts] = createSignal<Options>({
  theme: "auto", autosave: 5, beta: false, openLast: false, decimals: -1, reps: 3, entry: "rep", error: "sd", width: 80, height: 60, font: "Arial", fontSize: 10, style: "prism",
  dpi: 300, paper: "A4", landscape: false, company: "", logo: "",
});

// ---------- what is shown: the navigator's sections and items ----------
export type Section = "info" | "data" | "results" | "graphs" | "layouts";
/** The open item: a section, and for Data and Graphs the id of the table or graph. */
export const [item, setItem] = createSignal<{ s: Section; id: number }>({ s: "data", id: 0 });
export const [backstage, setBackstage] = createSignal<string | null>("home");
export const [tab, setTab] = createSignal("data");
export const [navOpen, setNavOpen] = createSignal(true);
export const table = (): Table | undefined => item().s === "data" ? out()?.project.tables.find(t => t.id === item().id) : undefined;
export const graph = (): Graph | undefined => item().s === "graphs" ? out()?.project.graphs.find(g => g.id === item().id) : undefined;
/** The table behind what is shown: the table itself, or the graph's data. */
export const curTable = (): Table | undefined => table() ?? out()?.project.tables.find(t => t.id === graph()?.table);
export const open = (s: Section, id = 0) => {
  if (!id && s === "data") id = out()?.project.tables[0]?.id ?? 0;
  if (!id && s === "graphs") id = out()?.project.graphs.find(g => g.table === curTable()?.id)?.id ?? out()?.project.graphs[0]?.id ?? 0;
  setItem({ s, id });
  setTab(s === "graphs" ? "graph" : s === "data" ? "data" : tab());
};
/** After a change, keep the open item valid (it may have been deleted or undone). */
const fixItem = () => {
  const p = out()?.project, it = item();
  if (!p) return;
  if (it.s === "data" && !p.tables.some(t => t.id === it.id)) setItem({ s: "data", id: p.tables[0]?.id ?? 0 });
  if (it.s === "graphs" && !p.graphs.some(g => g.id === it.id)) setItem(p.graphs[0] ? { s: "graphs", id: p.graphs[0].id } : { s: "data", id: p.tables[0]?.id ?? 0 });
};

// ---------- editing ----------
export const act = async (op: object, quiet = false): Promise<boolean> => {
  try { setOut(await invoke<Out>("apply", { op })); return true; }
  catch (e) { if (!quiet) toast(String(e)); return false; }
};
export const call = async <T = any>(cmd: string, args?: object): Promise<T | undefined> => {
  try { return await invoke<T>(cmd, args); } catch (e) { toast(String(e)); return undefined; }
};
/** Loads a project (new, opened, recovered) and shows its first graph. */
export const loadOut = async (cmd: string, args?: object) => {
  const o = await call<Out | null>(cmd, args);
  if (o) { setOut(o); setBackstage(null); const g = o.project.graphs[0]; if (g) open("graphs", g.id); else open("data"); }
  return o;
};

/** The Python engine: its versions once it answers, or why it could not start. */
export const [engine, setEngine] = createSignal<{ versions: Record<string, string> | null; error: string | null } | null>(null);

// ---------- messages, menus, dialogs ----------
export const [msg, setMsg] = createSignal<{ text: string; ok: boolean } | null>(null);
let timer = 0;
export const toast = (text: string, ok = false) => { setMsg({ text, ok }); clearTimeout(timer); timer = window.setTimeout(() => setMsg(null), ok ? 3000 : 7000); };
export type Item = { label: string; run?: () => void; keys?: string; off?: boolean; on?: boolean; sub?: Item[]; icon?: string } | "-";
export const [menu, setMenu] = createSignal<{ x: number; y: number; items: Item[] } | null>(null);
export const openMenu = (e: MouseEvent | { x: number; y: number }, items: Item[]) => {
  if ("preventDefault" in e) e.preventDefault();
  const r = (e as MouseEvent).currentTarget instanceof HTMLElement && (e as MouseEvent).type === "click" ? ((e as MouseEvent).currentTarget as HTMLElement).getBoundingClientRect() : null;
  setMenu({ x: r ? r.left : (e as MouseEvent).clientX ?? (e as any).x, y: r ? r.bottom + 2 : (e as MouseEvent).clientY ?? (e as any).y, items });
};
export const [dialogs, setDialogs] = createSignal<(() => JSX.Element)[]>([]);
export const openDialog = (d: () => JSX.Element) => setDialogs(v => [...v, d]);
export const closeDialog = () => setDialogs(v => v.slice(0, -1));
