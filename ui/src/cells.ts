// Shared by the task sheet and the Sheets tabs: tab-separated clipboard text, Excel-style series
// for the fill handle, and the last copy (values and formats) for Paste Special.
import { dateDay, iso } from "./api";

export const parseTsv = (t: string): string[][] => {
  const out: string[][] = [[]];
  let cell = "", q = false;
  for (let i = 0; i < t.length; i++) {
    const ch = t[i];
    if (q) { if (ch === '"' && t[i + 1] === '"') { cell += '"'; i++; } else if (ch === '"') q = false; else cell += ch; }
    else if (ch === '"' && cell === "") q = true;
    else if (ch === "\t") { out[out.length - 1].push(cell); cell = ""; }
    else if (ch === "\n" || ch === "\r") { if (ch === "\r" && t[i + 1] === "\n") i++; out[out.length - 1].push(cell); cell = ""; out.push([]); }
    else cell += ch;
  }
  out[out.length - 1].push(cell);
  while (out.length > 1 && out[out.length - 1].every(x => !x)) out.pop();
  return out;
};
export const toTsv = (m: string[][]) => m.map(r => r.map(v => (/[\t\n"]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v)).join("\t")).join("\n");
export const transpose = (m: string[][]) => Array.from({ length: Math.max(...m.map(r => r.length)) }, (_, j) => m.map(r => r[j] ?? ""));

/** The last copy from either grid: values and cell styles (for Paste Special › Formats). */
export const clip = { text: "", styles: [] as string[][] };

const NUM = /^(-?[\d,]*\.?\d+)(\s*\S*)$/, TAIL = /^(.*?)(\d+)$/;
export const asDate = (s: string) => { if (!/\d/.test(s) || !/[-/ ]/.test(s) || /^\d+$/.test(s)) return null; const d = new Date(s.replace(/-(\d\d)$/, " 20$1").replace(/-/g, " ")); return isNaN(+d) ? null : dateDay(d); };
/**
 * The k-th value (k = 1, 2, …) after the source cells `src`, as Excel's fill handle does:
 * numbers continue their step (a single number counts up by 1), "Phase 1" → "Phase 2",
 * dates continue their step (a single date is copied); anything else repeats. `copy` (Ctrl) repeats.
 */
export const series = (src: string[], k: number, copy = false): string => {
  const rep = src[(k - 1) % src.length] ?? "";
  if (copy || !src.length || src.some(s => !s.trim())) return rep;
  const nums = src.map(s => s.trim().match(NUM));
  if (nums.every(Boolean)) {
    const v = nums.map(m => +m![1].replace(/,/g, "")), unit = nums[0]![2], step = v.length > 1 ? (v[v.length - 1] - v[0]) / (v.length - 1) : 1;
    const x = v[v.length - 1] + step * k, dec = Math.max(...nums.map(m => (m![1].split(".")[1] ?? "").length));
    return `${x.toFixed(dec)}${unit}`;
  }
  const dates = src.map(asDate);
  if (dates.every(d => d !== null)) {
    if (dates.length < 2) return rep;
    const step = (dates[dates.length - 1]! - dates[0]!) / (dates.length - 1);
    return iso(dates[dates.length - 1]! + step * k);
  }
  const tails = src.map(s => s.match(TAIL));
  if (tails.every(t => t && t[1] === tails[0]![1])) {
    const v = tails.map(t => +t![2]), step = v.length > 1 ? (v[v.length - 1] - v[0]) / (v.length - 1) : 1;
    return `${tails[0]![1]}${v[v.length - 1] + step * k}`;
  }
  return rep;
};
