// File (backstage): Home with samples and recent projects, export, print, options, updates.
import { For, Show, createSignal, createResource, onMount, JSX } from "solid-js";
import { PAPERS, PrintPage } from "./print";
import { Options, Out } from "./api";
import { backstage, setBackstage, call, loadOut, out, setOut, opts, setOpts, toast, setThemeRaw, applyTheme, graph, engine } from "./store";
import { C } from "./cmds";
import * as D from "./dialogs";
import { Icon, Text, Pick, Check } from "./ui";
import { listen, invoke } from "./api";
import { ERRORS, FONTS, SIZES } from "./format";
import { RoadmapPage, importFile, newTable } from "./roadmap";

type Tpl = { id: string; name: string; desc: string; dots: [number, number][] };
type Info = { current: string; latest: string | null; beta: boolean; available: boolean; notes: string; published: string; url: string | null; sums: string | null; size: number; page: string };
export const [update, setUpdate] = createSignal<Info | null>(null);
export const [checking, setChecking] = createSignal(false), [checkedAt, setCheckedAt] = createSignal("");
export const checkUpdate = async (quiet: boolean) => {
  setChecking(true);
  try { setUpdate(await invoke<Info>("check_update")); setCheckedAt(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })); if (!quiet) toast(update()?.available ? `Version ${update()!.latest} is available.` : "You have the latest version.", true); }
  catch (e) { if (!quiet) toast(`Could not check for updates: ${e}`); }
  finally { setChecking(false); }
};
const GH = "https://github.com/Edgar-Mendonca/Datum-Plot";
/** Links to the project on GitHub: code, releases (change log) and issues (report a problem). */
export const GitHubLinks = () => (
  <div class="ghlinks">
    <For each={[["", "GitHub", "The project and its code"], ["/releases", "Releases", "Every version and its change log"], ["/issues/new", "Report an issue", "Tell us about a bug or an idea"]]}>{([path, l, t]) =>
      <button class="btn" title={t} onClick={() => call("open_url", { url: GH + path })}><svg class="ic"><use href={path === "/issues/new" ? "#i-bug" : path ? "#i-tag" : "#i-github"} /></svg>{l}</button>}</For>
  </div>
);

/** Release notes: headings, bullets and bold, enough for the changelog. */
const md = (s: string) => s.split("\n").map(l => {
  const e = l.replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]!).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`(.+?)`/g, "<code>$1</code>");
  return l.startsWith("## ") ? `<h3>${e.slice(3)}</h3>` : l.startsWith("- ") ? `<li>${e.slice(2)}</li>` : e.trim() ? `<p>${e}</p>` : "";
}).join("");

/** A sample's data as a small Prism-style picture. */
const Mini = (p: { t: Tpl }) => (
  <svg viewBox="0 0 100 60">
    <path d="M8 4v50h88" fill="none" stroke="currentColor" stroke-width="1.2" />
    <polyline points={p.t.dots.map(([x, y]) => `${12 + x * 80},${50 - y * 42}`).join(" ")} fill="none" stroke="#0072B2" stroke-width="1.2" />
    <For each={p.t.dots}>{([x, y]) => <circle cx={12 + x * 80} cy={50 - y * 42} r="2.2" fill="#0072B2" />}</For>
  </svg>
);

const Home = () => {
  const [tpls] = createResource(() => call<Tpl[]>("templates"));
  const [recent] = createResource(() => call<{ path: string; name: string; modified: string }[]>("recent"));
  const neu = (template: string | null) => loadOut("new_project", { template });
  return (
    <div class="home">
      <div>
        <h1>Good {new Date().getHours() < 12 ? "morning" : new Date().getHours() < 18 ? "afternoon" : "evening"}</h1>
        <div class="tiles">
          <button class="tile" onClick={() => neu(null)}><div class="pic"><svg class="ic"><use href="#i-xy" /></svg></div><b>Blank XY table</b><span>An X column and data sets with replicates, and its graph.</span></button>
          <For each={tpls() ?? []}>{t => <button class="tile" onClick={() => neu(t.id)}><div class="pic"><Mini t={t} /><small>sample</small></div><b>{t.name}</b><span>{t.desc}</span></button>}</For>
          <button class="tile" onClick={() => C.open()}><div class="pic"><svg class="ic"><use href="#i-open" /></svg></div><b>Open</b><span>A Datum Plot project (.dplot).</span></button>
          <button class="tile" onClick={async () => { if (!out()) await loadOut("new_project", { template: null }); importFile(); }}><div class="pic"><svg class="ic"><use href="#i-import" /></svg></div><b>Import data</b><span>A CSV, TXT or Excel file into a new XY table.</span></button>
          <button class="tile" onClick={() => D.guide()}><div class="pic"><svg class="ic"><use href="#i-pdf" /></svg></div><b>Guide</b><span>The step-by-step guide (PDF), in English, 中文 or Français.</span></button>
          <button class="tile" onClick={() => setBackstage("roadmap")}><div class="pic"><svg class="ic"><use href="#i-list" /></svg></div><b>Roadmap</b><span>Everything Datum Plot will do, and when.</span></button>
        </div>
        <h2>Recent</h2>
        <table class="recent"><tbody>
          <For each={recent() ?? []} fallback={<tr><td class="muted">Projects you open or save appear here.</td></tr>}>{r => <tr class="f" onClick={() => loadOut("open", { path: r.path })}><td><b>{r.name}</b><div class="p">{r.path}</div></td><td class="p">{r.modified}</td></tr>}</For>
        </tbody></table>
      </div>
      <UpdateCard />
    </div>
  );
};

