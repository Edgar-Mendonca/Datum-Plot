# Plan 0.3.12: testers' five issues and dates, second step

Session 11. A tester's five issues, passed on by the user, to be fixed in one release together with dates II (A20).

## 1. The testers' issues

| # | Problem | Cause | Fix |
|---|---|---|---|
| 1 | Renaming a data set (or table) and pressing Enter in the name box closes the window without the new name | A text box saves its text when it loses focus; Enter pressed OK first, so OK read the old name | Enter first ends typing in the box (so the text is taken), then presses OK. Every window, not only Rename |
| 2 | Error bars show only means; testers want the median | Only mean ± SD/SEM/CI/range existed | Three new error bars: **Median and interquartile range**, **Median and range**, **Median ± 95% CI** (order-statistic interval, ranks from the binomial distribution, coverage ≥ 95 %). The point or bar is the median. On XY, column, grouped and nested graphs. Median ± SEM is not offered: the SEM belongs to the mean |
| 3 | Right-click the Y axis › Format Axes opens Format Graph on the X axis | The menu command always opened the X Axis page | The menu opens the axis under the mouse (X, Y or the right Y axis), as double-click already did |
| 4 | Long data set titles ("Solvant + Drug A + Drug B - 24h") are cut off; columns cannot be widened | Titles were kept on one line; the drag handle at a heading's edge was hard to find | Titles wrap onto up to three lines and the heading row grows to fit; the edge shows a line on hover. Drag a heading's right edge to widen a column; double-click it to fit the title and values (since 0.2.21) |
| 5 | Each Format Axes / Format Graph command opens one more window (20 can stack); × closes the newest window, not the one clicked | Every command opened a new window; × closed the top of the stack | One Format Graph window: a new command switches it to the page asked for (another graph's command replaces it). × , Close, OK and Esc close their own window |

Found while building: the date axis's **Tick labels** choice (0.3.11) was not kept in the project; it is now.

## 2. Dates, second step (A20, as planned in PLAN-0.3.11)

- Pasting date-like text into a number X column asks once "Treat the X column as dates?"; the Import window ticks "The X column holds dates" when it sees dates (a first word such as "Date" counts as the title).
- Format Graph › X Axis on dates: **Major ticks every** day, week (Mondays), 2 weeks, month, 3 months or year; minor ticks one unit finer.
- Notes › **＋ Line at a date…**: a dashed vertical line across the graph at a typed date, with a label (on number axes: at an X value).
- Column formulas: `date(y, m, d)`, `today()`, `year(X)`, `month(X)`, `day(X)`, `days(b, a)`, `hours(b, a)`.
- Fits on dates: the X-intercept and interpolated X values as dates, and the fitted value at the first date.

## 3. Replies to the tester (plain language)

1. Fixed: pressing Enter in the name box now keeps the new name.
2. Added: Error Bars › Median and interquartile range, Median and range, Median ± 95% CI. The median goes with these spreads; ± SEM belongs to the mean.
3. Fixed: right-click on an axis › Format Axes opens that axis.
4. Long titles now wrap onto up to three lines. To widen a column, drag the right edge of its heading; double-click the edge to fit.
5. Fixed: one Format Graph window, which switches page; × closes the window you click.

## 4. Answers

The user (2026-11-02): "solve all of this in one update", together with the planned dates II.
