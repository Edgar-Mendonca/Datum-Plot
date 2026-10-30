# Datum Plot Guide

## Welcome

Datum Plot is a program for Windows that analyses scientific data and makes publication-ready graphs. You type, paste or import your data into a table; choose an analysis; and Datum Plot shows the results with a plain-language answer, draws the graph and lays out the figure for a journal, a poster or a slide. Everything stays linked: change a value in the table and every result and graph that uses it updates.

The calculations and the drawing are done by Python (numpy, SciPy and matplotlib) inside the app. Nothing else needs to be installed, and your data never leaves your computer.

This guide takes you through Datum Plot step by step, from installing it to an exported figure. You do not need to read it in one go: each chapter stands on its own.

How to read this guide:

- Names in **bold** are tabs, buttons and boxes exactly as they appear in Datum Plot.
- An arrow › is a path: **Analyze › Test Chooser** means the **Analyze** tab, then the **Test Chooser** button.
- Keys are shown like this: [[Ctrl+S]].
- The orange numbers on the pictures match the numbered lists under them.

> **Tip.** Almost every tool in Datum Plot has a small **?** beside its name. Click it for a short card that says what the tool does and how to use it.

## Install, update and start

### Install

1. Download `DatumPlot-x.y.z-setup.exe` from the Releases page: github.com/Edgar-Mendonca/Datum-Plot/releases.
2. Run it. It installs for your own Windows account, so you do not need administrator rights.
3. The first time, Windows may show **Windows protected your PC**, because the installer is not code-signed yet. Click **More info**, then **Run anyway**.

The first start takes a little longer while Datum Plot prepares its Python engine. The status bar says **Ready** when the engine has started.

### Updates

Datum Plot checks for a new version when it starts. When one is ready, an **Update x.y.z available** button appears in the title bar; click it, or open **File › Updates** and click **Update now**. The download is checked against its checksum before it installs, and Datum Plot restarts by itself. Your projects are not touched.

![File › Updates: the version, the update check and the links to GitHub.](img/updates.png)

### The Home page

![The Home page (File › Home).](img/home.png)

1. **Blank XY table.** An empty XY table with its graph, ready for your data.
2. **Samples.** Each sample is a small, complete project with real-looking data, an analysis and a graph: growth and standard curves, dose-response, group comparisons, tensile tests, survival studies, method comparison, diagnostic tests, response surfaces, polar patterns, spectra, DSC and TGA curves and more. Open one to see how a finished project looks, then replace the data with yours.
3. **The File page.** **New**, **Open**, **Import**, **Save**, **Save As**, **Export** and **Print**, and below them **Roadmap**, **Options** and **Updates**. The arrow at the top goes back to the project.

Further down the Home page are the **Guide** tile (this guide, in English, Chinese or French) and your recent projects.

## The window at a glance

![The Datum Plot window with a graph open.](img/window.png)

1. **Tabs.** **File** opens the File page. **Data**, **Analyze**, **Graph**, **Layout**, **Tools**, **View** and **Help** each show their own ribbon.
2. **Ribbon.** The tools of the current tab, in named groups. When the window is narrow, groups fold into smaller buttons.
3. **Sidebar.** Jumps between the project's **Info** sheet, **Data**, **Results**, **Graphs** and **Layouts**.
4. **Navigator.** Every data table, result, graph and layout in the project, with small pictures of the graphs. Right-click an item to rename, duplicate or delete it.
5. **The open item.** Here a graph; it can also be a data table, a results sheet or a page layout.

The box **Tell me what you want to do** at the top (or [[Ctrl+K]]) finds any command by name: type "log axis" or "t-test" and press [[Enter]].

### How a project is linked

A project holds data tables, analyses, graphs and layouts:

- A **data table** holds the numbers.
- An **analysis** reads a data table and gives a **results sheet**.
- A **graph** draws a data table, and can show the curves and significance stars of its analyses.
- A **layout** places graphs and text on a page.

When you change a value, every result and graph that depends on it is worked out again. You never need to "refresh".

## Data tables

### Kinds of table

Choose the kind of table that matches your experiment: **Data › New Table**.

![Data › New Table: choose a kind of table.](img/new-table.png)

1. **Groups of tables.** Data tables, and Worksheets and 3D.
2. **The kinds.** Click one to read what it is for; double-click to create it.

