# Changelog

## 0.4.3 — 2026-11-10

Error bars from the colour scheme, and a clearer Data Sets page.

**Error bars**
- On bar, box and violin graphs, automatic error bars take the colour scheme's colour, so changing a symbol's fill no longer changes them. Scatter dot plots and grouped bars keep their dark grey. The **Error bars** square still sets any colour.

**Format Graph › Data Sets**
- A line marks where the bars', the symbols' and the error bars' settings start, and each heading sits at the start of its group.

Graphs made with earlier versions open looking exactly as before.

## 0.4.2 — 2026-11-10

Testers' requests: symbols and error bars on their own, tidier legends, and choosing which analyses each graph shows.

**Symbols and error bars** (Format Graph › Data Sets)
- On bar, box and violin graphs the symbols have their own **Filled** tick box: unfilled bars no longer empty the symbols.
- An automatic symbol border follows the colour scheme, so changing a symbol's fill no longer changes its border.
- **Strength** for the bars' border and for the symbols' fill and border, in their colour pop-ups.
- The error bars have their own **colour** (Automatic keeps the usual one).

**Legends**
- The bars' border always shows in the legend, not only when its colour was chosen by hand.
- On a graph with a Y axis break the legend sits where you ask (Top left is the top left of the whole graph), no longer in the lower part.

**Analyses on each graph**
- **Format Graph › Graph › Analyses** lists the table's analyses that can be drawn: tick the ones this graph shows (fits, brackets and stars). Results › Show on [graph] still works.
- Running an analysis the table already has first offers to **open** it (or tick it on the graph you are on) or **Make Another**, so copies are not made by accident.

Graphs made with earlier versions open looking exactly as before.

## 0.4.1 — 2026-11-10

The graph digitizer: points from a picture of a graph.

**Digitize Graph** (Data › Insert)
- Open a picture of a graph (PNG, JPG, GIF, BMP or WebP), click two ticks on each axis and type their values, then click the points.
- Logarithmic axes, several curves in their own colours; a right-click removes the last point.
- **Make Table** gives one X column and one column per curve, with a graph. A slightly tilted scan still reads right.

## 0.4.0 — 2026-11-10

Wavelets and spectrograms: how a signal's frequencies change over time. The 0.4 series begins.

**Time–frequency pictures** (Analyze › Signals and spectra › Wavelets and spectrograms, or Signals › Operation)
- **Wavelet scalogram** (Morlet wavelet): a heat map of time against frequency, sharp in time for fast events and in frequency for slow ones. The pale area at each end (the cone of influence) is where the start and end of the record distort the power.
- **Spectrogram** (short-time Fourier transform): the same picture from a sliding window; choose the window's length.
- Choose the range of frequencies, or let Datum Plot take it from the record.
- The answer names the strongest frequency and when it happens; the **strongest frequency at each time** becomes a data table to graph.

## 0.3.21 — 2026-11-10

Colours of bars and symbols.

**Each colour on its own**
- On bar, box and violin graphs, **Format Graph › Data Sets** now lists the bars' settings first (**Filled**, **Fill**, **Border**) and then the symbols' (**Shape**, **Size**, **Fill**, **Border**). Changing a symbol's colour no longer changes the bars' border.
- Symbols can have their own **border** colour, on every kind of graph.

**A colour pop-up**
- Each colour is a small square showing the colour as drawn; click it for the colour scheme's colours, a colour of your own, or **Automatic** (back to the scheme). A square marked A is automatic.
- A fill's square shows its real, lighter colour, and its pop-up sets the fill's **Strength** (35 % for bars by default).
- **Reset all colours** puts every colour of the graph back to the colour scheme.

Graphs made with earlier versions open looking exactly as before.

## 0.3.20 — 2026-11-10

Users' requests.

**Undo from the keyboard**
- **Ctrl+Z** and **Ctrl+Y** undo and redo while Format Graph or Colour Schemes is open, and after changing a colour, a box or a list. In a text box they still undo your typing.

**Legends on column graphs**
- Column graphs (scatter, bars, box, violin, mean) can show a legend of their groups, with each group's colour or symbol: **Legend** in the ribbon, or **Format Graph › Graph › Legend › Show**, in the corner you choose or outside. Graphs made before keep no legend until you switch it on.

**Axis breaks where you want them**
- **Format Graph › Y Axis** (and X Axis on XY graphs): with a break set, choose how much of the axis the part below (or before) the break takes, such as 25 % or 70 %, and the **ticks beyond the break**, separately from the main part.

**Embedded graphs in a word processor**
- The guide now says it: paste with **Paste Special › Datum Plot Graph Object** (a plain paste may give a picture).

## 0.3.19 — 2026-11-07

Embedded graphs: the fixes from testing.

- **Double-clicking an embedded graph works.** In 0.3.18 it failed ("the server application … returned an unknown error", or nothing at all): Datum Plot started and read the graph, but could not reach its window from the thread the document called on. Every call from the document now comes to the window's thread.
- Double-clicking an embedded graph in a document opens Datum Plot **on that graph**, with the bar "Editing a graph embedded in …" and its **Update** button. In 0.3.18 the window could open on the Home page instead, hiding the graph and the bar.
- The bar now stands out (teal, with a white Update button), and **Graph › Share › Update Document** does the same.
- **Help › Check Embedded Graphs** starts Datum Plot the way a document does and says what happened, step by step; every step is also written to `embed.log` in Datum Plot's data folder, for reporting a problem.

## 0.3.18 — 2026-11-07

Embedded graphs: edit a pasted graph again in Datum Plot (Windows).

**Copy Embedded**
- **Graph › Copy Embedded** (also in the graph's and the navigator's right-click menus) copies the graph with its data. Paste it into a document, slides or a workbook: it looks like the picture.
- **Double-click it there** and Datum Plot opens it. Change anything, then click **Update** in the bar at the top (or press Ctrl+S, or close the window and choose **Update and Close**): the graph in the document changes.
- The data is kept inside the document, so anyone with Datum Plot can open the graph from it.
- **Copy Picture** stays as before: a plain picture.
- Windows only, like other programs' embedded objects: on a Mac or in a browser the graph shows as its picture.

This is the first version of embedded graphs: please tell us how it works in your office programs.

## 0.3.17 — 2026-11-07

Smaller screens.

**Ribbon**
- On a narrow window (a laptop screen), ribbon groups fold from the right into one button each that keeps the group's name, such as **Style ▾**. Click it and the group's commands open below it, with their names. No more rows of icons without names.

**File page and Home**
- On short screens the File page lists its commands in a compact column that scrolls, so **Roadmap**, **Options** and **Updates** stay reachable.
- On narrow windows the Home page puts the update card below the tiles.
- Format Graph takes less room beside the graph on narrow windows.

## 0.3.16 — 2026-11-07

Organising the navigator.

**Select several items**
- **Ctrl+click** adds items to a selection; **Shift+click** selects a run. Right-click the selection to **delete them together** (one undo step), move them to a folder or colour their names. **Delete** deletes the selection; **Esc** clears it.

**Folders and colours**
- Right-click › **Move to Folder** › **New Folder…** groups tables, results, graphs or layouts under a folder you name. Click a folder to open or close it; right-click it to rename it or remove it (its items stay).
- Right-click › **Colour**: red, orange, green, blue, pink or grey names, to find things at a glance.
- Folders and colours are saved with the project.

**A table's family**
- Right-click a data table › **Show Only This Family**: the navigator shows just that table, its results, its graphs and the layouts that show them. **Show All** brings back the rest.

## 0.3.15 — 2026-11-07

