// Tools › Python Console (H1) and My Analyses (H2): run your own Python on the project's tables.
// The code runs in the app's Python engine only when you press Run; projects never carry code.
import { For, Show, createSignal } from "solid-js";
import { Out, invoke } from "./api";
import { call, openDialog, openMenu, opts, setOpts, setOut, toast, Item } from "./store";
import { Dialog } from "./ui";

const [code, setCode] = createSignal("# Your tables are ready as pandas DataFrames, for example:\ntables\n");
const [log, setLog] = createSignal<{ code: string; out: string; figures: string[]; error: boolean }[]>([]);
const [busy, setBusy] = createSignal(false);
const [guide, setGuide] = createSignal(false);

export const EXAMPLES: [string, string][] = [
  ["List the tables", "tables"],
  ["Look at a table", "df = table(0)        # the first table; or tables['Its name']\ndf.describe()"],
  ["A column's statistics", "df = table(0)\ny = df.iloc[:, 1].dropna()     # the second column\nprint('mean', y.mean(), 'SD', y.std())\nstats.shapiro(y)"],
  ["Fit a straight line", "df = table(0)\nx, y = df.iloc[:, 0], df.iloc[:, 1]\nfit = stats.linregress(x, y)\nprint(f'slope {fit.slope:.4g}, R² {fit.rvalue**2:.4f}')"],
  ["Draw a figure", "df = table(0)\nplt.figure(figsize=(4, 3))\nplt.plot(df.iloc[:, 0], df.iloc[:, 1], 'o-')\nplt.xlabel(df.columns[0]); plt.ylabel(df.columns[1])"],
  ["Make a new table", "df = table(0)\nout = pd.DataFrame({'X': df.iloc[:, 0], 'log10 Y': np.log10(df.iloc[:, 1])})\nnew_table('Log values', out)"],
  ["Read a result", "r = result('Linear regression · Data 1')   # an analysis by its name\nprint(r['answer'])"],
];

const run = async (text = code()) => {
  if (busy() || !text.trim()) return;
  setBusy(true);
  try {
    const r = await invoke<{ out: string; figures: string[]; tables: unknown[]; error: boolean; state: Out }>("console", { code: text, reset: false });
    setOut(r.state);
    setLog([...log().slice(-30), { code: text, out: r.out, figures: r.figures, error: r.error }]);
    if (r.out === "" && !r.figures.length && !r.error) setLog([...log().slice(0, -1), { code: text, out: "(done: nothing printed — the last line's value or print(...) shows here)", figures: [], error: false }]);
  } catch (e) { setLog([...log(), { code: text, out: String(e), figures: [], error: true }]); }
  setBusy(false);
  queueMicrotask(() => document.querySelector(".conlog")?.scrollTo({ top: 1e9 }));
};
const reset = async () => { const r = await call<{ out: string }>("console", { code: "", reset: true }); if (r) setLog([...log(), { code: "", out: r.out, figures: [], error: false }]); };
const snippets = (): Record<string, string> => opts().snippets ?? {};
const keep = (s: Record<string, string>) => { const o = { ...opts(), snippets: s }; setOpts(o); return invoke("set_options", { opts: o }); };
const saveSnippet = () => {
  const name = prompt("Save this code as one of My Analyses. Name:", "");
  if (!name?.trim()) return;
  keep({ ...snippets(), [name.trim()]: code() }).then(() => toast(`“${name.trim()}” is in Tools › My Analyses.`, true)).catch(e => toast(String(e)));
};
/** Tools › My Analyses: the saved pieces of code, to open in the console or run at once. */
export const myAnalyses = (e: MouseEvent) => {
  const s = snippets(), names = Object.keys(s).sort();
  const items: Item[] = names.length ? names.flatMap(n => [{ label: `Run “${n}”`, icon: "fx", run: () => { setCode(s[n]); openConsole(); run(s[n]); } }] as Item[]) : [{ label: "No saved analyses yet: write code in the console, then Save As My Analysis", run: () => openConsole() }];
  openMenu(e, [...items, "-", ...names.map(n => ({ label: `Open “${n}” in the console`, run: () => { setCode(s[n]); openConsole(); } }) as Item), ...names.map(n => ({ label: `Delete “${n}”`, icon: "del", run: () => { const c = { ...s }; delete c[n]; keep(c); } }) as Item)]);
};

