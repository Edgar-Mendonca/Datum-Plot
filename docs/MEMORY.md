# Datum Plot: project memory

> **Paste this file at the start of each new session**, or just open the repo: `CLAUDE.md` tells Claude to read it.
> It records what exists, why, and what comes next. Update it at the end of every session.

| | |
| --- | --- |
| **Product** | Datum Plot: a Windows desktop app for scientific graphs, statistics and curve fitting, combining GraphPad Prism (guided tables → analyses → graphs, linked live) and OriginPro (workbooks, many graph types, analysis power) |
| **Family** | Second Datum app after Datum Plan (`Edgar-Mendonca/Datum-Plan`). Design and workflow: [Datum-Plan/docs/FAMILY.md](https://github.com/Edgar-Mendonca/Datum-Plan/blob/HEAD/docs/FAMILY.md). Plan's code is the reference implementation: copy, don't reinvent. |
| **Current version** | **0.2.2** (released 2026-10-25: https://github.com/Edgar-Mendonca/Datum-Plot/releases/tag/v0.2.2; installer 113 MB; the big build: compare groups, materials, data tools, styles, export; 28 features). Earlier: 0.1.0, 0.1.1, 0.2.0 (installer 113 MB), 0.2.1 (? help beside the tools) |
| **Repo** | `Edgar-Mendonca/Datum-Plot` · working branch `claude/epic-mayer-6faugf` |
| **Identity** | Accent **Teal** (`--blue #0E8C7F`, `--blue2 #0B7468`, `--sky #8FD3C9`, `--pale #E3F5F2`, `--sel #D3EFEA`, `--sel2 #A9DDD4`, `--accent2 #3FC2B2`; dark `--blue #3FC2B2`, File sidebar dark `#0A4A44`) · files `.dplot` · identifier `com.edgarmendonca.datumplot` · installer `DatumPlot-x.y.z-setup.exe` · logo `docs/brand/datum-plot-icon.svg` = `ui/public/logo.svg` (teal axes, tint points, fitted curve, amber `#F2B233` diamond) |
| **Stack** | Rust shell (`src-tauri`) + Rust project engine (`crates/core`), Tauri 2, WebView2, SolidJS + Vite UI in strict TypeScript, plain CSS tokens, IBM Plex. **Python worker** (`py/`) with numpy, SciPy and matplotlib for every calculation and every graph; the installer bundles embeddable CPython 3.13. |
| **Code size** | About 7,750 lines (0.2.2): core 1,200 (with 15 tests), shell 1,020, Python 2,380 (+ 480 lines of tests, 41 tests), UI 3,160 TSX/TS + CSS, UI tests 280 (54 checks) |
| **Installer** | NSIS `.exe`, per-user, with Python inside: **55 MB** download (0.1.0); the bundled Python folder is 229 MB installed (embeddable CPython 3.13.17, numpy 2.5.4, SciPy 1.18.1, matplotlib 3.11.2). UI bundle 129 kB JS (43 kB gzip). |

---

## 1. Architecture

```mermaid
flowchart LR
  subgraph UI["Window (WebView2) · ui/src/*.tsx → Vite → ui/dist"]
    Store[store.ts: project, open item, act(op)]
    Nav[nav.tsx: sidebar · navigator · Info · empty pages]
    Table[datatable.tsx: XY grid on the family grid engine]
    Graph[graph.tsx: engine SVG + hover, double-click hits]
    Fmt[format.tsx: Format Graph, docked]
    BS[ribbon.tsx · backstage.tsx · print.tsx · dialogs.tsx]
  end
  subgraph Shell["src-tauri (Rust)"]
    Cmd[main.rs: state · apply · new_table · history · new_project · open · save<br/>render · export_graph · graph_png · engine · options · recovery · open_url]
    Py[py.rs: two Python workers (Engine draws, Calc calculates), JSON lines, restart, caches]
    Upd[update.rs: REPO = Edgar-Mendonca/Datum-Plot]
  end
  subgraph Core["crates/core (pure Rust, 11 tests)"]
    Model[model.rs: Project · Info · Table · DataSet · Graph · GraphSettings]
    Doc[doc.rs: Op · undo/redo · .dplot · number parsing]
    Tpl[templates.rs: blank + 8 samples]
  end
  subgraph Python["py/ (numpy · SciPy · matplotlib, 12 tests)"]
    W[worker.py: ping · render · export · analyze · models · read · excel · summary]
    An[datum/analysis.py · groups.py · tools.py: every analysis]
    St[datum/stats.py: N, mean, SD, SEM, 95% CI, range]
    Gr[datum/graph.py: Prism-style matplotlib figure → SVG + geometry, exports]
  end
  UI -- "invoke(cmd, args)" --> Cmd
  Cmd --> Doc --> Model
  Cmd --> Py -- "stdin/stdout JSON" --> W --> St & Gr
```

**Rules:**
- The window never calculates. Every edit is an `Op` that the Rust core applies to a copy, normalises and keeps only if it changed something (undo/redo of whole projects, 200 steps). Statistics and drawing are done in Python.
- **Live chain** (Prism): graphs store only settings and their table's id; the shell sends `{table, graph settings}` to Python on every render (cached by request in `py.rs`), so editing a value redraws its graphs. `.dplot` stores data and settings, never results.
- Graphs: matplotlib draws the SVG the window shows (`svg.fonttype = none`, so text stays text) and every export. Python returns the plot area, axis limits, log flags, legend box and the points so the window can show values under the mouse and open the right Format Graph page on a double-click. Print uses the same SVG.
- JSON keys are camelCase everywhere (Rust `serde(rename_all = "camelCase")`, TypeScript, Python).
- Every statistic has a unit test against a value from R (later NIST StRD for regressions).

### Files
| Path | What it does |
| --- | --- |
| `crates/core/src/model.rs` | Format 1. `Project` (name, `info`, `tables`, `graphs`, `analyses`, `nextId`, `ui`), `Analysis` (id, table, name, kind, sets, options JSON), `GraphSettings.overlays` (analysis ids drawn on the graph: curves, or brackets on column graphs), `GraphSettings.column` (scatter/bars/box/violin/mean/paired), `GraphSettings.palette` (scheme name or "#hex, …"), `Info`, `Table` (`kind` "xy" or "column"; a column table keeps the X column but never uses or shows it; `Table::column(n)`; X column + `sets`; `cols` is the flat column list, column 0 = X; `rows`, `rowTitles`, `excluded` [row, col], `style` "r:c" → style string), `DataSet` (`entry` rep/msn/mesn, `reps`), `Graph` + `GraphSettings` (error, errorDir, points, line, cap, width/height mm, font, fontSize, boldTitles, style prism/frame, title, legend, `x`/`y` `Axis`, `sets` `SetStyle`). `normalize`, `add_table`, `from_json` (refuses newer formats). |
| `crates/core/src/doc.rs` | `Op`: NewTable, Delete, Rename, Duplicate, Cells (col −1 = row title), Import (rows → new table + graph; titles from the first row; sets of `reps`), AddAnalysis (overlay → drawn on the table's graphs, joining lines off), SetAnalysis, Overlay, Sort (rows by a column, empty last, titles/exclusions/styles move), CopyLook (look of one graph onto others, keeping titles, axis titles and ranges, overlays, line), Paste (first row of words = titles; grows rows and data sets), Exclude, TableSet, SetDef (add/replace/remove a data set, remapping columns, exclusions and styles), Rows (insert/delete, remapping), Style, AddGraph, GraphSet, Info, ProjectName, Ui, Batch. `number()` parses 1,234.5 / −4 / 12% / 1e-3. |
| `crates/core/src/templates.rs` | Blank XY, Growth curve, Standard curve (mean/SD/N), Dose-response (log X), Tensile test (modulus fit 0–0.003 + tensile analysis), Arrhenius (activation energy, log Y), Compare groups (column table, ANOVA + Tukey brackets), Weibull strength (column table, box plot, Weibull analysis), DSC peak (area above a straight baseline); `list()` gives tile pictures (column tables: the group means). |
| `crates/core/examples/dump.rs` | Fixture for the UI tests. |
| `src-tauri/src/main.rs` | Commands in the diagram plus `result` (an analysis via the Calc engine, cached), `models`, `export_all` (folder picker, every graph, unique file names), `export_excel` (save dialog → Python `excel`), `new_table(kind)` (column tables), graph requests carry `overlays`; `copy_graph` (PNG → Windows clipboard via `tauri-plugin-clipboard-manager`), `copy_text`, `read_clipboard`, `import_file`, `restart_engine`; `Options` (theme, autosave, beta, openLast, decimals, reps, entry, error, width, height, font, fontSize, style, dpi, paper, landscape, company, logo, `styles` = saved graph styles); `new_project` keeps a sample graph's x, y, line, error, overlays, points, column, sets, palette; new tables/graphs follow the options; recovery; recent files; `open_url` only for this repo. |
| `src-tauri/src/py.rs` | Finds Python (`DATUM_PYTHON`, the runtime pack, else `python`/`python3`); a reader thread lets requests time out (start 180 s, request 60 s → kill and report); `restart()`; and `py/worker.py` (bundled or the source tree), `MPLCONFIGDIR` in the app cache, `CREATE_NO_WINDOW`, restart once on failure, cache of the last 24 requests. **Two workers** (I3): `Engine` draws graphs, `Calc` runs results, models and Excel export, so a long fit never holds up drawing; both start in a thread at launch (Calc after Engine is ready); Restart Engine restarts both; emits `engine` with versions or the error. |
| `src-tauri/src/update.rs` | Datum Plan's updater with `REPO = Edgar-Mendonca/Datum-Plot`; downloads the release's `-setup.exe`; `download()` (progress + SHA-256). |
| `src-tauri/src/runtime.rs` | The Python runtime pack: `%LOCALAPPDATA%/com.edgarmendonca.datumplot/runtime/N` (N = `py/runtime.txt`); unpacked from `resources/runtime.zip` (in every installer); unzips with progress (`engine` status event), removes older runtimes, the zip and 0.1.0's `resources/python`. Release Windows builds only; dev builds use the PATH Python. 1 test. |
| `src-tauri/tauri.conf.json`, `tauri.release.conf.json` | Bundles `py/worker.py` and `py/datum/*.py`; the release config adds `runtime.zip`. |
| `py/runtime.txt` | The runtime pack number: **bump it whenever `py/requirements.txt` changes**, so installed apps download the new pack. |
| `py/datum/analysis.py` | Analyses: `run(kind, table, sets, options)` → {title, answer, tabs of formatted tables, checks, methods, legend, code, plots (small SVGs), curves (for graphs), cells (outliers)}. Kinds: describe, normality (Shapiro, D'Agostino, Anderson-Darling, Lilliefors + QQ), outliers (iterative Grubbs), linear (OLS/WLS via statsmodels, origin, polynomial, Deming with jackknife SEs, fit range, compare lines F tests, runs test, CI/PI bands, interpolation), fit (lmfit ExpressionModel, library or own equation, init/fixed, CIs, AICc, correlations, bands), arrhenius (ln k vs 1/T, Ea, A). `g()` formats numbers, `pv()` APA P values. |
| `py/datum/groups.py` | Compare groups (B4–B8, B16, B23): `column` (values by row, for pairing), `summary` (values, or entered mean/SD/N), `pairs_of`; `ttest` (unpaired Welch/Student from stats, paired, ratio, one-sample; effect sizes; Shapiro and Brown-Forsythe checks), `nonparam` (Mann-Whitney + Hodges-Lehmann, Wilcoxon (approximate with ties, as R), KS, Kruskal-Wallis + Dunn (Bonferroni), Friedman), `anova` (ordinary, Welch/Brown-Forsythe via statsmodels `anova_oneway`, repeated measures with Geisser-Greenhouse; posthoc Tukey (`scipy.stats.tukey_hsd`), Dunnett (`scipy.stats.dunnett`), Holm-Šidák, Šidák, Bonferroni, LSD; trend; η², ω²), `correlation` (Pearson + Fisher-z CI, Spearman, Kendall, matrix), `power` (statsmodels power solvers, curve). Results carry `brackets` [set, set, P]. |
| `py/datum/tools.py` | Data tools and materials (A15, A18, D4, B14, B27, B29): `transform` (X/Y functions, baseline, normalise, replicates → mean/SD/N), `check`, `frequency` (common bins, histogram/QQ/ECDF plots), `auc` (trapezoid, baselines incl. a straight line, peaks; curves with `fill`), `smooth` (Savitzky-Golay, LOWESS, moving average; derivatives, cumulative integral), `tensile` (per specimen: modulus by least squares in a range or 10–40 % of UTS, offset yield, UTS, elongations, toughness; dashed offset line), `weibull` (MLE with Hessian CIs, median-rank regression, Weibull plot). Results that make tables carry `table` (Results › New table from result → `NewTable`). |
| `py/datum/models.py` | The curve-fit model library (15 models: equation, first guess, description). |
| `py/datum/io.py` | File › Import readers: CSV/TSV/TXT (delimiter sniffing, decimal commas with `;`, encodings) and XLSX (openpyxl, every sheet); all cells as text. `write_excel` (G6): a sheet per table (excluded values blue italic) and per result (title, answer, every table, methods). |
| `py/worker.py` | The protocol loop: warm-up render, `{"ready": true}`, then one answer line per request; stdout reserved for the protocol. |
| `py/datum/stats.py` | `set_columns`, `value`, `describe` (n, mean, SD, SEM, CI via `scipy.stats.t`), `from_summary`, `summarize`. |
| `py/datum/graph.py` | `PALETTES` + `palette()` (schemes, colour maps spread over the sets, own #hex lists), `rc_for` (fonts, Prism or framed axes), `draw_overlays` (fitted curves, dashed lines, shaded areas (`fill`), CI/PI bands, equations in the emptiest corner; brackets on column graphs via `draw_brackets`, stacked), `column_figure` (dots with `swarm`, bars, box, violin, mean, before–after; y from 0), `axes` (shared axis code), `figure` (means ± error bars or each replicate, lines, log axes, ranges, ticks, grid, legend, title), `geometry`, `render` (SVG + geometry + points), `export` (png/svg/pdf/tiff/eps, dpi, transparent; base64 for the clipboard). |
| `py/tests/test_analysis.py` | Linear regression vs R `lm()` on Anscombe's data; NIST StRD Misra1a; model recovery for 6 library models; fixed parameters; Arrhenius Ea; describe; Shapiro vs R; Grubbs cells; compare lines; interpolation; Deming; replicates. |
| `py/tests/test_groups.py` | 0.2.2 analyses vs R: Welch/Student/paired t (sleep), from mean/SD/N, Mann-Whitney, Wilcoxon, Kruskal-Wallis, ANOVA + Tukey (PlantGrowth), every ANOVA variant, Pearson CI (Anscombe), power.t.test; transforms, AUC, derivative/integral, tensile on an ideal curve, Weibull recovery, frequency, checks, global fit, every column graph with brackets and palettes. |
| `py/tests/test_engine.py` | Statistics vs R, exclusions, mean/SD/N entry, renders, log axes, every export format, the worker protocol. |
| `py/requirements.txt` | numpy 2.5.4, scipy 1.18.1, matplotlib 3.11.2, openpyxl 3.1.5, statsmodels 0.15.0, lmfit 1.3.4 (pinned; runtime 2). |
| `ui/index.html` | Root and the icon sprite (Plan's ~90 icons recoloured teal + Plot icons: xy, graph, sheet, results, layout, infosheet, err, axis, log, legend, symbol, image, addset, addrow, delrow, exclude, sigma, curve, size, line, frame). |
| `ui/src/api.ts` | Types matching the Rust JSON, `Render`, `spans`/`width`/`letter`/`num`. |
| `ui/src/store.ts` | Signals: `out`, `item` {section, id}, `backstage`, `tab`, `navOpen`, `engine`, options, theme; `act`, `call`, `loadOut`, `open`; menus, dialogs, toasts. |
| `ui/src/tools.tsx` | Sort, Find (Ctrl+F; `goto` signal selects the cell), Exclude Rows by a rule, Test Chooser (questions → kind + preset), Statistics Guide, `STYLES` + `applyStyle`/`saveStyle`/`styleMenu` (D13), `PALETTES` + colour-blind preview (Machado matrices) `paletteDialog` (D16), `copyLook` (D14), `exportAll` (G4), `exportExcel` (G6), `significance` (D3). |
| `ui/src/datatable.tsx` | The XY or column grid (column tables hide the X column: width 0, skipped by the cursor) (selection column 0 = row title, k ≥ 1 = grid column k − 1): two-row headings by data set, typing, ranges, TSV copy/cut/paste (→ `Paste` op), fill handle + Ctrl+D/R, Paste Special, Ctrl+B/I/U, Ctrl+E exclude, context menu (insert/delete rows, format/add data set); `TableHead` (titles and units); `setDialog`, `addSet`, `rename`. |
| `ui/src/graph.tsx` | `useRender`, `GraphView` (zoom, crosshair, hover values, double-click → Format Graph page, context menu, Ctrl+C), `copyGraph` (PNG to the clipboard), `exportGraph` dialog, `newGraph`. |
| `ui/src/format.tsx` | Format Graph (docked right, changes apply at once): Data Sets, X Axis, Y Axis, Graph; `SIZES` (journal widths), `FONTS`, `ERRORS`, `OKABE_ITO`. |
| `ui/src/ribbon.tsx` | Title bar, Tell Me, ribbon: Data · Analyze · Graph · Layout · Tools · View · Help + contextual Graph Tools › Format; Plan's `B`/`G`/`S`, Font group and `fitRibbon`; `N` = a planned command (dimmed, amber dot, opens `soon(id)`). |
| `ui/src/backstage.tsx` | File page: Home (samples with mini graphs, recent, updates card with engine versions), Export tiles, Options (General, Start-up and saving, New data tables, New graphs, Printing and branding, Updates), Print, Updates. |
| `ui/src/print.tsx` | File › Print: graph pages at real size or fitted, with caption; data table and Info sheet as flowing pages; header/footer codes (&[Page], &[Pages], &[Date], &[Project], &[Item], &[Title], &[Researcher], &[Company], &[Logo]); saved in `project.ui.page`. |
| `ui/src/nav.tsx` | Sidebar (Info first, then Data, Results, Graphs, Layouts), navigator tree with context menus, graph thumbnails (E7, View › Thumbnails, `useRender` per graph), Info sheet, Results and Layouts empty pages. |
| `ui/src/dialogs.tsx` | Paste Special, Getting Started (for Prism and Origin users), Glossary, Shortcuts, save-before-close. |
| `ui/src/features.ts` | **The feature catalogue in the app** (99 entries: id, name, release, description, library), `VERSION_NOW`, `RELEASES`, `AREAS`, `ready()`. Mirrors PLAN-0.2 §4 with the §10 order; update it when a feature ships. |
| `ui/src/results.tsx` | `KINDS` (18 kinds; third field true = curves, "brackets" = column graphs only), `draws(kind, table)`, `BY_ID` (catalogue id → analysis; B14s = smoothing), "New table from result", `analysisDialog` (data sets + options per kind; models from Python), `ResultsView` (tabs, tables with Copy, plots, Explain panel: answer, checks, methods, legend, Python code; Exclude outliers; show/hide on each graph), `ResultsPage`. |
| `ui/src/roadmap.tsx` | `soon(id)` card for planned commands, `RoadmapPage` (File › Roadmap, Help › Roadmap), galleries `newTable`, `analyze`, `graphTypes` (categories · items · details), `importFile` dialog (sheet, headings, X column, replicates guessed from gaps in the titles, preview) → `Import` op. |
| `ui/src/help.tsx` | "?" help: the `HELP` table (`{ t, what, how?, tip? }` per topic), `<Help k>` (the small ? button, `.help`), `helpCard(k)` (the card dialog, `.helpcard`). Ribbon groups take `h=` on `G`, navigator heads `h=` on `Head`, dialogs and galleries `help=`. Help › What Is This Tool? lists every topic. |
| `ui/src/selection.ts`, `cells.ts`, `fmt.ts`, `ui.tsx` | Copied from Datum Plan (grid engine, TSV and series, formatting, building blocks; `Dialog` has a docked `side` mode). |
| `tests_ui/run.cjs` | Playwright: 54 checks (0.2.2 adds: global fit and second model in Curve Fit, Tensile Test op, Test Chooser → ANOVA → no brackets on XY, Sort op, New Table › Column, Styles › Nature, Colour Schemes preview and palette op, thumbnails); earlier: 31 checks (since 0.1.1 also: planned commands and their cards, Analyze gallery, Import dialog → `Import` op, Copy Picture → `copy_graph`, Roadmap list and search, every tab fits at 1280/1600 px) against `ui/dist` with the dump fixture and a **real Python render** of the sample graph (Home, opening a sample, Format Graph from a double-click, log scale op, docked dialog, hover values, heading alignment, typing, ranges, Count, Ctrl+E, paste, ribbon fit at 1280/1600, Analyze, Info, Print, Options, no script errors). |
| `.github/workflows/ci.yml` | ubuntu: Python deps + `unittest`, `check:ui`, build, clippy `-D warnings`, `cargo test`, UI tests. |
| `.github/workflows/release.yml` | windows: runtime pack in `rt/` (newest embeddable CPython 3.13 + requirements, pruned, compiled, ping smoke test) zipped to `src-tauri/runtime.zip`; one build with `tauri.release.conf.json` → `DatumPlot-x.y.z-setup.exe` + SHA256SUMS; notes from CHANGELOG. |

### Update flow (same as Plan)
On start and on "Check again": GET `/repos/Edgar-Mendonca/Datum-Plot/releases/latest` (or `/releases` with beta) → badge + Home card with the CHANGELOG section → Update now downloads `DatumPlot-x.y.z-setup.exe`, checks `SHA256SUMS.txt`, runs it with `/S`, restarts. Install only from this repo's release URLs.

### Release flow (same as Plan)
Bump `src-tauri/Cargo.toml` + `crates/core/Cargo.toml` → CHANGELOG `## x.y.z — date` → update this file → commit + push → `release.yml` (tag push, or workflow_dispatch when tags are blocked) → GitHub Release with setup.exe + SHA256SUMS.txt → users click Update now.

### How we work (from Datum Plan, FAMILY §11)
1. **The user reviews the last release** in the app and sends screenshots with bugs and wishes.
2. **Diagnose first.** Reproduce the problem in the test harness or the real app before changing code. Small fixes go straight to a release.
3. **Bigger asks get a plan file** (`docs/PLAN-x.y.md`): feedback, diagnosis, proposal, size, questions. Logged here and pushed. Build only after the user answers.
4. **Build in small steps**: the model and its op in `crates/core` (Rust test), the numbers or drawing in `py/datum` (Python test against R/NIST values), then the UI. Compact code in the surrounding style.
5. **Check in the real app** under Xvfb (`scratchpad/app.sh` restarts Xvfb and the debug app; drive it with `xdotool`, screenshot with `import -window root`). The app window sits at (80, 50) on the 1600×1000 screen. Fix what looks wrong.
6. **Add a UI test** for every reported bug and new feature (`tests_ui/run.cjs`). Make it fail on the old code where possible.
7. **Run the checks:** `python -m unittest discover -s py/tests`, clippy `-D warnings`, `cargo test --workspace`, `npm run check:ui`, `npm run test:ui`.
8. **Release:** bump, CHANGELOG (becomes the in-app "What's new"), update this file, commit, push, run `release.yml`, watch CI + Release, confirm the installer and its size.
9. **Report to the user** in plain language: what changed, what was checked, what is not done, what to check on Windows.

---

## 2. Decisions

| Date | Decision | Why |
| --- | --- | --- |
| 2026-10-24 | Name **Datum Plot**, `.dplot`, `com.edgarmendonca.datumplot`, Teal accent, releases from `Edgar-Mendonca/Datum-Plot` | The user's choice, per FAMILY.md §1 and §3. |
| 2026-10-24 | Same stack, look, updater, release and workflow as Datum Plan; copy Plan's code | FAMILY.md: one design and one way of working; only the accent and glyph change. |
| 2026-10-24 | Brainstorm and `PLAN-0.1.md` first; 0.1.0 = shell, updater, Home, XY table, XY graph | The user's instruction and FAMILY §12. The updater works from day one. |
| 2026-10-24 | **Python is built in** (numpy, SciPy, matplotlib), replacing the plan's Rust statistics and own SVG engine; Rust is the shell and project engine, SolidJS the window | The user's decision after the brainstorm: the Python libraries solve most problems and a 200–300 MB app is fine (like the Compressor Engineering Suite). See PLAN-0.1 §9. FAMILY §2 "no Python" is overridden for Datum Plot only. |
| 2026-10-24 | One long-running Python worker over JSON lines (not PyO3, not a process per request) | No Python ABI ties in the Rust build, a crash cannot take the window down, and imports (about 1 s) are paid once. |
| 2026-10-24 | Bundle the official **embeddable CPython 3.13** + pinned wheels in the installer (`tauri.release.conf.json`); dev builds use the system Python | Reproducible, no user install; the embeddable zip is the smallest official runtime. |
| 2026-10-24 | matplotlib draws both the on-screen graph (SVG, text as text) and every export; the window gets geometry back for hover and hit-testing | One renderer, so what you see is what you export; publication-quality vector output for free. |
| 2026-10-24 | Rust core keeps the project model, ops, undo, files and validation; no numerics in Rust | Python owns calculation; Rust owns the document. |
| 2026-10-24 | The 0.1.0 navigator is the family icon rail **plus** a Prism-style list; Info is the first sidebar item (Plan's Setup) | The user approved the plan's proposal (question 3) by approving the plan. |
| 2026-10-24 | Ribbon tabs Data · Analyze · Graph · View · Help + contextual Graph Tools › Format; Analyze shows what arrives when | No "Home" tab (rejected in Plan); honest empty states (FAMILY §7). |
| 2026-10-24 | Default graph look is Prism's (open axes, ticks out, bold titles, Arial 10 pt, 80 × 60 mm, Y from zero); framed (Origin) is one click | Most likely users are Prism users; both looks available (question 6 still open). |
| 2026-10-24 | Format Graph is docked on the right and applies each change immediately (each is an undo step) | The graph stays visible, as in Prism's live formatting. |
| 2026-10-24 | Excluded values: blue italic, struck through; stored as [row, col] in the table | Prism's convention, plus a strike so it reads in greyscale. |
| Session 2 | Brainstorm the full feature set first (catalogue A–J with IDs and releases in PLAN-0.2), then build release by release | The user wants to see what Datum Plot will do before evaluating more. |
| 0.1.1 | Python runtime as a numbered pack unpacked to the user's data folder (`runtime/N`); bump `py/runtime.txt` when requirements change | Starts stay fast; Python is unpacked only when its libraries change. |
| Session 4 | **One installer per release** (`-setup.exe` with `runtime.zip` inside) for installs and updates; no update-only installer, no separate runtime download | The user: separate files confuse people; the 87 MB in-app update was quick and fine. |
| Session 4 | Materials ideas B27–B31 added to the catalogue | The user's background. |
| Session 5 | **Small consecutive releases** (0.2.0, 0.2.1, 0.2.2 … up to 0.3, no jumped numbers); 0.2.0 = results + statistics + linear regression + curve fitting + Arrhenius; order in PLAN-0.2.0 §9 | The user: quick small updates are easier to check and use fewer tokens. |
| Session 5 | Equation and R² on the graph by default; regression uses every replicate by default; Summary + Details tabs | The user left these to us. |
| 0.1.1 | Clipboard writes and reads go through Rust (`tauri-plugin-clipboard-manager`), never `navigator.clipboard` | WebView2 blocks the browser clipboard on `http://tauri.localhost` (Copy Picture failed on Windows). |
| Session 3 | Libraries are added in the release that first needs them (openpyxl 0.1.1; statsmodels, lmfit 0.2; scikit-posthocs 0.3; lifelines 0.5; pybaselines 0.6; python-pptx/docx 0.7); no pingouin (GPL), no scikit-learn, no seaborn | The user agreed to the libraries; keep the pack small until needed; licences fit an MIT app. |
| Session 3 | **Lay out the whole UI first**: every catalogue feature has its place now (ribbon, galleries, navigator, Roadmap); planned ones are dimmed and explain what and when; then build feature by feature | The user: "build the app first… then feature by feature; much easier to see and understand the issues." |
| Session 3 | Release order: 0.2 statistics and regression, then 0.3 compare groups | The user's work (materials science R&D) is regression-heavy. |
| Session 3 | Exact P values with APA stars by default; Prism-style results sheets + Explain panel; Python console in 0.7; graph editing in 0.4; `.pzfx` in 0.6 | The user left these to us; no Prism files. |
| 0.2.1 | **? help beside the tools in every Datum app**: a small ? beside each ribbon group, panel and main dialog opens a card (what it is for, how to use it) from one `HELP` table in `ui/src/help.tsx`; Help › What Is This Tool? lists them all; no separate teaching mode. Help shipped as its own release (0.2.1) and the planned 0.2.1–0.2.5 moved up one number, so releases stay consecutive | The user's words: "at some of the tools, we can add a small question mark icon… we should do it in all of our applications." Built first in Datum Atlas 0.1.1; same code and styles in every app. |
| Session 7 | **Big builds**: after 0.2.0 worked well the user asked to "complete the application with all the pending… 10 to 15 features at a time", then to build the planned 0.2.1 and 0.2.2 groups as one version. The 28 features became **0.2.2** (0.2.1 had shipped ? help meanwhile); the rest regrouped into 0.2.3–0.2.7 and 1.0 (PLAN-0.2 §11). Numbers stay consecutive | The user: one big update at a time is fine now; optimise as we go. |
| Session 7 | **Column table** = `Table.kind = "column"`, same model (X column kept, hidden in the UI, unused by Python); each group a data set with `reps` 1 (or mean/SD/N) | No new table code in Rust; every op (paste, sort, exclude, sets) works unchanged. |
| Session 7 | Significance brackets are analysis overlays: t-test, nonparametric and ANOVA results carry `brackets`; drawn only on column graphs (`draws()`); options brackets sig/all/none and stars/P | Same live chain as fitted curves; nothing stored on the graph. |
| Session 7 | Transforms, histograms and smoothing are analyses whose result can become a table (Results › New table from result), not live linked tables | Keeps the core simple; the analysis itself stays live. |
| Session 7 | Second Python worker (`Calc`) for results and Excel; graphs keep their own | Long fits never block drawing; memory cost ~100 MB. |
| Session 3 | Samples and wording lean to materials science and engineering (tensile tests, Arrhenius plots, calibration lines, spectra) | The user's background. |

---

## 3. Roadmap

✅ done · 🔜 next · ⬜ planned. Small releases; every one goes through the in-app updater. **The full feature catalogue (IDs A1–J4) and the release plan are in [PLAN-0.2.md](PLAN-0.2.md)** (answered in session 3, order in §10); this table is its summary. The same catalogue is in the app: `ui/src/features.ts`, File/Help › Roadmap.

| Version | Theme | Contents (catalogue IDs) | Status |
| --- | --- | --- | --- |
| — | Brainstorm | Comparison, plan, memory, logo ([PLAN-0.1.md](PLAN-0.1.md)) | ✅ |
| **0.1.0** | Shell + XY + Python | Installer with Python, updater, Home with samples, File page, Options, Help, Info sheet, navigator, XY table, XY graph (matplotlib), docked Format Graph, hover values, export PNG/TIFF/SVG/PDF/EPS, Print, `.dplot`, undo, recovery | ✅ |
| — | Feature brainstorm | Catalogue A–J (99 features), Python libraries, fast updates, release plan ([PLAN-0.2.md](PLAN-0.2.md); answers and order in §10) | ✅ |
| **0.1.1** | Fixes, fast updates, import, full layout | Copy Picture through Rust (G2), runtime pack (I1), engine timeout/restart (I2), CSV/TXT/XLSX import (A12); **every catalogue feature laid out**: Roadmap page, galleries (New Table, Analyze, Graph Type), planned commands in every tab incl. new Layout and Tools tabs | ✅ |
| **0.2.0** | Results, statistics, regression, curve fitting ([PLAN-0.2.0.md](PLAN-0.2.0.md) §9) | Results sheets (Summary/Details/Residuals tabs, Explain, methods text, APA P values, copy, Python code, checklist), descriptive statistics, normality, outliers + exclude, linear regression (fit range, origin, polynomial, Deming, compare lines, interpolation), nonlinear fit (lmfit, model library, own equation), Arrhenius, curves + bands + equation on graphs, residual plots; Tensile and Arrhenius samples | ✅ |
| 0.2.1 | Help | A ? beside the tools, panels and dialogs; Help › What Is This Tool? (J5) | ✅ |
| **0.2.2** | Big build: statistics and regression complete, compare groups, materials, styles, export (PLAN-0.2 §11) | Column tables (A2) and column graphs (D2), t-tests (B4), nonparametric (B5), one-way ANOVA (B6) + multiple comparisons (B7) + effect sizes (B8), significance brackets (D3), correlation (B16), power (B23); tensile test (B27), Weibull (B29); global fit + model comparison (B12), area/smoothing/derivatives (B14); transforms (A15), sort/find/exclude rows (A17), data checks (A18), frequency distributions (D4); styles (D13), copy look (D14), colour schemes (D16), thumbnails (E7); export all graphs (G4), Excel workbook (G6); test chooser (C4), statistics guide (J3), samples (J2); second engine (I3) | ✅ |
| 0.2.3 | Two factors and counts | Grouped table (A3), contingency (A4), parts of whole (A6), two/three-way ANOVA (B15), contingency tests (B17), ROC and Bland-Altman (B18), grouped graphs and heat maps (D6), pie/donut (D7), axis breaks and double Y (D8), special graphs (D10) | 🔜 |
| 0.2.4 | Interactive graphs and layouts | Multi-panel (D12), annotations (D15), select/drag/edit on the graph (E2, E3), zoom/pan (E4), exclude from the graph (E6), layouts (F1), journal figures (F2), TIFF for journals (G3) | ⬜ |
| 0.2.5 | Survival, nested, many variables | Survival table (A5), multiple variables (A7), nested (A8), survival analysis (B19), nested tests (B20), multiple/logistic regression (B21), PCA/clustering (B22), survival curves (D9) | ⬜ |
| 0.2.6 | Origin power | Worksheets (A9), matrices (A10), column formulas (A11), peaks (B24), signal processing (B25), surface fits (B26), S–N curves (B30), DSC/TGA (B31), 3D/contour/polar (D11), large data (D17), region tools (E5) | ⬜ |
| 0.2.7 | Python scripting and automation | `.pzfx` import (A13), instrument import (A14), posters (F3), PowerPoint/Word (G5), Python console (H1), own analyses (H2), templates (H3), batch (H4), notebooks (H5) | ⬜ |
| 1.0.0 | Stable | Signed installer (I6), validation report (R/NIST, J4), user guide | ⬜ |

---

## 4. Session log

### 2026-10-24: Session 1 (brainstorm)
- The user started Datum Plot as the second Datum app and asked to follow FAMILY.md exactly, brainstorm, write `docs/PLAN-0.1.md`, and create `CLAUDE.md` and this file before building.
- Read Datum Plan (read-only): FAMILY.md, CLAUDE.md, MEMORY.md, CHANGELOG.md and the reference code (styles, sprite, ribbon, backstage, print, selection/cells/fmt, update.rs, workflows, UI tests) and the draft logo.
- Wrote [PLAN-0.1.md](PLAN-0.1.md): Prism vs Origin, architecture, 15 ideas, 0.1.0 scope, release plan to 1.0, 14 questions.

### 2026-10-24: Session 1, continued (0.1.0)
- The user approved the plan, icon and colours, wants to see the app before answering the questions, and decided **Python goes inside the app** (numpy, SciPy, matplotlib; Rust as the shell, SolidJS as the window; 200–300 MB is fine). Recorded in PLAN-0.1 §9 and the decisions above.
- Built: Rust core (model, ops, undo, files, templates; 11 tests), Python engine (stats, Prism-style matplotlib graphs, exports, worker protocol; 12 tests against R values), shell (commands, Python worker manager with cache and restart, updater, recovery), UI (navigator, XY grid on Plan's grid engine, graph view with hover and double-click hits, docked Format Graph, ribbon, File page, Options, Print, help), CI and release workflows with the bundled Python.
- Checked in the real app under Xvfb: Home, opening each sample, typing and Ctrl+E (the excluded value leaves the graph), range selection with Sum/Average/Count, double-click on the X axis → Format Graph › X Axis, live "Connect the points", log X dose-response. Fixed: missing base grid-cell CSS (headings were shifted one column); Format Graph hid the graph (now docked right); docked overlay class clashed with the sidebar's `.side`; dialogs without inputs or OK did not close on Escape (focus fallback).
- 23 Playwright checks pass, with a real Python render. Screenshots in `docs/images/`. Also fixed: fast typing lost characters (and Enter) pressed before the edit box had the focus.
- Released 0.1.0 with `release.yml` (workflow_dispatch): CI green; the release build's smoke test started the bundled Python on Windows and got the versions back; installer 55 MB.

### 2026-10-24: Session 2 (review of 0.1.0, feature brainstorm)
- Feedback on 0.1.0 (one screenshot: Growth graph with Format Graph docked): first start 3–6 s, install under a minute, the app is fast and should stay so; graph text is in Arial as intended; **Copy Picture does not work**; **updates are slow** (the whole 55 MB installer each time); too little to evaluate yet, so brainstorm the full feature set first, then build in steps; asked how graphs are made.
- Diagnosis: Copy Picture uses the browser clipboard, which WebView2 disables because the window's address (`http://tauri.localhost`) is not a secure origin (the Linux test browser allowed it, so tests passed); same for Paste Special's fallback and the Print page's code copy. Updates: 50 of the 55 MB is the Python runtime, re-downloaded every time.
- Wrote [PLAN-0.2.md](PLAN-0.2.md): how a graph is made (diagram), diagnosis, **feature catalogue A–J** (data tables, analyses with their Python libraries, results, graphs, on-screen editing, layouts, export, Python scripting, speed, help), libraries and sizes (pandas, openpyxl, statsmodels, scikit-posthocs, lmfit, lifelines, pybaselines, python-pptx/docx; not pingouin: GPL), architecture changes, release plan 0.1.1 → 1.0, 10 questions. Roadmap above replaced by its summary. No code changed. **Waiting for the answers.**

### 2026-10-24: Session 3 (answers, 0.1.1)
- The user answered PLAN-0.2: no Prism files, nothing missing; background materials science R&D (lots of linear regression and statistics on many data points), now project management; "build the app first: lay out the whole UI, then build feature by feature"; keep tracking everything in memory. Decisions and the new order are in PLAN-0.2 §10 and the decisions table.
- Built 0.1.1:
  - Engine: `Import` op (+ test); Python `io.py` (CSV/TSV/TXT with delimiter sniffing and decimal commas, XLSX with openpyxl) + 2 tests; worker `read`.
  - Shell: `runtime.rs` (runtime pack, unzip test), `update.rs` download/asset helpers and `-update.exe` preference, `py.rs` reader thread with timeouts and `restart()`, clipboard commands, `import_file`, `restart_engine`.
  - UI: `features.ts` (99-feature catalogue), `roadmap.tsx` (Roadmap page, planned-command cards, New Table / Analyze / Graph Type galleries, Import dialog), planned commands across Data, Analyze, Graph, Format and the new Layout and Tools tabs, Copy Picture via Rust, engine status while the runtime unpacks or downloads.
  - Release: runtime zip + update installer + full installer. Released 0.1.1 (CI green): setup 89 MB, update 2.3 MB, runtime-1.zip 87 MB.
- Checked in the real app (Xvfb): Analyze tab and gallery; Import through the real file dialog of a tensile-test CSV (2 replicates guessed from the headings) → table and graph; Copy Picture put a 944 × 708 PNG (80 × 60 mm at 300 dpi) on the clipboard (`xclip`); ribbon folds the Item group at 1440 px. 31 UI checks, 14 Python tests, 12 + 1 Rust tests pass.

### 2026-10-25: Session 4 (one installer, 0.2 plan)
- Feedback on 0.1.1: updated from the app (~87 MB), installed quickly, opened fast; **wants one file per release** (no separate update installer or runtime pack, it confuses people); import "kind of works"; Copy Picture works now; the app misses many features: list what comes next, brainstorm, then start.
- Changed the release to a single installer: `release.yml` builds one `-setup.exe` with `runtime.zip`; `update.rs` downloads `-setup.exe`; `runtime.rs` no longer downloads a runtime (always in the installer); catalogue I1 reworded. Not released yet (goes out with 0.2.0).
- Wrote [PLAN-0.2.0.md](PLAN-0.2.0.md): what 0.2 adds (results sheets with Explain, descriptive, normality, outliers, linear regression with fit range/Deming/compare lines/bands/equation, curve fitting with a model library and own equations, data tools, styles), materials ideas **B27 tensile, B28 Arrhenius, B29 Weibull, B30 S–N, B31 DSC/TGA** (added to `features.ts` and PLAN-0.2), build notes (Analysis items, `py/datum/analyses/`, second worker, statsmodels + lmfit, runtime 2), split 0.2.0/0.2.1/0.2.2, 6 questions. **Waiting for the answers.**

### 2026-10-25: Session 5 (answers, roadmap, 0.2.0)
- The user: combine the first two parts into one 0.2.0, then small consecutive releases 0.2.1, 0.2.2 … up to 0.3 (no jumped numbers); Arrhenius yes; the rest as proposed; keep updates small and quick to save tokens; keep memory and CLAUDE.md complete. Recorded in PLAN-0.2.0 §9, the roadmap above, `features.ts` (releases per feature) and CLAUDE.md.
- Built 0.2.0: `Analysis` items and overlays in the core (+ test), `py/datum/analysis.py` + `models.py` (+ 12 tests against R/NIST), curves on graphs with bands and equations, `result`/`models` commands, `results.tsx` (options dialogs, results sheet with Explain), Analyze gallery and ribbon buttons made real, Tensile and Arrhenius samples, statsmodels + lmfit (runtime 2), single-installer release.
- Checked in the real app (Xvfb): Tensile sample graph with both modulus lines over 0–0.003 and equations; the results sheet (summary per alloy, comparing the lines, residual plots, answer, checks, methods). Fixed: samples lost their fit overlays when opened (the shell rebuilt graph settings from Options); `2.034e+05` → `203400` in labels; equation labels placed in the emptiest corner with a light background; "DFn = 1.0".
- 26 Python tests, 13 + 1 Rust tests, 38 UI checks pass. Released 0.2.0 (CI green): one installer, 113 MB (statsmodels, lmfit and pandas added to the Python pack).

### 2026-10-25: Session 6 (0.2.1, ? help)
- User: every Datum app gets a small ? beside its tools that says what the tool is for and how to use it (built first in Datum Atlas 0.1.1); no separate teaching mode.
- Built: `ui/src/help.tsx` copied from Atlas with 35 Plot topics; `G` (ribbon group) takes `h`, the navigator `Head` takes `h`, `Dialog` and `Gallery` take `help`; ? on the table head, graph footer, results head and Info sheet; Help › What Is This Tool?; `i-help` icon; `.help`/`.helpcard` styles. Planned-only groups (Compare, More, Layout and Tools tabs) have no ? (their buttons already open their planned cards). Catalogue J5 added (PLAN-0.2, `features.ts`); 0.2.1–0.2.5 renumbered 0.2.2–0.2.6 in `features.ts`, PLAN-0.2.0 §9 and the roadmap above.
- Checks: 26 Python tests, 13 + 1 Rust tests, clippy, check:ui, 42 UI checks (4 new: ? beside Regression opens its card and closes with Escape, What Is This Tool? opens a card, ? in the navigator).

### 2026-10-25: Session 7 (the big build, 0.2.2)
- User (after testing 0.2.0: "works very well… loads in a few seconds"): list what is pending and propose a big build of 10–15 features. Proposed seven big builds; the user: "complete 0.2.1 and 0.2.2 together, as one version… optimise as we do it… keep everything in memory". Another session had meanwhile released **0.2.1 (? help)** on this branch, so the big build was merged with it and became **0.2.2**; `features.ts`, PLAN-0.2 §11 and the roadmap renumbered (0.2.3–0.2.7, 1.0).
- Built (28 features): Python `groups.py` and `tools.py` (all checked against R); global fit + model comparison in `analysis.py` (`make_model`, `start`, `fit_one`, `global_fit`, `compare_models`; new kinds load lazily via `more_kinds()` to avoid a circular import); `graph.py` palettes, column graphs, bee swarm, brackets, shaded areas; `io.write_excel`; worker `excel`. Rust: `GraphSettings.column/palette`, `Table::column`, `Op::Sort`, `Op::CopyLook`, 3 new samples + tensile analysis in the Tensile sample, `export_all`, `export_excel`, `new_table(kind)`, `Options.styles`, second worker `Calc`, cache 24. UI: `tools.tsx`, dialogs for 12 new analysis kinds, New table from result, column grid, Find/Sort/Exclude rows in the table menu, Graph › Column Graph/Significance/Styles/Copy Look/Colour Schemes, Tools › Export All/Excel, View › Thumbnails, Help › Statistics Guide/Test Chooser, help cards for the new groups, Getting Started, Tell Me entries.
- Checked in the real app (Xvfb): Home with 8 samples, Compare groups graph with Tukey stars, ANOVA results sheet, Weibull box plot, thumbnails. Fixed on the way: overlapping stacked brackets, dots hiding box plots, swarm spacing in data units, the Analyze ribbon regrouped so labels stay visible.
- Checks: 41 Python tests, 15 + 1 Rust tests, clippy, check:ui, 54 UI checks. Released 0.2.2 (CI green, release.yml by workflow_dispatch; tag pushes are blocked here): one installer, 113 MB.

---

## 5. Known limits and next steps

**Next:** the user tests 0.2.2 (try the Compare groups, Weibull, DSC and Tensile samples; Analyze › Test Chooser; Graph › Styles and Colour Schemes; Tools › Excel Workbook); then 0.2.3 two factors and counts.

**0.2.2 limits:** transforms/histograms/smoothing make plain tables (not live linked); repeated-measures ANOVA uses complete rows only; Weibull CIs are asymptotic (no ASTM unbiasing factor); Dunn's test is Bonferroni-adjusted only; no estimation plots or many-t-tests-with-FDR yet; brackets only on column graphs; partial correlation not yet.

**0.2.0 limits:** (column tables arrived in 0.2.2); residual and QQ plots are pictures in the results sheet, not graphs of their own (0.2.2); equations sit in a corner (not draggable until 0.4); the first start of 0.2.0 unpacks Python again (runtime 2).

**Checked by the user on Windows (0.1.0):** first start 3–6 s; install under a minute; graph text in Arial. Copy Picture failed (fixed in 0.1.1, checked on Linux only).

**Checked by the user on Windows (0.1.1):** in-app update (~87 MB) quick, app opens fast, Copy Picture works, import works in a first try.

**Not yet checked on a real Windows PC:**
- The bundled Python: first start time (matplotlib builds its font cache in `%LOCALAPPDATA%`), Arial/Calibri found by matplotlib, `CREATE_NO_WINDOW`, antivirus scanning many files.
- Print/Save as PDF of graph pages; export files opened in Word, Illustrator and a journal's checker.

**Known limits:**
- Every update downloads the whole installer (~90 MB, more with statsmodels/lmfit); the user prefers this to separate files.
- A worker request is cut off after 60 s; results run on the second worker since 0.2.2, so a slow one no longer blocks graphs.
- The installer's `runtime.zip` is deleted after unpacking; a damaged runtime is fixed by deleting the `runtime` folder and running the installer again. A repair command could come later.
- On Linux (development) graph text shows in a fallback font when Arial is missing.
- No analyses yet, one table type (XY), no layouts: they are laid out in the UI and come in the order of the roadmap.
- Windows SmartScreen warns on the first install (unsigned).
