"""Engine tests: statistics against values from R, graphs render and report their geometry.
Run: python -m unittest discover -s py/tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

import matplotlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from datum import graph, stats  # noqa: E402


def table(cols, sets, excluded=()):
    return {"rows": max(len(c) for c in cols), "xTitle": "Time", "xUnits": "h", "yTitle": "Response", "yUnits": "", "sets": sets, "cols": cols, "excluded": [list(e) for e in excluded]}


REP3 = {"title": "Control", "entry": "rep", "reps": 3}


class Stats(unittest.TestCase):
    def test_describe_matches_r(self):
        # R: x <- c(2.1, 2.5, 2.9); mean(x); sd(x); sd(x)/sqrt(3); qt(.975, 2) * sd(x)/sqrt(3)
        d = stats.describe([2.1, 2.5, 2.9])
        self.assertAlmostEqual(d["mean"], 2.5, places=12)
        self.assertAlmostEqual(d["sd"], 0.4, places=12)
        self.assertAlmostEqual(d["sem"], 0.2309401077, places=9)
        self.assertAlmostEqual(d["ci"], 0.9936551, places=6)

    def test_ci_large_n(self):
        # R: x <- 1:20; qt(.975, 19) * sd(x) / sqrt(20)  -> 2.768811
        self.assertAlmostEqual(stats.describe(list(range(1, 21)))["ci"], 2.768811, places=5)

    def test_single_value_has_no_spread(self):
        d = stats.describe([4.0, None])
        self.assertEqual((d["n"], d["sd"], d["sem"], d["ci"]), (1, 0.0, 0.0, 0.0))
        self.assertIsNone(stats.describe([None]))

    def test_excluded_and_empty_cells_are_skipped(self):
        t = table([[1, 2, None], [10, 20, 30], [12, 99, 30], [None, 22, 30]], [REP3], excluded=[(1, 2)])
        s = stats.summarize(t)[0]
        self.assertEqual([p["x"] for p in s], [1, 2])  # row 3 has no X
        self.assertEqual(s[0]["values"], [10, 12])
        self.assertEqual(s[1]["values"], [20, 22])  # 99 is excluded
        self.assertAlmostEqual(s[1]["mean"], 21)

    def test_entered_mean_sd_n(self):
        t = table([[1], [5.0], [2.0], [4]], [{"title": "A", "entry": "msn", "reps": 1}])
        p = stats.summarize(t)[0][0]
        self.assertAlmostEqual(p["sem"], 1.0)
        self.assertAlmostEqual(p["ci"], 3.182446 * 1.0, places=5)  # R: qt(.975, 3)
        t["sets"][0]["entry"] = "mesn"
        p = stats.summarize(t)[0][0]
        self.assertAlmostEqual(p["sd"], 4.0)

    def test_set_columns(self):
        t = table([[0]] * 6, [REP3, {"entry": "msn", "reps": 1}])
        self.assertEqual(stats.set_columns(t), [(1, 3), (4, 3)])


class Graphs(unittest.TestCase):
    T = table([[1, 2, 4, 8], [1, 2, 3, 4], [1.2, 2.2, 3.1, 4.4], [0.9, 1.8, 2.7, 4.1], [2, 3, 4, 5], [2.1, 3.3, 4.2, 5.1], [None] * 4],
              [REP3, {"title": "Treated", "entry": "rep", "reps": 3}])

    def test_render_svg_and_geometry(self):
        r = graph.render(self.T, {"width": 80, "height": 60, "error": "sem"})
        self.assertTrue(r["svg"].lstrip().startswith("<?xml"))
        self.assertIn("<svg", r["svg"])
        self.assertAlmostEqual(r["w"], 80 / 25.4 * 72, places=3)
        x0, y0, x1, y1 = r["plot"]
        self.assertTrue(0 < x0 < x1 < r["w"] and 0 < y0 < y1 < r["h"])
        self.assertIsNotNone(r["legend"])  # two data sets
        self.assertEqual(len(r["points"]), 8)
        self.assertEqual(r["ylim"][0], 0)  # positive data: Y starts at zero
        self.assertIn("Time (h)", r["svg"])  # text stays text (editable in drawing programs)

    def test_log_axis_and_fixed_range(self):
        r = graph.render(self.T, {"x": {"scale": "log"}, "y": {"auto": False, "min": 0, "max": 10, "step": 2}})
        self.assertTrue(r["xlog"])
        self.assertEqual(r["ylim"], [0, 10])

    def test_each_replicate_frame_style_and_hidden_set(self):
        r = graph.render(self.T, {"points": "each", "style": "frame", "line": True, "sets": [{}, {"show": False}]})
        self.assertIsNone(r["legend"])
        self.assertEqual(len(r["points"]), 4)

    def test_empty_table(self):
        r = graph.render(table([[]], [REP3]), {})
        self.assertIn("Enter X and Y values", r["svg"])

    def test_export_formats(self):
        with tempfile.TemporaryDirectory() as d:
            for fmt in ("png", "svg", "pdf", "tiff", "eps"):
                p = os.path.join(d, f"g.{fmt}")
                graph.export(self.T, {}, fmt, p, dpi=150)
                self.assertGreater(os.path.getsize(p), 500, fmt)
            with open(os.path.join(d, "g.png"), "rb") as f:
                self.assertEqual(f.read(8), b"\x89PNG\r\n\x1a\n")
        self.assertTrue(graph.export(self.T, {}, "png", dpi=72)["data"].startswith("iVBOR"))


class Medians(unittest.TestCase):
    """0.3.12: median error bars, against R: quantile(x, c(.25, .75)) (type 7) and the order-statistic CI."""
    X = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100]

    def test_spread(self):
        self.assertEqual(graph.spread(self.X, "median_iqr"), (5.5, 2.25, 2.25))  # Q1 3.25, Q3 7.75
        self.assertEqual(graph.spread(self.X, "median_range"), (5.5, 4.5, 94.5))
        self.assertEqual(graph.spread(self.X, "median_ci"), (5.5, 3.5, 3.5))  # ranks 2 and 9 (coverage 97.9 %)
        m, lo, hi = graph.spread(self.X, "sem")
        self.assertAlmostEqual((m, lo), (14.5, 9.535023160258534))

    def test_every_graph_draws_medians(self):
        xy = table([[1, 2], [1, 2], [2, 3], [9, 50], [None] * 2, [None] * 2, [None] * 2], [REP3, {"title": "Treated", "entry": "rep", "reps": 3}])
        r = graph.render(xy, {"error": "median_iqr"})
        self.assertEqual([p[2] for p in r["points"] if p[0] == 0], [2.0, 3.0])  # medians, not means (4 and 18.3)
        col = {"name": "T", "kind": "column", "rows": 10, "sets": [{"title": "G", "entry": "rep", "reps": 1}], "cols": [[None] * 10, self.X], "excluded": [], "xTitle": "", "yTitle": "Y"}
        grp = {"kind": "grouped", "rows": 1, "rowTitles": ["L"], "sets": [{"title": "A", "entry": "rep", "reps": 10}], "cols": [[None]] + [[v] for v in self.X], "excluded": []}
        nest = dict(col, kind="nested", rows=4, sets=[{"title": "G", "entry": "rep", "reps": 3}], cols=[[None] * 4, [1, 2, 3, 4], [2, 3, 4, 5], [9, 9, 9, 9]])
        for kind in ("median_iqr", "median_range", "median_ci"):
            for t, extra in ((col, {"column": "bars"}), (col, {"column": "scatter"}), (grp, {}), (nest, {})):
                self.assertIn("<svg", graph.render(t, dict(extra, error=kind))["svg"])
        self.assertEqual(graph.render(col, {"column": "bars", "error": "median_iqr"})["points"][0][2], 5.5)


class Swarm(unittest.TestCase):
    """0.3.14: a crowded group is squeezed to its width, never piled in a column at the edge."""
    def test_crowded_groups_fit_without_a_column_at_the_edge(self):
        import numpy as np
        rng = np.random.default_rng(1)
        v = np.r_[rng.uniform(10, 70, 120), rng.uniform(100, 180, 40)]
        off = graph.swarm(v, 6.0, 0.05, 0.38)
        self.assertLessEqual(np.abs(off).max(), 0.38 + 1e-12)
        edge = np.sum(np.isclose(np.abs(off), np.abs(off).max()))
        self.assertLessEqual(edge, 6, "no pile of dots at the edge")
        self.assertLess(abs(off.mean()), 0.05, "the cloud stays centred")
        few = graph.swarm(np.array([1.0, 1, 1, 5]), 0.5, 0.1, 0.38)
        self.assertEqual(list(few), [0.0, 0.1, -0.1, 0.0])  # small groups: unchanged spacing

    def test_equal_values_are_centred(self):
        # 0.4.13 (#54): an even number of equal values sat half a dot to the right; odd numbers were already centred
        import numpy as np
        for n in (2, 3, 4, 5):
            off = graph.swarm(np.array([3.0] * n + [2.0]), 0.2, 0.1, 0.38)
            row = off[:n]
            self.assertAlmostEqual(row.max() + row.min(), 0.0, places=12, msg=f"{n} equal values")
            self.assertAlmostEqual(sorted(row)[1] - sorted(row)[0], 0.1, places=12, msg="still a dot apart")
            self.assertEqual(off[n], 0.0, "a lone dot stays in the middle")


class OrderAndColours(unittest.TestCase):
    """0.3.15: a column graph's own order of data sets (#23), and fill and border colours (#20)."""
    T = {"name": "T", "kind": "column", "rows": 3, "sets": [{"title": t, "entry": "rep", "reps": 1} for t in ("Alpha", "Beta", "Gamma")],
         "cols": [[None] * 3, [1, 2, 3], [2, 3, 4], [5, 6, 7]], "excluded": [], "xTitle": "", "yTitle": "Y"}

    def test_order_moves_groups_not_their_colours(self):
        import re
        svg = graph.render(self.T, {"column": "bars", "order": [2, 0]})["svg"]
        names = [n for n in re.findall(r">([A-Za-z]+)</text>", svg) if n in ("Alpha", "Beta", "Gamma")]
        self.assertEqual(names, ["Gamma", "Alpha", "Beta"])
        self.assertEqual(graph.ordered({"order": [2, 0]}, [0, 1, 2]), [2, 0, 1])
        self.assertEqual(graph.ordered({}, [0, 1, 2]), [0, 1, 2])

    def test_fill_and_border(self):
        st = graph.style_of({"sets": [{"color": "#111111", "fill": "#ABCDEF"}]}, 0)
        self.assertEqual((st["color"], st["fill"], st["edge"]), ("#111111", "#ABCDEF", graph.OKABE_ITO[0]))  # 0.3.21: the border follows the scheme, not the symbol
        svg = graph.render(self.T, {"column": "bars", "sets": [{"fill": "#abcdef", "edge": "#123456"}]})["svg"].lower()
        self.assertIn("#abcdef", svg)
        self.assertIn("#123456", svg)


