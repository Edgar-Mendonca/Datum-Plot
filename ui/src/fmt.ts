// Text formatting (Excel's Font and Alignment groups) for the task sheet and the Sheets tabs.
// A style is a short string such as "b;i;c:#C0392B;f:#FFF2CC;z:12;a:c"; the engine stores it as is.
import { createSignal, JSX } from "solid-js";
import { toast } from "./store";

export type St = { b?: boolean; i?: boolean; u?: boolean; s?: boolean; c?: string; f?: string; z?: number; a?: string; n?: string };
export const parse = (x = ""): St => {
  const s: St = {};
  for (const t of x.split(";")) { const [k, v] = [t.slice(0, 1), t.slice(2)]; if ("bius".includes(k) && t.length === 1) (s as any)[k] = true; else if (k === "z") s.z = +v; else if (k === "c" || k === "f" || k === "a" || k === "n") s[k] = v; }
  return s;
};
export const ser = (s: St) => [s.b && "b", s.i && "i", s.u && "u", s.s && "s", s.c && `c:${s.c}`, s.f && `f:${s.f}`, s.z && `z:${s.z}`, s.a && `a:${s.a}`, s.n && `n:${s.n}`].filter(Boolean).join(";");
/** CSS for a style; `fill: false` leaves the background out (used where selection colours must win). */
export const css = (x?: string): JSX.CSSProperties => {
  if (!x) return {};
  const s = parse(x), o: JSX.CSSProperties = {};
  if (s.b) o["font-weight"] = "700";
  if (s.i) o["font-style"] = "italic";
  if (s.u || s.s) o["text-decoration"] = [s.u && "underline", s.s && "line-through"].filter(Boolean).join(" ");
  if (s.c) o.color = s.c;
  if (s.f) o.background = s.f;
  if (s.z) o["font-size"] = `${s.z}px`;
  if (s.n) o["font-family"] = `'${s.n}', sans-serif`;
  if (s.a) { o["text-align"] = s.a === "c" ? "center" : s.a === "r" ? "right" : "left"; o["justify-content"] = s.a === "c" ? "center" : s.a === "r" ? "flex-end" : "flex-start"; }
  return o;
};

/** The view with the focus says how to read and write the styles of its selected cells: [id, style]. */
/** `paste` (Paste Special) is called with what to paste and whether to transpose. */
export type Target = { get: () => [string, string][]; set: (list: [string, string][]) => Promise<unknown>; paste?: (what: "all" | "values" | "formats", transpose: boolean) => void };
export const [target, setTarget] = createSignal<Target | null>(null);
export const current = (): St => parse(target()?.get()[0]?.[1]);
const change = (f: (s: St) => St) => {
  const t = target(), list = t?.get() ?? [];
  if (!t || !list.length) return toast("Select the cells to format first.");
  const out = list.map(([id, v]) => [id, ser(f(parse(v)))] as [string, string]).filter(([, v], k) => v !== list[k][1]);
  if (out.length) t.set(out);
};
export const toggle = (k: "b" | "i" | "u" | "s") => { const on = !(target()?.get() ?? []).every(([, v]) => parse(v)[k]); change(s => ({ ...s, [k]: on })); };
export const setProp = <K extends "c" | "f" | "z" | "a" | "n">(k: K, v: St[K]) => change(s => ({ ...s, [k]: v }));
export const clearFmt = () => change(() => ({}));

// Format Painter: copy the active cell's style, then the next selection gets it.
export const [painter, setPainter] = createSignal<string | null>(null);
export const paint = () => { const s = target()?.get()[0]?.[1] ?? ""; setPainter(s); toast("Format Painter: select the cells to format."); };
/** Called by the grids when a mouse selection ends. */
export const painted = () => { const s = painter(); if (s === null) return; setPainter(null); change(() => parse(s)); };
