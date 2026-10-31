<div align="center">

<img src="docs/brand/datum-plot-icon.svg" width="88" alt="Datum Plot">

# Datum Plot

**Scientific graphs, statistics and curve fitting: one app for Windows.**

[![Latest release](https://img.shields.io/github/v/release/Edgar-Mendonca/Datum-Plot?label=release&color=0E8C7F)](https://github.com/Edgar-Mendonca/Datum-Plot/releases/latest)
[![CI](https://img.shields.io/github/actions/workflow/status/Edgar-Mendonca/Datum-Plot/ci.yml?label=CI&logo=githubactions&logoColor=white)](https://github.com/Edgar-Mendonca/Datum-Plot/actions/workflows/ci.yml)
[![Downloads](https://img.shields.io/github/downloads/Edgar-Mendonca/Datum-Plot/total?color=0E8C7F)](https://github.com/Edgar-Mendonca/Datum-Plot/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-0E8C7F)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078D4?logo=windows&logoColor=white)](https://github.com/Edgar-Mendonca/Datum-Plot/releases/latest)
[![Rust](https://img.shields.io/badge/Rust-shell-B7410E?logo=rust&logoColor=white)](crates/core)
[![Python](https://img.shields.io/badge/Python-numpy%20·%20SciPy%20·%20matplotlib-3776AB?logo=python&logoColor=white)](py)
[![Tauri 2](https://img.shields.io/badge/Tauri-2-24C8DB?logo=tauri&logoColor=white)](https://tauri.app)
[![SolidJS](https://img.shields.io/badge/SolidJS-UI-2C4F7C?logo=solid&logoColor=white)](ui/src)

[![Download for Windows](https://img.shields.io/badge/Download_for_Windows-0E8C7F?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/Edgar-Mendonca/Datum-Plot/releases/latest)
[![What's new](https://img.shields.io/badge/What%27s_new-3FC2B2?style=for-the-badge&logo=readthedocs&logoColor=white)](CHANGELOG.md)
[![Report an issue](https://img.shields.io/badge/Report_an_issue-C0392B?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Edgar-Mendonca/Datum-Plot/issues/new)
[![Memory and roadmap](https://img.shields.io/badge/Memory_%26_roadmap-0C1A2B?style=for-the-badge&logo=bookstack&logoColor=white)](docs/MEMORY.md)

</div>

<img src="docs/images/graph.png" alt="Datum Plot: a dose-response graph with Format Graph beside it" width="100%">

## What it does

Datum Plot is part of Datum; see its page: https://edgar-mendonca.github.io/Datum/apps/plot

Datum Plot keeps a project as a chain: **data tables → analyses → results → graphs → layouts**. Everything stays linked, so changing a value redraws its graphs.

- **Data tables** that work like a spreadsheet: XY tables (an X column and data sets with replicates, or a mean with SD or SEM and N) and column tables (one group per column). Paste from a spreadsheet, fill series, exclude a value without deleting it. **Worksheets** with free columns (X, Y, Y error), units and comments, and **column formulas** such as `log10(A)` or `(B - mean(B)) / sd(B)` that update as the data change.
- **Publication-quality graphs** drawn with matplotlib: means with SD, SEM, 95% CI or range, linear or log axes, colour-blind-safe colours, sizes in millimetres for journal columns.
- **Export** as PNG or TIFF at any dpi, or as SVG, PDF and EPS with editable text; every graph as slides (.pptx) or a report with graphs, results and methods (.docx); posters and slides as page layouts. Copy into documents and slides. Print with headers, footers and captions.
- **Import** CSV, TXT and .xlsx files, the tables of .pzfx projects, 96- and 384-well plates, and many runs at once. Large data sets (hundreds of thousands of points) stay quick, and a region tool gives the statistics of any part of a curve.
- **Statistics and regression** on the built-in Python engine (numpy, SciPy, statsmodels, lmfit): descriptive statistics, normality, outliers, t-tests, one-way ANOVA with multiple comparisons, nonparametric tests, effect sizes, correlation, power; linear regression (fit ranges, Deming, comparing lines), curve fitting with a model library or your own equation, global fits and model comparison, area under the curve and smoothing; multiple, logistic and Poisson regression, principal components and clustering on tables of many variables; survival analysis (Kaplan-Meier curves, median survival, log-rank test, hazard ratios); nested t-tests and ANOVA for subgroups within groups. Results stay linked to the data, explain themselves and give methods text.
- **Matrices and 3D**: Z values on an X–Y grid as contour maps, heat maps or 3D surfaces; surface fits (plane, quadratic with its maximum or minimum, cubic, 2D Gaussian peak); polar graphs of XY data.
- **Peaks and signals**: find peaks above a straight or polynomial baseline (positions, heights, widths, areas), fit them as Gaussian, Lorentzian or Voigt peaks; Fourier spectra, low-, high- and band-pass filters, resampling.
- **Materials testing**: tensile tests (modulus, yield, UTS, elongation, toughness), Weibull strength, Arrhenius activation energies, S–N fatigue curves (Basquin, with run-outs), DSC peaks (onset, peak temperature, enthalpy) and TGA steps (onset, mass lost, residue).
- **Column graphs** (dots, bars, box plots, violins) with significance stars, journal styles and colour-blind-safe schemes. Export every graph at once, or the whole project to a spreadsheet (.xlsx). More arrives in releases: see the [roadmap](docs/MEMORY.md#3-roadmap).

Everything stays on your computer. The only network call is the update check to GitHub.

## Install

Download `DatumPlot-x.y.z-setup.exe` from [Releases](https://github.com/Edgar-Mendonca/Datum-Plot/releases/latest) and run it. It installs for your user account, with its own Python, and updates itself from the Home page.

## The Python console

Tools › **Python Console** runs your own Python on the project's data, inside the app (nothing else to install):

1. **Write** code in the box at the top. Your tables are ready as pandas DataFrames: `tables` lists them, `table(0)` is the first, `tables['Name']` one by its name. Columns are named after the data sets (replicates as `Control 1`, `Control 2`), X first.
2. **Run** it with ▶ Run or **Ctrl+Enter**. What you `print`, the value of the last line and any `plt` figure appear underneath; an error names the line.
3. **Keep going**: variables last between runs (Reset clears them). `np`, `pd`, `stats` (scipy.stats), `scipy` and `plt` are ready.
4. **Put results back**: `new_table('Name', data)` adds a table to the project; `result('Analysis name')` gives an analysis's numbers.
5. **Save** code you reuse with Save As My Analysis, and run it again from Tools › My Analyses.

```python
df = table(0)
fit = stats.linregress(df.iloc[:, 0], df.iloc[:, 1])
print(f"slope {fit.slope:.4g}, R² {fit.rvalue**2:.4f}")
new_table("Log values", {"X": df.iloc[:, 0], "log10 Y": np.log10(df.iloc[:, 1])})
```

The ⓘ How to use button in the console and the ? beside it in the ribbon show the same guide. Code runs only when you press Run; projects never contain code, so opening someone else's project never runs anything.

## How to cite

If Datum Plot helped your work, please cite it with the version you used (File › Updates shows it):

> Mendonca, E. (2026). *Datum Plot* (Version 0.3.4) [Computer software]. https://github.com/Edgar-Mendonca/Datum-Plot

```bibtex
@software{datum_plot,
  author  = {Mendonca, Edgar},
  title   = {Datum Plot},
  version = {0.3.4},
  year    = {2026},
  url     = {https://github.com/Edgar-Mendonca/Datum-Plot},
  license = {MIT}
}
```

GitHub's **Cite this repository** button (from [CITATION.cff](CITATION.cff)) gives the same in APA and BibTeX. Every result's **methods text** already names Datum Plot and the Python library behind the calculation (for example SciPy or statsmodels); cite those too if your journal asks for it.

## Build

Rust (stable), Node 22 and Python 3.13 with `pip install -r py/requirements.txt`:

```
npm ci
npm run build:ui
cargo run -p datum-plot          # the app, using the Python on your PATH (or DATUM_PYTHON)
cargo test --workspace && npm run test:py && npm run test:ui
```

Datum Plot is the second app of the Datum family, after [Datum Plan](https://github.com/Edgar-Mendonca/Datum-Plan). MIT licence; third-party notices in [NOTICE](NOTICE).
