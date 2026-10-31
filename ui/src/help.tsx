// "?" help: a small button beside a tool; a click opens a short card saying what the tool is for
// and how to use it. One place for every explanation, so the whole app teaches itself.
import { For, Show } from "solid-js";
import { openDialog } from "./store";
import { Dialog } from "./ui";

type Topic = { t: string; what: string; how?: string[]; tip?: string };
export const HELP: Record<string, Topic> = {
  // Data tab
  clipboard: { t: "Clipboard", what: "Cut, copy and paste cells, also to and from spreadsheets.",
    how: ["Select cells, Ctrl+C, then click where they go and Ctrl+V.", "Paste ▾ › Paste Special (Ctrl+Alt+V) pastes only values, only formats, or turned sideways (Transpose).", "Format Painter: click it, then click the cells that should look the same."] },
  font: { t: "Font", what: "The typeface, size, colour, fill and bold/italic/underline of the selected cells in the table. Graph text is set on the Format tab." },
  alignment: { t: "Alignment", what: "Left, centre or right alignment of the selected cells, and Clear Formatting to put them back as they were." },
  insert: { t: "Insert", what: "New tables and more room in the open one.",
    how: ["New Table picks the kind of data table: XY (X against Y) Column (one group per column, for t-tests and ANOVA) Grouped (two factors: rows and data sets, for two-way ANOVA) Contingency (counts of outcomes per group, for chi-square and Fisher's test) or Parts of whole (parts in the rows, one whole per data set, for pie and donut charts).", "Import reads a CSV, TXT or .xlsx file into a new XY table.", "Add Data Set adds a column group, Remove Data Set deletes the ones you tick (or right-click a heading, or its ×); Add 10 Rows and Remove Last Row change the length."] },
  transform: { t: "Transform", what: "Work on the values themselves.",
    how: ["Transform makes a new table of log, 1/X, °C → K, baseline-subtracted or normalised values (or replicates as mean, SD and N).", "Sort orders the rows by a column; Find (Ctrl+F) jumps to a value; Exclude Rows leaves out rows by a rule, such as X above 0.003.", "Check Data looks for missing X values, missing N, typing mistakes and values a log axis cannot show.", "Find Outliers runs Grubbs' test on each data set."] },
  values: { t: "Values", what: "Commands for the selected cells and their data set.",
    how: ["Exclude / Include (Ctrl+E): the value stays in the table in blue italic, but graphs and analyses leave it out.", "Format Data Set: its title, how values are entered (replicates, or mean with SD or SEM and N) and how many replicates.", "Fill Down (Ctrl+D) copies the top cell into the cells below."] },
  graph: { t: "Graphs", what: "A graph draws a data table. It stays linked: change a value and the graph redraws.",
    how: ["New Graph makes a graph of the open table.", "Show Graph (or Graphs in the navigator) opens it."] },
  item: { t: "Item", what: "Rename, duplicate or delete the table, result or graph that is open. Right-click it in the navigator for the same commands." },
  // Analyze tab
  analyze: { t: "Analyze", what: "Adds an analysis of a data table. Its result appears under Results in the navigator and updates when the data change.",
    how: ["Analyze… lists every analysis with a short description; dimmed ones say when they arrive.", "Test Chooser asks a few questions and opens the right analysis.", "Pick the data sets and the options, then Analyze. Change… on the results sheet reopens them."] },
  statistics: { t: "Statistics", what: "Describe each data set and check it before testing.",
    how: ["Descriptive: n, mean, SD, SEM, 95% CI, median, quartiles, CV and more.", "Normality: Shapiro-Wilk and other tests, with QQ plots.", "Outliers: Grubbs' test; one click excludes what it finds.", "Frequency: a histogram and cumulative distribution (Make a table from it to graph it).", "Fractions: each part as a percentage of its whole (with 95% CIs for counts).", "Bland-Altman: do two methods agree (bias and limits of agreement)? ROC curve: how well a test separates two groups (AUC, best cut-off).", "Correlation: Pearson, Spearman and Kendall. Power: how many samples you need."] },
  regression: { t: "Regression and curve fitting", what: "Fit a line or a curve to XY data, with standard errors, 95% intervals and checks. The fit is drawn on the graph with its band and equation. Multiple predicts one variable from several at once (linear, logistic for 0/1 outcomes, Poisson for counts) on a table of many variables. More › Peaks finds and fits peaks above a baseline; More › Signal gives the Fourier spectrum, filters and resampling. More › PCA finds the main patterns in many variables; More › Clusters groups similar rows.",
    how: ["Linear Regression: slope, intercept, R²; fit only part of the data with “Fit X from … to …”; compare the lines of several data sets.", "Curve Fit: a model from the library or your own equation. Global fit shares a parameter between data sets and tests whether it differs; Compare with tests a second model (F test and AICc).", "Interpolate reads unknowns off a standard curve.", "Area: area under the curve and the peaks above a baseline. Smooth: Savitzky-Golay, LOWESS or moving average, or the derivative or integral."],
    tip: "Regression uses every replicate by default, not only the means." },
  compare: { t: "Compare groups", what: "Are the groups different? Put each group in a column of a column table.",
    how: ["t-test: two groups (unpaired with Welch's correction, paired, ratio or one sample); gives the difference with its 95% CI and Cohen's d.", "One-way ANOVA: three or more groups, then Tukey, Dunnett, Holm-Šidák… to see which pairs differ; η² and ω².", "Nonparametric: Mann-Whitney, Wilcoxon, Kruskal-Wallis with Dunn's test, Friedman, for skewed or ranked values.", "Two-way ANOVA (grouped tables): two factors and their interaction, with comparisons within each row.", "Contingency: chi-square and Fisher's exact test on counts, with the relative risk and odds ratio for 2 × 2 tables.", "On a column or grouped graph the result draws significance stars over the groups."] },
  materials: { t: "Materials", what: "Analyses for materials testing.",
    how: ["Tensile Test: X is strain, each replicate column one specimen's stress; gives Young's modulus, 0.2% offset yield, UTS, elongation and toughness, per specimen and as mean ± SD.", "Weibull: strengths of brittle specimens (one group per column); gives the Weibull modulus m and characteristic strength σ0 with the Weibull plot.", "Arrhenius: rate constants at several temperatures give the activation energy.", "S–N Curves: X is cycles to failure, Y the stress amplitude; a Basquin fit gives the fatigue strength at any life (run-outs are shown but not fitted).", "DSC / TGA: X is temperature; DSC gives each peak's onset, peak temperature and enthalpy (area ÷ heating rate), TGA each step's onset, mass lost and the residue."] },
  // Graph and Format tabs
  graphtab: { t: "Graph", what: "Make a graph, choose its type, or go back to its data table." },
  gdata: { t: "What the graph shows", what: "How each data set is drawn.",
    how: ["Error Bars: SD, SEM, 95% CI or the range, or none.", "Each Replicate draws every value instead of the mean.", "Connect Points joins the points; Legend shows or hides the key."] },
  axes: { t: "Axes", what: "Log or linear axes and the look of the frame.",
    how: ["Log X / Log Y switch an axis to a log scale (for dose-response or spectra).", "Framed Axes draws a box around the plot instead of two open axes.", "Format Axes sets ranges, ticks, titles and numbers.", "Axis Break (Graph tab, Format tab or right-click the graph): leave a gap in the Y axis (Format Graph › Y Axis) or the X axis (› X Axis), for values far from the others.", "Second Y axis: tick Right Y for a data set in Format Graph › Data Sets; its axis has its own page."] },
  annotate: { t: "Annotate", what: "Notes on the graph: text, arrows, lines and boxes.",
    how: ["Text: click where it goes and type it. Arrow, Line, Box: drag on the graph.", "Edit Notes (Format Graph › Notes) changes their text, position, colour, size or deletes them.", "Notes sit in the units of the axes, so they stay on their data when the graph is resized or exported."] },
  layouts: { t: "Layouts", what: "A page with several graphs and text, panel letters A, B, C, at a journal's size, exported as one file.",
    how: ["New Layout (Layout tab or ＋ beside Layouts) starts with up to four graphs, two per row; right-click a graph › New Layout with This Graph for one.", "Drag a panel to move it, its corner to resize it; Delete removes it; double-click opens the graph (or edits a text).", "Arrange puts the graphs in 1–4 columns, or stacks them sharing one X axis; their plot frames line up (Arrange › Line Up the Axes). Journal Figure sets the page to a column width; Panel Letters: A, a, (a) or none.", "Right-click a graph panel: Add an Inset Here (a small graph on a white card), Inset, Hide X Axis Title and Numbers, Bring to Front.", "Export Layout: PDF, SVG or EPS (vector) or PNG/TIFF at 300–1200 dpi; TIFF for Journals is CMYK, LZW, 600 dpi."],
    tip: "The graphs stay linked: change the data and the layout updates." },
  columns: { t: "Column graph", what: "How a column table is drawn: scatter dots with the mean, bars, box and whiskers, violins, mean ± error only, or before–after lines joining each row. A parts-of-whole table: pie, donut or bars stacked to 100%. A grouped table: grouped or stacked bars, grouped dots, lines (an interaction plot) or a heat map of the means. Show Each Value adds the dots." },
  style: { t: "Style", what: "The look of the graph in one click.",
    how: ["Styles: open axes, framed box, Nature, Science, ACS, IEEE, presentation or greyscale; Save This Graph's Style keeps your own.", "Copy Look gives other graphs this graph's fonts, sizes, colours and symbols (they keep their titles and ranges).", "Colour Schemes: Okabe-Ito, Tol, Tableau, viridis, greyscale or your own colours, each shown as people with colour-blindness see it."] },
  size: { t: "Size", what: "The size of the graph in millimetres, as it will be printed or exported. Journal column widths are in the list." },
  add: { t: "Add to the graph", what: "Fit a Curve runs linear regression or a curve fit and draws it on this graph. Significance runs a t-test (two groups) or a one-way ANOVA and puts stars over the columns of a column graph. Annotation adds text, arrows, lines and boxes." },
  share: { t: "Share", what: "Get the graph out of Datum Plot at publication quality.",
    how: ["Export: PNG or TIFF at any dpi, or SVG, PDF and EPS with editable text.", "Copy Picture puts the graph on the clipboard for documents and slides (Ctrl+C on the graph).", "Print (Ctrl+P) with page setup and headers."] },
  format: { t: "Format Graph", what: "Every setting of the graph, in a panel on the right. Each change shows at once and can be undone.",
    how: ["Data Sets: symbols, colours, lines and error bars.", "X Axis / Y Axis: range, scale, ticks, title and numbers.", "Graph: title, size, font, legend and frame.", "Double-click a part of the graph to open its page."] },
  text: { t: "Graph text", what: "The font and size of all the text in the graph, and bold axis titles. A+ and A− step the size." },
  glayout: { t: "Graph layout", what: "The graph's size, the legend, framed or open axes, and Graph Options (the Graph page of Format Graph)." },
  // Tools and View tabs
  exportall: { t: "Export", what: "Everything at once: Export All Graphs saves every graph of the project into a folder (PNG, TIFF, SVG, PDF or EPS); Workbook saves the data tables and every result as sheets of one .xlsx or .ods file; Slides makes a 16:9 deck with every graph on its own slide and a slide per result; Document writes the project's details, every graph with a caption, every result with its main table, and the methods text (.docx or .odt)." },
  linked: { t: "Copy Linked", what: "Keeps a graph as a picture in a folder beside the project, redrawn every time you save. Slides and documents that insert it as a linked picture show each new version when their links are updated, in any program.",
    how: ["Save the project, then Graph › Copy Linked (or right-click the graph). The picture's path is now on the clipboard.", "In your slides or document, insert a picture from a file, paste the path, and insert it as a link (not as a copy).", "Change the graph and save the project: the picture is redrawn. Reopen the slides (accept updating links) or use their Update Links command.", "Tools › Update Linked Pictures redraws all of them; Stop Linking in the Linked Picture window ends it."] },
  palette: { t: "Colour schemes", what: "Sets of colours for the data sets of a graph. Schemes marked colour-blind safe stay easy to tell apart for people with any of the three common kinds of colour-blindness; the default, Okabe-Ito, is one of them.",
    how: ["Graph › Colour Schemes: the window sits beside the graph, so each scheme you click shows at once.", "The three columns on the right show how people with red-, green- and blue-blindness see each scheme.", "Format Graph › Data Sets offers the chosen scheme's colours for single data sets.", "Type your own colours as #hex, separated by commas, and click Use my colours."] },
  guide: { t: "Guide", what: "The Datum Plot Guide: a step-by-step PDF with pictures, in English, Simplified Chinese (中文) or French (Français).",
    how: ["Help › Guide, or the Guide tile on the File page.", "Choose a language: the guide downloads from GitHub, is checked against its checksum, is saved in your Downloads folder and opens."] },
  console: { t: "Python console", what: "Run your own Python code on the project's data: tables arrive as pandas DataFrames, and what you print, the last line's value and the figures you draw appear below the code. Open it from Tools › Python Console.",
    how: ["Where to write: the large box at the top of the console. Start from Examples ▾ if you are new to it.",
      "How to run: press ▶ Run or Ctrl+Enter. The output (print, the last line's value) and figures (plt) appear underneath; an error says which line failed.",
      "Your data: tables lists the tables; table(0) is the first, tables['Name'] one by its name. Columns are the data sets (replicates as 'Control 1', 'Control 2'), with X first; row titles are the index.",
      "Ready to use, no import needed: np (numpy), pd (pandas), stats (scipy.stats), scipy and plt (matplotlib).",
      "Back into the project: new_table('Name', data) adds a table when the code has run (a DataFrame or {column: values}; for XY the first column is X). result('Analysis name') gives an analysis's numbers, as on its results sheet.",
      "Step by step: variables stay between runs; Reset forgets them. Code running longer than a minute is stopped and the engine restarts.",
      "Keep it: Save As My Analysis stores the code with the app; Tools › My Analyses runs it again on any project."],
    tip: "The code runs on your computer with your rights, like any Python script, so run only code you understand. Projects never contain code: opening a project from someone else never runs anything." },
  automate: { t: "Automate", what: "Do the same work again without repeating it by hand.", how: ["Analysis Template: pick a table you have analysed and tick other tables; each gets the same analyses with the same options (and its graph the same look).", "Batch Process: pick a template table, then many files (one run each); every file becomes a table with those analyses and a graph, and the answers are listed together.", "Notebook: saves the project as a Jupyter notebook (.ipynb) with its tables, each analysis's answer and the Python behind it."] },
  engine: { t: "Engine", what: "Datum Plot calculates and draws with two Python engines (numpy, SciPy, matplotlib) that run beside the window: one draws the graphs, the other calculates results, so a long fit never holds up drawing. If something stops, Restart Engine starts both again; your project is not touched." },
  show: { t: "Show", what: "Opens the project's Info sheet, its data tables or its graphs; Navigator shows or hides the list on the left." },
  zoom: { t: "Zoom", what: "How big the graph looks on screen. It does not change the graph's size in exports (Ctrl+wheel zooms too)." },
  theme: { t: "Theme", what: "Light, dark, or Auto to follow Windows. Graphs keep their own colours so exports look the same." },
  // Panels and dialogs
  navigator: { t: "Navigator", what: "The project as a chain: data tables → results → graphs → layouts. Everything stays linked.",
    how: ["Click an item to open it; ＋ adds one to its section.", "Right-click for rename, duplicate and delete; double-click to rename."] },
  info: { t: "Info sheet", what: "What the project is about: title, experiment, researcher, organisation, date and notes. Saved with the project; some fields can be printed in headers and footers." },
  table: { t: "Data table", what: "An XY table has one X column, then data sets A, B, C… each with its replicate columns (Y1, Y2…) or entered as mean with SD or SEM and N. A column table has one group per column with the values down the rows, for t-tests and ANOVA. A grouped table has one factor in the rows (named by the row titles) and the other in the data sets, with replicates side by side, for two-way ANOVA.",
    how: ["Type or paste from a spreadsheet; headings in the first row become the titles.", "The titles and units above the grid become the axis titles.", "Double-click a data set heading to format it; right-click for sort, find and exclude rows."] },
  graphview: { t: "Graph", what: "The graph as it will be exported, drawn by the engine. You can work on it directly.",
    how: ["Hover a point for its values; right-click it to exclude it or format its data set.", "Double-click an axis, the legend or the data to format it; double-click a note to edit its text.", "Click a note to select it, drag to move it, Delete to remove it.", "Zoom and Pan (Format tab or right-click): zoom to a box, pan by dragging, zoom out, reset the axes. Ctrl+wheel zooms the view only."] },
  results: { t: "Results sheet", what: "The result of one analysis, linked to its table: tables you can copy, small plots, and on the right the answer in one sentence, checks of the assumptions, methods text and a figure legend.",
    how: ["The tabs (Summary, Details…) hold the tables; Copy puts one on the clipboard for a spreadsheet or a document.", "“Show on” draws the fit on a graph.", "Change… reopens the options; Python code shows the same calculation in Python."] },
  options: { t: "Analysis options", what: "Which data sets to analyse and how.",
    how: ["Tick the data sets.", "For fits: the range of X to fit, every replicate or only the means, the band (confidence or prediction) and whether to show the equation."] },
  newtable: { t: "New data table", what: "The kinds of data table. XY for a measurement against a variable (time, dose, strain, temperature); Column for groups to compare (control, treated…; alloy A, B, C); Grouped for two factors at once (alloy × heat treatment); Contingency for counts (passed/failed per process); Parts of whole for fractions (phases, composition). Matrix for Z values on an X–Y grid (X down the first column, Y values as the column titles) for contour maps and 3D surfaces; Worksheet for free columns with roles (X, Y, Y error), units and comments; Nested for subgroups within groups (each group's sub-columns are its batches or animals, replicates down the rows); Survival for times to an event with censored subjects (time in X, 1 = event or 0 = still going in the group's column); Many variables for one row per sample with several measured properties (carbon, tempering temperature, hardness): multiple regression, with the first variable on the graph's X axis. Dimmed kinds say when they arrive." },
  graphtype: { t: "Graph type", what: "The kinds of graph. An XY table draws as an XY graph, a column table as a column graph (dots, bars, box plots, violins); the other types arrive with their tables (Help › Roadmap)." },
  import: { t: "Import", what: "Reads a CSV, TXT or .xlsx file into a new XY table, the tables of a .pzfx project, a plate reader's plate, or several runs at once.",
    how: ["Pick the sheet, whether the first row holds titles, and the X column.", "Say what the other columns are: replicates (and how many per data set), or mean, SD (or SEM) and N.", "The preview shows the table as it will be imported.",
      "A .pzfx project brings all its tables over (XY, column, grouped, contingency, survival, parts, nested) with titles, replicates, row titles and excluded values.",
      "A sheet with a 96- or 384-well block (columns 1, 2, 3… and rows A, B, C…) offers to import the plate as a grouped table.",
      "Several Files reads many runs at once (tensile tests, spectra): one data set per file, in one table when they share their X values."] },
  region: { t: "Statistics of a region", what: "Drag a box over part of the curves: for each, the points inside, mean, SD, range, area, slope and highest point.", how: ["Graph › Zoom ▾ › Statistics of a Region, or right-click the graph.", "Copy puts the table on the clipboard; Linear fit of this range opens a linear regression limited to the box's X range."] },
  dataset: { t: "Format data set", what: "The data set's title, how its values are entered (replicates, or mean with SD or SEM and N), how many replicates it has, its units and comment, its role in a worksheet (X, Y, Y error or not plotted) and an optional formula." },
  formula: { t: "Column formula", what: "Fills a data set (one value per row) from the others, and updates it whenever they change.", how: ["A, B, C… are the data sets (each row's mean when they have replicates), X the X column, i the row number, col(\"title\") a data set by its title.", "Arithmetic + − * / ^ and comparisons; log10 (also log), ln, exp, sqrt, abs, round, sin, cos, tan; mean, sd, sem, sum, min, max, median, count (of the whole column); cumsum, diff; if(test, a, b); pi and e.", "Empty cells stay empty. Edits recalculate the formula columns left to right, in the same undo step."] },
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
