# Plan 0.3.11: dates and times

Session 10. Datum Plan's brief (PLOT-DATES.md, passed on by the user) asks Datum Plot to read, show, graph and analyse
dates, as an option per column, and to receive Plan's time charts with `xFormat: "date"`.

## 1. Compatibility check (done before any change)

| Brief | Datum Plot today | Fit |
|---|---|---|
| Value = days since 1970-01-01, fraction = time of day | matplotlib 3.11 in the app uses exactly this epoch (`dates.get_epoch()` = 1970-01-01) | ✅ no conversion |
| `Table.xFormat` optional, `.dplot` stays format 1 | Project JSON ignores unknown fields and every field has a default; `FORMAT = 1` | ✅ old files unchanged, new field optional |
| Plan's sample file (`format`, `info.notes`, `ui`, `rowTitles`, graph `sets` with `symbol: "none"`) | All these fields exist with the same names | ✅ opens today, shows 20738… until `xFormat` is read |
| Dates in .xlsx files arrive as ISO text | `io.py` already turns .xlsx dates into ISO text | ✅ only the parsing is missing |
| Typed text → number in Rust (`doc::number`) | Exists; a date stays empty today | ✅ add `doc::date_number` beside it |
| CSV export of tables | Datum Plot has no CSV export of tables (workbooks only: .xlsx/.ods) | ⚠ "CSV" means: workbooks write real dates; CSV only in notebook exports |
| Guide "both languages" | Datum Plot's guide has three (en, zh, fr) | ⚠ all three get the section |
| Column formulas with date functions | Formulas run in Python (`sheet.py`) | ✅ add DATE, TODAY, YEAR, MONTH, DAY, DAYS |
| Descriptive statistics of a date column | Analyses read the Y data sets; X is never "described" | ⚠ only when Y date columns come (later) |

Nothing existing changes unless a column is set to Date: numbers, analyses, graphs and files behave as now.

## 2. Proposed releases (small steps)

**0.3.11 — dates I (what the Plan hand-off needs):**
- Core: `Table.x_format` ("", "date", "datetime"), clamped on loading; `Op::XFormat` (undoable); `doc::date_number(s, day_first)` for ISO, d/m/y or m/d/y, month names (`5-Nov-26`, `5 Nov 2026`, `Nov 5, 2026`), times; impossible dates refused; typing and pasting into a date X column use it.
- Options: "Dates are written day first / month first" (default from the system's language).
- Table: X column heading › Format › Number / Date / Date and time, with a display format (`5 Nov 2026`, `05-Nov-26`, `2026-11-05`, `05/11/2026`, `Nov 2026`, with or without the time).
- Graphs: date X axis (`AutoDateLocator`, `ConciseDateFormatter`); Format Graph › X Axis: tick labels (Auto, Day month, Month year, ISO, Week), min and max typed as dates; hover shows the date; every export keeps the date ticks.
- Analyses: fits and regressions on dates report slopes "per day".
- Workbook export (.xlsx/.ods): date columns as real dates.
- Plan's sample opens with dates in the table and on the axis, no questions asked.

**0.3.12 — dates II:**
- Detection: pasting or importing date-like text into a number X column offers once "Treat as dates?".
- Format Graph: major step (days, weeks, months), minor ticks; annotations at a typed date (a vertical line at a date).
- Column formulas: DATE, TODAY, YEAR, MONTH, DAY, DAYS (differences in days or hours).
- Intercepts and fitted values shown as dates where meaningful.

**Later** (as the brief says): date columns among Y values, durations (h:mm), working-day axes.

The roadmap then moves by two: wavelets 0.3.13, digitizer 0.3.14, Bayesian tests 0.3.15, Mac and Linux 0.3.16.

## 3. Questions

1. Dates in two releases (0.3.11, 0.3.12) as above, before wavelets — or all in one?
2. Default day order: from the system's language (recommended), or always day first?
3. Display format default `5 Nov 2026` (as the brief says)?

## 4. Answers (2026-11-01)

The user: "go ahead and release 0.3.11 as per your recommendation". Two releases as proposed; the day order from the
system's language on the first start; "5 Nov 2026" as the default display.