const UpdateCard = () => {
  const [pct, setPct] = createSignal<number | null>(null);
  const [ver] = createResource(() => call<string>("version"));
  onMount(() => { listen("update-progress", (p: number) => setPct(p)); if (!update()) checkUpdate(true); });
  const install = async () => { const u = update(); if (!u?.url) return; setPct(0); await call("install_update", { url: u.url, sums: u.sums }); setPct(null); };
  return (
    <div class="card">
      <div class="brand"><img src="logo.svg" alt="" /><div><b>Datum Plot</b><span class="muted">Version {ver()}{opts().beta ? " · beta channel" : ""}</span></div></div>
      <Show when={update()} fallback={<><span class="pill">{checking() ? "Checking for updates…" : "Not checked yet"}</span><button class="btn wide" disabled={checking()} onClick={() => checkUpdate(false)}>{checking() ? <><i class="spin" /> Checking…</> : "Check for updates"}</button><GitHubLinks /></>}>{u => <>
        <Show when={u().available} fallback={<span class="pill ok">You have the latest version</span>}><span class="pill warn">Version {u().latest}{u().beta ? " (beta)" : ""} is ready</span></Show>
        <Show when={u().available && u().url}><button class="btn pri wide" disabled={pct() !== null} onClick={install}>{pct() === null ? `Update now (${Math.round(u().size / 1048576)} MB)` : `Downloading… ${pct()}%`}</button></Show>
        <Show when={pct() !== null}><div class="prog"><i style={{ width: `${pct()}%` }} /></div></Show>
        <button class="btn wide" disabled={checking()} onClick={() => checkUpdate(false)}>{checking() ? <><i class="spin" /> Checking…</> : "Check again"}</button>
        <Show when={checkedAt() && !checking()}><span class="muted small">Checked at {checkedAt()}</span></Show>
        <GitHubLinks />
        <EngineLine />
        <div class="notes"><h4>What's new{u().latest ? ` in ${u().latest}` : ""}</h4><div innerHTML={md(u().notes || "Release notes will appear here.")} /></div>
      </>}</Show>
    </div>
  );
};
const EngineLine = () => <p class="muted small engine">{engine()?.versions ? `Engine: ${Object.entries(engine()!.versions!).filter(([k]) => k !== "ok").map(([k, v]) => `${k} ${v}`).join(" · ")}` : engine()?.error ? `Engine: ${engine()!.error}` : "Engine: starting…"}</p>;

const Export = () => (
  <div><h1>Export</h1>
    <Show when={graph()} fallback={<p class="muted">Open a graph first (sidebar › Graphs), then come back here to export it.</p>}>{g => <>
      <p class="muted">Exporting <b>{g().name}</b> at its size, {g().settings.width} × {g().settings.height} mm.</p>
      <div class="tiles">
        <For each={[["png", "PNG picture", "For slides, documents and the web. 300 dpi by default."], ["tiff", "TIFF picture", "What many journals ask for, at 300–1200 dpi."], ["svg", "SVG vector", "Sharp at any size; text stays editable in Illustrator or Inkscape."],
          ["pdf", "PDF vector", "For LaTeX, print shops and archiving."], ["eps", "EPS vector", "For older publishing tools."]]}>{([k, n, d]) =>
          <button class="tile" onClick={() => C.exportG(k)}><div class="pic"><svg class="ic"><use href="#i-image" /></svg><small>.{k}</small></div><b>{n}</b><span>{d}</span></button>}</For>
        <button class="tile" onClick={() => { setBackstage(null); C.copyG(); }}><div class="pic"><svg class="ic"><use href="#i-copy" /></svg></div><b>Copy picture</b><span>Paste the graph straight into Word, PowerPoint or an email.</span></button>
        <button class="tile" onClick={() => setBackstage("print")}><div class="pic"><svg class="ic"><use href="#i-print" /></svg></div><b>Print or save as PDF</b><span>A page with the graph, headers and footers.</span></button>
      </div>
    </>}</Show>
  </div>
);

