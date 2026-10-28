# Datum Plot after 0.1.0: the full feature catalogue, Python, fast updates

Status: **answered (session 3) — 0.1.1 built; the detailed 0.2 plan is [PLAN-0.2.0.md](PLAN-0.2.0.md) (session 4).** The answers and the new release order are in §10; they replace §7. The catalogue in §4 is mirrored in the app (`ui/src/features.ts`, Help › Roadmap) with the release numbers of §10.

This follows the family pattern: feedback → diagnosis → proposal → size → questions. §4 is the full catalogue of what Datum Plot will do: every feature gets an ID (A1, B12…) and a release, so we can tick them off one by one.

---

## 1. Your feedback on 0.1.0 (24 Oct 2026)

1. **First start:** quick, about 3–6 seconds. **Install:** under a minute. After start the app is very fast and feels optimised: keep it that way.
2. **Graph font:** the text in the graph shows in Arial, as intended (that is what "Arial" in my list meant: the font matplotlib uses for the graph's text).
3. **Copy Picture does not work.**
4. **Updates are slow:** every update downloads the whole installer, Python included.
5. There is too little in the app to evaluate yet. Brainstorm first: put the full list of features on the table, say what Datum Plot will do, then build them in steps.
6. You asked how the graph is made (see §2).

## 2. How a graph is made today (in plain words)

```mermaid
sequenceDiagram
  participant W as Window (what you see)
  participant R as Rust (the app's core)
  participant P as Python (numpy · SciPy · matplotlib)
  W->>R: you type 2.5 in a cell
  R->>R: checks it, stores it, adds an undo step
  W->>R: "draw graph 2"
  R->>P: the table's numbers + the graph's settings
  P->>P: SciPy/numpy: mean, SD, SEM, CI per X<br/>matplotlib: draws the figure
  P-->>R: the picture (SVG) + where the axes and legend are
  R-->>W: shows it; hover and double-click use those positions
```

- **matplotlib draws every graph**, on screen and in every export (PNG, TIFF, SVG, PDF, EPS). What you see is exactly what you export.
- **Python runs inside the app**: a small Python program (`py/worker.py`) starts with Datum Plot and waits for requests. Nothing is installed on your PC apart from the app.
- **Rust keeps the project**: tables, graphs, undo, files. It never calculates statistics.
- A redraw takes about 15 ms after start-up, which is why typing a value updates the graph almost at once.

## 3. Diagnosis

### 3.1 Copy Picture
`graph.tsx` uses the browser clipboard (`navigator.clipboard.write`). On Windows, Tauri 2 serves the window from `http://tauri.localhost`. That is not a "secure" address, so WebView2 switches the clipboard API off and the copy fails (it worked in the Linux test browser, which is why the tests did not catch it). The same problem affects Paste Special's fallback and the header-code copy on the Print page.
**Fix (0.1.1):** Rust puts the picture on the Windows clipboard itself (`tauri-plugin-clipboard-manager`, image + text), so it no longer depends on the browser. Office then pastes it as a picture. Add an in-app test for the command, and you check it in Word.

### 3.2 Slow updates
The 0.1.0 installer is 55 MB because 50 MB of it is Python and its libraries, and every update repeats that download even when Python did not change. The app itself (Rust + window + our Python code) is about 4 MB.
**Fix (0.1.1): ship Python separately ("runtime pack").**

| | Today | Proposed |
| --- | --- | --- |
| First install | `DatumPlot-0.1.0-setup.exe`, 55 MB | `DatumPlot-x.y.z-setup.exe` with the runtime inside (same as today, about 55–80 MB) |
| Update when only Datum Plot changed | 55 MB | **about 4 MB** (`DatumPlot-x.y.z-update.exe`, app only) |
| Update when Python libraries changed (rare: new library, new versions) | 55 MB | the small update + `DatumPlot-runtime-N.zip` once |

- The runtime lives in `%LOCALAPPDATA%\com.edgarmendonca.datumplot\runtime\N\` (outside the program folder, so app updates never touch it). `N` is a runtime number that only changes when `py/requirements.txt` changes.
- Each release publishes `runtime.json` (number, size, SHA-256). The updater downloads the runtime zip only when the number is new, checks its SHA-256, unpacks it beside the old one, switches, then deletes the old one. If anything fails the old runtime stays.
- Our own Python code (`py/datum`) stays inside the small app update, because it changes with every release.
- Update now shows both steps with progress ("Downloading Datum Plot 4 MB… Downloading the Python runtime 62 MB (only this time)…").

### 3.3 Other findings while reviewing 0.1.0
- If Python ever hangs (rather than crashes), the app waits. Add a timeout and restart (0.1.1).
- Format Graph's data set table needs a horizontal scrollbar on smaller screens (seen in your screenshot); move colour, size and line to a per-data-set row editor (0.1.1).
- The graph shows at 150 % zoom by default; add "fit to window" and remember the zoom (0.1.1).

---

## 4. The feature catalogue

Releases: **0.1.1** fixes and fast updates · **0.2** compare groups · **0.3** curve fitting and regression · **0.4** two factors, interactive graphs, layouts · **0.5** survival, nested, many variables · **0.6** Origin power · **0.7** Python scripting and automation · **1.0** stable. ✅ = in 0.1.0.

### A. Data tables and data entry

| ID | Feature | What it means | Release |
| --- | --- | --- | --- |
| A1 | XY table | X + data sets with replicates or mean/SD/SEM/N | ✅ |
| A2 | Column table | One group per column, values down (or mean/SD/N) — for t-tests and one-way ANOVA | ✅ 0.2.2 |
| A3 | Grouped table | Rows × data sets with replicates — two-way ANOVA, grouped bars | ✅ 0.2.3 |
| A4 | Contingency table | Counts in rows × columns — chi-square, Fisher | ✅ 0.2.4 |
| A5 | Survival table | Time + event/censored per group — Kaplan-Meier | 0.5 |
| A6 | Parts of whole | Values that make a whole — pie, donut, 100 % stacked | ✅ 0.2.5 |
| A7 | Multiple variables | One row per subject, many columns (numbers and text) — multiple/logistic regression, correlation matrix, PCA | ✅ 0.2.14 |
| A8 | Nested table | Sub-columns within groups (cells within animals) — nested t-test/ANOVA | 0.5 |
| A9 | Worksheet (Origin) | Free columns with roles (X, Y, Z, error, label), long name, units, comments, sparklines | 0.6 |
| A10 | Matrix | A Z grid for heat maps, contours, 3D surfaces | 0.6 |
| A11 | Column formulas | "Set column values" with formulas, e.g. `log10(A)`, `(B - mean(B)) / sd(B)`, evaluated by numpy | 0.6 |
| A12 | Import CSV / TXT / XLSX | With a preview: delimiter, header rows, which columns go where | 0.1.1 |
| A13 | Import Prism `.pzfx` | Tables, titles and replicates from Prism projects | 0.4 |
| A14 | Instrument and plate import | Plate readers (96/384 wells) with a plate map of samples, standards and blanks; Origin ASCII; spectra folders | 0.6 |
| A15 | Transforms | New linked table: log, ln, reciprocal, normalise (0–100 %), subtract baseline, row means, transpose, remove blanks, fractions of total | ✅ 0.2.2 |
| A16 | Exclude, outlier flags | Exclude by hand ✅; flag outliers found by ROUT/Grubbs and exclude them in one click | 0.2 |
| A17 | Sort, find, filter | Sort rows by X, find values, hide rows by a rule | ✅ 0.2.2 |
| A18 | Data checks | Warn about text in number cells, empty X, too few replicates, duplicated X | ✅ 0.2.2 |

### B. Analyses (Python: SciPy, statsmodels, lmfit, lifelines)

| ID | Feature | Python library | Release |
| --- | --- | --- | --- |
| B1 | Descriptive statistics: n, mean, SD, SEM, CI, median, quartiles, min/max, CV, geometric mean, skewness, kurtosis | numpy, scipy.stats | 0.2 |
| B2 | Normality: Shapiro-Wilk, D'Agostino-Pearson, Anderson-Darling, Kolmogorov-Smirnov; QQ plot | scipy.stats | 0.2 |
| B3 | Outliers: Grubbs, ROUT (Q = 1 %) | own code on numpy (ROUT on the curve fit) | 0.2 |
| B4 | t-tests: unpaired (Student, Welch), paired, one-sample, ratio paired; multiple t-tests with FDR | scipy.stats, statsmodels | ✅ 0.2.2 |
| B5 | Nonparametric: Mann-Whitney, Wilcoxon, Kolmogorov-Smirnov, Kruskal-Wallis + Dunn, Friedman + Dunn | scipy.stats, scikit-posthocs | ✅ 0.2.2 |
| B6 | One-way ANOVA: ordinary, Welch, Brown-Forsythe, repeated measures (+ Greenhouse-Geisser) | scipy.stats, statsmodels | ✅ 0.2.2 |
| B7 | Multiple comparisons: Tukey, Dunnett, Šidák, Bonferroni, Holm-Šidák, Fisher LSD, Dunn; test for trend | scipy.stats, statsmodels, scikit-posthocs | ✅ 0.2.2 |
| B8 | Effect sizes with 95 % CI: mean difference, Cohen's d, Hedges' g, η², ω² | numpy, scipy (bootstrap) | ✅ 0.2.2 |
| B9 | Linear regression: slope, intercept, R², CIs, runs test, compare slopes and intercepts, through origin, Deming | scipy.stats, statsmodels | 0.3 |
| B10 | Nonlinear curve fitting: bounds, fixed and shared parameters, weighting, CIs (asymptotic and profile), robust fit | **lmfit** (on scipy.optimize) | 0.3 |
| B11 | Model library: dose-response 3/4/5-parameter, Hill, binding (one site, two sites, competition), enzyme kinetics (Michaelis-Menten, substrate inhibition, allosteric), exponential growth/decay 1–2 phases, Gaussian, Lorentzian, Voigt, logistic, Gompertz, polynomial 1–6, sine, power, user equations | lmfit models + ours | 0.3 |
| B12 | Global fitting, compare models (extra sum-of-squares F test, AICc), compare a parameter between data sets | lmfit, scipy | ✅ 0.2.2 |
| B13 | Interpolate unknowns from a standard curve (ELISA, BCA, qPCR) | lmfit, numpy | 0.3 |
| B14 | Area under the curve, derivatives, integrals, smoothing (Savitzky-Golay, LOWESS) | numpy, scipy.signal, statsmodels | ✅ 0.2.2 |
| B15 | Two-way and three-way ANOVA (ordinary, repeated measures, mixed model) | statsmodels | ✅ 0.2.3 |
| B16 | Correlation: Pearson, Spearman, Kendall, matrix, partial | scipy.stats, pandas | ✅ 0.2.2 |
| B17 | Contingency: chi-square (Yates), Fisher's exact, relative risk, odds ratio, sensitivity/specificity, McNemar | scipy.stats, statsmodels | ✅ 0.2.4 |
| B18 | ROC curves and AUC, Bland-Altman | numpy, scipy | ✅ 0.2.6 |
| B19 | Survival: Kaplan-Meier, log-rank, Gehan-Breslow-Wilcoxon, median survival, hazard ratio, Cox regression | **lifelines** | 0.5 |
| B20 | Nested t-test, nested one-way ANOVA (mixed models) | statsmodels | 0.5 |
| B21 | Multiple linear, logistic and Poisson regression | statsmodels | ✅ 0.2.14 |
| B22 | PCA, clustering (hierarchical, k-means) | numpy SVD, scipy.cluster | ✅ 0.2.15 |
| B23 | Power and sample size (t-tests, ANOVA, proportions) | statsmodels.stats.power | ✅ 0.2.2 |
| B24 | Peak analysis: baseline, find peaks, areas, multi-peak fit | scipy.signal, lmfit, pybaselines | 0.6 |
| B25 | Signal processing: FFT, filters, convolution, resampling, interpolation | numpy.fft, scipy.signal, scipy.interpolate | 0.6 |
| B26 | Surface fitting (Z = f(X, Y)), implicit fits | lmfit | 0.6 |
| B27 | Tensile test analysis: modulus, 0.2 % offset yield, UTS, elongation, toughness (added session 4) | numpy, scipy | ✅ 0.2.2 |
| B28 | Arrhenius / activation energy (added session 4) | scipy | 0.2 |
| B29 | Weibull analysis of strength (added session 4) | scipy | ✅ 0.2.2 |
| B30 | Fatigue S–N curves, Basquin fit (added session 4) | scipy | 0.6 |
| B31 | DSC/TGA peak areas and onsets (added session 4) | scipy | 0.6 |

### C. Results: how answers are shown

| ID | Feature | Release |
| --- | --- | --- |
| C1 | Results sheets in the navigator, linked to their table: change a value and the result updates (Prism's chain) | 0.2 |
| C2 | Tabs per result: Summary, Details, Multiple comparisons, Descriptive, Normality, Residuals | 0.2 |
| C3 | **Explain panel**: the question asked, the answer in one sentence, assumption checks (✓/⚠) and what to do if one fails | 0.2 |
| C4 | **Test chooser**: 3–4 questions (groups, paired, normal, what you want to know) open the right analysis | ✅ 0.2.2 |
| C5 | **Methods and legend text** ready to paste into a paper, with the software version | 0.2 |
| C6 | P-value styles (Prism GP, APA, NEJM, exact) and decimal places | 0.2 |
| C7 | Copy results to Excel / Word, export as XLSX | 0.2 |
| C8 | "Show as Python code": the exact numpy/SciPy code that reproduces a result, so a reviewer can check it | 0.3 |
| C9 | Analysis checklist warnings (too few values, unequal variances, outliers found) | 0.2 |

### D. Graphs (matplotlib)

| ID | Feature | Release |
| --- | --- | --- |
| D1 | XY: points, lines, means ± SD/SEM/CI/range, every replicate, log axes, journal sizes | ✅ |
| D2 | Column graphs: scatter dot plot (mean/median lines), bar ± error, box (Tukey, min–max, percentiles), violin, swarm/beeswarm, before–after, estimation plot (Gardner-Altman, Cumming) | ✅ 0.2.2 |
| D3 | **Significance brackets** with stars or P values, placed automatically from the analysis and updated with it | ✅ 0.2.2 |
| D4 | Histogram, cumulative distribution, KDE, QQ plot | ✅ 0.2.2 |
| D5 | Fitted curves with confidence and prediction bands, residual plots | 0.3 |
| D6 | Grouped bars (interleaved, separated, stacked), grouped scatter, heat map | ✅ 0.2.3 |
| D7 | Pie, donut, 100 % stacked bars | ✅ 0.2.5 |
| D8 | Axis breaks (one or more), double Y axis, top/right axes, reverse, probability and reciprocal scales | ✅ 0.2.7 |
| D9 | Survival curves with censor ticks and the number-at-risk table | 0.5 |
| D10 | Volcano, forest, bubble, Bland-Altman, ROC | ✅ 0.2.6 |
| D11 | Contour, 3D surface and scatter, polar, ternary, waterfall, vector field, radar | 0.6 |
| D12 | Multi-panel graphs (stacked, 2×2, 3×3), insets, layers with linked axes (Origin) | ✅ 0.2.12 |
| D13 | **Graph styles and themes**: Prism, Origin, Nature, Science, Cell, ACS, IEEE, presentation, greyscale; save your own | ✅ 0.2.2 |
| D14 | **Copy look** (Prism's Magic): apply one graph's formatting to others | ✅ 0.2.2 |
| D15 | Text, arrows, lines, boxes, images on the graph; Greek letters, sub/superscripts, simple LaTeX in titles (matplotlib mathtext) | ✅ 0.2.8 |
| D16 | Colour schemes: Okabe-Ito ✅, viridis family, greyscale, custom palettes; colour-blind preview | ✅ 0.2.2 |
| D17 | Large data (1 million points) with fast decimation for screen | 0.6 |

### E. Working with the graph on screen

| ID | Feature | Release |
| --- | --- | --- |
| E1 | Hover values, crosshair, double-click to format ✅ | ✅ |
| E2 | **Click to select any part** (title, axis, tick labels, legend, one data set, one point): matplotlib reports where each element is, the window highlights it and the ribbon/Format pane shows its settings | ✅ 0.2.9 |
| E3 | Drag the legend, titles and annotations; edit text in place | ✅ 0.2.9 |
| E4 | Zoom and pan the plot (box zoom, wheel), reset | ✅ 0.2.9 |
| E5 | Region of interest: drag a box to get statistics, area, a quick fit or peaks for just that region (Origin Gadgets) | 0.6 |
| E6 | Exclude points from the graph (click a point → exclude it in the table) | ✅ 0.2.9 |
| E7 | Undo every graph change ✅; graph thumbnails in the navigator | ✅ 0.2.2 |

### F. Layouts and figures for papers

| ID | Feature | Release |
| --- | --- | --- |
| F1 | Layout pages: several graphs, tables, text and pictures on a page; panel letters A, B, C; align and distribute | ✅ 0.2.11 |
| F2 | Figure sizes for journals; export a whole layout as one PDF/TIFF/SVG (drawn by matplotlib at real size) | ✅ 0.2.11 |
| F3 | Poster and slide templates | 0.6 |

### G. Export and sharing

| ID | Feature | Release |
| --- | --- | --- |
| G1 | PNG, TIFF, SVG, PDF, EPS export ✅ | ✅ |
| G2 | **Copy picture that works on Windows** (PNG through Rust), copy as SVG for Office 365 | 0.1.1 |
| G3 | TIFF in CMYK and LZW for journals; colour profile | ✅ 0.2.11 |
| G4 | Batch export: every graph in the project at once | ✅ 0.2.2 |
| G5 | **Send to PowerPoint**: one slide per graph; **Word report**: graphs, results tables and methods text | 0.7 (python-pptx, python-docx) |
| G6 | Export tables and results to Excel | ✅ 0.2.2 |

### H. Python inside: scripting and extending

| ID | Feature | Release |
| --- | --- | --- |
| H1 | **Python console** in the app: tables are numpy/pandas objects (`T["Growth"]`), results and graphs too; run code, plot with matplotlib into the project | 0.7 |
| H2 | Your own analyses and fit equations written in Python, saved with the project or as plugins | 0.7 |
| H3 | Analysis templates: run the same analyses and graphs on new data with one click | 0.7 |
| H4 | Batch processing: a folder of files → one table, analysis and graph each, plus a summary | 0.7 |
| H5 | Notebook export (`.ipynb`) of a project's analyses | 0.7 |

### I. Speed, size and reliability

| ID | Feature | Release |
| --- | --- | --- |
| I1 | **Separate Python runtime** so updates are about 4 MB (§3.2) | 0.1.1 |
| I2 | Worker timeout and restart; a "Restart the engine" button | 0.1.1 |
| I3 | Second worker for long analyses (fits, bootstraps) so drawing never waits | ✅ 0.2.2 |
| I4 | Results and graph caches; nothing recalculated twice | ✅ graphs, 0.2 results |
| I5 | Start-up under 3 s: load Python libraries lazily (SciPy modules only when used) | 0.1.1 |
| I6 | Code signing (no SmartScreen warning), signed updates, crash reports | 0.6 |

### J. Learning and help

| ID | Feature | Release |
| --- | --- | --- |
| J1 | Getting Started, Glossary, Shortcuts ✅ | ✅ |
| J2 | A sample project for every analysis (Home › Samples), with the reason the analysis was chosen | ✅ 0.2.2 |
| J3 | Statistics guide: which test when, what P values and CIs mean, common mistakes | ✅ 0.2.2 |
| J4 | Validation page: every statistic checked against R and NIST reference data, with the numbers | 1.0 |
| J5 | ? help: a small ? beside each tool opens a card saying what it is for and how to use it; Help › What Is This Tool? lists every card (all Datum apps; ✅ 0.2.1) | 0.2.1 |

---

## 5. Python libraries to add, and the size

| Library | For | Licence | Installed size (about) | When |
| --- | --- | --- | --- | --- |
| numpy, SciPy, matplotlib | everything so far | BSD / PSF | 229 MB with Python | ✅ |
| pandas | import, tables in the console, needed by statsmodels and lifelines | BSD | +60 MB | 0.1.1 (import) |
| openpyxl | Excel import and export | MIT | +5 MB | 0.1.1 |
| statsmodels | ANOVA (RM, two-way, mixed), regression, power, multiple comparisons | BSD | +40 MB | 0.2 |
| scikit-posthocs | Dunn and other post-hoc tests | MIT | +1 MB | 0.2 |
| lmfit | nonlinear curve fitting with parameters, bounds, global fits, CIs | BSD | +3 MB | 0.3 |
| lifelines | survival analysis | MIT | +5 MB | 0.5 |
| pybaselines | spectra baselines | BSD | +3 MB | 0.6 |
| python-pptx, python-docx | PowerPoint and Word export | MIT | +5 MB | 0.7 |

- Total about 350 MB installed, a download of about 90 MB **once** (the runtime pack), then about 4 MB per update.
- Left out on purpose: **pingouin** (GPL licence, cannot ship inside an MIT app), **scikit-learn** (large; PCA and clustering are easy with numpy/SciPy), **seaborn** (we draw with matplotlib directly, in our own style).

## 6. Architecture changes

- **Results** become a third kind of item: `Analysis { id, kind, input table, data sets, options }` in `crates/core` (Rust stores settings only), computed by `py/datum/analyses/*.py` and cached by revision. Graphs can draw from a table or from a result (fitted curves, brackets).
- **Python package layout** grows into modules: `stats.py`, `tests_group.py` (t-tests, ANOVA, post hoc), `fit.py` + `models.py` (lmfit), `survival.py`, `signal.py`, `io.py` (CSV/XLSX/pzfx), `graph/` (one module per graph family), `explain.py` (plain-language text), each with tests against R values.
- **Element geometry** (for E2–E4): matplotlib returns the bounding box of every artist with an id (`axis.x.title`, `set.1.points`, `legend`), so the window can select, drag and edit.
- **Runtime pack** (I1): `runtime.json` + the updater change in `update.rs`; `py.rs` looks for the runtime in the data folder first.

## 7. Release plan

| Version | Theme | Contents (IDs) | Size |
| --- | --- | --- | --- |
| **0.1.1** | Fix and speed | G2 Copy Picture, I1 small updates (runtime pack), I2 timeout/restart, I5 faster start, A12 CSV/XLSX import, Format Graph pane tidy, fit-to-window zoom | small |
| **0.2.0** | Compare groups | A2 Column table, A15–A18, B1–B8, C1–C7 + C9, D2–D4, D13, D14, D16, E7, G4, G6, J2–J3 | big |
| **0.3.0** | Curve fitting and regression | B9–B14, C8, D5, I3 | big |
| **0.4.0** | Two factors, interactive graphs, layouts | A3, A4, A6, A13, B15–B18, D6–D8, D10, D15, E2–E4, E6, F1–F2, G3 | big |
| **0.5.0** | Survival, nested, many variables | A5, A7, A8, B19–B23, D9, D10 | medium |
| **0.6.0** | Origin power | A9–A11, A14, B24–B26, D11, D12, D17, E5, F3, I6 | big |
| **0.7.0** | Python scripting and automation | H1–H5, G5 | medium |
| **1.0.0** | Stable | J4, user guide, polishing | — |

Each big release can go out in betas (0.2.0-beta.1, …) through the opt-in beta channel, so you can review step by step.

## 8. Ideas that set Datum Plot apart

1. **One click from data to paper**: table → analysis chosen by the test chooser → graph with brackets → methods and legend text → layout → PDF/TIFF at journal size.
2. **Explain everything**: every result says in plain words what it means and whether its assumptions hold.
3. **Reproducible**: every result can show the Python code that reproduces it; every statistic is validated against R.
4. **Python when you want it**: a console and your own analyses, without leaving the app or installing anything.
5. **Small updates, fast app**: a 4 MB update and a graph redraw in ~15 ms.

## 9. Questions for you

1. **Order:** after 0.1.1, which first: **0.2 compare groups** (t-tests, ANOVA, column graphs, brackets — Prism's core) or **0.3 curve fitting** (dose-response, standard curves, kinetics)? What do you use most?
2. **Your field** (or your users'): biology/pharma, chemistry, engineering, physics? This decides the samples and the order of the Origin features.
3. **0.1.1 scope:** OK as listed (Copy Picture, small updates with the runtime pack, CSV/XLSX import, timeouts, faster start)?
4. **Libraries and size:** OK to add pandas, openpyxl, statsmodels, scikit-posthocs, lmfit, lifelines (about 350 MB installed, about 90 MB once, then about 4 MB per update)?
5. **Results:** Prism-style results sheets with tabs plus the Explain panel (my proposal)?
6. **P values:** default Prism GP style (ns, *, **, ***, ****) or APA (*, **, ***)?
7. **Python console (H1):** important to you early, or fine in 0.7?
8. **Interactive graph editing (E2–E4: click, drag, edit in place):** keep in 0.4, or earlier?
9. **Prism import (`.pzfx`):** do you have Prism files to move over? Then it can come earlier.
10. Anything missing from the catalogue that you use in Prism or Origin every day?

---

## 10. Answers (session 3, 24 Oct 2026) and the new order

The user answered in one message: no Prism files; nothing missing from the catalogue; their background is **materials science R&D (now project management)**, with a lot of **linear regression and statistical analysis of many data points**. "Build the app first: lay out the whole UI with every feature in place, then build feature by feature, so it is easier to see and understand." The other questions were left to us; decided as follows.

| # | Question | Decision |
| --- | --- | --- |
| 1 | Order | **Statistics and regression first (0.2)**, comparing groups second (0.3) — the user's own work is regression-heavy. |
| 2 | Field | Materials science and engineering first: samples for tensile tests, Arrhenius plots, calibration lines, XRD/spectra (J2, B24). |
| 3 | 0.1.1 scope | As proposed, **plus the full UI laid out**: every catalogue feature reachable now, planned ones dimmed and explaining when they come. |
| 4 | Libraries | Yes; each one is added in the release that first needs it (openpyxl in 0.1.1; statsmodels and lmfit in 0.2; …). |
| 5 | Results | Prism-style results sheets with tabs plus the Explain panel. |
| 6 | P values | **Exact P values with APA stars** by default (engineering and materials journals); Prism GP and others as options. |
| 7 | Python console | 0.7. |
| 8 | Graph editing | 0.4. |
| 9 | `.pzfx` | No Prism files: moved to 0.6. |
| 10 | Missing | Nothing. |

### Release order (replaces §7)

| Version | Theme | Catalogue IDs |
| --- | --- | --- |
| **0.1.1** ✅ | Fixes, fast updates, import, full layout | A12, G2, I1, I2; galleries, Roadmap, planned commands |
| **0.2.0** | Statistics and regression | A15–A18, B1–B3, B9–B14, C1–C9, D4, D5, D13, D14, D16, G4, G6, I3, J2, J3 |
| 0.3.0 | Compare groups | A2, B4–B8, D2, D3, E7 |
| 0.4.0 | Two factors, interactive graphs, layouts | A3, A4, A6, B15–B18, D6–D8, D10, D15, E2–E4, E6, F1, F2, G3 |
| 0.5.0 | Survival, nested, many variables | A5, A7, A8, B19–B23, D9 |
| 0.6.0 | Origin power | A9–A11, A13, A14, B24–B26, D11, D12, D17, E5, F3, I6 |
| 0.7.0 | Python scripting and automation | H1–H5, G5 |
| 1.0.0 | Stable | J4 |


## 11. Big builds (session 7, 25 Oct 2026)

After 0.2.0 the user asked for bigger releases: "complete the application with all the pending… build around 10 to 15 features at a time", then "complete 0.2.1 and 0.2.2 together, as one version". Meanwhile 0.2.1 shipped "? help beside the tools" (J5) from another session, so the big build is **0.2.2** and the numbers stay consecutive.

| Release | Theme | Features |
| --- | --- | --- |
| **0.2.2** ✅ | Statistics and regression complete, compare groups, materials, styles, export | A2, A15, A17, A18, B4–B8, B12, B14, B16, B23, B27, B29, C4, D2, D3, D4, D13, D14, D16, E7, G4, G6, I3, J2, J3 (28) |
| 0.2.3 | Two factors and counts | A3, A4, A6, B15, B17, B18, D6, D7, D8, D10 |
| 0.2.4 | Interactive graphs and layouts | D12, D15, E2, E3, E4, E6, F1, F2, G3 |
| 0.2.5 | Survival, nested, many variables | A5, A7, A8, B19, B20, B21, B22, D9 |
| 0.2.6 | Origin power | A9, A10, A11, B24, B25, B26, B30, B31, D11, D17, E5 |
| 0.2.7 | Python scripting and automation | A13, A14, F3, G5, H1–H5 |
| 1.0 | Stable | I6, J4 |


## 12. Small steps (session 8, 27 Oct 2026)

The user: "this is a very big gap and we are short of tokens… break it into very small steps, many small versions, and complete as much as possible this week." The 49 remaining features, one to four per release (replaces the groups in §11 after 0.2.2):

| Release | Features |
| --- | --- |
| **0.2.3** ✅ | Grouped table (A3), two-way ANOVA (B15), grouped bars and heat map (D6) |
| **0.2.4** ✅ | Contingency table (A4), chi-square and Fisher (B17) |
| **0.2.5** ✅ | Parts of whole (A6), pie and donut (D7) |
| **0.2.6** ✅ | ROC and Bland-Altman (B18), special graphs (D10: Bland-Altman, ROC, forest; volcano and bubble later) |
| **0.2.7** ✅ | Axis breaks and a second Y axis (D8) |
| **0.2.8** ✅ | Annotations (D15) |
| **0.2.9** ✅ | Select, drag and edit (E2, E3), zoom and pan (E4), exclude from the graph (E6) |
| **0.2.10** ✅ | Users' requests (session 8): new tables open at once, Remove Data Set, Significance offers t-test/ANOVA/nonparametric, empty data sets left out, X axis breaks |
| **0.2.11** ✅ | Layouts (F1), journal figures (F2), TIFF for journals (G3) |
| **0.2.12** ✅ | Multi-panel figures (D12) |
| **0.2.13** ✅ | Security: `zip` 2 → 9.1.3 (RUSTSEC-2026-0367/0368/0369), `deny.toml` and the cargo-deny CI job (FAMILY §11), reported by Datum Sim |
| **0.2.14** ✅ | Many variables (A7), multiple, logistic and Poisson regression (B21) |
| **0.2.15** ✅ | PCA and clustering (B22) |
| 0.2.16 | Survival table (A5), analysis (B19), curves (D9) |
| 0.2.17 | Nested table (A8) and tests (B20) |
| 0.2.18 | Peaks (B24), signal processing (B25) |
| 0.2.19 | DSC/TGA (B31), S–N curves (B30) |
| 0.2.20 | Worksheet (A9), column formulas (A11) |
| 0.2.21 | Matrix (A10), 3D/contour/polar (D11), surface fits (B26) |
| 0.2.22 | Large data (D17), region tools (E5) |
| 0.2.23 | Prism import (A13), instrument import (A14) |
| 0.2.24 | PowerPoint and Word (G5), posters (F3) |
| 0.2.25 | Python console (H1), own analyses (H2) |
| 0.2.26 | Templates (H3), batch (H4), notebooks (H5) |
| 1.0 | Signed installer (I6, needs a code-signing certificate from the user), validation report (J4) |
