# Changelog

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
- Works like Excel: select ranges with the mouse, Shift and Ctrl; copy and paste with Excel (a first row of headings becomes the titles, and the table grows to fit); fill handle with series; Paste Special; bold, italic, colours and alignment.
- **Exclude** a value with Ctrl+E: it stays in the table, shown in blue and struck through, and graphs leave it out.
- Sum, Average and Count of the selected cells above the grid.

**Graphs**
- Every table comes with a graph; add more with New Graph.
- Means with error bars (SD, SEM, 95% confidence interval or range, above, below or both), or every replicate. Points can be joined by lines.
- Linear or logarithmic axes, automatic or fixed ranges, tick spacing, minor ticks and gridlines.
- Prism-style open axes or a framed box, Okabe-Ito colours that people with colour-blindness can tell apart, eight symbols, a legend, and the graph's size in millimetres with journal presets (single, 1.5 and double column).
- **Format Graph** opens beside the graph and every change shows at once. Double-click an axis, the legend or the data to open the right page.
- Hover over a point to see its mean, n, SD and SEM; elsewhere the crosshair shows the X and Y values.

**Export and print**
- Export as PNG or TIFF at 150 to 1200 dpi, or as SVG, PDF or EPS with the text kept as text (editable in Illustrator or Inkscape). Transparent backgrounds too.
- Copy a graph (Ctrl+C on the graph) and paste it into Word, PowerPoint or an email.
- File › Print with a live preview: the graph at its real size or fitted to the page, a caption saying what the points show, headers and footers with your logo, page numbers and Info fields. Choose "Save as PDF" to make a PDF. Data tables and the Info sheet print too.

**Known limits in 0.1**
- No analyses yet: column statistics arrive in 0.1.1, t-tests, ANOVA and curve fitting in 0.2.0. The Analyze tab says what comes when.
- Only XY tables. Column, grouped, contingency and survival tables come later.
- No CSV or Excel import yet: copy the cells in Excel and paste them into a table.
- No page layouts with several graphs yet (0.3).
- The installer is larger than Datum Plan's because it carries Python, numpy, SciPy and matplotlib. The first start after installing takes a few seconds longer while matplotlib reads the installed fonts.