/** One option: name and a one-line explanation on the left, the control on the right. */
const Opt = (p: { l: string; hint?: string; children: JSX.Element }) => <div class="opt"><div><b>{p.l}</b>{p.hint && <small>{p.hint}</small>}</div><div class="ctl">{p.children}</div></div>;
const Sec = (p: { t: string; about: string; children: JSX.Element }) => <section class="osec"><h3>{p.t}</h3><p class="muted">{p.about}</p>{p.children}</section>;

const OptionsPage = () => {
  const [o, setO] = createSignal<Options>({ ...opts() });
  const save = async () => { const r = await call<Out>("set_options", { opts: o() }); if (r) { setOpts(o()); setOut(r); toast("Options saved.", true); } };
  const put = <K extends keyof Options>(k: K, v: Options[K]) => setO({ ...o(), [k]: v });
  return (
    <div class="options"><h1>Options</h1>
      <p class="muted">Settings for Datum Plot on this computer. Defaults for new tables and graphs apply when they are created; change an open graph with Format Graph.</p>
      <Sec t="General" about="How the window looks and numbers are shown.">
        <Opt l="Theme" hint="Auto follows the Windows light or dark setting."><Pick value={o().theme || "auto"} set={v => { put("theme", v); setThemeRaw(v); applyTheme(); }} options={[["auto", "Auto (follow Windows)"], ["light", "Light"], ["dark", "Dark"]]} /></Opt>
        <Opt l="Decimals in data tables" hint="Values are stored exactly; this is only how they are shown."><Pick value={String(o().decimals)} set={v => put("decimals", +v)} options={[["-1", "As typed"], ["0", "0"], ["1", "1"], ["2", "2"], ["3", "3"], ["4", "4"], ["6", "6"]]} /></Opt>
      </Sec>
      <Sec t="Start-up and saving" about="What happens when Datum Plot starts, and how your work is protected.">
        <Opt l="When Datum Plot starts" hint="Open the File page, or reopen the project you used last."><Pick value={o().openLast ? "last" : "home"} set={v => put("openLast", v === "last")} options={[["home", "Show the File page"], ["last", "Reopen the last project"]]} /></Opt>
        <Opt l="Recovery copy every" hint="A copy is kept while you work, so a crash or power cut loses little. 0 turns it off."><span class="inline"><input type="number" min="0" style={{ width: "70px" }} value={o().autosave} onChange={e => put("autosave", +e.currentTarget.value)} /> minutes</span></Opt>
      </Sec>
      <Sec t="New data tables" about="How a new XY table is set up.">
        <Opt l="Enter values as" hint="Replicates, or a mean with its SD or SEM and N."><Pick value={o().entry} set={v => put("entry", v)} options={[["rep", "Replicate values"], ["msn", "Mean, SD and N"], ["mesn", "Mean, SEM and N"]]} /></Opt>
        <Opt l="Replicates per data set" hint="Sub-columns Y1, Y2, … for each data set."><input type="number" min="1" max="50" value={o().reps} onChange={e => put("reps", Math.max(1, Math.min(50, +e.currentTarget.value)))} /></Opt>
      </Sec>
      <Sec t="New graphs" about="The look of every new graph.">
        <Opt l="Error bars" hint="What the bars through each mean show."><Pick value={o().error} set={v => put("error", v)} options={ERRORS} /></Opt>
        <Opt l="Size" hint="Width and height in millimetres; 85 mm is a journal's single column."><span class="inline"><input type="number" min="10" max="1000" style={{ width: "80px" }} value={o().width} onChange={e => put("width", +e.currentTarget.value)} /> × <input type="number" min="10" max="1000" style={{ width: "80px" }} value={o().height} onChange={e => put("height", +e.currentTarget.value)} /> mm
          <Pick value="" set={v => { const z = SIZES.find(q => q[0] === v); if (z) setO({ ...o(), width: z[1], height: z[2] }); }} options={[["", "Journal sizes…"], ...SIZES.map(z => [z[0], z[0]] as [string, string])]} /></span></Opt>
        <Opt l="Font" hint="One font and size for the whole graph."><span class="inline"><Pick value={o().font} set={v => put("font", v)} options={FONTS} /><input type="number" min="5" max="36" step="0.5" style={{ width: "64px" }} value={o().fontSize} onChange={e => put("fontSize", +e.currentTarget.value)} /> pt</span></Opt>
        <Opt l="Axes" hint="Open axes (Prism) or a framed box (Origin)."><Pick value={o().style} set={v => put("style", v)} options={[["prism", "Open, ticks out"], ["frame", "Framed box, ticks in"]]} /></Opt>
        <Opt l="Picture resolution" hint="For PNG and TIFF export and copied pictures."><Pick value={String(o().dpi)} set={v => put("dpi", +v)} options={[["150", "150 dpi"], ["300", "300 dpi"], ["600", "600 dpi"], ["1200", "1200 dpi"]]} /></Opt>
      </Sec>
      <Sec t="Printing and branding" about="Your organisation and logo can go in page headers (File › Print).">
        <Opt l="Paper" hint="Default paper for printouts."><span class="inline"><Pick value={o().paper || "A4"} set={v => put("paper", v)} options={PAPERS.map(p => p[0])} /><Pick value={o().landscape ? "1" : "0"} set={v => put("landscape", v === "1")} options={[["0", "Portrait"], ["1", "Landscape"]]} /></span></Opt>
        <Opt l="Organisation" hint="Shown in headers and footers with &[Company]."><Text value={o().company} set={v => put("company", v)} /></Opt>
        <Opt l="Logo" hint="PNG or JPG for page headers (&[Logo])."><span class="inline">{o().logo && <img src={o().logo} class="logoprev" />}<button class="btn sm" onClick={async () => { const l = await call<string | null>("pick_logo"); if (l) put("logo", l); }}>Choose picture…</button>{o().logo && <button class="btn sm" onClick={() => put("logo", "")}>Remove</button>}</span></Opt>
      </Sec>
      <Sec t="Updates" about="Datum Plot checks GitHub for new versions when it starts. Updates install from File › Updates.">
        <Opt l="Beta versions" hint="Get new features early. They may have bugs."><Check label="Get beta versions" value={o().beta} set={v => put("beta", v)} /></Opt>
      </Sec>
      <p class="osave"><button class="btn pri" onClick={save}>Save options</button><span class="muted">Datum Plot keeps everything on this computer. It connects only to GitHub: to check for updates and to download the guide.</span></p>
    </div>
  );
};