| Kind | What it holds | Typical analyses |
|---|---|---|
| **XY** | X values (time, dose, strain…) and Y data sets with replicates | regression, curve fitting |
| **Column** | each column is a group | t-tests, ANOVA, Bland-Altman, ROC |
| **Grouped** | two factors: rows and data sets | two-way ANOVA |
| **Contingency** | counts of outcomes per group | chi-square, Fisher's exact test |
| **Survival** | one row per subject: time, and 1 (event) or 0 (censored) | Kaplan-Meier, log-rank |
| **Parts of whole** | parts of a total | fractions, pie and donut |
| **Many variables** | one row per sample, many properties | multiple regression, PCA, clustering |
| **Nested** | groups with subgroups (batches, animals) | nested t-test and ANOVA |
| **Worksheet** | free columns with roles, units and formulas | raw instrument data |
| **Matrix** | Z values on an X–Y grid | contour maps, 3D surfaces, surface fits |

### Entering data

![A data table (Data tab).](img/table.png)

1. **Data › Insert.** **New Table**, **Import**, **Several Files**, **Add Data Set**, **Remove Data Set** and rows.
2. **Headings.** The X title and units, and each data set's title. Double-click a heading to change it, the replicates or the way values are entered.
3. **Cells.** Type a value and press [[Enter]]. Copy and paste work with Excel ([[Ctrl+C]], [[Ctrl+V]]); [[Ctrl+D]] fills down.

A data set can be entered as replicates (each value in its own column) or as **mean, SD and N** or **mean, SEM and N** from a paper or another program: choose it in the data set's heading.

To leave a value out of graphs and analyses without deleting it, select it and press [[Ctrl+E]] (**Exclude / Include**). Excluded values are shown in blue italics, struck through.

### Formulas and transforms

- **Data › Column Formula** fills a column from the others, for example `(B - A) / A * 100`. The column updates when the data change.
- **Data › Transform** makes a new table of transformed values: logarithms, 1/X, °C to K, a baseline subtracted, normalised.
- **Data › Check Data** looks for typing mistakes, missing values and values a log axis cannot show.

### Import

**Data › Import** (or **File › Import**) reads CSV, TXT and TSV files, Excel workbooks (.xlsx) and .pzfx projects. A preview shows how the columns will be read; choose the header row and the replicates and click **Import**. **Data › Several Files** imports many runs at once: one data set per file in one table when they share their X values, otherwise one table per file. Plate-reader layouts (96 and 384 wells) are recognised.

## Analyses and results

### Choosing an analysis

![The Analyze tab.](img/analyze-tab.png)

1. **Analyze… and Test Chooser.** **Analyze…** lists every analysis; **Test Chooser** asks three questions about your data and suggests the right test.

The other groups of the Analyze tab start an analysis directly: **Statistics**, **Compare Groups**, **Regression**, **Materials** and more.

![Analyze…: every analysis, by group.](img/analyze.png)

1. **Groups.** Statistics, regression and fitting, materials, compare groups, relationships, survival, signals and spectra.
2. **Analyses.** Click one to read what it does and which Python libraries it uses; **Next…** asks which data sets to include and the options.

### The results sheet

![A results sheet: a logistic curve fit.](img/results.png)

1. **Result tables.** The numbers, with standard errors and 95% confidence intervals. **Copy** copies a table for Excel or Word.
2. **The answer.** What the analysis found, in plain words.
3. **Checks.** Whether the assumptions hold (for example, whether residuals scatter randomly), with a tick or a warning.

Below them are the **Methods** text, ready to paste into a paper (**Copy methods text**), and the figure legend. **Change…** reopens the options; **Python code** shows the Python behind the result so you can repeat it elsewhere. Tick **Show on graph** to draw a fit or the significance stars on the graph.

> **Tip.** Not sure what a number means? Click **?** beside it, or open **Help › Glossary**.

### What Datum Plot can analyse

- **Statistics:** descriptive statistics, normality tests, outliers, frequency distributions, fractions of a total.
- **Compare groups:** t-tests (unpaired, Welch, paired), nonparametric tests, one-way and two-way ANOVA with multiple comparisons, nested t-tests and ANOVA, effect sizes, power.
- **Relationships:** correlation, Bland-Altman method comparison, ROC curves, contingency tables (chi-square, Fisher, relative risk, odds ratio).
- **Regression and fitting:** linear regression, curve fitting from a model library or your own equation, global fits and model comparison, interpolation, area under the curve, smoothing, multiple, logistic and Poisson regression, principal components and clustering, surface fits.
- **Survival:** Kaplan-Meier curves, the log-rank test and hazard ratios.
- **Signals and spectra:** peak finding, Gaussian, Lorentzian and Voigt peak fits, Fourier spectra and filters.
- **Materials:** tensile tests, Weibull strength, Arrhenius activation energies, S–N fatigue curves, DSC and TGA thermal analysis.