Users' requests.

**Fixes**
- Typing into the table of a new project no longer fails with an error on every value.
- **Delete** now deletes layouts from their right-click menu.
- Significance stars and fits added from a graph are drawn on that graph only, not on every graph of the same table.
- Right-clicking a graph's preview in the navigator opens the same menu as its name.

**Starting**
- Datum Plot opens on the Home page. Choose **Empty project**, **Blank XY table**, **Blank XY table and graph** or **Blank column table**, or open a sample. An empty project shows how to add a table or import data.

**Graphs**
- **Format Graph › Data Sets › Order**: move data sets earlier or later on a column, grouped, pie or nested graph; the table keeps its own order.
- **Fill** and **Border** colours for bars, boxes and violins, separate from the symbols. The Line and Width settings (now **Connect** and **Line width**) show only on graphs that draw lines.

**Navigator**
- The **＋** beside Graphs offers a new graph of any table, or a copy of the open graph with all its formatting.
- Right-click a table › **Duplicate with Graphs and Results** or **Duplicate Table Only**.
- Right-click a layout › **Copy Picture** or **Export**.
- Drag the right edge of the navigator to widen it; long names show in full on hover.

## 0.3.14 — 2026-11-03

Fixes from users.

**Graphs**
- Choosing **Error Bars** from the ribbon no longer switches **Each Replicate** off on column and grouped graphs.
- Groups with many values spread their dots evenly across the group's width instead of piling the extra dots in a column at one edge.

**Format Graph**
- The Format Graph window always works on the graph you are looking at: open another graph and it follows it, on the same page; open a table, results or a layout and it closes.

**Finding your graph**
- The graph's name is shown above it (double-click to rename).
- In the navigator, each graph's preview sits right under its name. Right-click a graph › **Hide Previews** (or **View › Thumbnails**) to save space.

## 0.3.13 — 2026-11-02

A tidier Home page.

**Three blank starts**
- **Blank XY table and graph**, as before; **Blank XY table** without a graph, for when you only want to enter and analyse data; **Blank column table** without a graph, groups side by side for t-tests and ANOVA. A graph can be added at any time.

**A Samples folder**
- The sample projects moved from Home into **Samples**, which opens inside Home with every sample under a heading: curves and regression, comparing groups, survival and reliability, medical tests, signals and thermal analysis, maps and special graphs.
- Home now shows only the starts, Samples, Open, Import data, Guide, Roadmap and your recent projects.

## 0.3.12 — 2026-11-02

Dates, second step; median error bars; fixes from testers.

**Fixes from testers**
- Pressing **Enter** in a name box (renaming a data set, a table and so on) now keeps the new name before the window closes.
- **Right-click an axis › Format Axes** opens the page of the axis you clicked (X, Y or the right Y axis), not always X.
- **One Format Graph window**: Format Axes, Format Graph and double-clicks switch the open window to the page asked for instead of opening another. **×**, Close and Esc close the window they belong to, not the newest one.
- **Long data set titles** wrap onto up to three lines and the heading grows to fit. Drag the right edge of a heading to widen a column; double-click it to fit.
- The date axis's **Tick labels** choice is now kept in the project (0.3.11 forgot it).

**Median error bars**
- **Error Bars** offer the **median with its interquartile range**, **with its range**, or **with a 95% confidence interval** (from the order statistics), on XY, column, grouped and nested graphs. The point or bar shows the median.

**Dates, second step**
- Pasting or importing text that looks like dates into a number X column offers to **treat the column as dates**.
- **Format Graph › X Axis › Major ticks every** day, week, 2 weeks, month, 3 months or year; minor ticks one step finer.
- **Format Graph › Notes › Line at a date**: a dashed line across the graph at a date you type, with a label.
- Column formulas know dates: `date(2026, 11, 5)`, `today()`, `year(X)`, `month(X)`, `day(X)`, `days(B, A)`, `hours(B, A)`.
- Straight-line fits on dates give the X-intercept and interpolated X values as dates, and the fitted value at the first date.

**Public text**
- Product and file-format names are trademarks of their owners and are used only to describe file compatibility; code and documents name file types by extension, checked by a test.

## 0.3.11 — 2026-11-01

Dates and times.

