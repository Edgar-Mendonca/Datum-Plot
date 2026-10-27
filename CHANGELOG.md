# Changelog

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
- **Styles**: Prism, Origin, Nature, Science, ACS, IEEE, presentation and greyscale; save your own.
- **Colour schemes**: Okabe-Ito, Tol bright and muted, Tableau, viridis, cividis, magma, greyscale or your own colours, each previewed as people with colour-blindness see it.
- **Copy Look** gives other graphs a graph's fonts, sizes, colours and symbols.
- **Thumbnails** of the graphs in the navigator (View › Thumbnails).
- **Export All Graphs** into a folder, and an **Excel workbook** with every data table and result (Tools tab).

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
- Each results sheet has tabs (Summary, Details, Interpolated) with tables you can copy straight into Excel or Word, and small plots (residuals, QQ plots, Arrhenius plots).
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
- Copy Picture (and Ctrl+C on a graph) now puts the graph on the Windows clipboard as a picture, so it pastes into Word, PowerPoint and email. Paste Special and the Print page's codes use the Windows clipboard too.

**Import data**
- File › Import, Data › Import or Home › Import data: CSV, TSV, TXT and Excel (.xlsx) files.
- A preview shows the file. Choose the sheet, whether the first row holds titles, the X column, and how many replicates make one data set (guessed from the titles, such as "Sample 1, , Sample 2, ,").
- Semicolon files with decimal commas (1,5) are read correctly.

**Everything laid out**
- **Help › Roadmap** (also on the File page and Home): all 99 features (ready and planned), what each does, the Python library behind it and the release it arrives in. Search it or filter by release.
- Planned commands already sit in the ribbon, dimmed with an amber dot. Clicking one tells you what it will do and when.
- New ribbon tabs: **Layout** (layouts, journal figures, posters) and **Tools** (Python console, your own analyses, batch processing, PowerPoint and Word export, Restart Engine).
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
