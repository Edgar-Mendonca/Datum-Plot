# Plan 0.3.3: testers' comments (colours, copy and re-edit, generic names, open formats)

Session 10. Three testers' comments, passed on by the user. The user asked for: each problem, the solution, a
recommendation, then a decision before building.

## 1. Colour Schemes dialog

| # | Problem | Cause | Fix | Size |
|---|---|---|---|---|
| 1a | The table's columns are far too wide: the dialog scrolls sideways | `.tbl` is `width: 100%`, so the Colours column stretches; the custom-colours input is 210 px | Compact table (`width: auto`), narrower swatches, shorter column titles ("Protan", "Deutan", "Tritan" with a tooltip) | small |
| 1b | The dialog cannot be moved, so it covers the graph while you try schemes | Dialogs are centred overlays; only Format Graph is docked | Let it sit beside the graph like Format Graph (docked, no dark overlay), so every click shows on the graph at once. Optionally: any dialog can be dragged by its title bar | small |
| 1c | After choosing a scheme, Format Graph › Data Sets still shows the old colours, and its row of quick colours is always Okabe-Ito, not the chosen scheme | The colour box shows `colour set by hand` or else Okabe-Ito, never the scheme; the quick-colour row is hard-coded | The colour box shows the colour the graph really uses (from the scheme); the quick-colour row shows the chosen scheme's colours | small |

Recommendation: do all three (1b as "docked beside the graph", plus title-bar dragging for every dialog).

## 2. Copy a graph into a presentation and edit it again from there

Asked for: copy a graph, paste it into slides (any program), later reopen it from the slide, change it and have the
slide updated.

Options:

| Option | How it works | For | Against |
|---|---|---|---|
| A. Embedded object (the way some commercial apps do it) | The slide holds a live Datum Plot object; double-clicking it opens Datum Plot | Exactly what was asked | A Windows-only COM/OLE server: large, fragile, works fully only in one office suite; months of work; not in the family's small, open style. **Not recommended.** |
| B. The picture carries its graph | Every copied or exported picture (PNG, SVG) carries a hidden copy of the graph (data and settings). To edit: copy the picture from the slide, **Paste** in Datum Plot (or open the picture file); the graph comes back editable; change it, copy, and paste over the old one | Works with any program that keeps the picture as it is; no install, no links | Some presentation programs re-encode pictures and drop hidden data; needs testing on Windows with each program |
| C. Linked pictures | **Copy Link** / "Keep a picture up to date": Datum Plot writes the graph to a file beside the project and rewrites it whenever the graph changes. The slide inserts it as a linked picture (every presentation program can) and shows the new version when reopened | Works everywhere, open, simple | Editing starts in Datum Plot, not by double-clicking in the slide |

Recommendation: **C now** (reliable, every program), **B next** as an experiment, tested with the programs the
testers use. Also copy pictures as **vector** (SVG beside the PNG on the clipboard), so pasted graphs stay sharp.

## 3. Generic names instead of other companies' products

Today the window names other products about 60 times (buttons **PowerPoint**, **Word Report**, **Excel Workbook**,
texts like "paste into Word, PowerPoint or an email", "Excel-like", a few mentions of other graphing apps), and the
guide about 8 times.

Fix: name the thing and its file type, never the product:

| Today | New |
|---|---|
| PowerPoint | **Slides** (.pptx, .odp) |
| Word Report | **Report** (.docx, .odt) |
| Excel Workbook | **Workbook** (.xlsx, .ods) |
| "paste into Word, PowerPoint or an email" | "paste into documents, slides or an email" |
| "works with Excel" (copy and paste) | "works with spreadsheets" |
| mentions of other graphing apps | removed (the .pzfx import keeps the extension only) |

Recommendation: do it everywhere: window, help cards, guide (all three languages), CHANGELOG from now on. A
CLAUDE.md rule keeps it so.

## 4. OpenDocument formats (.ods, .odt, .odp)

| Format | Import | Export | How | Size |
|---|---|---|---|---|
| .ods (spreadsheet) | yes | yes (tables and results, like the workbook) | `odfpy` (pure Python, Apache-2.0), read with pandas' `odf` engine | small |
| .odt (report) | — | yes (like the .docx report: details, graphs with captions, results, methods) | `odfpy` | medium |
| .odp (slides) | — | yes (a graph per slide, results) | `odfpy` | medium |

`odfpy` adds about 1 MB to the Python runtime (runtime pack 4). The export buttons then ask for the format (the
open one or the other) in the Save dialog.

Recommendation: all three. They fit the open-source spirit, and LibreOffice/OnlyOffice/Euro-office users get files
in their own format.

## 5. Proposed releases (small steps)

- **0.3.3**: colours (1a–1c), generic names (3), linked pictures and vector copy (2C).
- **0.3.4**: OpenDocument import and export (4).
- **0.3.5**: (if wanted) pictures that carry their graph (2B), after testing on Windows.

## 6. Questions

1. Colours (1a–1c): go?
2. Copy and edit again: C (linked pictures) now, B later; or another choice?
3. Generic names everywhere (including the guide): go? Should the buttons show the extensions ("Slides (.pptx/.odp)") or just "Slides"?
4. OpenDocument: all three formats, and in 0.3.4 or together with 0.3.3?