class LegendAndBreak(unittest.TestCase):
    """0.3.20: column graphs show their groups' legend when it is on (#36); a break's position and ticks (#34)."""
    T = {"name": "T", "kind": "column", "rows": 3, "sets": [{"title": t, "entry": "rep", "reps": 1} for t in ("Alpha", "Beta")],
         "cols": [[None] * 3, [1, 2, 3], [20, 30, 40]], "excluded": [], "xTitle": "", "yTitle": "Y"}

    def test_column_legend_only_when_switched_on(self):
        for kind in ("bars", "scatter", "box", "violin"):
            on = graph.render(self.T, {"column": kind, "legend": {"show": True, "loc": "lower left", "groups": True}})
            off = graph.render(self.T, {"column": kind, "legend": {"show": True, "loc": "lower left"}})
            self.assertIsNotNone(on["legend"], kind)
            self.assertIsNone(off["legend"], "graphs made before 0.3.20 stay as they were")

    def test_break_shares_and_ticks(self):
        self.assertEqual(graph.break_shares({"breakRatio": 0.75}, True), [0.25, 0.75])
        self.assertEqual([round(v, 9) for v in graph.break_shares({"breakRatio": 5}, False)], [0.9, 0.1], "kept within 10–90 %")
        g = {"column": "bars", "y": {"breakFrom": 5, "breakTo": 15, "breakRatio": 0.3, "breakStep": 5}}
        r = graph.render(self.T, g)
        self.assertIn("<svg", r["svg"])
        with matplotlib.rc_context(graph.rc_for(g)):
            fig, ax, *_ = graph.figure(self.T, g)
        top, low = sorted(fig.axes, key=lambda a: -a.get_position().y0)[:2]
        share = low.get_position().height / (low.get_position().height + top.get_position().height)
        self.assertAlmostEqual(share, 0.3, delta=0.04)
        self.assertTrue(all(abs(t % 5) < 1e-9 for t in top.get_yticks()), "ticks every 5 above the break")


