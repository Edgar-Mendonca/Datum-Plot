# Plan 0.3.2: the Datum Plot Guide (English, 中文, Français) and more templates

The user (session 9): "first we need to have manuals in this application like how we did in Datum Plan; also more
templates would be nice; Guide I need in 3 languages: English, Chinese, French"; "let's call this the 0.3.1 update".
**0.3.1 is already out** (publisher "Datum", 2026-10-29), so the next free number is **0.3.2**.

## 1. The guide (copied from Datum Plan 0.4.4)

- **Text**: `docs/guide/en.md`, `zh.md`, `fr.md` (one Markdown source each, about 25–30 A4 pages). The window stays in
  English, so the Chinese and French guides give the English button names in bold with the meaning beside them.
- **Pictures**: `tests_ui/guide_shots.cjs` takes screenshots of the built window (a project in progress from
  `dump guide`) with numbered orange markers; the shots are in English and shared by all three languages.
- **PDFs**: `scripts/guide.cjs` (Plan's script, Teal colours, Noto Sans SC for Chinese) builds
  `DatumPlot-Guide-en.pdf`, `-zh.pdf`, `-fr.pdf`; `release.yml` attaches them and lists them in `SHA256SUMS.txt`.
- **In the app**: Help › **Guide** (and a tile on the File page) with English / 中文 / Français. One click downloads the PDF
  from this version's release, checks it against `SHA256SUMS.txt` and a `%PDF` header (the updater's rules),
  saves it in Downloads and opens it. The installer stays the same size.
- **Chapters**: Welcome · Install, update and start · The window · Data tables (every kind) · Import ·
  Analyses and results · Graphs · Layouts and export · Matrices and 3D · Peaks, thermal and materials · The Python
  console and automation · Files · Help in the app · Statistics cheat sheet (which test when) · Glossary · Shortcuts and
  troubleshooting.

## 2. More templates (19 today)

| ID | Template | Table | Analysis and graph |
|---|---|---|---|
| T1 | Enzyme kinetics | XY | Michaelis–Menten fit, Km and Vmax |
| T2 | Before and after | column (paired) | paired t-test, before–after lines |
| T3 | Survival study | survival | Kaplan–Meier curves, log-rank |
| T4 | Method comparison | column | Bland–Altman |
| T5 | Diagnostic test | column | ROC curve, AUC |
| T6 | Calibration with LOD | XY | linear fit, limits of detection and quantification |
| T7 | Correlation | XY / multi | Pearson and Spearman, scatter with fit |
| T8 | Frequency distribution | column | histogram, normality |
| T9 | Repeated wells (nested) | nested | nested t-test |
| T10 | Response surface | matrix | contour map, quadratic surface fit |
| T11 | Polar pattern | XY (polar) | polar graph |
| T12 | Growth inhibition (IC50) | XY | four-parameter logistic, IC50 |

## 3. Questions

1. Is 0.3.2 right (0.3.1 is already out), and should the guide and templates ship together or as 0.3.2 (guide) then 0.3.3 (templates)?
2. Guide as a downloaded PDF (like Datum Plan) — or also readable inside the app?
3. Chinese = Simplified (mainland), French = France: right?
4. Which templates from the table (all twelve, or some)?

## 4. Also in 0.3.2

Datum Plan 0.4.3 moved its publisher with an installer hook (`src-tauri/windows/hooks.nsh`): someone who installed into a
folder of their own choosing is updated in place, and the old `Software\Edgar Mendonca\Datum Plot` key is removed.
0.3.1 changed the publisher without it, so 0.3.2 adds the same hook.

## 5. Answers (2026-10-30)

1. **0.3.2**, guide and templates together.
2. **Downloaded PDF**, as in Datum Plan.
3. **Simplified Chinese** (mainland) and **French (France)**.
4. **Medical and engineering**: T3 survival study, T4 method comparison, T5 diagnostic test, T10 response surface, T11 polar pattern.