**Dates in tables**
- The X column of an XY table can hold **dates** or **dates and times**: right-click its heading and choose how they are shown (5 Nov 2026, 05-Nov-26, 2026-11-05, 05/11/2026 or Nov 2026). Nothing changes for tables you leave as numbers, and older files open as before.
- Type or paste dates in many forms: 2026-11-05, 2026-11-05 14:30, 5-Nov-26, 5 Nov 2026, Nov 5, 2026, 05/11/2026; impossible dates (31 Feb) are refused. **File › Options › Dates** sets whether 05/11/2026 is day first or month first (the first time, from your system's language).
- Dates are kept as numbers, days since 1 January 1970, so everything else works on them unchanged.

**Dates on graphs**
- A date X axis with automatic ticks (the year once, then months or days), or day and month, month and year, ISO or week numbers (**Format Graph › X Axis**), with the range typed as dates. Hovering shows the date, and every export keeps the date ticks.

**Analyses and exports**
- Straight-line fits on dates give the slope **per day**. Workbook exports (.xlsx, .ods) write real dates.

**From Datum Plan**
- **Datum Plot 0.3.11 is the first version that opens Datum Plan's time charts with dates** (`xFormat: "date"`, days since 1970): they open on a date axis with no questions asked.

**New sample**
- **Readings over time**: weekly dissolved oxygen at two river sites, on a date axis, with the fall per day.

## 0.3.10 — 2026-11-01

Control charts and design of experiments.

**Control charts** (Analyze › Quality › Control Chart)
- **Individuals and moving range** for one value per row, **X̄ and R** or **X̄ and S** for subgroups (each row a subgroup in its sub-columns), and the **p chart** for defectives out of the number inspected.
- 3σ limits, points beyond them and runs of 8 on one side of the centre line are flagged; give the specification limits for **Cp and Cpk**.

**Design of experiments**
- **New Design** makes a two-level factorial design as a table: 2 to 7 factors, full factorial or half fraction, replicates and centre points, the factors coded −1/+1 and the runs in a random order (row titles). Type each result in the Response column.
- **Factorial Analysis** gives each factor's and interaction's effect with its test (Lenth's method when there are no replicates), a Pareto chart of the effects and the main-effect plot.

**Checked**: the control limits equal the textbook constants (A2, D4, A3, B4, 2.66, 3.267) and the binomial limits of the p chart; known effects are recovered from a simulated design; designs are balanced and orthogonal.

## 0.3.9 — 2026-11-01

More statistics: three-way ANOVA, ANCOVA, agreement, bootstrap confidence intervals and spline fits.

**Compare groups**
- **Three-way ANOVA**: a grouped table whose rows are the first factor and whose data sets are named by two levels with a slash ("Young / Drug", "Old / Placebo"…). Main effects and every interaction, with effect sizes.
- **ANCOVA**: an XY table with the covariate in X and one data set per group. Checks that the slopes are parallel, then compares the groups' adjusted means (with Šidák comparisons) and draws the parallel lines on the graph.

**Relationships**
- **Agreement**: a contingency table of paired ratings (the first rating in the rows, the second in the data sets). Cohen's kappa with its 95% CI and strength, weighted for ordered categories, and McNemar's test (2 × 2) or Bowker's test (larger tables) for a systematic difference.

**Statistics and fitting**
- **Bootstrap confidence intervals** of each data set's mean, median or SD, and of the difference between the first two, without assuming a distribution (BCa, repeatable).
- **Spline fit**: Smooth has a smoothing spline whose smoothness is chosen automatically; it is drawn on the graph.

**Fixed**
- Double-clicking an item in the Analyze or Graph gallery now closes the gallery behind the window it opens.

**Checked** against independent results: kappa by its formula, McNemar's exact test by the binomial distribution, three-way sums of squares by hand, ANCOVA by nested models, the spline by SciPy.

## 0.3.8 — 2026-10-31

Vector fields and 3D scatter graphs.

**New graph styles** for tables of many variables (Graph › Graph Style, or Format Graph › Graph)
- **3D scatter**: the first three variables as X, Y and Z, coloured by a fourth when there is one. Tilt and turn the view in Format Graph.
- **Vector field**: an arrow at each X, Y with its two components from the next two variables, coloured by its length. Arrows are scaled so the longest is about the distance between neighbouring arrows.

## 0.3.7 — 2026-10-31

Ternary, waterfall, radar and bubble graphs.

**New graph styles** (Graph › Graph Style, or Format Graph › Graph)
- **Waterfall** (XY tables): each data set's curve is lifted above the last and labelled at its end, for spectra, runs or temperatures. The lift is automatic, or set it in Format Graph.
- **Ternary** (tables of many variables): the first three variables of each row as shares of 100 % on a triangle, for compositions.
- **Bubble** (tables of many variables): X, Y, bubble size from the third variable, and colour from a fourth if there is one, with a size key and a colour bar.
- **Radar** (grouped tables): the rows are the spokes and each data set is an outline through its means, for comparing profiles.
- A graph style a table cannot make says why (a radar needs at least three rows, a ternary three variables).

**New sample**
- **Composition triangle**: copper, nickel and zinc in 18 alloys on a ternary graph; switch to Bubble to see hardness as bubble size.

## 0.3.6 — 2026-10-31

Multiple t-tests and volcano plots.

**Multiple t-tests**
- **Analyze › Multiple t-tests** (in Compare Groups): a grouped table with one row per gene, protein or compound and two data sets (for example Control and Treated) with their replicates. Each row gets its own test: Welch's or ordinary unpaired t-test, paired t-test, or the Mann-Whitney test.
- The P values are corrected for the number of rows by the false discovery rate (Benjamini-Hochberg, or the two-stage method of Benjamini, Krieger and Yekutieli) or by Holm-Šidák or Bonferroni. Rows below the threshold (q < 0.05 by default) are discoveries, and the answer says how many went up and down.
- The results list every row by P value with the means, the difference, the log₂ fold change, t, P and q.

**Volcano plots**
- The result shows a volcano plot: log₂ fold change (or the difference) against −log₁₀ P, discoveries coloured and the strongest labelled by their row names.
- **New table from result** turns it into an editable graph, with every row's name kept.

**Checked**
- Each row's test equals SciPy's, and the false discovery rates equal the Benjamini-Hochberg step-up worked by hand.

## 0.3.5 — 2026-10-31

Repeated measures and mixed-effects two-way ANOVA; Copy Linked is removed again.

**Repeated measures**
- **Two-way ANOVA** has a new **Repeated measures** option for grouped tables where the same subjects are measured again (one sub-column per subject): in every row (for example at each time point), in every data set, or in both.
- With complete data it is a repeated measures ANOVA with the right error term for each effect and the Geisser-Greenhouse correction for sphericity. When values are missing it fits a mixed-effects model instead, so no subject is thrown away.
- Multiple comparisons within each row or each data set, with stars on the graph, come from the fitted model. The results show the variance between subjects and the sphericity estimates.
- Checked against independent calculations: the fully repeated design matches a reference repeated measures ANOVA exactly, and the classic and mixed-model tests agree for complete data.

**Removed**
- **Copy Linked** (0.3.4) is gone: it depended on other programs' linking steps and was too awkward to use. Copy Picture, Export, Slides, Document and Workbook remain. Projects saved with 0.3.4 open as before.

## 0.3.4 — 2026-10-31

Copy Linked: slides and documents follow your graph.

**Copy Linked**
- **Graph › Copy Linked** (also on the graph's right-click menu) keeps the graph as a picture in a folder beside the project, and redraws it every time you save. Insert that picture into your slides or document *as a link* once: from then on they show the new graph whenever their links are updated, in any program. The Linked Picture window gives the steps; its path is already on the clipboard.
- **Tools › Update Linked Pictures** redraws every linked picture at once; **Stop Linking** ends it for one graph.
- A project file can only name pictures inside its own pictures folder.

**Roadmap**
- The next releases are planned in Help › Roadmap: repeated measures and mixed-effects ANOVA, multiple t-tests and volcano plots, ternary, waterfall, radar, bubble, vector and 3D scatter graphs, more statistics, control charts and design of experiments, wavelets, a graph digitizer, Bayesian tests, and then Mac and Linux versions.
- The roadmap now says plainly that two-way ANOVA is ordinary only for now; repeated measures and mixed models for two and three factors come next.

## 0.3.3 — 2026-10-30

Testers' requests: colour schemes beside the graph, OpenDocument export, and plain names for file types.

**Colours**
- **Graph › Colour Schemes** now sits beside the graph, so each scheme you click shows on the graph at once. Its table is compact again (the colour columns were far too wide).
- Schemes whose colours stay easy to tell apart for colour-blind readers carry a small **colour-blind safe** label: Okabe-Ito (the default), Bright, Muted and Cividis. We checked them by simulating the three common kinds of colour-blindness.
- **Format Graph › Data Sets** shows each data set's colour as it is drawn in the chosen scheme, and its quick colours are that scheme's colours.
- Every window can be moved by dragging its title bar.

**OpenDocument**
- **Tools › Workbook** saves .xlsx or .ods, **Tools › Slides** .pptx or .odp, and **Tools › Document** .docx or .odt: choose the type in the Save dialog. Datum Plot writes the OpenDocument files itself.

**Plain names**
- Buttons and texts name the file type, not another company's product: **Workbook**, **Slides** and **Document**; texts say "a spreadsheet", "a document" or "slides". The "Classic" colour scheme and the "Open axes" and "Framed box" graph styles have plain names too.

## 0.3.2 — 2026-10-30

The Datum Plot Guide in English, Chinese and French, and five new samples.

**Guide**
- **Help › Guide** (and the Guide tile on the File page): a step-by-step guide with numbered pictures, from your first table to analyses, graphs, layouts, export and the Python console, with a "which test when" table, a glossary and shortcuts. Choose English, 中文 or Français: the PDF downloads from this release, is checked against its checksum, is saved in your Downloads folder and opens. The installer stays the same size.

**New samples**
- **Survival study**: months to relapse on two treatments, with Kaplan-Meier curves, the log-rank test and the hazard ratio.
- **Method comparison**: a bedside glucose meter against the lab, with Bland-Altman bias and limits of agreement.
- **Diagnostic test**: a biomarker in healthy people and patients, with the ROC curve, its AUC and the best cut-off.
- **Response surface**: process yield over temperature and time, with a contour map and a quadratic surface fit that finds the best settings.
- **Polar pattern**: the radiation pattern of two antennas on a polar graph.

**Installer**
- An installation in a folder of your own choosing is updated in place after last version's publisher change.

## 0.3.1 — 2026-10-29

The family publisher name.

**Installer**
- Windows now lists the publisher as Datum.

## 0.3.0 — 2026-10-29

A full check of the whole application: security, robustness, reliability and speed. No new features; everything that was there works more safely.

**Nothing is lost**
- Saving a project, the options and every export (pictures, pages, .xlsx, .pptx, .docx, notebooks) now writes a temporary file first and swaps it in only when it is complete: a crash, a full disk or a power cut never leaves a half-written file.
- If something unexpected goes wrong inside the app during an edit, that one step is refused, your project stays exactly as it was, and the details go to `crash.log` in the app's data folder instead of closing the app.
- A project whose internal numbers were damaged (repeated or impossible identifiers) is repaired on opening, with every graph, result and layout still linked to its data.

**Safe files**
- Graph settings out of range in a project file (sizes, fonts, angles, contour levels, marker sizes) are brought back within limits when it opens.
- Damaged or unreadable data files (broken workbooks, garbled text, cut-off .pzfx files) give a clear message instead of an engine error.
- Spreadsheet exports never contain live formulas: text that looks like one (starting with `=`) is written as text. Notebook CSV files mark text starting with `=`, `+`, `-` or `@` so a spreadsheet will not run it.

**Safe updates and window**
- The updater accepts only an installer with the expected name, requires the release's checksum file, limits the download size and saves it in a new private folder.
- The window refuses frames, plug-ins, forms and remote scripts (a stricter content security policy).

**Tested to break**
- New robustness tests feed the engine hundreds of random and hostile projects and edit sequences, damaged and truncated files, and impossible values; they found and fixed one crash (pasting at an impossible position).
- An engine check runs every sample project through the real Python engine: every analysis, every graph type on every kind of table, every export format, layouts, slides, reports, notebooks and the console (532 requests, no failures).
- The checks now also run on Windows and macOS on every change.

**Faster**
- Typing a value in a very large table (a million rows) is about seven times quicker (0.05 s instead of 0.4 s): checking whether an edit changed anything no longer compares a million empty row titles one by one.

## 0.2.23 — 2026-10-28

The Python console, your own analyses, templates, batch processing and notebooks; and a full security, robustness and hardening review.

**Python console**
- Tools › **Python Console**: write Python in the box, press ▶ Run (or Ctrl+Enter), and see what you print, the value of the last line and any figure you draw. Your tables are ready as pandas DataFrames (`tables`, `table(0)`, `tables['Name']`), with numpy, pandas, SciPy and matplotlib loaded. `new_table(...)` puts results back into the project and `result(...)` reads an analysis's numbers. Variables last between runs.
- **How to use** is built in: the ⓘ How to use button in the console and the ? beside it in the ribbon explain where to write, how to run, how to reach your data and how to put results back; Examples ▾ fills in working code to start from.

**Your own analyses, templates, batches, notebooks**
- **My Analyses**: save console code under a name and run it again from Tools › My Analyses on any project. It is kept with the app, never inside projects.
- **Analysis Template**: repeat one table's analyses (with their options) and its graph's look on other tables.
- **Batch Process**: choose a template table and many files; each file becomes a table with those analyses and a graph, and the answers are listed together.
- **Notebook**: save the project as a Jupyter notebook (.ipynb): its tables, each analysis's answer and the Python behind it.
- Every command in the ribbon now works: none are left “coming soon”.

**Security and hardening**
- Updates are installed only when the release's checksum file is there and matches the download exactly; links open only on this project's own pages.
- Project files with impossible sizes, and files larger than 1 GB, are refused or kept within limits (a million rows, 1000 data sets, 50 replicates) instead of exhausting memory; imported files are limited to 300 MB.
- Code never runs from a project: the console runs only what you type when you press Run, and My Analyses stay with the app.
- Every change is now also checked for known vulnerabilities in the window's packages and the bundled Python packages, as it already was for the Rust ones.

**Robustness**
- Every analysis was run on awkward data (identical values, a single value, gaps, empty cells, numbers near the limits) on every kind of table: where something cannot be worked out, it now says why in plain words instead of failing. Editing with impossible values (rows beyond the end, columns that do not exist) is refused safely.
- Tables can now hold up to a million rows (before: 100 000, and larger imports were cut off). Undo keeps fewer steps for very large projects, so memory stays bounded.
- A damaged .pzfx file, or an unexpected number in a result, gives a message instead of stopping the engine.

## 0.2.22 — 2026-10-28

Large data, region statistics, importing projects, plates and many runs, and slides, reports and posters.

**Large data**
- Graphs with hundreds of thousands of points stay quick: a line is thinned to what the screen can show, and dense points are drawn as a picture inside SVG and PDF files while the text stays text. 200 000 points draw in about a second (before: over six) and export at 75 kB (before: 21 MB). Analyses of large tables are faster too.

**Statistics of a region**
- Right-click a graph › **Statistics of a Region** (or Graph › Zoom ▾), then drag a box over part of the curves: for each curve, the points inside, mean, SD, range, area, slope and highest point. Copy the table, or open a linear fit limited to that range.

**Import**
- **.pzfx projects**: File › Import reads every table of a .pzfx file (XY, column, grouped, contingency, survival, parts of whole and nested) with titles, replicates, row titles and excluded values, each with its graph.
- **Plate readers**: a sheet with a 96- or 384-well block (columns 1, 2, 3… and rows A, B, C…) is offered as a plate: a grouped table with rows A–H and columns 1–12, ready for a heat map.
- **Several files at once**: Data › Several Files reads many runs (tensile tests, spectra): one data set per file, in one table when they share their X values.

**Slides, reports and posters**
- Tools › **Slides**: a 16:9 deck with a title slide, every graph on its own slide and a slide per result (.pptx).
- Tools › **Document**: the project's details, every graph with a numbered caption, every result with its answer and main table, and the methods text (.docx).
- Layout › **Poster** (A0) and **Slide** (16:9): a page with a large title and your graphs in a grid; graph text grows to suit the page. New page sizes: poster A0 and A1, slide 4:3.

**Behind the scenes**
- The built-in Python adds two libraries for slides and documents, so the first start after this update unpacks a new Python runtime (about a minute, once).

## 0.2.21 — 2026-10-28

Testers' requests (axis breaks on column graphs, wider columns, empty columns left alone), and matrices with contour maps, 3D surfaces, polar graphs and surface fits.

**Your requests**
- **Axis breaks on column, grouped and nested graphs**: Graph › Axis Break now works on dot plots, bars, box plots and grouped bars, not only on XY graphs (Format Graph › Y Axis › Axis break). Where a break cannot apply, the page says why instead of showing nothing.
- **Wider columns**: drag the right edge of any column heading to widen it, or double-click the edge to fit its name and values. Widths are saved with the project.
- **More room for names**: the × that deleted a data set from its heading is gone, so the name has the whole heading. Delete a data set from its right-click menu, or with Data › Remove Data Set.
- **Empty columns stay out of the way**: graphs and analyses already left out data sets without values; now the analysis dialogs leave them unticked and dim them, and Format Graph marks them “(empty)”, so 3 or 20 columns make no difference.

**Matrices and 3D**
- File › New Table › **Matrix**: Z values on an X–Y grid. X runs down the first column, the Y values are the column titles, and each cell is a Z value (Z title in the bar above the table).
- Its graph is a **contour map** (with contour lines), a **heat map**, a **3D surface** or a **3D wireframe** (Graph › Column Graph, or Format Graph), with a colour bar, a choice of colour maps, the number of contour levels and the 3D viewing angle.
- **Polar graphs**: Format Graph › Data Sets › Polar draws an XY graph with X as the angle in degrees and Y as the radius.

**Surface fits**
- Analyze › Regression › **Surface Fit**: fits Z = f(X, Y) to a matrix, or to three columns (X, Y, Z) of a table of many variables or a worksheet: a plane, a quadratic surface (with its maximum, minimum or saddle point), a cubic surface or a 2D Gaussian peak (centre, height and widths). Coefficients with standard errors and 95% CIs, R², and residual plots; on a matrix graph the fit is drawn as dashed contours or a wireframe.
- A new sample on the Home page, **Hardness map**: hardness across a weld on a 21 × 9 grid, with a 2D Gaussian fit of the hard zone.

## 0.2.20 — 2026-10-28

Worksheets with free columns, and column formulas.

**Worksheets**
- File › New Table › **Worksheet**: free columns, one value per row, for raw instrument data. Each column has a **role** (X, Y, Y error or not plotted), a long name, **units** and a **comment** (Format Data Set, or double-click its heading).
- The graph uses the X column for X, and each Y column as a data set; a Y error column right after a Y column gives its error bars. Units go into the axis titles. Linear regression, curve fits and the other XY analyses work on worksheets the same way.
- A new sample on the Home page, **Worksheet**: a cooling curve with an error column and a formula column in kelvin.

**Column formulas**
- Data › Transform › **Column Formula** (or Format Data Set › Formula): fills a data set from the others, for example `log10(A)`, `B + 273.15`, `(B - mean(B)) / sd(B)` or `if(C > 0, C, 0)`. A, B, C… are the data sets, X the X column, i the row number, `col("title")` a data set by its title; with log10, ln, exp, sqrt, abs, sin, mean, sd, sum, min, max, median, cumsum, diff and more.
- Works on any table, for data sets with one value per row; a heading marked ƒ has a formula.
- Formula columns **update by themselves** when their data change, left to right, and Undo takes back an edit together with its recalculation.

## 0.2.19 — 2026-10-28

Thermal analysis (DSC and TGA) and fatigue S–N curves.

**DSC and TGA**
- Analyze › More › **DSC / TGA**, for curves with temperature in X.
- **DSC** (heat flow): for each peak, the extrapolated onset (where the steepest tangent meets the baseline), the peak and endset temperatures, the area and the **enthalpy** (area ÷ heating rate: J/g when Y is in W/g). Endotherms down or up; a straight or polynomial baseline; a temperature range to look in.
- **TGA** (mass): for each step, the onset, the temperature of fastest loss (the peak of the derivative), the end and the mass lost, plus the residue and the temperature at 5% loss. The derivative curve (DTG) is shown beside the results.
- The DSC sample on the Home page now uses it, and a new **TGA steps** sample shows a filled polymer losing mass in two steps.

**S–N fatigue curves**
- Analyze › Materials › **S–N Curves**: stress amplitude against cycles to failure, fitted with Basquin's law S = A·N^b (or against reversals 2N). Gives A and b with its 95% CI, R², and the **fatigue strength** at the lives you choose (10⁶ and 10⁷ cycles by default).
- **Run-outs** (specimens that did not fail) are marked with an arrow and left out of the fit.
- A new **S–N curve** sample: an aluminium alloy with two run-outs at 10⁷ cycles.

## 0.2.18 — 2026-10-28

Peaks and signals: find and fit peaks, Fourier spectra and filters.

**Peak analysis**
- Analyze › More › **Peaks**: finds the peaks of each XY data set above a baseline, a straight line from the first to the last point or a polynomial that follows a curved background. For each peak: its position, height, width at half height and area. Dips (endotherms, absorption bands) work too.
- Optionally fits all the peaks at once as **Gaussian, Lorentzian or Voigt** peaks: centres and areas with their standard errors, so overlapping peaks are separated.
- The graph shows the baseline (dashed), the fitted curve and a number at each peak. New table from result gives the baseline-corrected data. Noise is not counted as peaks.
- A new sample on the Home page, **Spectrum peaks**: three overlapping bands on a curved background.

**Signal processing**
- Analyze › More › **Signal**: the **Fourier spectrum** (which frequencies a signal holds, and the strongest one), **low-, high- and band-pass filters** (Butterworth, run forwards and backwards so nothing shifts), and **resampling** onto evenly spaced X. Unevenly spaced data are interpolated first, and the result says so.

## 0.2.17 — 2026-10-28

Nested data: subgroups within groups, the nested t-test and the nested one-way ANOVA.

**Nested tables**
- File › New Table › **Nested**: for measurements that come in subgroups, such as specimens from batches or cells from animals. Each group is a data set; its sub-columns are its subgroups, with the replicates down the rows.
- The graph shows each group's subgroups side by side as small columns of dots with their means, and the group mean with an error bar across the subgroup means (Format Graph › Error bars).
- A new sample on the Home page, **Batches**: specimens from three batches of each of three suppliers.

**Nested t-test and ANOVA**
- Analyze › Compare Groups › **Nested** (or Significance on a nested graph): tests the groups against the spread between subgroups, because replicates from one subgroup are not independent. Two groups give the nested t-test, more give the nested one-way ANOVA.
- The full table (between groups, between subgroups within groups, residual), each group's subgroup means, and the variance components from a mixed model: how much of the variation lies between subgroups (intraclass correlation).

## 0.2.16 — 2026-10-28

Survival: time-to-event tables, Kaplan-Meier curves, the log-rank test and hazard ratios.

**Survival tables**
- File › New Table › **Survival**: one row per subject (a patient, a specimen, a component). Enter the time in X and, in that subject's group column, 1 if the event happened (death, failure) or 0 if it was censored (still going when the study ended, or lost).
- A new sample on the Home page, **Time to failure**: bare and coated steel specimens in a salt-spray test stopped at 1000 hours.

**Survival analysis**
- Analyze › More › **Survival**: the Kaplan-Meier survival of each group, its median survival with a 95% confidence interval, and the full survival table (at risk, events, survival, standard error and 95% CI at each time).
- With two or more groups: the log-rank test of whether the curves differ, and hazard ratios against the first group with their 95% CIs (Cox model). Checked against R (`survfit`, `survdiff`, `coxph`).

**Survival curves**
- A survival table's graph draws a staircase per group from 100%, with a tick at each censored subject. Format Graph › **Confidence band** shades each curve's 95% CI. Hovering shows the survival and the number still at risk.

## 0.2.15 — 2026-10-28

Patterns in many variables: principal component analysis and clustering.

**Principal components**
- Analyze › More › **PCA**: finds the few directions that carry most of the variation in many variables. You get each component's eigenvalue and share of the variance, the loadings (which variables make up each component), the scores of every row, how many components are worth keeping, a scree plot and a biplot (rows as points, variables as arrows).
- Each variable is scaled to SD 1 by default, so units do not matter; untick it to keep the original scales. Checked against R (`prcomp`).

**Clustering**
- Analyze › More › **Clusters**: groups similar rows. Hierarchical clustering (Ward's, average or complete linkage) with a dendrogram, or k-means (the best of ten starts). You choose the number of clusters and get each cluster's size and means, the cluster of every row, the mean silhouette (how distinct the clusters are) and a picture of the clusters on the first two components.

**Results become tables**
- **New table from result** turns the PC scores, or the data with each row's cluster number, into a table of many variables to graph or analyse further.

## 0.2.14 — 2026-10-28

Many variables: a table with one row per sample, and multiple, logistic and Poisson regression.

**Many variables**
- File › New Table › **Many variables**: one row per sample (name the rows), one column per measured property. Its graph puts the first variable on X and the others on Y; every XY analysis (linear regression, curve fits…) works on it the same way.
- A new sample on the Home page, **Many variables**: the hardness of 24 steels from their carbon content and tempering temperature.

**Multiple regression**
- Analyze › Regression › **Multiple**: predict one variable (the outcome) from several others at once. Choose the model:
  - **Linear** for a measurement: each predictor's effect with its standard error, P value and 95% CI; R², adjusted R², the F test, AIC, and how much the predictors overlap (VIF).
  - **Logistic** for an outcome of 0 or 1 (fail or pass): odds ratios with their 95% CIs, the likelihood ratio test, pseudo R² and how many rows the model classifies correctly.
  - **Poisson** for counts: rate ratios, and a check for counts that vary more than the model expects.
- Rows with a missing value are left out and counted. Plots of predicted against actual values and of the residuals. Checked against R (`lm` and `glm`).

**How to cite**
- The README says how to cite Datum Plot, and GitHub's "Cite this repository" button gives APA and BibTeX.

## 0.2.13 — 2026-10-28

Security: updated the library that unpacks the Python engine.

**Security**
- The library that unpacks the built-in Python engine on the first start (`zip`) moves from version 2 to 9.1.3, which fixes three reported problems with symbolic links and file permissions (RUSTSEC-2026-0367, 0368 and 0369). Datum Plot only ever unpacks its own bundled file and did not use the affected function, so the risk was low, but it is now gone.
- Every change is now checked for security advisories, licences and where libraries come from (`cargo deny`), as in the other Datum apps.

**Roadmap**
- Multiple variables and regression move to 0.2.14, and the releases after them one number up (Help › Roadmap).

## 0.2.12 — 2026-10-28

Multi-panel figures: lined-up axes, stacked panels sharing one X axis, and insets.

**Lined-up axes**
- On a layout, graphs in the same column line up their plot frames left and right, and graphs in the same row top and bottom, even when their Y numbers or titles differ in width (Arrange › Line Up the Axes; on by default).

**Stacked panels**
- Arrange › **Stack, sharing the X axis**: the graphs in one column with no gaps; only the bottom one keeps its X axis title and numbers. Any panel can drop them (right-click › Hide X Axis Title and Numbers).

**Insets**
- Right-click a graph panel › **Add an Inset Here**: a small graph on a white card in its top-right corner, with smaller text and no panel letter. Move and resize it like any panel; any panel can be made an inset.
- **Bring to Front** puts a panel over the others.

## 0.2.11 — 2026-10-27

Page layouts: several graphs on one page with panel letters, at a journal's size, exported as one file.

**Layouts**
- **New Layout** (Layout tab, or ＋ beside Layouts in the navigator) starts with up to four of the project's graphs, two per row; right-click a graph › **New Layout with This Graph** for one.
- **Drag** a panel to move it and its corner to resize it (whole millimetres); **Delete** removes it; double-click opens the graph. **＋ Graph** and **＋ Text** add more (a caption, a label).
- **Arrange** puts the graphs in one to four columns; **Panel Letters**: A, a, (a) or none.
- The graphs stay linked: change the data and the layout updates.

**Journal figures**
- **Journal Figure** sets the page to a column width (85, 114, 174 or 183 mm) or a page (A4, Letter, a 16:9 slide); or type the size.
- **Export Layout**: PDF, SVG or EPS (vector, text stays text) or PNG and TIFF at 300–1200 dpi, at the page's real size.

**TIFF for journals**
- **TIFF for Journals**: CMYK, LZW-compressed, 600 dpi. Single graphs can be exported as CMYK TIFF too (Export › TIFF › CMYK).

## 0.2.10 — 2026-10-27

Your requests: new tables open at once, data sets are easy to remove, Significance lets you pick the test, and gaps work on the X axis too.

**New tables open at once**
- File › New Table (choose a kind, Create) now closes the File page and shows the new table, instead of staying on the Home page.

**Remove data sets**
- Data › **Remove Data Set**: tick the data sets (columns) to delete. Also on the right-click menu of the table (**Delete Data Set**) and as a small **×** on each data set's heading. Undo brings them back.

**Choose the test for significance stars**
- Graph › Significance now offers **t-test**, **one-way ANOVA** or a **nonparametric** test, with only the groups that hold values ticked. A column table with two filled groups and empty ones can now use a t-test.
- Empty data sets are left out of t-tests, ANOVA, nonparametric tests and other comparisons (the checks say so) instead of stopping them.

**Gaps in axes**
- Axis breaks now work on the **X axis** as well as the Y axis (Format Graph › X Axis or Y Axis › Axis break), and are easier to find: **Axis Break** on the Graph tab and on the graph's right-click menu.

**Roadmap**
- Page layouts move to 0.2.11, and the releases after them one number up (Help › Roadmap).

## 0.2.9 — 2026-10-27

Work directly on the graph: move notes, zoom and pan, exclude points.

**Select, drag and edit**
- Click a note to select it, **drag it** to move it, press **Delete** to remove it, **double-click** it to edit its text.

**Zoom and pan**
- Format › Zoom and Pan (or right-click the graph): **Zoom to a Box** (drag around the part you want), **Pan** (drag the graph until Esc), **Zoom Out**, **Reset Axes**. The ranges are saved with the graph, so exports show the same view.

**Exclude from the graph**
- Right-click a point: **Exclude** it (its replicates at that X stay in the table in blue italics, and graphs and analyses leave them out), or format its data set.

## 0.2.8 — 2026-10-27

Notes on graphs: text, arrows, lines and boxes.

**Annotations**
- Format › Annotate (or Graph › Annotation): **Text** — click where it goes and type it; **Arrow**, **Line** and **Box** — drag on the graph. An arrow can carry a label at its start, a box a title.
- Format Graph › **Notes** lists every note: change its text, position, colour, size or boldness, or delete it.
- Notes sit in the units of the axes, so they stay on their data when the graph is resized, zoomed or exported, and they never change the axis ranges. Copy Look leaves each graph's notes alone.

## 0.2.7 — 2026-10-27

Axis breaks and a second Y axis.

**Second Y axis**
- Tick **Right Y** for a data set (Format Graph › Data Sets, or Format › Second Y Axis): it is drawn against its own axis on the right, with its own title, scale, range and ticks (Format Graph › Right Y Axis). Fitted curves follow their data set's axis; hovering shows the values.

**Axis breaks**
- Format Graph › Y Axis › **Axis break**: leave out a stretch of the Y axis (for example 12 to 95) when one data set sits far above the others. The graph splits into a short top panel and a tall bottom one, with break marks.

## 0.2.6 — 2026-10-27

Do two methods agree, and how good is a test: Bland-Altman and ROC curves.

**Bland-Altman**
- Analyze › **Bland-Altman**: two methods measured on the same items (one row each). Gives the bias and the 95% limits of agreement with their confidence intervals, a check for proportional bias, and the Bland-Altman plot. Differences can be plain, as % of the mean, or ratios.

**ROC curves**
- Analyze › **ROC Curve**: the values of a test in controls and in cases. Gives the area under the curve with its 95% CI and P value, the best cut-off (Youden) with its sensitivity and specificity, every cut-off in a table, and the ROC curve.

**Special graphs**
- Bland-Altman and ROC plots in the results; **New table from result** turns either into a data table to graph and style.
- One-way ANOVA now shows a **forest plot** of the differences between groups with their 95% CIs.

## 0.2.5 — 2026-10-27

Parts of a whole: pie and donut charts, and each part as a percentage.

**Parts of whole**
- File › New Table › **Parts of whole**: the parts in the rows (such as phases or elements), one whole per data set (such as two heat treatments).
- Graphs: **pie**, **donut**, or bars stacked to 100%, one per data set, with the percentages on them (Graph › Column Graph).
- Analyze › **Fractions**: each part as a percentage of its whole; when the values are counts, with 95% confidence intervals (Wilson).

**Also**
- A new sample: Phase fractions (point counts of annealed and quenched steel).

## 0.2.4 — 2026-10-27

Counts: contingency tables with the chi-square and Fisher's exact tests.

**Contingency tables**
- File › New Table › **Contingency**: counts of outcomes (data sets, such as passed and failed) in each group (rows, such as two processes).
- Graphs as bars, stacked bars or **stacked to 100%** (Graph › Column Graph).

**Tests on counts**
- Analyze › **Contingency**: the chi-square test (with Yates' correction if you want it), Cramér's V, observed and expected counts, and row percentages. A check warns when expected counts are too small.
- For 2 × 2 tables: **Fisher's exact test**, the **relative risk** and **odds ratio** with 95% CIs, and the difference of the proportions; for a diagnostic test also the sensitivity, specificity and predictive values. Checked against R.

**Also**
- A new sample: Pass or fail (two coating processes).

## 0.2.3 — 2026-10-27

Two factors at once: grouped tables, two-way ANOVA and grouped graphs.

**Grouped tables**
- File › New Table › **Grouped**: one factor in the rows (named by the row titles, such as alloys), the other in the data sets (such as heat treatments), with replicates side by side.

**Two-way ANOVA**
- Analyze › Two-way ANOVA: the effect of each factor and their **interaction**, with SS, DF, MS, F, P and the % of total variation (Type III sums of squares, so unequal numbers of replicates are fine). Checked against R.
- Partial η² for each effect, the cell means, and checks of equal SDs and normal residuals.
- Comparisons within each row (or within each data set) with Šidák, Holm-Šidák, Bonferroni or no correction, drawn as **stars over the bars**.

**Grouped graphs**
- Grouped bars, stacked bars, grouped dots, lines (an interaction plot) and a **heat map** of the means (Graph › Column Graph).

**Also**
- A new sample: Two factors (three alloys, as received and aged).
- Results checks now always show their ✓ or ⚠ mark.
- The roadmap is now in small steps: one or two features per release, 0.2.4 to 0.2.24, then 1.0 (Help › Roadmap).

## 0.2.2 — 2026-10-25

A big update: comparing groups, materials testing, data tools, graph styles and exporting everything at once (28 features).

**Compare groups**
- **Column tables** (New Table › Column): one group per column, values down the rows, or entered as mean, SD and N.
- **Column graphs**: scatter dots (bee swarm) with mean and error bars, bars, box and whiskers, violins, mean ± error, and before–after lines (Graph › Column Graph).
- **t-tests**: unpaired (Welch or Student), paired, ratio paired and one-sample, with the difference and its 95% CI. Works from entered means, SDs and Ns too.
- **One-way ANOVA**: ordinary, Welch, Brown-Forsythe and repeated measures (Geisser-Greenhouse), with **multiple comparisons** (Tukey, Dunnett, Holm-Šidák, Šidák, Bonferroni, Fisher LSD) and a test for linear trend.
- **Nonparametric tests**: Mann-Whitney, Wilcoxon, Kolmogorov-Smirnov, Kruskal-Wallis with Dunn's test, Friedman.
- **Effect sizes**: Cohen's d and Hedges' g with 95% CIs; η² and ω² for ANOVA.
- **Significance brackets**: stars (or P values) over the groups, kept up to date from the analysis (Graph › Significance).
- **Correlation** (Pearson with 95% CI, Spearman, Kendall, correlation matrix) and **power and sample size** (t-tests, ANOVA, proportions).

**Materials**
- **Tensile test**: Young's modulus, 0.2% offset yield, UTS, strain at UTS, elongation at break and toughness for every specimen, with mean ± SD; the offset line is drawn on the graph.
- **Weibull analysis**: Weibull modulus and characteristic strength by maximum likelihood (with 95% CIs) or regression, the Weibull plot, and strengths at 1% and 10% failure probability.

**Fitting**
- **Global fit**: share parameters across data sets and test whether they differ (extra sum-of-squares F test).
- **Compare two models** for each data set (F test and AICc, with the probability each is right).
- **Area under the curve** with peaks above a baseline (zero, a value, or a straight line from the first to the last point), shaded on the graph.
- **Smoothing** (Savitzky-Golay, LOWESS, moving average), **derivatives** and **cumulative integrals**.

**Data tools**
- **Transform**: log, ln, 1/X, square root, powers, °C ↔ K, scale or shift, subtract a baseline, normalise to 0–100%, replicates to mean, SD and N.
- **New table from result**: transforms, histograms and smoothed curves become data tables you can graph and analyse.
- **Sort**, **Find** (Ctrl+F), **Exclude rows by a rule**, and **Check Data** (missing X, missing N, typing mistakes, values a log axis cannot show).
- **Frequency distributions**: histograms with a normal curve, cumulative distributions and QQ plots.

**Graphs and export**
- **Styles**: open axes, framed box, Nature, Science, ACS, IEEE, presentation and greyscale; save your own.
- **Colour schemes**: Okabe-Ito, Tol bright and muted, classic, viridis, cividis, magma, greyscale or your own colours, each previewed as people with colour-blindness see it.
- **Copy Look** gives other graphs a graph's fonts, sizes, colours and symbols.
- **Thumbnails** of the graphs in the navigator (View › Thumbnails).
- **Export All Graphs** into a folder, and a **spreadsheet workbook (.xlsx)** with every data table and result (Tools tab).

**Help and samples**
- **Test Chooser**: a few questions open the right analysis. **Statistics Guide**: which test when, P values, confidence intervals, SD or SEM, common mistakes.
- New samples: Compare groups (ANOVA with brackets), Weibull strength, DSC peak (area = enthalpy); the Tensile sample has a tensile analysis.

**Faster**
- A second Python engine calculates results, so a long fit never holds up the graphs.

**Roadmap**
- Two factors and counts are next (0.2.3), then interactive graphs and layouts (0.2.4) (Help › Roadmap).

## 0.2.1 — 2026-10-25

A small "?" beside the tools: click it to see what the tool is for and how to use it.

**Help beside every tool**
- Every ribbon group with working tools has a small **?** next to its name. A click opens a short card: what the tool does, how to use it, and a tip where one helps.
- The navigator (Data tables, Results, Graphs), the Info sheet, the data table, the graph, the results sheet, Format Graph, Export, Import, the analysis options and the New Data Table, Analyze Data and Graph Type galleries have one too.
- Help › **What Is This Tool?** lists every card, so you can read about a tool before you look for it.

**Roadmap**
- The data tools and the releases after them each move up one number: data tools are now 0.2.2 (Help › Roadmap).

## 0.2.0 — 2026-10-25

Statistics, linear regression and curve fitting, with results that stay linked to your data and explain themselves.

**Results**
- Analyze… (or the Analyze tab) adds an analysis to the project. It appears under **Results** in the navigator, linked to its table: change a value and the result updates.
- Each results sheet has tabs (Summary, Details, Interpolated) with tables you can copy straight into a spreadsheet or a document, and small plots (residuals, QQ plots, Arrhenius plots).
- The panel on the right gives **the answer in one sentence**, **checks** of the assumptions (✓, ⚠), **methods text** and a figure legend to paste into a report, and **Python code** that reproduces the calculation.
- P values are exact (or < 0.0001) with APA stars.

**Statistics**
- **Descriptive statistics**: n, mean, SD, SEM, 95% CI, quartiles, median, range, CV, geometric mean and SD, skewness, kurtosis.
- **Normality tests**: Shapiro-Wilk, D'Agostino-Pearson, Anderson-Darling and Kolmogorov-Smirnov (Lilliefors), with QQ plots.
- **Outliers**: Grubbs' test; one click excludes the outliers (they stay in the table in blue).

**Linear regression**
- Slope, intercept, X-intercept, R², adjusted R², Sy.x, ANOVA table, runs test, with standard errors and 95% confidence intervals.
- **Fit only part of the data** (Fit X from … to …), for example the elastic region of a stress–strain curve.
- Through the origin, polynomials (order 2–6), **Deming regression** (errors in X and Y), weighting by 1/Y², every replicate or only the means.
- **Compare lines**: are the slopes (then the intercepts) of the data sets different?
- **Interpolate**: read X for unknown Y values off the line.

**Curve fitting**
- A model library: exponential decay and growth, two-phase decay, power law, logarithmic, logistic, Gompertz, dose-response, Gaussian, Lorentzian, Michaelis-Menten, Langmuir, Freundlich, Arrhenius and Avrami.
- **Your own equation**, such as `Y = A*exp(-k*X) + C`, with starting values and fixed parameters.
- Best-fit values with standard errors and 95% CIs, R², AICc, parameter correlations, residuals, convergence checks.

**Arrhenius**
- Rates at several temperatures (°C or K) give the **activation energy** (kJ/mol, eV, kcal/mol) and the pre-exponential factor, with confidence intervals and the Arrhenius plot.

**On the graph**
- Fits are drawn on the table's graphs with their 95% confidence band (or prediction band) and the **equation and R²**, placed where they do not cover the data. Each result can be shown or hidden per graph.

**Samples**
- **Tensile test** (elastic modulus of two alloys from the elastic region) and **Arrhenius** (activation energies of two catalysts), each with its analysis ready.

**Releases**
- One installer per release, used both to install and to update. Python is unpacked once more on the first start of this version (new libraries: statsmodels and lmfit).

## 0.1.1 — 2026-10-24

Copy Picture works, updates are small, data import, and the whole app laid out: every planned feature has its place and says when it arrives.

**Small, fast updates**
- Python and its libraries are now a separate "runtime pack". Update now downloads only Datum Plot itself (a few MB); the runtime is downloaded again only when its libraries change.
- The first start after installing unpacks the Python engine once (a short wait, shown in the status bar). Later starts are as fast as before.
- The copy of Python that 0.1.0 kept in the program folder is removed.

**Copy Picture works**
- Copy Picture (and Ctrl+C on a graph) now puts the graph on the Windows clipboard as a picture, so it pastes into documents, slides and email. Paste Special and the Print page's codes use the Windows clipboard too.

**Import data**
- File › Import, Data › Import or Home › Import data: CSV, TSV, TXT and spreadsheet (.xlsx) files.
- A preview shows the file. Choose the sheet, whether the first row holds titles, the X column, and how many replicates make one data set (guessed from the titles, such as "Sample 1, , Sample 2, ,").
- Semicolon files with decimal commas (1,5) are read correctly.

**Everything laid out**
- **Help › Roadmap** (also on the File page and Home): all 99 features (ready and planned), what each does, the Python library behind it and the release it arrives in. Search it or filter by release.
- Planned commands already sit in the ribbon, dimmed with an amber dot. Clicking one tells you what it will do and when.
- New ribbon tabs: **Layout** (layouts, journal figures, posters) and **Tools** (Python console, your own analyses, batch processing, slide and document export, Restart Engine).
- **Analyze…** opens a gallery of every analysis by family: statistics, regression and fitting, comparing groups, relationships, survival, signals and spectra, planning.
- **New Table** opens a gallery of every kind of data table; **Graph Type** a gallery of every kind of graph.

**Reliability**
- If the Python engine ever takes longer than a minute, it is restarted instead of freezing the app. Tools › Restart Engine does it by hand.

**What comes next**
- 0.2: statistics and regression: descriptive statistics, normality, outliers, linear and polynomial regression, nonlinear curve fitting with a model library, interpolation, results sheets with explanations.

## 0.1.0 — 2026-10-24

The first version of Datum Plot: the application, automatic updates, an XY data table and publication-quality graphs drawn by a built-in Python engine.

**Install and update**
- A Windows installer for your user account, with no administrator rights needed. It brings its own Python with numpy, SciPy and matplotlib, so there is nothing else to install.
- The Home page shows your version and checks GitHub for new releases. **Update now** downloads the new version, checks its SHA-256 checksum, installs it and restarts.
- An **Update available** badge appears in the title bar when a new version is out. Beta versions can be turned on in Options.

**Projects**
- A project holds an Info sheet, data tables and graphs, listed in the navigator next to the sidebar (Info, Data, Results, Graphs, Layouts).
- Save and open `.dplot` files (Ctrl+S, Ctrl+O). Double-clicking a `.dplot` file opens it. Recent projects are on the Home page.
- Undo and redo (Ctrl+Z, Ctrl+Y), up to 200 steps. A recovery copy is kept while you work, and Datum Plot asks before closing with unsaved changes.
- Samples on the Home page: a growth curve, a standard curve (entered as mean, SD and N) and a dose-response experiment on a log axis.

**XY data table**
- An X column, then data sets A, B, C… Each data set has replicate columns (Y1, Y2, …), or takes a mean with its SD or SEM and N.
- Titles and units for X and Y become the axis titles. Row titles for samples or animals.
- Works like a spreadsheet: select ranges with the mouse, Shift and Ctrl; copy and paste with spreadsheets (a first row of headings becomes the titles, and the table grows to fit); fill handle with series; Paste Special; bold, italic, colours and alignment.
- **Exclude** a value with Ctrl+E: it stays in the table, shown in blue and struck through, and graphs leave it out.
- Sum, Average and Count of the selected cells above the grid.

**Graphs**
- Every table comes with a graph; add more with New Graph.
- Means with error bars (SD, SEM, 95% confidence interval or range, above, below or both), or every replicate. Points can be joined by lines.
- Linear or logarithmic axes, automatic or fixed ranges, tick spacing, minor ticks and gridlines.
- Open axes with outward ticks or a framed box, Okabe-Ito colours that people with colour-blindness can tell apart, eight symbols, a legend, and the graph's size in millimetres with journal presets (single, 1.5 and double column).
- **Format Graph** opens beside the graph and every change shows at once. Double-click an axis, the legend or the data to open the right page.
- Hover over a point to see its mean, n, SD and SEM; elsewhere the crosshair shows the X and Y values.

**Export and print**
- Export as PNG or TIFF at 150 to 1200 dpi, or as SVG, PDF or EPS with the text kept as text (editable in drawing programs). Transparent backgrounds too.
- Copy a graph (Ctrl+C on the graph) and paste it into a document, a slide or an email.
- File › Print with a live preview: the graph at its real size or fitted to the page, a caption saying what the points show, headers and footers with your logo, page numbers and Info fields. Choose "Save as PDF" to make a PDF. Data tables and the Info sheet print too.

**Known limits in 0.1**
- No analyses yet: column statistics arrive in 0.1.1, t-tests, ANOVA and curve fitting in 0.2.0. The Analyze tab says what comes when.
- Only XY tables. Column, grouped, contingency and survival tables come later.
- No CSV or spreadsheet import yet: copy the cells in a spreadsheet and paste them into a table.
- No page layouts with several graphs yet (0.3).
- The installer is larger than Datum Plan's because it carries Python, numpy, SciPy and matplotlib. The first start after installing takes a few seconds longer while matplotlib reads the installed fonts.