![A one-way ANOVA results sheet with multiple comparisons.](img/anova-results.png)

## Graphs

### The Graph tab

![The Graph tab.](img/graph-tab.png)

1. **Graph.** **New Graph**, **Graph Type** (scatter, bars, box, violin, before–after, lines and more) and **Data Table** (back to the data).
2. **Axes.** Logarithmic axes, framed axes, **Format Axes** and **Axis Break**.
3. **Style.** Ready-made **Styles** for journals and presentations, **Copy Look** to other graphs, and **Colour Schemes** (including colour-blind-safe ones).
4. **Share.** **Export**, **Copy Picture** (paste straight into Word or PowerPoint) and **Print**.

The other groups set the **Error Bars**, show **Each Replicate**, connect points, show the legend, set the **Size** and add a curve fit, significance stars or annotations.

### Formatting a graph

Double-click any part of a graph (an axis, a data set, the title) to format it, or use **Graph › Format Axes**.

![Format Graph, docked beside the graph.](img/format.png)

1. **Pages.** **Data Sets** (symbols, colours, lines, error bars, the right Y axis), **X Axis**, **Y Axis**, **Graph** (size and fonts) and notes.
2. **Settings.** Changes apply at once.
3. **The graph** stays visible while you work.

### Working on the graph

- Hover a point to see its values.
- Drag a note to move it; double-click it to edit.
- Right-click a point to exclude it.
- **Zoom to a Box**, **Pan** and **Statistics of a Region** are in the graph's right-click menu; [[Ctrl]] and the mouse wheel zoom the view.

### Graphs for every kind of data

![Compare groups: each value, mean and SD, with significance stars from the ANOVA.](img/anova.png)

![A matrix table as a contour map with a surface fit.](img/contour.png)

![A survival study: Kaplan-Meier curves with censored subjects marked.](img/survival.png)

XY graphs can also be polar graphs (**Format Graph › Graph › Polar**); matrix tables can be drawn as contour maps, heat maps, 3D surfaces or wireframes.

## Layouts and export

### Page layouts

A layout places several graphs and text on one page: a multi-panel figure for a journal, a poster or a slide.

![A two-panel figure (Layout tab).](img/layout.png)

1. **Layout.** **New Layout**, **Panel Letters** (A, a, (a)), **Arrange** (line up and size panels), **Journal Figure** (a single or double column of a journal) and **Add Graph**.
2. **The page.** Drag a panel to move it; drag a corner to resize it. Right-click a panel for more choices.

The **Templates** group starts a **Poster** or a **Slide**. The **Export** group saves the page.

### Export

![File › Export: the formats.](img/export.png)

1. **File › Export** exports the open graph.
2. **Formats.** **PNG** for slides and the web; **TIFF** (300–1200 dpi, CMYK if asked) for journals; **SVG**, **PDF** and **EPS** vectors that stay sharp at any size. **Copy picture** puts the graph on the clipboard.

Other ways to share, under **Tools**:

- **Export All Graphs** at once.
- **Excel Workbook**: every table and result in a .xlsx file.
- **PowerPoint**: every graph on its own slide (.pptx).
- **Word Report**: the project's details, every graph with a caption, every result and the methods text (.docx).

### Print

**File › Print** prints a graph with a header and footer, or saves it as a PDF.

## The Python console and automation

### Python console

The Python console runs your own Python code on the project's data.

![Tools › Python Console.](img/console.png)

1. **Code.** Write Python here. Your tables are ready as pandas DataFrames: `tables` lists them, `table(0)` is the first, `tables['Name']` one by its name.
2. **Run** (or [[Ctrl+Enter]]).
3. **Output.** What you print, the value of the last line, and any figure you draw with `plt`.
4. **How to use.** A short guide inside the console; **Examples** fills in working code to start from.

Ready to use: `np` (numpy), `pd` (pandas), `stats` (scipy.stats), `scipy` and `plt` (matplotlib). `new_table('Name', data)` adds a table to the project; `result('Analysis name')` gives an analysis's numbers. Variables stay between runs until you press **Reset**.

> **Note.** The console runs code you write, with your rights, like any Python script. Projects never contain code: opening a project from someone else never runs anything.

### Automation

