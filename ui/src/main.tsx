// Datum Plot window: layout, sidebar and navigator, status bar, keyboard shortcuts, startup and recovery.
import { render } from "solid-js/web";
import { For, Show, Switch, Match, onMount } from "solid-js";
import "@fontsource/ibm-plex-sans/latin-400.css";
import "@fontsource/ibm-plex-sans/latin-500.css";
import "@fontsource/ibm-plex-sans/latin-600.css";
import "@fontsource/ibm-plex-sans/latin-700.css";
import "@fontsource/ibm-plex-mono/latin-400.css";
import "@fontsource/ibm-plex-mono/latin-500.css";
import "@fontsource/ibm-plex-mono/latin-600.css";
import "./styles.css";
import { invoke, listen, Out, Options } from "./api";
import { out, setOut, backstage, setBackstage, setOpts, opts, dialogs, call, openDialog, toast, loadOut, setThemeRaw, applyTheme, item, table, graph, engine, setEngine, P } from "./store";
import { C } from "./cmds";
import { TitleBar, Ribbon, palette } from "./ribbon";
import { DataTable } from "./datatable";
import { GraphView, zoomG, setZoomG } from "./graph";
import { Side, Navigator, InfoPage, ResultsPage, LayoutsPage } from "./nav";
import { Backstage, update, checkUpdate } from "./backstage";
import { Menu, Toast, Dialog } from "./ui";
import * as D from "./dialogs";

const Status = () => (
  <footer class="status">
    <span classList={{ late: !!engine()?.error }}>{engine()?.error ? "Graph engine not available" : engine()?.versions ? "Ready" : "Starting the graph engine…"}</span>
    <span class="muted">{out() ? `${P().tables.length} ${P().tables.length === 1 ? "table" : "tables"} · ${P().graphs.length} ${P().graphs.length === 1 ? "graph" : "graphs"}` : ""}</span>
    <Show when={table()}>{t => <span class="muted">{t().name}: {t().rows} rows × {t().sets.length} data {t().sets.length === 1 ? "set" : "sets"}</span>}</Show>
    <Show when={graph()}>{g => <span class="muted">{g().name}: {g().settings.width} × {g().settings.height} mm</span>}</Show>
    <span class="grow" />
    <Show when={item().s === "graphs"}>
      <button onClick={() => C.zoom(1 / 1.15)}>−</button><input class="zoom" type="range" min="50" max="400" value={Math.round(zoomG() * 100 / 1.5)} onInput={e => setZoomG(+e.currentTarget.value * 1.5 / 100)} /><button onClick={() => C.zoom(1.15)}>+</button>
      <span class="muted">{Math.round(zoomG() * 100 / 1.5)}%</span>
    </Show>
  </footer>
);

const App = () => {
  onMount(async () => {
    try {
      const o = await invoke<Options>("options"); setOpts(o); setThemeRaw(o.theme || "auto"); applyTheme();
      setOut(await invoke<Out>("state"));
      listen("engine", e => setEngine(e));
      invoke("engine").then(e => setEngine(e)).catch(() => {});
      const start = await invoke<string | null>("startup_file");
      if (start) await loadOut("open", { path: start });
      const rec = await invoke<{ name: string; saved: string } | null>("recovery");
      if (rec) openDialog(() => (
        <Dialog title="Recover unsaved work?" okText="Recover" cancel="Discard" ok={async () => { const r = await call<Out>("recover", { keep: true }); if (r) { setOut(r); setBackstage(null); } }}>
          <p>Datum Plot closed before “{rec.name}” was saved. A copy from {rec.saved} was kept.</p>
        </Dialog>
      ));
      checkUpdate(true);
      setInterval(() => { if (opts().autosave > 0) invoke("autosave").catch(() => {}); }, Math.max(1, opts().autosave) * 60000);
      listen("close-requested", () => D.confirmClose(() => invoke("quit")));
    } catch (e) { toast(String(e)); }
  });
  const keys = (e: KeyboardEvent) => {
    const ctrl = e.ctrlKey || e.metaKey, k = e.key.toLowerCase(), typing = e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement;
    if (dialogs().length) return;
    if ((ctrl && k === "k") || (e.altKey && k === "q")) { e.preventDefault(); palette(); }
    else if (ctrl && k === "s") { e.preventDefault(); C.save(e.shiftKey); }
    else if (ctrl && k === "o") { e.preventDefault(); C.open(); }
    else if (ctrl && k === "n") { e.preventDefault(); setBackstage("home"); }
    else if (ctrl && k === "p") { e.preventDefault(); C.print(); }
    else if (ctrl && k === "z" && !typing) { e.preventDefault(); C.undo(); }
    else if (ctrl && k === "y" && !typing) { e.preventDefault(); C.redo(); }
    else if (e.key === "F1") { e.preventDefault(); D.shortcuts(); }
    else if (e.key === "Escape" && backstage() && out()) setBackstage(null);
  };
  return (
    <div class="app" ref={() => document.addEventListener("keydown", keys)}>
      <TitleBar update={update()?.available ? update()!.latest : null} />
      <Ribbon />
      <main class="work">
        <Side />
        <Show when={out()}><Navigator /></Show>
        <div class="content">
          <Show when={out()}>
            <Switch>
              <Match when={item().s === "info"}><InfoPage /></Match>
              <Match when={item().s === "results"}><ResultsPage /></Match>
              <Match when={item().s === "layouts"}><LayoutsPage /></Match>
              <Match when={item().s === "graphs" && graph()}><For each={[graph()!.id]}>{() => <GraphView g={graph()!} />}</For></Match>
              <Match when={table()}><For each={[table()!.id]}>{() => <DataTable t={table()!} />}</For></Match>
            </Switch>
          </Show>
        </div>
      </main>
      <Status />
      <Show when={backstage()}><Backstage /></Show>
      <For each={dialogs()}>{d => d()}</For>
      <Menu /><Toast />
    </div>
  );
};

render(() => <App />, document.getElementById("app")!);
