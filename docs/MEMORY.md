# Datum Plot: project memory

> **Paste this file at the start of each new session**, or just open the repo: `CLAUDE.md` tells Claude to read it.
> It records what exists, why, and what comes next. Update it at the end of every session.

| | |
| --- | --- |
| **Product** | Datum Plot: a Windows desktop app for scientific graphs, statistics and curve fitting, combining GraphPad Prism (guided tables → analyses → graphs, linked live) and OriginPro (workbooks, many graph types, analysis power) |
| **Family** | Second Datum app after Datum Plan (`Edgar-Mendonca/Datum-Plan`). Design and workflow: [Datum-Plan/docs/FAMILY.md](https://github.com/Edgar-Mendonca/Datum-Plan/blob/HEAD/docs/FAMILY.md). Plan's code is the reference implementation: copy, don't reinvent. |
| **Current version** | None released yet. Next: **0.1.0** (planned in [PLAN-0.1.md](PLAN-0.1.md), waiting for answers) |
| **Repo** | `Edgar-Mendonca/Datum-Plot` · working branch `claude/epic-mayer-6faugf` |
| **Identity** | Accent **Teal** (`--blue #0E8C7F`, `--blue2 #0B7468`, `--sky #8FD3C9`, `--pale #E3F5F2`, `--sel #D3EFEA`, `--sel2 #A9DDD4`, dark `--blue #3FC2B2`, File sidebar dark `#0A4A44`) · files `.dplot` · identifier `com.edgarmendonca.datumplot` · installer `DatumPlot-x.y.z-setup.exe` · logo `docs/brand/datum-plot-icon.svg` (teal axes, tint points, fitted curve, amber `#F2B233` diamond) |
| **Stack** | Rust engine (`crates/core`) + Tauri 2 shell (`src-tauri`), WebView2, SolidJS + Vite UI in strict TypeScript, plain CSS tokens, IBM Plex Sans/Mono, own SVG graph engine (proposed), `statrs` for distributions (proposed). No Python. |
| **Code size** | 0 lines (docs only) |

---

## 1. Architecture (planned for 0.1.0; see PLAN-0.1 §3)

```mermaid
flowchart LR
  subgraph UI["Window (WebView2) · ui/src/*.tsx → Vite → ui/dist"]
    Store[store.ts: project, open item, selection, act(op)]
    Nav[navigator.tsx: Info · Data · Results · Graphs · Layouts]
    Table[table.tsx: data grid on the family grid engine]
    Graph[graph.tsx: SVG renderer for GraphOut]
    BS[ribbon.tsx · backstage.tsx · print.tsx from Plan]
  end
  subgraph Shell["src-tauri (Rust)"]
    Cmd[main.rs: new · open · save · apply · item · graph · options · recovery · save_file · open_url]
    Upd[update.rs: REPO = Edgar-Mendonca/Datum-Plot]
  end
  subgraph Core["crates/core (pure Rust, unit-tested)"]
    Model[model.rs: Project · DataTable · Analysis · Graph · Layout]
    Doc[doc.rs: Op · undo/redo · .dplot]
    Stats[stats/: descriptive · distributions · tests]
    Fit[fit/: Levenberg-Marquardt · models]
    Plot[plot.rs: scales · ticks · error bars → GraphOut]
  end
  UI -- "invoke(cmd, args)" --> Cmd --> Doc --> Model
  Cmd --> Stats & Fit & Plot
```

**Rules:**
- The window never computes a statistic, tick or error bar. Every edit is an `Op`; the engine applies it and returns what the window shows (same as Plan).
- **Live chain** (Prism): analyses and graphs store settings and their input's id; results are computed on demand and cached by revision. `.dplot` stores data and settings, never results.
- Graphs: the engine builds a `GraphOut` scene (ranges, ticks, labels, points, error segments, lines, legend; data and mm units); the window draws SVG. Screen, print and every export come from the same scene.
- Every statistic has a unit test against a published value (NIST StRD, R output).

### Files
| Path | What it does |
| --- | --- |
| `docs/PLAN-0.1.md` | Prism vs Origin comparison, architecture, ideas, 0.1.0 scope, release plan, questions |
| `docs/MEMORY.md` | This file |
| `docs/brand/datum-plot-icon.svg` | Draft logo (from Datum Plan's `docs/brand`) |
| `CLAUDE.md` | Notes for Claude: read this file first, preferences, checks, release steps |
| `LICENSE`, `.gitignore` | MIT; same ignores as Plan |

Planned for 0.1.0 (copied from Plan, then renamed): `Cargo.toml` (workspace), `crates/core` (`model.rs`, `doc.rs`, `stats.rs`, `plot.rs`, `templates.rs`, `tests.rs`, `examples/dump.rs`), `src-tauri` (`main.rs`, `update.rs`, `tauri.conf.json`, `capabilities`, `icons`), `ui/` (`index.html` + sprite, `public/logo.svg`, `src/` `styles.css`, `api.ts`, `store.ts`, `cmds.ts`, `ui.tsx`, `ribbon.tsx`, `backstage.tsx`, `print.tsx`, `selection.ts`, `cells.ts`, `fmt.ts`, `navigator.tsx`, `table.tsx`, `graph.tsx`, `format.tsx`, `main.tsx`), `package.json`, `.github/workflows/ci.yml` + `release.yml`, `tests_ui/run.cjs`, `NOTICE`, `README.md`, `CHANGELOG.md`.

### Update flow (same as Plan)
On start and on "Check again": GET `/repos/Edgar-Mendonca/Datum-Plot/releases/latest` (or `/releases` with beta) → badge + Home card with the CHANGELOG section → Update now downloads `DatumPlot-x.y.z-setup.exe`, checks `SHA256SUMS.txt`, runs it with `/S`, restarts. Install only from this repo's release URLs.

### Release flow (same as Plan)
Bump `src-tauri/Cargo.toml` + `crates/core/Cargo.toml` → CHANGELOG `## x.y.z — date` → update this file → commit + push → `release.yml` (tag push, or workflow_dispatch when tags are blocked) → GitHub Release with setup.exe + SHA256SUMS.txt → users click Update now.

### How we work (from Datum Plan, FAMILY §11)
1. **The user reviews the last release** in the app and sends screenshots with bugs and wishes.
2. **Diagnose first.** Reproduce the problem in the test harness or the real app before changing code. Small fixes go straight to a release.
3. **Bigger asks get a plan file** (`docs/PLAN-x.y.md`): feedback, diagnosis, proposal, size, questions. Logged here and pushed. Build only after the user answers.
4. **Build in small steps**, engine first (`crates/core`, with a unit test, numbers checked against NIST/R), then the UI. Compact code in the surrounding style.
5. **Check in the real app** under Xvfb, with screenshots of each change. Fix what looks wrong.
6. **Add a UI test** for every reported bug and new feature (`tests_ui/run.cjs`, Playwright against `ui/dist` with the `dump` fixture). Make it fail on the old code where possible.
7. **Run the checks:** clippy `-D warnings`, `cargo test --workspace`, `npm run check:ui`, the UI tests.
8. **Release:** bump, CHANGELOG (becomes the in-app "What's new"), update this file, commit, push, run `release.yml`, watch CI + Release, confirm the installer.
9. **Report to the user** in plain language: what changed, what was checked, what is not done, what to check on Windows.

---

## 2. Decisions

| Date | Decision | Why |
| --- | --- | --- |
| 2026-10-24 | Name **Datum Plot**, `.dplot`, `com.edgarmendonca.datumplot`, Teal accent, releases from `Edgar-Mendonca/Datum-Plot` | The user's choice, per FAMILY.md §1 and §3. |
| 2026-10-24 | Same stack, look, updater, release and workflow as Datum Plan; copy Plan's code (`styles.css`, sprite, `ribbon.tsx`, `backstage.tsx`, `print.tsx`, `selection.ts`, `cells.ts`, `fmt.ts`, `update.rs`, workflows, `tests_ui/run.cjs`) | FAMILY.md: one design and one way of working; only the accent and glyph change. |
| 2026-10-24 | Brainstorm and `PLAN-0.1.md` before any feature; 0.1.0 = shell, updater, Home, XY table, XY graph | The user's instruction and FAMILY §12. The updater must work from day one. |
| 2026-10-24 | Proposed (awaiting answers): Prism's linked chain as the backbone (table → analysis → results → graph → layout) with Origin's freedom added later; own SVG graph engine fed by a Rust `GraphOut` scene; `statrs` + own Levenberg-Marquardt; statistics validated against NIST StRD and R; no Python | See PLAN-0.1 §3 and §8. |

---

## 3. Roadmap

✅ done · 🔜 next · ⬜ planned. Small releases; every one goes through the in-app updater. Details in [PLAN-0.1.md](PLAN-0.1.md) §6.

| Version | Theme | Contents | Status |
| --- | --- | --- | --- |
| — | Brainstorm | Comparison, plan, memory, logo | ✅ |
| **0.1.0** | Shell + XY | Installer, updater, Home, File page, Options, Help, Info sheet, XY table (replicates or mean/SD/N), XY graph (points, lines, SD/SEM/CI/range error bars, linear/log axes, legend, mm size), Format Graph, SVG/PNG export, Print, `.dplot`, undo, recovery | 🔜 |
| 0.1.1 | Column data + statistics | Column table and graphs (dot plot, bar, box, violin), column statistics, normality + QQ, histogram, CSV/XLSX import, Results, Explain panel | ⬜ |
| 0.2.0 | Compare groups + curve fitting | t-tests, nonparametric, one-way ANOVA + multiple comparisons, significance brackets, test chooser, methods text, linear regression, nonlinear fitting engine with ~20 models, styles | ⬜ |
| 0.2.1 | Curve fitting power | Global fitting, compare models, interpolation, ROUT, ~60 models, AUC, transforms | ⬜ |
| 0.3.0 | Two factors, counts, layouts | Grouped + two-way ANOVA, contingency, correlation, pie, ROC, Bland-Altman, axis breaks, double Y, Layouts, TIFF/EMF, `.pzfx` import, journal presets | ⬜ |
| 0.4.0 | Survival, nested, many variables | Kaplan-Meier, log-rank, Cox; nested t/ANOVA; multiple/logistic regression, PCA; volcano, forest; power | ⬜ |
| 0.5.0 | Origin power | Worksheets + formulas, matrices, contour/3D/polar/waterfall/ternary, layers/insets/multi-panel, peaks, smoothing, FFT, ROI gadgets | ⬜ |
| 0.6.0 | Automation | Batch processing, analysis templates, batch export, plate import, R code | ⬜ |
| 0.6.1 | Hardening | Large data, signing, signed updates, crash reports | ⬜ |
| 1.0.0 | Stable | User guide, validation report | ⬜ |

---

## 4. Session log

### 2026-10-24: Session 1 (brainstorm)
- The user started Datum Plot as the second Datum app and asked to follow FAMILY.md exactly, brainstorm, write `docs/PLAN-0.1.md`, and create `CLAUDE.md` and this file before building.
- Read Datum Plan (read-only): FAMILY.md, CLAUDE.md, MEMORY.md, CHANGELOG.md, `styles.css`, the sprite in `index.html`, `ribbon.tsx`, `backstage.tsx`, `print.tsx`, `selection.ts`, `cells.ts`, `fmt.ts`, `update.rs`, `release.yml`, `ci.yml`, `tests_ui/run.cjs`, and the draft logo.
- Wrote [PLAN-0.1.md](PLAN-0.1.md): Prism vs Origin (tables, analyses, graphs, layouts, export), architecture, 15 ideas beyond both, 0.1.0 scope, release plan to 1.0, 14 questions.
- Added `CLAUDE.md`, this file, LICENSE (MIT), `.gitignore`, `docs/brand/datum-plot-icon.svg`, a short README. No code yet. **Waiting for the user's answers before building 0.1.0.**

---

## 5. Known limits and next steps

- Nothing is built yet. Next: answers to PLAN-0.1 §8, then build and release 0.1.0 (copy the Plan skeleton, rename, teal, XY table and graph).
- To work on this repo, also add `Edgar-Mendonca/Datum-Plan` read-only: it is the reference code and holds FAMILY.md.