export const Backstage = () => (
  <div class="bs">
    <aside>
      <button class="back" onClick={() => out() && setBackstage(null)} title="Back">←</button>
      <For each={[["home", "home", "Home"], ["new", "new", "New"], ["open", "open", "Open"], ["import", "import", "Import"], ["save", "save", "Save"], ["saveas", "save", "Save As"], ["export", "export", "Export"], ["print", "print", "Print"]]}>{([k, i, l]) =>
        <button classList={{ on: backstage() === k }} onClick={() => {
          if (k === "open") C.open(); else if (k === "import") importFile(); else if (k === "new") newTable(); else if (k === "save") C.save(); else if (k === "saveas") C.save(true);
          else setBackstage(k);
        }}><Icon n={i} size={22} />{l}</button>}</For>
      <span class="grow" />
      <button classList={{ on: backstage() === "roadmap" }} onClick={() => setBackstage("roadmap")}><Icon n="list" size={22} />Roadmap</button>
      <button classList={{ on: backstage() === "options" }} onClick={() => setBackstage("options")}><Icon n="opts" size={22} />Options</button>
      <button classList={{ on: backstage() === "about" }} onClick={() => setBackstage("about")}><Icon n="upd" size={22} />Updates</button>
    </aside>
    <section class="bsmain">
      <Show when={backstage() === "home"}><Home /></Show>
      <Show when={backstage() === "export"}><Export /></Show>
      <Show when={backstage() === "options"}><OptionsPage /></Show>
      <Show when={backstage() === "roadmap"}><RoadmapPage /></Show>
      <Show when={backstage() === "print"}><PrintPage /></Show>
      <Show when={backstage() === "about"}><div class="about"><h1>Updates</h1><UpdateCard /><p><button class="btn" onClick={() => D.shortcuts()}>Keyboard shortcuts</button></p></div></Show>
    </section>
  </div>
);
