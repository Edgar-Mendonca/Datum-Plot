// Help and small dialogs: Paste Special, Getting Started, Glossary, Shortcuts, save before closing.
import { For, Show, createSignal } from "solid-js";
import { Out } from "./api";
import { openDialog, closeDialog, toast, call, P } from "./store";
import * as F from "./fmt";
import { Dialog, Row, Check } from "./ui";

export const pasteSpecial = () => {
  const t = F.target();
  if (!t?.paste) return toast("Click in a data table first.");
  openDialog(() => {
    const [what, setWhat] = createSignal<"all" | "values" | "formats">("all"), [tr, setTr] = createSignal(false);
    return (
      <Dialog title="Paste Special" okText="Paste" ok={() => { t.paste!(what(), tr()); }}>
        <div class="form">
          <Row label="Paste"><div class="stackr">{([["all", "All (values and formats)"], ["values", "Values only"], ["formats", "Formats only"]] as const).map(([k, l]) => <label class="chk"><input type="radio" name="ps" checked={what() === k} onChange={() => setWhat(k)} />{l}</label>)}</div></Row>
          <Row label=""><Check label="Transpose (rows become columns)" value={tr()} set={setTr} /></Row>
        </div>
        <p class="muted">Pastes what you last copied in Datum Plot. Text copied from Excel or elsewhere pastes as values.</p>
      </Dialog>
    );
  });
};

export const gettingStarted = () => openDialog(() => (
  <Dialog title="Getting Started" wide>
    <div class="guide">
      <p><b>Datum Plot</b> keeps a project as a chain, like GraphPad Prism: <b>data tables → analyses → results → graphs → layouts</b>. Everything stays linked: change a value and its graphs redraw.</p>
      <h4>Coming from Prism</h4>
      <ul><li>An <b>XY table</b> works as in Prism: one X column, then data sets A, B, C… each with its replicate sub-columns (Y1, Y2, Y3), or entered as mean with SD or SEM and N (Format Data Set).</li>
        <li>A new table comes with its graph. Double-click an axis, the legend or the data to format them. Error bars can show SD, SEM, 95% CI or the range.</li>
        <li><b>Exclude</b> a value (Ctrl+E) instead of deleting it: it turns blue and italic, and graphs skip it.</li></ul>
      <h4>Coming from OriginPro</h4>
      <ul><li>The table is a worksheet with fixed column roles: X, then Y columns grouped by data set. Paste a block from Excel with headings in the first row and they become the titles.</li>
        <li>Graphs are drawn by matplotlib, so exports are publication quality: PNG or TIFF at any dpi, and SVG, PDF and EPS with editable text.</li></ul>
      <h4>First steps</h4>
      <ol><li>File › Home: pick a sample (growth curve, standard curve, dose-response) or a blank XY table.</li>
        <li>Type or paste your data. Titles and units above the grid become the axis titles.</li>
        <li>Open the graph in the sidebar (Graphs). Use the Graph and Format tabs, or double-click parts of the graph.</li>
        <li>Export the graph, copy it into Word or PowerPoint (Ctrl+C on the graph), or print it (Ctrl+P).</li></ol>
      <h4>Analyses (0.2)</h4>
      <ul><li>Analyze… (or the Analyze tab): descriptive statistics, normality tests, outliers, linear regression, curve fitting and Arrhenius. Each result is linked to its table and updates when the data change.</li>
        <li>Fits are drawn on the graph with their 95% band and equation. Fit only part of the data with “Fit X from … to …” (e.g. the elastic region of a stress–strain curve).</li>
        <li>The results sheet explains the answer, checks the assumptions and gives methods text to paste into a report.</li></ul>
      <p class="muted">More arrives in small releases; Help › Roadmap lists every feature and when it comes. Planned commands are already in the ribbon (shown dimmed).</p>
    </div>
  </Dialog>
));