class Colours(unittest.TestCase):
    """0.3.21 (#38): bars and symbols take their colours separately; a symbol border; a fill strength."""
    T = LegendAndBreak.T

    def test_symbol_colour_leaves_the_bars_alone(self):
        st = graph.style_of({"sets": [{"color": "#ff0000"}]}, 0)
        self.assertEqual((st["color"], st["fill"], st["edge"]), ("#ff0000", graph.OKABE_ITO[0], graph.OKABE_ITO[0]))
        svg = graph.render(self.T, {"column": "bars", "points": "each", "sets": [{"color": "#ff0000", "markerEdge": "#00ff00", "alpha": 0.8}]})["svg"].lower()
        for c in ("#ff0000", "#00ff00"):
            self.assertIn(c, svg)
        self.assertIn("opacity: 0.8", svg, "the fill strength")


class Symbols(unittest.TestCase):
    """0.4.2: the symbols' own fill switch (#42), their border following the scheme, strengths and the error bars'
    colour (#43), the legend's border (#40) and its place on a graph with an axis break (#41)."""
    T = LegendAndBreak.T

    def fig(self, g):
        with matplotlib.rc_context(graph.rc_for(g)):
            return graph.figure(self.T, g)

    def dots(self, ax):
        return [l for l in ax.get_lines() if l.get_marker() not in ("None", None, "") and len(l.get_xdata()) == 3]

    def test_unfilled_bars_keep_filled_symbols(self):
        fig, ax, *_ = self.fig({"column": "bars", "points": "each", "sets": [{"filled": False}, {"filled": False, "markerFilled": False}]})
        a, b = self.dots(ax)
        self.assertNotEqual(matplotlib.colors.to_hex(a.get_markerfacecolor()), "#ffffff", "#42: the bars' switch leaves the symbols")
        self.assertEqual(matplotlib.colors.to_hex(b.get_markerfacecolor()), "#ffffff")

    def test_symbol_border_follows_the_scheme_and_strengths(self):
        fig, ax, *_ = self.fig({"column": "bars", "points": "each", "sets": [{"color": "#ff0000", "markerAlpha": 0.5, "markerEdgeAlpha": 0.25, "edgeAlpha": 0.6}]})
        d = self.dots(ax)[0]
        self.assertEqual(matplotlib.colors.to_hex(d.get_markeredgecolor()), graph.OKABE_ITO[0].lower(), "#43: a new fill leaves the automatic border")
        self.assertAlmostEqual(matplotlib.colors.to_rgba(d.get_markerfacecolor())[3], 0.5)
        self.assertAlmostEqual(matplotlib.colors.to_rgba(d.get_markeredgecolor())[3], 0.25)
        self.assertTrue(any(abs(p.get_edgecolor()[3] - 0.6) < 1e-9 for p in ax.patches), "the bars' border strength")

    def test_error_bar_colour(self):
        svg = graph.render(self.T, {"column": "bars", "error": "sd", "sets": [{"errColor": "#123456"}]})["svg"].lower()
        self.assertIn("#123456", svg)
        svg = graph.render(Graphs.T, {"sets": [{"errColor": "#654321"}]})["svg"].lower()
        self.assertIn("#654321", svg, "XY graphs too")

    def test_automatic_error_bars_follow_the_scheme(self):
        # 0.4.3 (#43): a new symbol fill leaves automatic error bars alone on bar graphs.
        fig, ax, *_ = self.fig({"column": "bars", "error": "sd", "points": "each", "sets": [{"color": "#ff0000"}]})
        from matplotlib.collections import LineCollection
        cols = {matplotlib.colors.to_hex(c) for lc in ax.collections if isinstance(lc, LineCollection) for c in lc.get_colors()}
        self.assertIn(graph.OKABE_ITO[0].lower(), cols)
        self.assertNotIn("#ff0000", cols)

    def test_a_styles_look_for_every_data_set(self):
        # 0.4.9 (#46): black error bars and 35 % symbol fills for every data set, unless one sets its own
        look = {"errColor": "#000000", "markerAlpha": 0.35, "markerFilled": True}
        st = graph.style_of({"setLook": look, "sets": [{}, {"errColor": "#ff0000", "markerAlpha": None}]}, 1)
        self.assertEqual((st["err"], st["malpha"]), ("#ff0000", 0.35))
        st = graph.style_of({"setLook": look}, 4)
        self.assertEqual((st["err"], st["malpha"], st["mfilled"]), ("#000000", 0.35, True), "a data set added later too")
        self.assertIsNone(graph.style_of({}, 0)["err"])

    def test_legend_border_at_full_strength(self):
        fig, ax, leg, _ = self.fig({"column": "bars", "legend": {"show": True, "groups": True}})
        h = leg.legend_handles[0]
        self.assertAlmostEqual(h.get_facecolor()[3], 0.35)
        self.assertAlmostEqual(h.get_edgecolor()[3], 1.0, msg="#40")

    def test_legend_with_a_break_uses_the_whole_graph(self):
        g = {"column": "bars", "legend": {"show": True, "groups": True, "loc": "upper left"}, "y": {"breakFrom": 5, "breakTo": 15}}
        fig, ax, leg, _ = self.fig(g)
        fig.canvas.draw()
        top = max(fig.axes, key=lambda a: a.get_position().y0)
        r, box = fig.canvas.get_renderer(), top.get_window_extent()
        self.assertGreater(leg.get_window_extent(r).y1, box.y0, "#41: at the top of the graph, not of the lower panel")


