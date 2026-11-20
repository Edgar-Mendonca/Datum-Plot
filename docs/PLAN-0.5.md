# Datum Plot 0.5: validation and hardening (plan, questions first)

The user's request (2026-11-20): "We need to do a strict hardening test … there were issues in analysis (#67) … a strict and strong hardening test, evaluation and optimisation." **The user's answers (2026-11-20):** the reference values are only for checking, kept in the scratch area and not stored in the project or published (no fixtures, no report); R runs in the cloud workspace only, never in the app; real errors are fixed and released as consecutive 0.4.x versions (no jump to 0.5; the modules stay unplanned); where two methods are both valid, the user chooses: offer both as a choice with a ? explaining them, the reference's as the default. Parts A–F are done in that spirit; G (the report) is dropped.

## 1. Where we stand

- **41 analyses** in the engine (`analysis.KINDS` and `more_kinds()`), each with several options.
- About **35 test checks compare with an outside reference** (R, NIST, published examples), mostly in t-tests, ANOVA and regression. Many analyses are only checked by "it runs" (`py/tests/smoke.py`: 26 sample projects, 1,098 requests) or by values worked out by hand in the same way as the code, which cannot catch a wrong method.
- **#67** showed the gap: the two-way ANOVA table matched another program exactly, but the comparisons after a main-effects-only model did not follow the model. No test compared that case with a reference.
- R (the reference for most statistics) can be installed in the development container (`apt-get install r-base`, plus `r-cran-*` packages).

## 2. The aim

Every number Datum Plot shows, for every analysis and its main options, is checked against an **independent reference** (R's standard packages, NIST StRD, or a published worked example), and every analysis gives a correct answer or a clear message, never a crash or a wrong number, on awkward data.

## 3. The work

**A. Reference validation (the core).** For each analysis × its main options: a public dataset (R's own: PlantGrowth, warpbreaks, ToothGrowth, sleep, mtcars, airquality, lung, esoph…; NIST StRD for regression, ANOVA and nonlinear fits; published examples for materials and quality), the result computed in R with the standard package (stats, car, emmeans, afex/lme4, survival, drc, pROC, irr, boot, qcc…), stored as a JSON fixture with the R script that made it (`py/tests/reference/`). A test compares **every** number in our result with the fixture (to the digits shown). About 150 analysis × option cases.

**B. Consistency checks (properties that must always hold).** Reordering rows or data sets does not change P values; scaling or shifting the data scales or shifts estimates as it should; a t-test equals one-way ANOVA with two groups; adjusted P ≥ unadjusted; brackets show the same P as the table; comparisons follow the fitted model (LS means); excluded values really are left out; results with the interaction equal cell-mean comparisons.

**C. Awkward data (robustness).** Every analysis on: empty and one-value groups, all-equal values, ties, missing cells, unequal n, very small and very large numbers (#67's densities were 1e-6), thousands of rows, negative and zero values where logs are taken, names with symbols. Each must give a right answer or a plain message. Automated over all analyses × table shapes (an extension of the smoke test).

**D. Graphs equal results.** What is drawn is computed and checked: means, SD/SEM/CI error bars, medians and quartiles, whiskers, brackets and their stars, fitted curves and bands.

**E. The rest of the app.** Damaged and old project files, undo/redo after every edit, every op with bad input (fuzzing the Rust core), and the UI tests we have.

**F. Optimisation, measured.** Time every analysis and render on small and large data; fix only what is measurably slow (with a speed gate in the tests, as we have for edits).

**G. A validation report.** A page listing each analysis, its reference, our value, the reference value and the difference, rebuilt at every release: in Help › Validation and as a PDF beside the guides. Testers (like #67's) can check it themselves.

Each release fixes whatever fails; a difference that is a valid other convention (not an error) becomes an option, with the reference's default, and is written in the report.

## 4. Suggested releases (small steps)

| Release | Contents |
|---|---|
| 0.5.0 | R reference fixtures and the comparison harness; **compare groups**: t-tests, nonparametric, one-way (all comparisons), two-way (all comparisons, repeated measures, mixed model), three-way, ANCOVA, multiple t-tests, nested |
| 0.5.1 | Regression and fitting: linear (Deming, comparing lines), nonlinear fits and the model library, global fits, IC50/EC50, interpolation, AUC, splines (NIST StRD) |
| 0.5.2 | Relationships and survival: correlation, contingency, agreement, Bland-Altman, ROC, multiple/logistic/Poisson regression, PCA, clustering, survival, power, bootstrap, Bayes factors |
| 0.5.3 | Materials, quality, signals: tensile, Weibull, Arrhenius, S–N, DSC/TGA, control charts, factorial designs, peaks, Fourier, filters, wavelets |
| 0.5.4 | Awkward data (C) and graphs equal results (D) over every analysis |
| 0.5.5 | App hardening (E), measured optimisation (F), and the validation report (G) in Help and as a PDF |

## 5. What stays the same

Small releases, every one in the updater; the modules and Mac/Linux stay in the roadmap.

## 6. Questions for the user

1. **R for the references:** install R only where I build the reference files (the R scripts are kept in the repository so anyone can re-run them), and CI compares with the stored files (fast, recommended); or install R in CI too, so the references are recomputed on every push (slower, about 10 more minutes per run)?
2. **Numbering:** make this the **0.5 series** and move the modules to 0.6? Or keep going 0.4.26, 0.4.27…?
3. **Order:** compare groups first (the most used, and where #67 was), as in §4? Or another order?
4. **The validation report:** public, in Help and as a PDF with each release (recommended: it builds trust with users and journals)?
5. **When we differ from the reference but our way is also valid** (a different default, not an error): switch our default to the reference's and keep ours as an option (recommended), or keep ours and only explain the difference in the report?
