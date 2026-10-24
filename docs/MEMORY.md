# Datum Plot: project memory

> **Paste this file at the start of each new session**, or just open the repo: `CLAUDE.md` tells Claude to read it.
> It records what exists, why, and what comes next. Update it at the end of every session.

| | |
| --- | --- |
| **Product** | Datum Plot: a Windows desktop app for scientific graphs, statistics and curve fitting, combining GraphPad Prism (guided tables → analyses → graphs, linked live) and OriginPro (workbooks, many graph types, analysis power) |
| **Family** | Second Datum app after Datum Plan (`Edgar-Mendonca/Datum-Plan`). Design and workflow: [Datum-Plan/docs/FAMILY.md](https://github.com/Edgar-Mendonca/Datum-Plan/blob/HEAD/docs/FAMILY.md). Plan's code is the reference implementation: copy, don't reinvent. |
| **Current version** | **0.1.1** (2026-10-24). Earlier: 0.1.0 |
| **Repo** | `Edgar-Mendonca/Datum-Plot` · working branch `claude/epic-mayer-6faugf` |
| **Identity** | Accent **Teal** (`--blue #0E8C7F`, `--blue2 #0B7468`, `--sky #8FD3C9`, `--pale #E3F5F2`, `--sel #D3EFEA`, `--sel2 #A9DDD4`, `--accent2 #3FC2B2`; dark `--blue #3FC2B2`, File sidebar dark `#0A4A44`) · files `.dplot` · identifier `com.edgarmendonca.datumplot` · installer `DatumPlot-x.y.z-setup.exe` · logo `docs/brand/datum-plot-icon.svg` = `ui/public/logo.svg` (teal axes, tint points, fitted curve, amber `#F2B233` diamond) |
| **Stack** | Rust shell (`src-tauri`) + Rust project engine (`crates/core`), Tauri 2, WebView2, SolidJS + Vite UI in strict TypeScript, plain CSS tokens, IBM Plex. **Python worker** (`py/`) with numpy, SciPy and matplotlib for every calculation and every graph; the installer bundles embeddable CPython 3.13. |
| **Code size** | About 4,300 lines: core 950 (with 12 tests), shell 740, Python 400 (+ 14 tests), UI 2,100 TSX/TS + CSS, UI tests 160 |
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
    Py[py.rs: one Python worker, JSON lines, restart, render cache]
    Upd[update.rs: REPO = Edgar-Mendonca/Datum-Plot]
  end
  subgraph Core["crates/core (pure Rust, 11 tests)"]
    Model[model.rs: Project · Info · Table · DataSet · Graph · GraphSettings]
    Doc[doc.rs: Op · undo/redo · .dplot · number parsing]
    Tpl[templates.rs: blank, growth, standard, dose]
  end
  subgraph Python["py/ (numpy · SciPy · matplotlib, 12 tests)"]
    W[worker.py: ping · render · export · summary]
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
| `crates/core/src/model.rs` | Format 1. `Project` (name, `info`, `tables`, `graphs`, `nextId`, `ui`), `Info`, `Table` (XY: X column + `sets`; `cols` is the flat column list, column 0 = X; `rows`, `rowTitles`, `excluded` [row, col], `style` "r:c" → style string), `DataSet` (`entry` rep/msn/mesn, `reps`), `Graph` + `GraphSettings` (error, errorDir, points, line, cap, width/height mm, font, fontSize, boldTitles, style prism/frame, title, legend, `x`/`y` `Axis`, `sets` `SetStyle`). `normalize`, `add_table`, `from_json` (refuses newer formats). |
| `crates/core/src/doc.rs` | `Op`: NewTable, Delete, Rename, Duplicate, Cells (col −1 = row title), Import (rows → new table + graph; titles from the first row; sets of `reps`), Paste (first row of words = titles; grows rows and data sets), Exclude, TableSet, SetDef (add/replace/remove a data set, remapping columns, exclusions and styles), Rows (insert/delete, remapping), Style, AddGraph, GraphSet, Info, ProjectName, Ui, Batch. `number()` parses 1,234.5 / −4 / 12% / 1e-3. |
| `crates/core/src/templates.rs` | Blank XY, Growth curve, Standard curve (mean/SD/N), Dose-response (log X); `list()` gives tile pictures. |
| `crates/core/examples/dump.rs` | Fixture for the UI tests. |
| `src-tauri/src/main.rs` | Commands in the diagram plus `copy_graph` (PNG → Windows clipboard via `tauri-plugin-clipboard-manager`), `copy_text`, `read_clipboard`, `import_file`, `restart_engine`; `Options` (theme, autosave, beta, openLast, decimals, reps, entry, error, width, height, font, fontSize, style, dpi, paper, landscape, company, logo); new tables/graphs follow the options; recovery; recent files; `open_url` only for this repo. |
| `src-tauri/src/py.rs` | Finds Python (`DATUM_PYTHON`, the runtime pack, else `python`/`python3`); a reader thread lets requests time out (start 180 s, request 60 s → kill and report); `restart()`; and `py/worker.py` (bundled or the source tree), `MPLCONFIGDIR` in the app cache, `CREATE_NO_WINDOW`, restart once on failure, cache of the last 8 renders. Started in a thread at launch; emits `engine` with versions or the error. |
| `src-tauri/src/update.rs` | Datum Plan's updater with `REPO = Edgar-Mendonca/Datum-Plot`; prefers the `-update.exe` asset; `download()` (progress + SHA-256) and `asset_url()` shared with the runtime pack. |
| `src-tauri/src/runtime.rs` | The Python runtime pack: `%LOCALAPPDATA%/com.edgarmendonca.datumplot/runtime/N` (N = `py/runtime.txt`); from `resources/runtime.zip` (full installer) or downloaded from this version's release; unzips with progress (`engine` status event), removes older runtimes, the zip and 0.1.0's `resources/python`. Release Windows builds only; dev builds use the PATH Python. 1 test. |
| `src-tauri/tauri.conf.json`, `tauri.release.conf.json` | Bundles `py/worker.py` and `py/datum/*.py`; the release config adds `runtime.zip` for the full installer. |
| `py/runtime.txt` | The runtime pack number: **bump it whenever `py/requirements.txt` changes**, so installed apps download the new pack. |
| `py/datum/io.py` | File › Import readers: CSV/TSV/TXT (delimiter sniffing, decimal commas with `;`, encodings) and XLSX (openpyxl, every sheet); all cells as text. |
| `py/worker.py` | The protocol loop: warm-up render, `{"ready": true}`, then one answer line per request; stdout reserved for the protocol. |
| `py/datum/stats.py` | `set_columns`, `value`, `describe` (n, mean, SD, SEM, CI via `scipy.stats.t`), `from_summary`, `summarize`. |
| `py/datum/graph.py` | `rc_for` (fonts, Prism or framed axes), `figure` (means ± error bars or each replicate, lines, log axes, ranges, ticks, grid, legend, title), `geometry`, `render` (SVG + geometry + points), `export` (png/svg/pdf/tiff/eps, dpi, transparent; base64 for the clipboard). |
| `py/tests/test_engine.py` | Statistics vs R, exclusions, mean/SD/N entry, renders, log axes, every export format, the worker protocol. |
| `py/requirements.txt` | numpy 2.5.4, scipy 1.18.1, matplotlib 3.11.2 (pinned). |
| `ui/index.html` | Root and the icon sprite (Plan's ~90 icons recoloured teal + Plot icons: xy, graph, sheet, results, layout, infosheet, err, axis, log, legend, symbol, image, addset, addrow, delrow, exclude, sigma, curve, size, line, frame). |
| `ui/src/api.ts` | Types matching the Rust JSON, `Render`, `spans`/`width`/`letter`/`num`. |
| `ui/src/store.ts` | Signals: `out`, `item` {section, id}, `backstage`, `tab`, `navOpen`, `engine`, options, theme; `act`, `call`, `loadOut`, `open`; menus, dialogs, toasts. |
| `ui/src/datatable.tsx` | The XY grid (selection column 0 = row title, k ≥ 1 = grid column k − 1): two-row headings by data set, typing, ranges, TSV copy/cut/paste (→ `Paste` op), fill handle + Ctrl+D/R, Paste Special, Ctrl+B/I/U, Ctrl+E exclude, context menu (insert/delete rows, format/add data set); `TableHead` (titles and units); `setDialog`, `addSet`, `rename`. |
| `ui/src/graph.tsx` | `useRender`, `GraphView` (zoom, crosshair, hover values, double-click → Format Graph page, context menu, Ctrl+C), `copyGraph` (PNG to the clipboard), `exportGraph` dialog, `newGraph`. |
| `ui/src/format.tsx` | Format Graph (docked right, changes apply at once): Data Sets, X Axis, Y Axis, Graph; `SIZES` (journal widths), `FONTS`, `ERRORS`, `OKABE_ITO`. |
| `ui/src/ribbon.tsx` | Title bar, Tell Me, ribbon: Data · Analyze · Graph · Layout · Tools · View · Help + contextual Graph Tools › Format; Plan's `B`/`G`/`S`, Font group and `fitRibbon`; `N` = a planned command (dimmed, amber dot, opens `soon(id)`). |
| `ui/src/backstage.tsx` | File page: Home (samples with mini graphs, recent, updates card with engine versions), Export tiles, Options (General, Start-up and saving, New data tables, New graphs, Printing and branding, Updates), Print, Updates. |
| `ui/src/print.tsx` | File › Print: graph pages at real size or fitted, with caption; data table and Info sheet as flowing pages; header/footer codes (&[Page], &[Pages], &[Date], &[Project], &[Item], &[Title], &[Researcher], &[Company], &[Logo]); saved in `project.ui.page`. |
| `ui/src/nav.tsx` | Sidebar (Info first, then Data, Results, Graphs, Layouts), navigator tree with context menus, Info sheet, Results and Layouts empty pages. |
| `ui/src/dialogs.tsx` | Paste Special, Getting Started (for Prism and Origin users), Glossary, Shortcuts, save-before-close. |
| `ui/src/features.ts` | **The feature catalogue in the app** (99 entries: id, name, release, description, library), `VERSION_NOW`, `RELEASES`, `AREAS`, `ready()`. Mirrors PLAN-0.2 §4 with the §10 order; update it when a feature ships. |
| `ui/src/roadmap.tsx` | `soon(id)` card for planned commands, `RoadmapPage` (File › Roadmap, Help › Roadmap), galleries `newTable`, `analyze`, `graphTypes` (categories · items · details), `importFile` dialog (sheet, headings, X column, replicates guessed from gaps in the titles, preview) → `Import` op. |
| `ui/src/selection.ts`, `cells.ts`, `fmt.ts`, `ui.tsx` | Copied from Datum Plan (grid engine, TSV and series, formatting, building blocks; `Dialog` has a docked `side` mode). |
| `tests_ui/run.cjs` | Playwright: 31 checks (since 0.1.1 also: planned commands and their cards, Analyze gallery, Import dialog → `Import` op, Copy Picture → `copy_graph`, Roadmap list and search, every tab fits at 1280/1600 px) against `ui/dist` with the dump fixture and a **real Python render** of the sample graph (Home, opening a sample, Format Graph from a double-click, log scale op, docked dialog, hover values, heading alignment, typing, ranges, Count, Ctrl+E, paste, ribbon fit at 1280/1600, Analyze, Info, Print, Options, no script errors). |
| `.github/workflows/ci.yml` | ubuntu: Python deps + `unittest`, `check:ui`, build, clippy `-D warnings`, `cargo test`, UI tests. |
| `.github/workflows/release.yml` | windows: runtime pack in `rt/` (newest embeddable CPython 3.13 + requirements, pruned, compiled, ping smoke test) zipped as `DatumPlot-runtime-N.zip`; app-only build → `-update.exe`; build with `tauri.release.conf.json` (+ `runtime.zip`) → `-setup.exe`; SHA256SUMS over all; notes from CHANGELOG. |

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
| 0.1.1 | Python runtime as a separate, numbered pack in the user's data folder (`runtime/N`); three release files (full setup with `runtime.zip`, app-only update, runtime zip); bump `py/runtime.txt` when requirements change | Updates were slow because the 50 MB runtime came with every update. |
| 0.1.1 | Clipboard writes and reads go through Rust (`tauri-plugin-clipboard-manager`), never `navigator.clipboard` | WebView2 blocks the browser clipboard on `http://tauri.localhost` (Copy Picture failed on Windows). |
| Session 3 | Libraries are added in the release that first needs them (openpyxl 0.1.1; statsmodels, lmfit 0.2; scikit-posthocs 0.3; lifelines 0.5; pybaselines 0.6; python-pptx/docx 0.7); no pingouin (GPL), no scikit-learn, no seaborn | The user agreed to the libraries; keep the pack small until needed; licences fit an MIT app. |
| Session 3 | **Lay out the whole UI first**: every catalogue feature has its place now (ribbon, galleries, navigator, Roadmap); planned ones are dimmed and explain what and when; then build feature by feature | The user: "build the app first… then feature by feature; much easier to see and understand the issues." |
| Session 3 | Release order: 0.2 statistics and regression, then 0.3 compare groups | The user's work (materials science R&D) is regression-heavy. |
| Session 3 | Exact P values with APA stars by default; Prism-style results sheets + Explain panel; Python console in 0.7; graph editing in 0.4; `.pzfx` in 0.6 | The user left these to us; no Prism files. |
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
| **0.2.0** | Statistics and regression | Transforms, outliers, sort/filter, data checks, descriptive, normality, linear/polynomial/Deming regression, lmfit curve fitting + model library, global fits, model comparison, interpolation, AUC/smoothing, results sheets + Explain + test chooser + methods text + "show as Python code", histogram/QQ, fitted curves with bands and residuals, styles, copy look, colour schemes, batch export, Excel export, second worker, materials-science samples, statistics guide | 🔜 |
| 0.3.0 | Compare groups | Column table, t-tests, nonparametric, one-way ANOVA + post hoc, effect sizes, column graphs (dot, bar, box, violin, swarm, estimation), significance brackets, graph thumbnails | ⬜ |
| 0.4.0 | Two factors, interactive graphs, layouts | Grouped + two-way ANOVA, contingency, correlation, ROC, Bland-Altman, grouped bars, heat map, pie, axis breaks, double Y, annotations, click/drag/edit on the graph, layouts, CMYK TIFF | ⬜ |
| 0.5.0 | Survival, nested, many variables | Kaplan-Meier, log-rank, Cox (lifelines), nested, multiple/logistic regression, PCA, clustering, power, survival/volcano/forest graphs | ⬜ |
| 0.6.0 | Origin power | Worksheets, matrices, numpy column formulas, `.pzfx` import, instrument/plate import, peaks, signal processing, surface fits, 3D/contour/polar/ternary/waterfall, multi-panel, large data, ROI, posters, code signing | ⬜ |
| 0.7.0 | Python scripting and automation | Python console, own analyses and fit equations, analysis templates, batch processing, notebooks, PowerPoint and Word export | ⬜ |
| 1.0.0 | Stable | Validation report (R/NIST), user guide | ⬜ |

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
  - Release: runtime zip + update installer + full installer.
- Checked in the real app (Xvfb): Analyze tab and gallery; Import through the real file dialog of a tensile-test CSV (2 replicates guessed from the headings) → table and graph; Copy Picture put a 944 × 708 PNG (80 × 60 mm at 300 dpi) on the clipboard (`xclip`); ribbon folds the Item group at 1440 px. 31 UI checks, 14 Python tests, 12 + 1 Rust tests pass.

---

## 5. Known limits and next steps

**Next:** the user reviews 0.1.1 (Copy Picture in Word, the first-start unpacking time, an update to 0.1.2+ downloading only the small installer, Import with their own files, the laid-out UI). Then 0.2.0 statistics and regression (plan file first: `docs/PLAN-0.2.0.md` or a section in PLAN-0.2).

**Checked by the user on Windows (0.1.0):** first start 3–6 s; install under a minute; graph text in Arial. Copy Picture failed (fixed in 0.1.1, checked on Linux only).

**To check on Windows in 0.1.1:** the runtime unpacking on first start (time, Defender), that 0.1.0 → 0.1.1 removes the old `resources/python`, that the next update downloads only `-update.exe`, Copy Picture into Word/PowerPoint.

**Not yet checked on a real Windows PC:**
- The bundled Python: first start time (matplotlib builds its font cache in `%LOCALAPPDATA%`), Arial/Calibri found by matplotlib, `CREATE_NO_WINDOW`, antivirus scanning many files.
- Print/Save as PDF of graph pages; export files opened in Word, Illustrator and a journal's checker.

**Known limits:**
- The update from 0.1.0 to 0.1.1 is still the full installer (0.1.0's updater only knows `-setup.exe`); small updates start from 0.1.1.
- A worker request is cut off after 60 s; long analyses (fits, bootstraps) will need the second worker (I3, 0.2) or a longer limit.
- The full installer's `runtime.zip` is deleted after unpacking; a damaged runtime is fixed by deleting the `runtime` folder (the app then downloads it). A repair command could come later.
- On Linux (development) graph text shows in a fallback font when Arial is missing.
- No analyses yet, one table type (XY), no layouts: they are laid out in the UI and come in the order of the roadmap.
- Windows SmartScreen warns on the first install (unsigned).