class Brackets(unittest.TestCase):
    """0.4.6 (#52): many groups and brackets: labels never overlap one another, and the axis stays sensible."""

    def fig(self, k, height=60):
        rng = np.random.default_rng(1)
        means = [2, 2.2, 3, 3.1, 5, 2.1, 4, 6][:k]
        T = {"name": "T", "kind": "column", "rows": 5, "sets": [{"title": f"G{i + 1}", "entry": "rep", "reps": 1} for i in range(k)],
             "cols": [[None] * 5] + [list(m + rng.normal(0, 0.4, 5)) for m in means], "excluded": [], "xTitle": "", "yTitle": "Y"}
        g = {"column": "bars", "points": "each", "width": 80, "height": height}
        ov = [{"kind": "anova", "sets": [], "options": {"posthoc": "tukey", "brackets": "all"}}]
        with matplotlib.rc_context(graph.rc_for(g)):
            fig, ax, *_ = graph.figure(T, g, ov)
        fig.canvas.draw()
        return fig, ax

    def test_labels_do_not_overlap(self):
        for k, h in ((4, 60), (6, 60), (8, 130)):
            fig, ax = self.fig(k, h)
            r = fig.canvas.get_renderer()
            boxes = [t.get_window_extent(r) for t in ax.texts if t.get_text() in ("ns", "*", "**", "***", "****")]
            self.assertEqual(len(boxes), k * (k - 1) // 2)
            for i, a in enumerate(boxes):
                for b in boxes[i + 1:]:
                    self.assertFalse(a.overlaps(b), f"{k} groups: two labels overlap")
            # no label crosses another bracket's line (its own line lies just below it)
            lines = [ax.transData.transform([(l.get_xdata()[1], l.get_ydata()[1]), (l.get_xdata()[2], l.get_ydata()[2])])
                     for l in ax.get_lines() if len(l.get_xdata()) == 4]
            for t in boxes:  # every line above a label, over the same columns, leaves a clear gap (old: touching)
                for (x1, y), (x2, _) in lines:
                    if y > t.y0 + 1 and min(x1, x2) < t.x1 and t.x0 < max(x1, x2):
                        self.assertGreaterEqual(y - t.y1, 1.5, f"{k} groups: a label touches another bracket's line")

    def test_a_graph_chooses_its_own_brackets(self):
        # 0.4.7 (#51): the analysis says "significant pairs, stars"; this graph says "all pairs, P values"
        rng = np.random.default_rng(2)
        T = {"name": "T", "kind": "column", "rows": 6, "sets": [{"title": f"G{i}", "entry": "rep", "reps": 1} for i in range(4)],
             "cols": [[None] * 6] + [list(m + rng.normal(0, 0.3, 6)) for m in (1, 1.1, 3, 5)], "excluded": [], "xTitle": "", "yTitle": "Y"}
        ov = [{"id": 7, "kind": "anova", "sets": [], "options": {"posthoc": "tukey", "brackets": "sig", "ptext": "stars"}}]
        labels = lambda g: [t.get_text() for t in graph.figure(T, g, ov)[1].texts if t.get_text() == "ns" or t.get_text().startswith(("*", "P"))]
        own = labels({"column": "bars"})
        self.assertTrue(own and all(x.startswith("*") for x in own) and len(own) < 6, own)
        mine = labels({"column": "bars", "bracketOpts": {"7": {"brackets": "all", "ptext": "p"}}})
        self.assertEqual(len(mine), 6)
        self.assertTrue(all(x.startswith("P") for x in mine), mine)
        self.assertFalse(labels({"column": "bars", "bracketOpts": {"7": {"brackets": "none"}}}))
        self.assertEqual(labels({"column": "bars", "bracketOpts": {"8": {"brackets": "none"}}}), own, "another analysis's choice changes nothing")

    def test_the_axis_stays_sensible(self):
        fig, ax = self.fig(8)  # 28 brackets on a 60 mm graph: smaller labels, not a runaway axis
        self.assertLess(ax.get_ylim()[1], 40)


class LabelsAndSizes(unittest.TestCase):
    """0.4.13 (#55): the X labels' angle (automatic only when names would overlap, or as chosen) and text sizes."""

    def fig(self, names, g):
        T = {"name": "T", "kind": "column", "rows": 3, "sets": [{"title": n, "entry": "rep", "reps": 1} for n in names],
             "cols": [[None] * 3] + [[1, 2, 3]] * len(names), "excluded": [], "xTitle": "", "yTitle": "Response (units)"}
        g = {"column": "bars", "title": "Title", "legend": {"show": True, "groups": True}, **g}
        with matplotlib.rc_context(graph.rc_for(g)):
            return graph.figure(T, g)

    def angles(self, ax):
        return {t.get_rotation() for t in ax.get_xticklabels() if t.get_text()}

    def test_automatic_tilts_only_when_names_overlap(self):
        long = ["Untreated control", "Low dose treatment", "High dose treatment", "Vehicle only control", "Positive control"]
        self.assertEqual(self.angles(self.fig(long, {"width": 60})[1]), {30.0})
        self.assertEqual(self.angles(self.fig(["A", "B", "C"], {"width": 80})[1]), {0.0})

    def test_a_chosen_angle_always_applies(self):
        for a in ("0", "45", "90"):
            self.assertEqual(self.angles(self.fig(["A", "B", "C"], {"xAngle": a})[1]), {float(a)})

    def test_text_sizes(self):
        fig, ax, leg, _ = self.fig(["A", "B"], {"fontSize": 10, "titleSize": 14, "axisTitleSize": 12, "tickSize": 7, "legendSize": 6})
        self.assertEqual((ax.title.get_fontsize(), ax.yaxis.label.get_fontsize()), (14, 12))
        self.assertEqual(ax.get_xticklabels()[0].get_fontsize(), 7)
        self.assertEqual(leg.get_texts()[0].get_fontsize(), 6)
        plain = self.fig(["A", "B"], {"fontSize": 10})
        self.assertEqual(plain[1].yaxis.label.get_fontsize(), 10, "unchanged when not set")


class Titles(unittest.TestCase):
    """0.4.14 (#56): a subtitle, and long titles wrapped so they stay inside the graph."""
    T = {"name": "T", "kind": "column", "rows": 3, "sets": [{"title": t, "entry": "rep", "reps": 1} for t in ("Control", "Drug X", "Drug Y")],
         "cols": [[None] * 3, [1, 1.2, 0.9], [1.6, 1.8, 1.7], [2.6, 2.4, 2.9]], "excluded": [], "xTitle": "", "yTitle": "Relative expression of the target gene (fold change)"}

    def fig(self, g):
        g = {"column": "bars", "width": 70, "height": 65, **g}
        with matplotlib.rc_context(graph.rc_for(g)):  # drawn inside the graph's settings, as the app does
            fig, ax, *_ = graph.figure(self.T, g)
            fig.canvas.draw()
        return fig, ax

    def test_long_titles_wrap_inside_the_graph(self):
        fig, ax = self.fig({"title": "Effect of drug X and drug Y on gene expression after 24 hours", "subtitle": "HeLa cells, n = 3 per group"})
        r, fb = fig.canvas.get_renderer(), fig.bbox
        self.assertIn("\n", ax.get_title())
        self.assertIn("\n", ax.yaxis.label.get_text(), "the long axis title too")
        subs = [t for t in ax.texts if t.get_text() == "HeLa cells, n = 3 per group"]
        self.assertEqual(len(subs), 1)
        for t in (ax.title, subs[0]):
            b = t.get_window_extent(r)
            self.assertTrue(fb.x0 - 1 <= b.x0 and b.x1 <= fb.x1 + 1, "inside the graph")
        self.assertLess(subs[0].get_window_extent(r).y1, ax.title.get_window_extent(r).y0 + 1, "the subtitle sits under the title")

    def test_short_titles_and_hidden_titles_stay(self):
        fig, ax = self.fig({"title": "Short", "subtitle": "Sub"})
        self.assertEqual(ax.get_title(), "Short")
        fig, ax = self.fig({"title": "Short", "subtitle": "Sub", "showTitle": False})
        self.assertEqual(ax.get_title(), "")
        self.assertFalse([t for t in ax.texts if t.get_text() == "Sub"], "no subtitle when the title is hidden")


class GroupedShapes(unittest.TestCase):
    """0.4.16 (#60): grouped tables as box plots or violins, and the rows' own order and hidden rows."""
    T = {"name": "T", "kind": "grouped", "rows": 3, "rowTitles": ["Tissue 1", "Tissue 2", "Tissue 3"],
         "sets": [{"title": "Low", "entry": "rep", "reps": 3}, {"title": "High", "entry": "rep", "reps": 3}],
         "cols": [[None] * 3, [1, 2, 3], [1.5, 2.5, 3.5], [1.2, 2.2, 3.2], [4, 5, 6], [4.4, 5.4, 6.4], [4.2, 5.2, 6.2]], "excluded": [], "xTitle": "", "yTitle": "Y"}

    def fig(self, g):
        with matplotlib.rc_context(graph.rc_for(g)):
            return graph.figure(self.T, g)

    def test_box_and_violin(self):
        fig, ax, leg, pts = self.fig({"column": "box", "points": "each"})
        self.assertEqual(len(pts), 6, "one box per data set in each row")
        self.assertEqual([t.get_text() for t in leg.get_texts()], ["Low", "High"])
        self.assertTrue(any(p.__class__.__name__ == "PathPatch" for p in ax.patches), "boxes drawn")
        fig, ax, leg, pts = self.fig({"column": "violin"})
        self.assertEqual(len(pts), 6)
        self.assertTrue(ax.collections, "violins drawn")

    def test_rows_in_their_own_order_and_hidden(self):
        fig, ax, *_ = self.fig({"column": "bars", "rowOrder": [2, 0, 1], "rowHide": [1]})
        self.assertEqual([t.get_text() for t in ax.get_xticklabels()], ["Tissue 3", "Tissue 1"])


class Patterns(unittest.TestCase):
    """0.4.17 (#59): fill patterns on bars, boxes and violins, in the legend too; their colour."""

    def test_patterns_everywhere(self):
        T = GroupedShapes.T
        sets = [{"pattern": "diag", "patternColor": "#ff0000"}, {"pattern": "dots"}]
        for kind in ("bars", "box", "violin"):
            g = {"column": kind, "sets": sets}
            with matplotlib.rc_context(graph.rc_for(g)):
                fig, ax, leg, _ = graph.figure(T, g)
            arts = list(ax.patches) + list(ax.collections)
            hatches = {a.get_hatch() for a in arts if a.get_hatch()}
            self.assertEqual(hatches, {"///", "..."}, kind)
            self.assertEqual({h.get_hatch() for h in leg.legend_handles}, {"///", "..."}, f"{kind}: in the legend")
        red = [a for a in arts if a.get_hatch() == "///"]
        self.assertEqual(matplotlib.colors.to_hex(red[0].get_hatchcolor()), "#ff0000")
        st = graph.style_of({"sets": [{"pattern": "nope"}]}, 0)
        self.assertIsNone(st["hatch"], "unknown patterns draw nothing")


class Worker(unittest.TestCase):
    def test_protocol(self):
        p = subprocess.Popen([sys.executable, os.path.join(os.path.dirname(HERE), "worker.py")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.assertTrue(json.loads(p.stdout.readline())["ready"])
        for q in ({"cmd": "ping"}, {"cmd": "nope"}, {"cmd": "render", "table": Graphs.T, "graph": {}}):
            p.stdin.write(json.dumps(q) + "\n")
            p.stdin.flush()
        a, b, c = (json.loads(p.stdout.readline()) for _ in range(3))
        p.stdin.close()
        p.wait(10)
        self.assertTrue(a["ok"] and "matplotlib" in a)
        self.assertFalse(b["ok"])
        self.assertIn("Unknown request", b["error"])
        self.assertTrue(c["ok"] and "<svg" in c["svg"])


if __name__ == "__main__":
    unittest.main()


class Import(unittest.TestCase):
    def test_csv_and_semicolon_decimal_comma(self):
        from datum import io as dio
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "a.csv")
            open(p, "w", encoding="utf-8").write("Strain,Sample 1,Sample 2\n0,0,0\n0.01,70.5,68\n\n")
            s = dio.read_file(p)["sheets"][0]
            self.assertEqual(s["rows"], [["Strain", "Sample 1", "Sample 2"], ["0", "0", "0"], ["0.01", "70.5", "68"]])
            p = os.path.join(d, "b.txt")
            open(p, "w", encoding="cp1252").write("Temp;Résistance\n20;1,5\n30;2,25\n")
            s = dio.read_file(p)["sheets"][0]
            self.assertEqual(s["rows"][0][1], "Résistance")
            self.assertEqual(s["rows"][2], ["30", "2.25"])

    def test_excel_every_sheet(self):
        from openpyxl import Workbook
        from datum import io as dio
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "w.xlsx")
            wb = Workbook()
            wb.active.title = "Run 1"
            for r in (["T", "R"], [1, 2.5], [2.0, None]):
                wb.active.append(r)
            wb.create_sheet("Empty")
            wb.save(p)
            s = dio.read_file(p)["sheets"]
            self.assertEqual([x["name"] for x in s], ["Run 1", "Empty"])
            self.assertEqual(s[0]["rows"], [["T", "R"], ["1", "2.5"], ["2", ""]])
            self.assertEqual(s[1]["rows"], [])
        with self.assertRaises(ValueError):
            dio.read_file("x.ods")