const GLOSSARY: [string, [string, string][]][] = [
  ["Data", [
    ["Data table", "A grid of values of one kind. An XY table has one X column and one or more data sets of Y values."],
    ["Data set", "One group of Y values (for example Control or Treated), with its own column title, symbol and colour."],
    ["Replicate", "A repeated measurement of the same thing at the same X. Each replicate is a sub-column (Y1, Y2…)."],
    ["Excluded value", "A value kept in the table but left out of graphs and analyses. Shown in blue italics. Ctrl+E switches it."],
    ["Row title", "A label for a row, such as an animal or a sample name."],
  ]],
  ["Statistics", [
    ["Mean", "The average: the sum of the values divided by how many there are."],
    ["SD (standard deviation)", "How spread out the values are. Use it to show the variation in your data."],
    ["SEM (standard error of the mean)", "How precisely the mean is known: SD divided by the square root of n. It shrinks as n grows."],
    ["95% CI (confidence interval)", "The range that contains the true mean with 95% confidence: mean ± t × SEM, with t from the t distribution with n − 1 degrees of freedom."],
    ["n", "The number of values (replicates) behind a mean."],
    ["Range", "From the smallest to the largest value."],
  ]],
  ["Graphs", [
    ["Error bar", "A line through a mean showing SD, SEM, 95% CI or the range. Say which one in your figure legend."],
    ["Log axis", "An axis where each step multiplies by 10. Used for concentrations in dose-response curves; zero and negative values cannot be shown."],
    ["Okabe-Ito colours", "Eight colours that people with colour-blindness can tell apart. The default for data sets."],
    ["Vector file (SVG, PDF, EPS)", "A picture made of lines and text, sharp at any size. Journals and Illustrator prefer it."],
    ["dpi", "Dots per inch of a picture file. 300 dpi suits most journals; 600 dpi or more for line art."],
  ]],
];
export const glossary = () => openDialog(() => {
  const [q, setQ] = createSignal("");
  return (
    <Dialog title="Glossary" wide>
      <input class="find" placeholder="Search terms" value={q()} onInput={e => setQ(e.currentTarget.value)} />
      <div class="gloss"><For each={GLOSSARY}>{([h, list]) => { const f = () => list.filter(x => (x[0] + x[1]).toLowerCase().includes(q().toLowerCase())); return <Show when={f().length}><h4>{h}</h4><dl><For each={f()}>{([t, d]) => <><dt>{t}</dt><dd>{d}</dd></>}</For></dl></Show>; }}</For></div>
    </Dialog>
  );
});

export const shortcuts = () => openDialog(() => (
  <Dialog title="Keyboard Shortcuts">
    <table class="keys"><tbody><For each={[["F2 / Enter", "Edit the cell"], ["Ctrl+C / X / V", "Copy, cut, paste (TSV, works with Excel)"], ["Ctrl+Alt+V", "Paste Special"], ["Ctrl+E", "Exclude or include values"],
      ["Ctrl+D / Ctrl+R", "Fill down / right"], ["Ctrl+B / I / U", "Bold, italic, underline"], ["Ctrl+A", "Select all"], ["Ctrl+C on a graph", "Copy the graph as a picture"], ["Ctrl+wheel", "Zoom the graph"],
      ["Ctrl+Z / Y", "Undo, redo"], ["Ctrl+S", "Save"], ["Ctrl+Shift+S", "Save As"], ["Ctrl+O", "Open"], ["Ctrl+N", "New (File › Home)"], ["Ctrl+P", "Print"], ["Ctrl+K or Alt+Q", "Tell me what you want to do"], ["F1", "This list"]]}>{([k, d]) => <tr><td>{k}</td><td>{d}</td></tr>}</For></tbody></table>
  </Dialog>
));

export const confirmClose = (then: () => void) => openDialog(() => (
  <Dialog title="Save changes?" okText="Save" cancel="Cancel" ok={async () => { const o = await call<Out | null>("save", { asNew: false }); if (o) then(); return !!o; }}
    extra={<button class="btn" onClick={() => { closeDialog(); then(); }}>Don't save</button>}>
    <p>Do you want to save the changes to “{P().name}”?</p>
  </Dialog>
));
