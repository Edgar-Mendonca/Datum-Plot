// "?" help: a small button beside a tool; a click opens a short card saying what the tool is for
// and how to use it. One place for every explanation, so the whole app teaches itself.
import { For, Show } from "solid-js";
import { openDialog } from "./store";
import { Dialog } from "./ui";

type Topic = { t: string; what: string; how?: string[]; tip?: string };
export const HELP: Record<string, Topic> = {
  // Data tab
  clipboard: { t: "Clipboard", what: "Cut, copy and paste cells, also to and from Excel.",
    how: ["Select cells, Ctrl+C, then click where they go and Ctrl+V.", "Paste ▾ › Paste Special (Ctrl+Alt+V) pastes only values, only formats, or turned sideways (Transpose).", "Format Painter: click it, then click the cells that should look the same."] },
  font: { t: "Font", what: "The typeface, size, colour, fill and bold/italic/underline of the selected cells in the table. Graph text is set on the Format tab." },
  alignment: { t: "Alignment", what: "Left, centre or right alignment of the selected cells, and Clear Formatting to put them back as they were." },
  insert: { t: "Insert", what: "New tables and more room in the open one.",
    how: ["New Table picks the kind of data table (XY today; more kinds are listed with their release).", "Import reads a CSV, TXT or Excel file into a new XY table.", "Add Data Set adds a column group (B, C…); Add 10 Rows and Remove Last Row change the length."] },
  transform: { t: "Transform", what: "Work on the values themselves. Find Outliers runs Grubbs' test on each data set; the dimmed commands arrive in later releases (Help › Roadmap)." },
  values: { t: "Values", what: "Commands for the selected cells and their data set.",
    how: ["Exclude / Include (Ctrl+E): the value stays in the table in blue italic, but graphs and analyses leave it out.", "Format Data Set: its title, how values are entered (replicates, or mean with SD or SEM and N) and how many replicates.", "Fill Down (Ctrl+D) copies the top cell into the cells below."] },
  graph: { t: "Graphs", what: "A graph draws a data table. It stays linked: change a value and the graph redraws.",
    how: ["New Graph makes a graph of the open table.", "Show Graph (or Graphs in the navigator) opens it."] },
  item: { t: "Item", what: "Rename, duplicate or delete the table, result or graph that is open. Right-click it in the navigator for the same commands." },
  // Analyze tab
  analyze: { t: "Analyze", what: "Adds an analysis of a data table. Its result appears under Results in the navigator and updates when the data change.",
    how: ["Analyze… opens the list of analyses with a short description of each; dimmed ones say when they arrive.", "Pick the data sets and the options, then Analyze.", "Change… on the results sheet reopens the options."] },
  statistics: { t: "Statistics", what: "Describe each data set and check it before testing.",
    how: ["Descriptive: n, mean, SD, SEM, 95% CI, median, quartiles, CV and more.", "Normality: Shapiro-Wilk and other tests, with QQ plots: is the data close to a normal distribution?", "Outliers: Grubbs' test; one click on the results sheet excludes them."] },
  regression: { t: "Regression and curve fitting", what: "Fit a line or a curve to XY data, with standard errors, 95% intervals and checks. The fit is drawn on the graph with its band and equation.",
    how: ["Linear Regression: slope, intercept, R²; fit only part of the data with “Fit X from … to …”; compare the lines of several data sets.", "Curve Fit: pick a model from the library or type your own equation, e.g. Y = A*exp(-k*X) + C.", "Arrhenius: activation energy from rates at several temperatures.", "Interpolate: read X off the fit for unknown Y values."],
    tip: "Regression uses every replicate by default, not only the means." },
  // Graph and Format tabs
  graphtab: { t: "Graph", what: "Make a graph, choose its type, or go back to its data table." },
  gdata: { t: "What the graph shows", what: "How each data set is drawn.",
    how: ["Error Bars: SD, SEM, 95% CI or the range, or none.", "Each Replicate draws every value instead of the mean.", "Connect Points joins the points; Legend shows or hides the key."] },
  axes: { t: "Axes", what: "Log or linear axes and the look of the frame.",
    how: ["Log X / Log Y switch an axis to a log scale (for dose-response or spectra).", "Framed Axes draws a box around the plot instead of two open axes.", "Format Axes sets ranges, ticks, titles and numbers."] },
  size: { t: "Size", what: "The size of the graph in millimetres, as it will be printed or exported. Journal column widths are in the list." },
  add: { t: "Add to the graph", what: "Fit a Curve runs linear regression or a curve fit and draws it on this graph. Significance brackets and annotations arrive later (Help › Roadmap)." },
  share: { t: "Share", what: "Get the graph out of Datum Plot at publication quality.",
    how: ["Export: PNG or TIFF at any dpi, or SVG, PDF and EPS with editable text.", "Copy Picture puts the graph on the clipboard for Word or PowerPoint (Ctrl+C on the graph).", "Print (Ctrl+P) with page setup and headers."] },
  format: { t: "Format Graph", what: "Every setting of the graph, in a panel on the right. Each change shows at once and can be undone.",
    how: ["Data Sets: symbols, colours, lines and error bars.", "X Axis / Y Axis: range, scale, ticks, title and numbers.", "Graph: title, size, font, legend and frame.", "Double-click a part of the graph to open its page."] },
  text: { t: "Graph text", what: "The font and size of all the text in the graph, and bold axis titles. A+ and A− step the size." },
  glayout: { t: "Graph layout", what: "The graph's size, the legend, framed or open axes, and Graph Options (the Graph page of Format Graph)." },
  // Tools and View tabs
  engine: { t: "Engine", what: "Datum Plot calculates and draws with a Python engine (numpy, SciPy, matplotlib) that runs beside the window. If graphs stop drawing, Restart Engine starts it again; your project is not touched." },
  show: { t: "Show", what: "Opens the project's Info sheet, its data tables or its graphs; Navigator shows or hides the list on the left." },
  zoom: { t: "Zoom", what: "How big the graph looks on screen. It does not change the graph's size in exports (Ctrl+wheel zooms too)." },
  theme: { t: "Theme", what: "Light, dark, or Auto to follow Windows. Graphs keep their own colours so exports look the same." },
  // Panels and dialogs
  navigator: { t: "Navigator", what: "The project as a chain: data tables → results → graphs → layouts. Everything stays linked.",
    how: ["Click an item to open it; ＋ adds one to its section.", "Right-click for rename, duplicate and delete; double-click to rename."] },
  info: { t: "Info sheet", what: "What the project is about: title, experiment, researcher, organisation, date and notes. Saved with the project; some fields can be printed in headers and footers." },
  table: { t: "XY data table", what: "One X column, then data sets A, B, C… each with its replicate columns (Y1, Y2…) or entered as mean with SD or SEM and N.",
    how: ["Type or paste from Excel; headings in the first row become the titles.", "The X and Y titles and units above the grid become the axis titles.", "Double-click a data set heading to format it; Ctrl+E excludes the selected values."] },
  graphview: { t: "Graph", what: "The graph as it will be exported, drawn by the engine.",
    how: ["Hover a point for its values.", "Double-click an axis, the legend or the data to format it; right-click for more.", "Ctrl+wheel zooms the view."] },
  results: { t: "Results sheet", what: "The result of one analysis, linked to its table: tables you can copy, small plots, and on the right the answer in one sentence, checks of the assumptions, methods text and a figure legend.",
    how: ["The tabs (Summary, Details…) hold the tables; Copy puts one on the clipboard for Excel or Word.", "“Show on” draws the fit on a graph.", "Change… reopens the options; Python code shows the same calculation in Python."] },
  options: { t: "Analysis options", what: "Which data sets to analyse and how.",
    how: ["Tick the data sets.", "For fits: the range of X to fit, every replicate or only the means, the band (confidence or prediction) and whether to show the equation."] },
  newtable: { t: "New data table", what: "The kinds of data table. Each fits one kind of experiment: XY for a measurement against a variable (time, dose, strain, temperature). Dimmed kinds say when they arrive." },
  graphtype: { t: "Graph type", what: "The kinds of graph. An XY table draws as an XY graph today; the other types arrive with their tables (Help › Roadmap)." },
  import: { t: "Import", what: "Reads a CSV, TXT or Excel file into a new XY table.",
    how: ["Pick the sheet, whether the first row holds titles, and the X column.", "Say what the other columns are: replicates (and how many per data set), or mean, SD (or SEM) and N.", "The preview shows the table as it will be imported."] },
  dataset: { t: "Format data set", what: "The data set's title, how its values are entered (replicates, or mean with SD or SEM and N) and how many replicates it has." },
  export: { t: "Export", what: "Saves the graph as a file: PNG or TIFF pictures at the dpi you choose, or SVG, PDF and EPS vectors with editable text. Transparent background is optional." },
};

/** The small "?" beside a tool. */
export const Help = (p: { k: string }) => <button class="help" title={`What is ${HELP[p.k]?.t ?? "this"}?`} onClick={e => { e.stopPropagation(); helpCard(p.k); }}>?</button>;

export const helpCard = (k: string) => openDialog(() => {
  const h = HELP[k];
  return (
    <Dialog title={h?.t ?? "Help"}>
      <div class="helpcard"><p>{h?.what}</p>
        <Show when={h?.how}><h4>How to use it</h4><ul><For each={h!.how}>{x => <li>{x}</li>}</For></ul></Show>
        <Show when={h?.tip}><p class="muted">{h!.tip}</p></Show></div>
    </Dialog>
  );
});