![The Tools tab.](img/tools-tab.png)

1. **Python.** **Python Console**, **My Analyses** (code you saved with **Save As My Analysis**) and **Notebook** (the project as a Jupyter notebook).

- **Analysis Template** repeats one table's analyses (with their options) and its graph's look on other tables.
- **Batch Process** takes a template table and many files: each file becomes a table with those analyses and a graph, and the answers are listed together.

## Files

- **Save** ([[Ctrl+S]]) keeps the whole project in one `.dplot` file: tables, analyses, graphs and layouts. Saving is atomic: a crash or a full disk never leaves a half-written file.
- **Open** ([[Ctrl+O]]) opens a `.dplot` file; you can also double-click it in Windows.
- Datum Plot saves a recovery copy every few minutes (**File › Options**). If it closes unexpectedly, it offers to recover your work at the next start.
- **Undo** and **Redo** ([[Ctrl+Z]], [[Ctrl+Y]]) go back through every change.

## Help in the app

![The Help tab.](img/help-tab.png)

1. **Learn.** **Guide** (this guide), **Getting Started**, **Roadmap** (what Datum Plot will do, and when), **Glossary**, **What Is This Tool?**, **Statistics Guide**, **Test Chooser**, **Shortcuts** and **Tell Me**.
2. **Updates.** **Check for Updates**.

![Help › Guide: choose a language.](img/guide-dialog.png)

1. **Languages.** English, 中文 or Français. The guide downloads from GitHub, is checked against its checksum, is saved in your Downloads folder and opens.

## Which test when

| Your question | Your data | Analysis |
|---|---|---|
| Do two groups differ? | two columns of values | t-test (Mann-Whitney if not normal) |
| Did the same items change? | before and after, paired by row | paired t-test (Wilcoxon if not normal) |
| Do three or more groups differ? | columns of values | one-way ANOVA with multiple comparisons (Kruskal-Wallis if not normal) |
| Do two factors matter? | grouped table | two-way ANOVA |
| Are proportions different? | counts | chi-square or Fisher's exact test |
| How are X and Y related? | XY | linear regression or curve fit |
| Do two variables move together? | two columns | correlation |
| Do two methods agree? | paired values | Bland-Altman |
| How well does a test detect a condition? | values of controls and cases | ROC curve |
| How long until an event? | times with events and censored subjects | Kaplan-Meier and log-rank |

> **Tip.** **Analyze › Test Chooser** asks these questions for you.

## Glossary

| Term | Meaning |
|---|---|
| **Data set** | One series of values in a table (a column, or a group of replicate columns). |
| **Replicate** | A repeated measurement of the same thing. |
| **SD** | Standard deviation: how spread out the values are. |
| **SEM** | Standard error of the mean: how precisely the mean is known (SD/√n). |
| **95% CI** | 95% confidence interval: the range that contains the true value with 95% confidence. |
| **P value** | How likely a difference this large would be if there were no real difference. |
| **R²** | The share of the variation that a fitted line or curve explains. |
| **Censored** | A subject whose event had not happened when it was last seen. |
| **Residual** | The distance of a point from the fitted curve. |

## Shortcuts and troubleshooting

### Shortcuts

| Keys | Action |
|---|---|
| [[Ctrl+S]] / [[Ctrl+Shift+S]] | Save / Save As |
| [[Ctrl+O]] / [[Ctrl+N]] | Open / New |
| [[Ctrl+Z]] / [[Ctrl+Y]] | Undo / Redo |
| [[Ctrl+C]] / [[Ctrl+V]] | Copy / paste (works with Excel) |
| [[Ctrl+E]] | Exclude or include values |
| [[Ctrl+D]] | Fill down |
| [[Ctrl+C]] on a graph | Copy the graph as a picture |
| [[Ctrl+P]] | Print |
| [[Ctrl+K]] | Tell me what you want to do |
| [[F1]] | All shortcuts |

### Troubleshooting

- **The status bar says the graph engine is not available.** Click **Tools › Restart Engine**. If it still fails, reinstall Datum Plot from the Releases page; your projects are not affected.
- **An analysis says it cannot be worked out.** The message says why (too few values, identical values, a missing X). Fix the data or choose other data sets with **Change…**.
- **A graph shows no points on a log axis.** Values of zero or below cannot be drawn on a log axis; **Data › Check Data** finds them.
- **Something else went wrong.** That step is refused and your project stays as it was; the details are in `crash.log` in the app's data folder. Please report it with **Help › Report an Issue**.