const Guide = () => (
  <div class="conguide">
    <h4>How to use the Python console</h4>
    <ol>
      <li><b>Write</b> Python in the box at the top. Your data tables are ready as pandas DataFrames: <code>tables</code> lists them, <code>table(0)</code> is the first, <code>tables['Name']</code> one by its name. Columns are named after the data sets (replicates as “Control 1”, “Control 2”; the X column first).</li>
      <li><b>Run</b> with the Run button or <kbd>Ctrl</kbd>+<kbd>Enter</kbd>. What you <code>print</code>, and the value of the last line, appear below; figures you draw with <code>plt</code> appear as pictures. Errors say which line went wrong.</li>
      <li><b>Keep going</b>: variables stay between runs (until Reset or an engine restart), so you can work step by step.</li>
      <li><b>Put results back</b>: <code>new_table('Name', data)</code> adds a table to the project when the code has run (a DataFrame or <code>{'{'}column: values{'}'}</code>; for XY the first column is X). <code>result('Analysis name')</code> gives an analysis's numbers.</li>
      <li><b>Save</b> code you use often with Save As My Analysis; run it later from Tools › My Analyses.</li>
    </ol>
    <p>Ready to use: <code>np</code> (numpy), <code>pd</code> (pandas), <code>stats</code> (scipy.stats), <code>scipy</code>, <code>plt</code> (matplotlib). Code that runs longer than a minute is stopped (the engine restarts and variables are cleared). The code runs on your computer with your rights, like any Python script: run only code you understand. Projects never contain code, so opening a file from someone else never runs anything.</p>
  </div>
);

export const openConsole = () => openDialog(() => (
  <Dialog title="Python Console" help="console" wide cancel="Close"
    extra={<><button class="btn" onClick={reset} title="Forget all variables and imports">Reset</button><button class="btn" onClick={() => setLog([])}>Clear output</button></>}>
    <div class="console">
      <div class="conbar">
        <button class="btn pri" disabled={busy()} onClick={() => run()} title="Run the code (Ctrl+Enter)">{busy() ? "Running…" : "▶ Run"}</button>
        <button class="btn" onClick={e => openMenu(e, EXAMPLES.map(([l, c]) => ({ label: l, run: () => setCode(c) })))}>Examples ▾</button>
        <button class="btn" onClick={myAnalyses}>My Analyses ▾</button>
        <button class="btn" onClick={saveSnippet}>Save As My Analysis…</button>
        <span class="grow" />
        <button class="btn" classList={{ on: guide() }} onClick={() => setGuide(!guide())} title="How to use the console">ⓘ How to use</button>
      </div>
      <Show when={guide()}><Guide /></Show>
      <textarea class="concode mono" spellcheck={false} value={code()} onInput={e => setCode(e.currentTarget.value)} aria-label="Python code"
        onKeyDown={e => {
          if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); run(); }
          else if (e.key === "Tab") { e.preventDefault(); const t = e.currentTarget, a = t.selectionStart, b = t.selectionEnd; t.setRangeText("    ", a, b, "end"); setCode(t.value); }
        }} />
      <div class="conlog">
        <Show when={!log().length}><p class="muted">Output appears here. New to it? Press ⓘ How to use, or pick one of the Examples and press Run.</p></Show>
        <For each={log()}>{l => <div class="conrun">
          <Show when={l.code}><pre class="conin mono">{l.code.length > 400 ? l.code.slice(0, 400) + " …" : l.code}</pre></Show>
          <Show when={l.out}><pre class="conout mono" classList={{ err: l.error }}>{l.out}</pre></Show>
          <For each={l.figures}>{svg => <img class="config" alt="Figure" src={`data:image/svg+xml;base64,${btoa(unescape(encodeURIComponent(svg)))}`} />}</For>
        </div>}</For>
      </div>
    </div>
  </Dialog>
));
