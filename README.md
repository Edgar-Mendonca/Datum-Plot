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

Datum Plot keeps a project as a chain: **data tables → analyses → results → graphs → layouts**. Everything stays linked, so changing a value redraws its graphs.

- **Data tables** that work like Excel: an X column and data sets with replicates, or a mean with SD or SEM and N. Paste from Excel, fill series, exclude a value without deleting it.
- **Publication-quality graphs** drawn with matplotlib: means with SD, SEM, 95% CI or range, linear or log axes, colour-blind-safe colours, sizes in millimetres for journal columns.
- **Export** as PNG or TIFF at any dpi, or as SVG, PDF and EPS with editable text. Copy into Word or PowerPoint. Print with headers, footers and captions.
- **Statistics and curve fitting** arrive release by release on the built-in Python engine (numpy, SciPy): column statistics in 0.1.1, t-tests, ANOVA and nonlinear regression in 0.2.0. See the [roadmap](docs/MEMORY.md#3-roadmap).

Everything stays on your computer. The only network call is the update check to GitHub.

## Install

Download `DatumPlot-x.y.z-setup.exe` from [Releases](https://github.com/Edgar-Mendonca/Datum-Plot/releases/latest) and run it. It installs for your user account, with its own Python, and updates itself from the Home page.

## Build

Rust (stable), Node 22 and Python 3.13 with `pip install -r py/requirements.txt`:

```
npm ci
npm run build:ui
cargo run -p datum-plot          # the app, using the Python on your PATH (or DATUM_PYTHON)
cargo test --workspace && npm run test:py && npm run test:ui
```

Datum Plot is the second app of the Datum family, after [Datum Plan](https://github.com/Edgar-Mendonca/Datum-Plan). MIT licence; third-party notices in [NOTICE](NOTICE).
