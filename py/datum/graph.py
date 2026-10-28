"""Graphs with matplotlib in the Prism style: what the window shows (SVG) and what is exported.

`render(table, graph)` returns the SVG plus where the plot area, the axes and the legend are
(in points from the top-left), so the window can map the mouse to data and open the right
part of Format Graph on a double-click.
"""
import base64
import io
import math

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib.backends.backend_agg import FigureCanvasAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.ticker import AutoMinorLocator, MultipleLocator, LogLocator, NullLocator  # noqa: E402

from . import stats  # noqa: E402

OKABE_ITO = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000"]
SYMBOLS = {"circle": "o", "square": "s", "triangle": "^", "down": "v", "diamond": "D", "pentagon": "p", "hexagon": "h", "star": "*", "none": ""}
SYMBOL_ORDER = ["circle", "square", "triangle", "down", "diamond", "pentagon", "hexagon", "star"]
LEGEND = {"best": "best", "upper left": "upper left", "upper right": "upper right", "lower left": "lower left", "lower right": "lower right"}
MM = 1 / 25.4


def axis_title(a, title, units):
    if a.get("title"):
        return a["title"]
    return f"{title} ({units})" if title and units else title or ""


PALETTES = {"okabe": OKABE_ITO, "tableau": ["#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F", "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC"],
            "bright": ["#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377", "#BBBBBB"], "muted": ["#332288", "#88CCEE", "#44AA99", "#117733", "#999933", "#DDCC77", "#CC6677", "#882255", "#AA4499"],
            "dark": ["#1B9E77", "#D95F02", "#7570B3", "#E7298A", "#66A61E", "#E6AB02", "#A6761D", "#666666"], "pastel": ["#A6CEE3", "#B2DF8A", "#FB9A99", "#FDBF6F", "#CAB2D6", "#FFFF99", "#1F78B4", "#33A02C"]}


def palette(graph, n):
    """The colours of a graph's data sets: a named scheme, a colour map spread over the data sets, or a list of #hex."""
    name = (graph.get("palette") or "okabe").strip()
    if "#" in name:
        cols = [c.strip() for c in name.split(",") if c.strip().startswith("#")]
        return cols or OKABE_ITO
    if name in ("viridis", "cividis", "magma", "plasma", "grey"):
        import matplotlib.colors as mc
        from matplotlib import colormaps
        n = max(n, 1)
        ts = np.linspace(0.0, 0.62, n) if name == "grey" else np.linspace(0.05, 0.85, n) if n > 1 else [0.3]
        return [mc.to_hex(colormaps["Greys_r" if name == "grey" else name](t)) for t in ts]
    return PALETTES.get(name, OKABE_ITO)


def style_of(graph, k, colors=OKABE_ITO):
    """A data set's look: saved settings over the defaults for its position."""
    s = (graph.get("sets") or [])[k] if k < len(graph.get("sets") or []) else {}
    return {"show": s.get("show", True), "color": s.get("color") or colors[k % len(colors)], "symbol": s.get("symbol") or SYMBOL_ORDER[k % 8],
            "size": s.get("size") or 6, "filled": s.get("filled", True), "line": s.get("line"), "width": s.get("width") or 1.0}


def error_of(d, kind):
    """(below, above) error bar lengths for a summary point."""
    if kind == "range" and d.get("min") is not None:
        return d["mean"] - d["min"], d["max"] - d["mean"]
    e = d.get(kind, 0.0) if kind in ("sd", "sem", "ci") else 0.0
    return e, e


def rc_for(graph):
    """matplotlib settings for a graph's font and style; they must be active while saving too."""
    font = graph.get("font") or "Arial"
    frame = graph.get("style") == "frame"
    rc = {"font.family": "sans-serif", "font.sans-serif": [font, "Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"], "font.serif": [font, "Times New Roman", "DejaVu Serif"],
          "font.size": float(graph.get("fontSize") or 10), "axes.linewidth": 1.0, "xtick.direction": "in" if frame else "out", "ytick.direction": "in" if frame else "out",
          "xtick.major.width": 1.0, "ytick.major.width": 1.0, "xtick.major.size": 4, "ytick.major.size": 4, "xtick.minor.size": 2, "ytick.minor.size": 2,
          "xtick.top": frame, "ytick.right": frame, "svg.fonttype": "none", "svg.hashsalt": "datum-plot", "axes.unicode_minus": True}
    if font in ("Times New Roman", "Georgia", "Cambria"):
        rc["font.family"] = "serif"
    return rc


def draw_brackets(ax, brackets, pos, tops, size, o):
    """Significance brackets over a column or grouped graph: stars (or P values), stacked so they never
    overlap. A bracket is [set, set, P], or [set, set, P, row] within a row of a grouped graph; `pos`
    maps set (or (set, row)) to its x position and `tops` maps x positions to the top of the data."""
    from .analysis import pv, stars
    show = o.get("brackets", "sig")
    keys = lambda b: ((b[0], b[3]), (b[1], b[3])) if len(b) > 3 else (b[0], b[1])
    br = [(pos[ka], pos[kb], b[2]) for b in brackets for ka, kb in [keys(b)] if ka in pos and kb in pos and show != "none" and (show == "all" or b[2] < 0.05)]
    if not br:
        return
    lo, hi = ax.get_ylim()
    h = hi - lo
    placed, top = [], hi
    for x1, x2, p in sorted(br, key=lambda t: (abs(t[1] - t[0]), min(t[:2]))):
        x1, x2 = sorted((x1, x2))
        y = max(t for x, t in tops.items() if x1 - 1e-9 <= x <= x2 + 1e-9) + 0.06 * h
        for a, b, yy in placed:
            if a <= x2 and x1 <= b:
                y = max(y, yy + 0.12 * h)
        ax.plot([x1, x1, x2, x2], [y - 0.025 * h, y, y, y - 0.025 * h], color="#222222", linewidth=0.9, zorder=4)
        text = stars(p) if o.get("ptext") != "p" else (f"P {pv(p)}" if pv(p).startswith("<") else f"P = {pv(p)}")
        ax.text((x1 + x2) / 2, y + 0.005 * h, text, ha="center", va="bottom", fontsize=size * 0.85, zorder=4)
        placed.append((x1, x2, y))
        top = max(top, y + 0.1 * h)
    ax.set_ylim(lo, top)


def draw_overlays(ax, table, graph, overlays, size, colors=OKABE_ITO, pos=None, tops=None, twin=None, label=True):
    """What analyses add to a graph: fitted curves with their 95 % bands and equation, shaded
    areas, and (column graphs) significance brackets."""
    from . import analysis
    labels = []
    for ov in overlays:
        try:
            res = analysis.run(ov["kind"], table, ov.get("sets", []), ov.get("options", {}))
        except Exception:
            continue
        o = ov.get("options", {})
        if pos is not None:
            draw_brackets(ax, res.get("brackets", []), pos, tops, size, o)
            continue
        for c in res.get("curves", []):
            st = style_of(graph, c["set"], colors)
            if not st["show"]:
                continue
            col = st["color"]
            ax_ = ax
            if twin and c["set"] in twin[1]:
                ax, ax_ = twin[0], ax
            if c.get("fill"):
                ax.fill_between(c["x"], c["fill"], c["y"], color=col, alpha=0.18, linewidth=0, zorder=1)
                ax.plot(c["x"], c["fill"], color=col, linewidth=0.7, linestyle=":", zorder=2)
            else:
                ax.plot(c["x"], c["y"], color=col, linewidth=1.1 if c.get("dash") else 1.4, linestyle="--" if c.get("dash") else "-", zorder=2.5)
            bands = o.get("bands", "ci")
            if c.get("lo") and bands in ("ci", "both"):
                ax.fill_between(c["x"], c["lo"], c["hi"], color=col, alpha=0.14, linewidth=0, zorder=1)
            if c.get("plo") and bands in ("pi", "both"):
                ax.plot(c["x"], c["plo"], color=col, linewidth=0.8, linestyle="--", zorder=2)
                ax.plot(c["x"], c["phi"], color=col, linewidth=0.8, linestyle="--", zorder=2)
            for mx, my, mt in c.get("marks", []):  # numbered peaks
                ax.annotate(mt, (mx, my), xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", color=col, fontsize=size * 0.75, zorder=5)
            ax = ax_ if twin and c["set"] in twin[1] else ax
            if o.get("label", True) and c.get("label"):
                labels.append((c["label"], col))
    if not labels or not label:
        return
    # The corner with the fewest data points gets the equations.
    ax.autoscale_view()
    pts = np.concatenate([np.column_stack([np.asarray(ln.get_xdata(), float), np.asarray(ln.get_ydata(), float)]) for ln in ax.get_lines() if len(ln.get_xdata())] or [np.zeros((0, 2))])
    pts = pts[np.all(np.isfinite(pts), axis=1)]
    fr = ax.transAxes.inverted().transform(ax.transData.transform(pts)) if len(pts) else np.zeros((0, 2))
    h = 0.08 * len(labels) + 0.04
    corners = [(0.03, 0.97, "left", "top"), (0.97, 0.03 + h, "right", "top"), (0.97, 0.97, "right", "top"), (0.03, 0.03 + h, "left", "top")]
    def busy(c):
        x0 = c[0] if c[2] == "left" else c[0] - 0.55
        return int(np.sum((fr[:, 0] >= x0) & (fr[:, 0] <= x0 + 0.55) & (fr[:, 1] <= c[1]) & (fr[:, 1] >= c[1] - h)))
    x, y, ha, va = min(corners, key=busy)
    for i, (text, col) in enumerate(labels):
        ax.text(x, y - i * 0.08, text, transform=ax.transAxes, ha=ha, va=va, color=col, fontsize=size * 0.8, zorder=5,
                bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "none", "pad": 0.6})


def draw_notes(ax, graph, size):
    """Annotations (D15): text, arrows, lines and boxes in data coordinates."""
    from matplotlib.patches import Rectangle
    for n in graph.get("notes") or []:
        col, fs = n.get("color") or "#222222", float(n.get("size") or 0) or size
        x, y, x2, y2, kind = float(n.get("x", 0)), float(n.get("y", 0)), float(n.get("x2", 0)), float(n.get("y2", 0)), n.get("kind", "text")
        fw = "bold" if n.get("bold") else "normal"
        if kind == "arrow":
            ax.annotate(n.get("text", ""), xy=(x2, y2), xytext=(x, y), color=col, fontsize=fs, fontweight=fw, ha="center", va="center", zorder=6,
                        arrowprops={"arrowstyle": "-|>", "color": col, "lw": 1.0, "shrinkA": 4 if n.get("text") else 0, "shrinkB": 1})
        elif kind == "line":
            ax.plot([x, x2], [y, y2], color=col, linewidth=1.0, zorder=6)
            if n.get("text"):
                ax.text((x + x2) / 2, (y + y2) / 2, n["text"], color=col, fontsize=fs, fontweight=fw, ha="center", va="bottom", zorder=6)
        elif kind == "box":
            ax.add_patch(Rectangle((min(x, x2), min(y, y2)), abs(x2 - x), abs(y2 - y), fill=False, edgecolor=col, linewidth=1.0, linestyle="--", zorder=6))
            if n.get("text"):
                ax.text(min(x, x2), max(y, y2), " " + n["text"], color=col, fontsize=fs, fontweight=fw, ha="left", va="bottom", zorder=6)
        elif n.get("text"):
            ax.text(x, y, n["text"], color=col, fontsize=fs, fontweight=fw, ha="center", va="center", zorder=6)


def figure(table, graph, overlays=(), fig=None):
    """Builds the matplotlib figure (call inside `rc_context(rc_for(graph))`), or draws into `fig` (a
    panel of a page layout); returns (fig, ax, legend, points)."""
    fig, ax, leg, points = build(table, graph, overlays, fig)
    if graph.get("notes"):
        lims = ax.get_xlim(), ax.get_ylim()
        draw_notes(ax, graph, float(graph.get("fontSize") or 10))
        ax.set_xlim(*lims[0]); ax.set_ylim(*lims[1])  # notes never move the axes
    return fig, ax, leg, points


def build(table, graph, overlays=(), fig=None):
    size = float(graph.get("fontSize") or 10)
    frame = graph.get("style") == "frame"
    if fig is None:
        fig = Figure(figsize=(max(20, graph.get("width") or 80) * MM, max(20, graph.get("height") or 60) * MM), dpi=72, layout="constrained")
        FigureCanvasAgg(fig)
    ax = fig.add_subplot()
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)
    if not frame:
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    hidden_x = table.get("kind") == "multi"
    if hidden_x:  # many variables: the first one on X, the others on Y
        from .regress import xy_view
        table, sets = xy_view(table), list(graph.get("sets") or [])
        graph = dict(graph, sets=[dict(sets[0] if sets else {}, show=False), *sets[1:]])
    colors = palette(graph, len(table["sets"]))
    if hidden_x:
        colors = colors[-1:] + colors[:-1]  # the first Y variable takes the first colour
    if table.get("kind") == "column":
        return column_figure(fig, ax, table, graph, overlays, colors, size)
    if table.get("kind") == "parts":
        return parts_figure(fig, ax, table, graph, size)
    if table.get("kind") == "nested":
        return nested_figure(fig, ax, table, graph, colors, size)
    if table.get("kind") == "survival":
        return survival_figure(fig, ax, table, graph, colors, size)
    if table.get("kind") in ("grouped", "contingency"):
        return grouped_figure(fig, ax, table, graph, overlays, colors, size)
    summary = stats.summarize(table)
    err, each, conn = graph.get("error", "sd"), graph.get("points") == "each", graph.get("line", False)
    direction = graph.get("errorDir", "both")
    right = {k for k, x in enumerate(graph.get("sets") or []) if x.get("right")}
    ya = graph.get("y") or {}
    bf, bt = ya.get("breakFrom"), ya.get("breakTo")
    broken = bf is not None and bt is not None and bt > bf and ya.get("scale") != "log" and not right

    def plot_sets(ax, which=None):
        """Draws the data sets (all, or only those on the left or right Y axis) into `ax`."""
        points = []
        for k, (s, pts) in enumerate(zip(table["sets"], summary)):
            st = style_of(graph, k, colors)
            if not st["show"] or not pts or (which == "left" and k in right) or (which == "right" and k not in right):
                continue
            xs, ys = [p["x"] for p in pts], [p["mean"] for p in pts]
            mk, col = SYMBOLS.get(st["symbol"], "o"), st["color"]
            face = col if st["filled"] else "white"
            line = st["line"] if st["line"] is not None else conn
            label = (s.get("title") or f"Data set {chr(65 + k)}") + (" (right axis)" if which == "right" else "")
            if each:
                ex = [p["x"] for p in pts for _ in p["values"]]
                ey = [v for p in pts for v in p["values"]]
                ax.plot(ex, ey, linestyle="none", marker=mk or "o", markersize=st["size"], markerfacecolor=face, markeredgecolor=col, color=col, label=label, zorder=3)
                if line:
                    ax.plot(xs, ys, color=col, linewidth=st["width"], zorder=2)
            else:
                yerr = None
                if err != "none":
                    lo, hi = zip(*(error_of(p, err) for p in pts))
                    yerr = [[0 if direction == "up" else v for v in lo], [0 if direction == "down" else v for v in hi]]
                ax.errorbar(xs, ys, yerr=yerr, linestyle="-" if line else "none", linewidth=st["width"], marker=mk or None, markersize=st["size"],
                            markerfacecolor=face, markeredgecolor=col, color=col, ecolor=col, elinewidth=1.0, capsize=graph.get("cap", 3), capthick=1.0, label=label, zorder=3)
            points += [[k, p["x"], p["mean"], p["n"], p["sd"], p["sem"]] for p in pts]
        return points

    lg = graph.get("legend") or {}
    nsets = len([1 for k in range(len(table["sets"])) if style_of(graph, k, colors)["show"] and summary[k]])
    def legend(ax, handles=None):
        if not (lg.get("show", True) and nsets > 1):
            return None
        h, l_ = handles or ax.get_legend_handles_labels()
        if lg.get("loc") == "outside":
            return ax.legend(h, l_, loc="upper left", bbox_to_anchor=(1.02, 1), frameon=False, borderaxespad=0)
        return ax.legend(h, l_, loc=LEGEND.get(lg.get("loc", "best"), "best"), frameon=False)

    if broken:
        # An axis break: the same data in a short top panel (above the gap) and a tall bottom one (below it).
        fig.clear()
        gs = fig.add_gridspec(2, 1, height_ratios=[1, 2.2], hspace=0.04)
        top = fig.add_subplot(gs[0])
        ax = fig.add_subplot(gs[1], sharex=top)
        for a_ in (top, ax):
            a_.patch.set_alpha(0)
            for side in ("top", "right"):
                a_.spines[side].set_visible(frame)
        points = plot_sets(ax)
        plot_sets(top)
        axes(ax, table, graph, points)
        axes(top, table, graph, points)
        lo = ax.get_ylim()[0]
        ax.set_ylim(lo, bf)
        top.set_ylim(bt, max(top.get_ylim()[1], bt + (bf - lo) * 0.2))
        top.set_xlabel(""); top.set_ylabel("")
        top.spines["bottom"].set_visible(False); ax.spines["top"].set_visible(False)
        top.tick_params(axis="x", which="both", bottom=False, labelbottom=False, top=False)
        d = dict(marker=[(-1, -0.6), (1, 0.6)], markersize=7, linestyle="none", color="#222222", mec="#222222", mew=1, clip_on=False)
        top.plot([0], [0], transform=top.transAxes, **d)
        ax.plot([0], [1], transform=ax.transAxes, **d)
        if graph.get("title") and graph.get("showTitle", True):
            top.set_title(graph["title"], fontweight="bold", fontsize=size * 1.15)
        leg = legend(top)
        if overlays and points:
            draw_overlays(top, table, graph, overlays, size, colors, label=False)
            draw_overlays(ax, table, graph, overlays, size, colors)
        return fig, ax, leg, points
    xa = graph.get("x") or {}
    xf, xt = xa.get("breakFrom"), xa.get("breakTo")
    if xf is not None and xt is not None and xt > xf and xa.get("scale") != "log" and not right:
        # An X axis break: a wide left panel (before the gap) and a narrow right one (after it).
        fig.clear()
        gs = fig.add_gridspec(1, 2, width_ratios=[2.2, 1], wspace=0.04)
        ax = fig.add_subplot(gs[0])
        rt = fig.add_subplot(gs[1], sharey=ax)
        for a_ in (ax, rt):
            a_.patch.set_alpha(0)
            for side in ("top", "right"):
                a_.spines[side].set_visible(frame)
        points = plot_sets(ax)
        plot_sets(rt)
        axes(ax, table, graph, points)
        axes(rt, table, graph, points)
        lo = ax.get_xlim()[0]
        ax.set_xlim(lo, xf)
        rt.set_xlim(xt, max(rt.get_xlim()[1], xt + (xf - lo) * 0.2))
        rt.set_xlabel(""); rt.set_ylabel("")
        rt.spines["left"].set_visible(False); ax.spines["right"].set_visible(False)
        rt.tick_params(axis="y", which="both", left=False, labelleft=False, right=False)
        d = dict(marker=[(-0.6, -1), (0.6, 1)], markersize=7, linestyle="none", color="#222222", mec="#222222", mew=1, clip_on=False)
        ax.plot([1], [0], transform=ax.transAxes, **d)
        rt.plot([0], [0], transform=rt.transAxes, **d)
        if graph.get("title") and graph.get("showTitle", True):
            ax.set_title(graph["title"], fontweight="bold", fontsize=size * 1.15)
        leg = legend(rt)
        if overlays and points:
            draw_overlays(rt, table, graph, overlays, size, colors, label=False)
            draw_overlays(ax, table, graph, overlays, size, colors)
        return fig, ax, leg, points
    points = plot_sets(ax, "left" if right else None)
    axes(ax, table, graph, points)
    ax2 = None
    if right:
        # A second Y axis on the right for the data sets marked "Right Y".
        ax2 = ax.twinx()
        ax2.patch.set_alpha(0)
        ax2.spines["top"].set_visible(frame)
        ax2.spines["right"].set_visible(True)
        pts2 = plot_sets(ax2, "right")
        y2 = dict(graph.get("y2") or {})
        if not y2.get("title"):
            y2["title"] = ", ".join(table["sets"][k].get("title") or f"Data set {chr(65 + k)}" for k in sorted(right) if k < len(table["sets"]))
        axes(ax2, table, {**graph, "y": y2}, pts2, only_y=True, x=False)
        if graph.get("style") == "frame":
            ax.tick_params(axis="y", right=False)
        (l0, l1), (r0, r1) = ax.get_ylim(), ax2.get_ylim()
        f = (lambda v: math.log10(v)) if ax2.get_yscale() == "log" else (lambda v: v)
        g_ = (lambda v: 10 ** v) if ax.get_yscale() == "log" else (lambda v: v)
        fl = (lambda v: math.log10(v)) if ax.get_yscale() == "log" else (lambda v: v)
        for p in pts2:
            try:  # where the point sits in left-axis units, so the window's hover finds it
                p.append(g_(fl(l0) + (f(p[2]) - f(r0)) / (f(r1) - f(r0)) * (fl(l1) - fl(l0))))
            except (ValueError, ZeroDivisionError):
                p.append(float("nan"))
        points += pts2
    if graph.get("title") and graph.get("showTitle", True):
        ax.set_title(graph["title"], fontweight="bold", fontsize=size * 1.15)
    h1, l1_ = ax.get_legend_handles_labels()
    h2, l2_ = ax2.get_legend_handles_labels() if ax2 else ([], [])
    leg = legend(ax, (h1 + h2, l1_ + l2_))
    if overlays and points:
        draw_overlays(ax, table, graph, overlays, size, colors, twin=(ax2, right) if ax2 else None)
    if not points:
        ax.text(0.5, 0.5, "Enter X and Y values in the data table", transform=ax.transAxes, ha="center", va="center", color="#8D9AAB")
    return fig, ax, leg, points


def axes(ax, table, graph, points, only_y=False, x=True):
    """Axis titles, scales, ranges, ticks and grids from the graph settings (`x` False: the Y axis only)."""
    for which, a, title, units in (("x", graph.get("x") or {}, table.get("xTitle", ""), table.get("xUnits", "")), ("y", graph.get("y") or {}, table.get("yTitle", ""), table.get("yUnits", ""))):
        if which == "x" and not x:
            continue
        if only_y and which == "x":
            ax.set_xlabel((graph.get("x") or {}).get("title", ""), fontweight="bold" if graph.get("boldTitles", True) else "normal")
            continue
        setlabel, scale, lim, axis = (ax.set_xlabel, ax.set_xscale, ax.set_xlim, ax.xaxis) if which == "x" else (ax.set_ylabel, ax.set_yscale, ax.set_ylim, ax.yaxis)
        setlabel(axis_title(a, title, units), fontweight="bold" if graph.get("boldTitles", True) else "normal")
        log = a.get("scale") == "log"
        if log:
            scale("log")
        if not a.get("auto", True) and a.get("min") is not None and a.get("max") is not None and a["max"] > a["min"] and (not log or a["min"] > 0):
            lim(a["min"], a["max"])
        elif not log and which == "y" and points and min(p[2] for p in points) >= 0:
            lim(bottom=0)  # Prism starts a positive Y axis at zero
        if log:
            axis.set_major_locator(LogLocator(base=10))
            axis.set_minor_locator(LogLocator(base=10, subs=range(2, 10)) if a.get("minor", True) else NullLocator())
        else:
            if a.get("step"):
                axis.set_major_locator(MultipleLocator(a["step"]))
            if a.get("minor", False):
                axis.set_minor_locator(AutoMinorLocator())
        if a.get("grid"):
            ax.grid(True, axis=which, color="#D9DDE1", linewidth=0.6)
            ax.set_axisbelow(True)


def swarm(v, h, step, lim):
    """Sideways offsets that keep dots closer than `h` (one dot, in Y units) apart: a simple bee swarm."""
    off, placed = np.zeros(len(v)), []
    for i in np.argsort(v):
        near = [o for (y, o) in placed if abs(y - v[i]) < h]
        x = next((k * s_ * step for k in range(0, 60) for s_ in ((1, -1) if k else (1,)) if all(abs(k * s_ * step - o) >= step * 0.999 for o in near)), 0.0)
        off[i] = max(-lim, min(lim, x))
        placed.append((v[i], off[i]))
    return off


def column_figure(fig, ax, table, graph, overlays, colors, size):
    """A column graph: one column per data set as dots, bars, box plots, violins or before–after lines."""
    from .groups import column, summary
    from scipy import stats as sst
    kind, err = graph.get("column") or "scatter", graph.get("error", "sd")
    each = graph.get("points", "each") == "each"
    shown = [k for k in range(len(table["sets"])) if style_of(graph, k, colors)["show"]]
    data = [(k, *summary(table, k)) for k in shown]
    data = [d for d in data if d[2] > 0]
    allv = np.concatenate([d[1] if d[1] is not None else np.array([d[3]]) for d in data]) if data else np.zeros(0)
    yr = (float(allv.max()) - min(0.0, float(allv.min()))) if len(allv) else 1.0
    plot_h, plot_w = max(20, graph.get("height") or 60) * 2.835 * 0.7, max(20, graph.get("width") or 80) * 2.835 * 0.8
    points, pos, tops = [], {}, {}
    if kind == "paired":
        cols = [column(table, k) for k, *_ in data]
        for r in range(table["rows"]):
            pts = [(i, c[r]) for i, c in enumerate(cols) if c[r] is not None]
            if len(pts) > 1:
                ax.plot(*zip(*pts), color="#9AA5B1", linewidth=0.8, zorder=1)
    for i, (k, v, n, m, sd) in enumerate(data):
        st = style_of(graph, k, colors)
        col, mk = st["color"], SYMBOLS.get(st["symbol"], "o") or "o"
        sem = sd / math.sqrt(n) if n > 1 else 0.0
        e = {"sd": sd, "sem": sem, "ci": float(sst.t.ppf(0.975, n - 1)) * sem if n > 1 else 0.0, "none": 0.0}.get(err, sd)
        e = 0.0 if not math.isfinite(e) else e
        yerr = [[m - v.min()], [v.max() - m]] if err == "range" and v is not None else [[0 if graph.get("errorDir") == "up" else e], [0 if graph.get("errorDir") == "down" else e]]
        top = max(m + yerr[1][0], float(v.max()) if v is not None else m)
        if kind == "bars":
            ax.bar(i, m, width=0.62, color=col if st["filled"] else "none", alpha=0.35 if st["filled"] else 1, edgecolor=col, linewidth=1.2, zorder=1)
            ax.bar(i, m, width=0.62, color="none", edgecolor=col, linewidth=1.2, zorder=1.1)
        elif kind == "box" and v is not None and len(v) > 1:
            b = ax.boxplot(v, positions=[i], widths=0.5, patch_artist=True, showfliers=not each, manage_ticks=False, zorder=1,
                           boxprops={"facecolor": col, "alpha": 0.3, "edgecolor": col}, medianprops={"color": col, "linewidth": 1.6}, whiskerprops={"color": col}, capprops={"color": col}, flierprops={"markeredgecolor": col})
            del b
        elif kind == "violin" and v is not None and len(v) > 2 and np.ptp(v) > 0:
            vp = ax.violinplot(v, [i], widths=0.75, showextrema=False)
            for body in vp["bodies"]:
                body.set_facecolor(col); body.set_edgecolor(col); body.set_alpha(0.3)
            q1, med, q3 = np.percentile(v, [25, 50, 75])
            ax.vlines(i, q1, q3, color=col, linewidth=3, zorder=2)
            ax.plot(i, med, "o", color="white", markeredgecolor=col, markersize=4, zorder=3)
        dots = v is not None and (kind in ("scatter", "paired") or (each and kind in ("bars", "box", "violin")))
        if dots:
            ms = st["size"] * (1.0 if kind == "scatter" else 0.75 if kind in ("bars", "paired") else 0.55)
            lim = 0.38 if kind == "scatter" else 0.22
            xs = i + (swarm(v, ms / plot_h * (yr or 1.0), ms / plot_w * max(len(data), 1), lim) if kind != "paired" else np.zeros(len(v)))
            ax.plot(xs, v, linestyle="none", marker=mk, markersize=ms, markerfacecolor=col if st["filled"] else "white", markeredgecolor=col if kind in ("scatter", "paired", "bars") else "white",
                    markeredgewidth=0.6 if kind in ("box", "violin") else 1.0, alpha=0.9, zorder=3)
        if kind in ("scatter", "bars", "mean") or (kind == "paired" and err != "none"):
            if kind in ("scatter", "paired"):
                ax.hlines(m, i - 0.26, i + 0.26, color="#222222" if kind == "scatter" else col, linewidth=1.6, zorder=4)
            if err != "none":
                ax.errorbar(i, m, yerr=yerr, fmt="none" if kind != "mean" else mk, markersize=st["size"], color="#222222" if kind == "scatter" else col, ecolor="#222222" if kind == "scatter" else col,
                            elinewidth=1.0, capsize=graph.get("cap", 3) * (1.6 if kind != "mean" else 1), capthick=1.0, zorder=4)
            elif kind == "mean":
                ax.plot(i, m, mk, color=col, markersize=st["size"], zorder=4)
        pos[k] = i
        tops[i] = top
        points.append([k, float(i), m, n, sd, sem])
    names = [table["sets"][k].get("title") or f"Data set {chr(65 + k)}" for k, *_ in data]
    ax.set_xticks(range(len(data)), names)
    ax.set_xlim(-0.6, len(data) - 0.4)
    ax.tick_params(axis="x", length=0)
    axes(ax, table, graph, [[0, 0, float(allv.min()) if len(allv) else 0]], only_y=True)
    if sum(len(n) for n in names) * size * 0.7 > (graph.get("width") or 80) * 2.4:
        for lab in ax.get_xticklabels():
            lab.set_rotation(30); lab.set_ha("right")
    if graph.get("title") and graph.get("showTitle", True):
        ax.set_title(graph["title"], fontweight="bold", fontsize=size * 1.15)
    if overlays and points:
        draw_overlays(ax, table, graph, overlays, size, colors, pos, tops)
    if not points:
        ax.text(0.5, 0.5, "Enter values in the data table", transform=ax.transAxes, ha="center", va="center", color="#8D9AAB")
    return fig, ax, None, points


def parts_figure(fig, ax, table, graph, size):
    """Parts of a whole: a pie or donut per data set (rows are the parts), or bars stacked to 100 %."""
    from .groups import cells
    rows, cv = cells(table)
    kind = graph.get("column") if graph.get("column") in ("pie", "donut", "percent") else "pie"
    cols = palette(graph, len(rows))
    shown = [k for k in range(len(table["sets"])) if style_of(graph, k)["show"]]
    labels = [lab for _, lab in rows]
    vals = {k: [sum(cv.get((k, r), [0])) for r, _ in rows] for k in shown}
    shown = [k for k in shown if sum(v for v in vals[k] if v > 0) > 0]
    title = lambda k: table["sets"][k].get("title") or f"Data set {chr(65 + k)}"
    handles = None
    if not shown:
        ax.text(0.5, 0.5, "Enter the parts (rows) of each whole (data set)", transform=ax.transAxes, ha="center", va="center", color="#8D9AAB")
        ax.axis("off")
        return fig, ax, None, []
    if kind == "percent":
        bottom = np.zeros(len(shown))
        handles = []
        for i, lab in enumerate(labels):
            h = [100 * max(vals[k][i], 0) / sum(v for v in vals[k] if v > 0) for k in shown]
            handles.append(ax.bar(range(len(shown)), h, bottom=bottom, width=0.62, color=cols[i % len(cols)], edgecolor="white", linewidth=0.6, label=lab))
            for j, v in enumerate(h):
                if v >= 6:
                    ax.text(j, bottom[j] + v / 2, f"{v:.0f}%", ha="center", va="center", fontsize=size * 0.8, color="white")
            bottom += h
        ax.set_xticks(range(len(shown)), [title(k) for k in shown]); ax.tick_params(axis="x", length=0)
        ax.set_ylim(0, 100); ax.set_xlim(-0.6, len(shown) - 0.4)
        ax.set_ylabel((graph.get("y") or {}).get("title") or "% of total", fontweight="bold" if graph.get("boldTitles", True) else "normal")
        handles = [h[0] for h in handles]
    else:
        for i, k in enumerate(shown):
            v = [max(x, 0) for x in vals[k]]
            wp = {"edgecolor": "white", "linewidth": 1.0, **({"width": 0.42} if kind == "donut" else {})}
            wedges, *_ = ax.pie(v, colors=cols, center=(i * 2.6, 0), radius=1, startangle=90, counterclock=False, wedgeprops=wp, pctdistance=0.79 if kind == "donut" else 0.62,
                                autopct=lambda p: f"{p:.0f}%" if p >= 4 else "", textprops={"fontsize": size * 0.8, "color": "white"})
            handles = handles or wedges
            if len(shown) > 1 or kind == "donut":
                ax.text(i * 2.6, -1.18 if len(shown) > 1 else 0, title(k) if len(shown) > 1 else "", ha="center", va="top" if len(shown) > 1 else "center", fontsize=size, fontweight="bold")
        ax.set_aspect("equal"); ax.axis("off")
        ax.set_xlim(-1.15, (len(shown) - 1) * 2.6 + 1.15); ax.set_ylim(-1.45 if len(shown) > 1 else -1.1, 1.1)
    if graph.get("title") and graph.get("showTitle", True):
        ax.set_title(graph["title"], fontweight="bold", fontsize=size * 1.15)
    leg = None
    if (graph.get("legend") or {}).get("show", True):
        leg = ax.legend(handles, labels, loc="upper left", bbox_to_anchor=(1.02, 1), frameon=False, borderaxespad=0)
    return fig, ax, leg, []


def nested_figure(fig, ax, table, graph, colors, size):
    """A nested graph: each group's subgroups side by side as small columns of dots with their means, the group mean ± error across the subgroup means."""
    from scipy import stats as sst
    from .nested import subgroups
    err = graph.get("error", "sd")
    points, labels = [], []
    shown = [k for k in range(len(table["sets"])) if style_of(graph, k, colors)["show"]]
    for i, k in enumerate(shown):
        st, subs = style_of(graph, k, colors), subgroups(table, k)
        labels.append(table["sets"][k].get("title") or f"Data set {chr(65 + k)}")
        m = len(subs)
        for j, v in enumerate(subs):
            x = i + (j - (m - 1) / 2) * min(0.8 / max(m, 1), 0.22)
            ax.plot(np.full(len(v), x), v, linestyle="none", marker=SYMBOLS.get(st["symbol"], "o") or "o", markersize=st["size"] * 0.7, markerfacecolor=st["color"] if st["filled"] else "white",
                    markeredgecolor=st["color"], alpha=0.85, zorder=3)
            ax.hlines(v.mean(), x - 0.06, x + 0.06, color="#222222", linewidth=1.0, zorder=4)
            points.append([k, float(x), float(v.mean()), len(v), float(v.std(ddof=1)) if len(v) > 1 else 0.0, float(v.std(ddof=1) / math.sqrt(len(v))) if len(v) > 1 else 0.0])
        if m:
            mm = np.array([v.mean() for v in subs])
            gm = mm.mean()
            ax.hlines(gm, i - 0.4, i + 0.4, color=st["color"], linewidth=1.8, zorder=2)
            if err != "none" and m > 1:
                sd = mm.std(ddof=1)
                e = {"sd": sd, "sem": sd / math.sqrt(m), "ci": sd / math.sqrt(m) * float(sst.t.ppf(0.975, m - 1))}.get(err, 0.0)
                if err == "range":
                    ax.vlines(i + 0.42, mm.min(), mm.max(), color=st["color"], linewidth=1.0)
                elif e:
                    ax.errorbar(i + 0.42, gm, yerr=e, fmt="none", ecolor=st["color"], elinewidth=1.0, capsize=graph.get("cap", 3), zorder=2)
    ax.set_xticks(range(len(shown)), labels); ax.tick_params(axis="x", length=0)
    ax.set_xlim(-0.6, len(shown) - 0.4)
    axes(ax, table, graph, points, x=False)
    if graph.get("title") and graph.get("showTitle", True):
        ax.set_title(graph["title"], fontweight="bold", fontsize=size * 1.15)
    if not points:
        ax.text(0.5, 0.5, "Enter each group's subgroups in its sub-columns, replicates down the rows", transform=ax.transAxes, ha="center", va="center", color="#8D9AAB")
    return fig, ax, None, points


def survival_figure(fig, ax, table, graph, colors, size):
    """Kaplan-Meier curves (D9): a staircase per group from 100 %, a tick at each censored subject, 95 % CI shaded when the error is "ci"."""
    from .survival import km, steps, subjects
    points = []
    for k in range(len(table["sets"])):
        st = style_of(graph, k, colors)
        t, e = subjects(table, k)
        if not st["show"] or not len(t):
            continue
        rows = km(t, e)
        xs, ys = steps(rows)
        label = table["sets"][k].get("title") or f"Data set {chr(65 + k)}"
        ax.plot(xs, ys, drawstyle="steps-post", color=st["color"], linewidth=st["width"] * 1.2, label=label, zorder=3)
        if graph.get("error") == "ci":
            lo, hi = [100.0] + [100 * r[6] for r in rows], [100.0] + [100 * (r[7] if math.isfinite(r[7]) else r[6]) for r in rows]
            ax.fill_between(xs, lo, hi, step="post", color=st["color"], alpha=0.15, linewidth=0, zorder=2)
        cx = [r[0] for r in rows if r[3]]
        ax.plot(cx, [100 * r[4] for r in rows if r[3]], linestyle="none", marker="|", markersize=st["size"] * 0.9, markeredgewidth=1.0, color=st["color"], zorder=4)
        points += [[k, r[0], 100 * r[4], r[1], 0.0, 0.0] for r in rows]
    graph = {**graph, "y": {"auto": False, "min": 0, "max": 105, **{a: b for a, b in (graph.get("y") or {}).items() if a in ("step", "grid", "minor", "title")}}} if (graph.get("y") or {}).get("auto", True) else graph
    axes(ax, table, graph, points)
    if graph.get("title") and graph.get("showTitle", True):
        ax.set_title(graph["title"], fontweight="bold", fontsize=size * 1.15)
    lg = graph.get("legend") or {}
    leg = ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), frameon=False, borderaxespad=0) if lg.get("loc") == "outside" and len(points) and lg.get("show", True) else \
        ax.legend(loc=LEGEND.get(lg.get("loc", "best"), "best"), frameon=False) if lg.get("show", True) and len({p[0] for p in points}) > 1 else None
    if not points:
        ax.text(0.5, 0.5, "Enter each subject's time in X and 1 (event) or 0 (censored) in its group", transform=ax.transAxes, ha="center", va="center", color="#8D9AAB")
    return fig, ax, leg, points


def grouped_figure(fig, ax, table, graph, overlays, colors, size):
    """A grouped table: one group of bars (or dots, stacked bars, lines) per row, one colour per data
    set; or a heat map of the means (rows × data sets)."""
    from .groups import cells
    from scipy import stats as sst
    kind, err = graph.get("column") or "bars", graph.get("error", "sd")
    if kind not in ("bars", "stacked", "percent", "scatter", "lines", "heatmap"):
        kind = "bars"
    each = graph.get("points", "mean") == "each"
    rows, cv = cells(table)
    if kind == "percent":  # stacked to 100 % of each row
        tot = {r: sum(sum(cv.get((k, r), [])) for k in range(len(table["sets"]))) for r, _ in rows}
        cv = {(k, r): [100 * sum(v) / tot[r]] for (k, r), v in cv.items() if tot[r]}
        kind, err, pct = "stacked", "none", True
    else:
        pct = False
    shown = [k for k in range(len(table["sets"])) if style_of(graph, k, colors)["show"]]
    names = [table["sets"][k].get("title") or f"Data set {chr(65 + k)}" for k in shown]
    labels = [lab for _, lab in rows]
    points, pos, tops, leg = [], {}, {}, None
    if not rows or not shown:
        ax.text(0.5, 0.5, "Enter values in the data table", transform=ax.transAxes, ha="center", va="center", color="#8D9AAB")
        return fig, ax, None, points
    if kind == "heatmap":
        M = np.array([[np.mean(cv[(k, r)]) if cv.get((k, r)) else np.nan for k in shown] for r, _ in rows])
        cmap = graph.get("palette") if graph.get("palette") in ("viridis", "cividis", "magma", "plasma") else "viridis"
        im = ax.imshow(M, cmap=cmap, aspect="auto")
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                if math.isfinite(M[i, j]):
                    ax.text(j, i, f"{M[i, j]:.3g}", ha="center", va="center", fontsize=size * 0.8, color="white" if im.norm(M[i, j]) < 0.55 else "black")
        ax.set_xticks(range(len(shown)), names); ax.set_yticks(range(len(rows)), labels)
        for sd in ax.spines.values():
            sd.set_visible(False)
        cb = fig.colorbar(im, ax=ax, shrink=0.85)
        cb.set_label(axis_title(graph.get("y") or {}, table.get("yTitle", ""), table.get("yUnits", "")), fontweight="bold" if graph.get("boldTitles", True) else "normal")
        if graph.get("title") and graph.get("showTitle", True):
            ax.set_title(graph["title"], fontweight="bold", fontsize=size * 1.15)
        return fig, ax, None, points
    n = len(shown)
    w = 0.8 / n if kind != "stacked" else 0.62
    base = np.zeros(len(rows))
    allv = [0.0]
    for j, k in enumerate(shown):
        st = style_of(graph, k, colors)
        col, mk = st["color"], SYMBOLS.get(st["symbol"], "o") or "o"
        xs, ms_, es, bs = [], [], [], []
        for i, (r, _) in enumerate(rows):
            v = np.asarray(cv.get((k, r), []), float)
            if not len(v):
                continue
            m, sd = float(v.mean()), float(v.std(ddof=1)) if len(v) > 1 else 0.0
            sem = sd / math.sqrt(len(v)) if len(v) > 1 else 0.0
            e = {"sd": sd, "sem": sem, "ci": float(sst.t.ppf(0.975, len(v) - 1)) * sem if len(v) > 1 else 0.0, "none": 0.0}.get(err, sd)
            x = i if kind in ("stacked", "lines") else i - 0.4 + w * (j + 0.5)
            b0 = base[i] if kind == "stacked" else 0.0
            xs.append(x); ms_.append(m + b0); es.append(e); bs.append(b0)
            pos[(k, r)] = x
            tops[x] = max(tops.get(x, -np.inf), m + b0 + e, float(v.max()) + b0 if kind != "stacked" else m + b0)
            points.append([k, float(x), m, len(v), sd, sem])
            allv += list(v)
            if kind == "stacked":
                base[i] += m
            if each and kind in ("bars", "scatter"):
                ax.plot(x + (np.arange(len(v)) - (len(v) - 1) / 2) * min(w / max(len(v), 1), 0.05), v, linestyle="none", marker=mk, markersize=st["size"] * 0.6,
                        markerfacecolor="white", markeredgecolor=col, zorder=3)
        if not xs:
            continue
        lab = names[j]
        d = graph.get("errorDir", "both")
        yerr = [[0 if d == "up" else e for e in es], [0 if d == "down" else e for e in es]] if err != "none" else None
        if kind == "bars":
            ax.bar(xs, ms_, width=w * 0.92, color=col if st["filled"] else "none", alpha=0.85 if st["filled"] else 1, edgecolor=col, linewidth=1.0, label=lab, zorder=1)
            if yerr:
                ax.errorbar(xs, ms_, yerr=yerr, fmt="none", ecolor="#222222", elinewidth=1.0, capsize=graph.get("cap", 3), zorder=2)
        elif kind == "stacked":
            ax.bar(xs, [m - b for m, b in zip(ms_, bs)], bottom=bs, width=w, color=col, edgecolor="white", linewidth=0.6, label=lab, zorder=1)
        else:
            ax.errorbar(xs, ms_, yerr=yerr, marker=mk, markersize=st["size"], linestyle="-" if kind == "lines" else "none", color=col, markerfacecolor=col if st["filled"] else "white",
                        ecolor=col, elinewidth=1.0, capsize=graph.get("cap", 3), linewidth=st["width"], label=lab, zorder=3)
    ax.set_xticks(range(len(rows)), labels)
    ax.set_xlim(-0.6, len(rows) - 0.4)
    ax.tick_params(axis="x", length=0)
    axes(ax, table, graph, [[0, 0, float(min(allv))]], only_y=True)
    if pct:
        ax.set_ylabel((graph.get("y") or {}).get("title") or "% of row", fontweight="bold" if graph.get("boldTitles", True) else "normal")
        ax.set_ylim(0, 100)
    if graph.get("title") and graph.get("showTitle", True):
        ax.set_title(graph["title"], fontweight="bold", fontsize=size * 1.15)
    lg = graph.get("legend") or {}
    if lg.get("show", True) and n > 1:
        leg = ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), frameon=False, borderaxespad=0) if lg.get("loc") == "outside" or (pct and lg.get("loc", "best") == "best") else ax.legend(loc=LEGEND.get(lg.get("loc", "best"), "best"), frameon=False)
    if overlays and points and kind not in ("stacked", "lines"):
        draw_overlays(ax, table, graph, overlays, size, colors, pos, tops)
    return fig, ax, leg, points


def geometry(fig, ax, leg):
    """Plot area, legend and limits in points from the top-left of the figure."""
    w, h = fig.get_size_inches() * 72
    fig.canvas.draw()
    r = fig.canvas.get_renderer()

    def box(b):
        return [b.x0, h - b.y1, b.x1, h - b.y0]
    return {"w": w, "h": h, "plot": box(ax.get_window_extent(r)), "all": box(ax.get_tightbbox(r)), "legend": box(leg.get_window_extent(r)) if leg else None,
            "xlim": list(ax.get_xlim()), "ylim": list(ax.get_ylim()), "xlog": ax.get_xscale() == "log", "ylog": ax.get_yscale() == "log"}


def render(table, graph, overlays=()):
    """SVG text and geometry for the window."""
    with matplotlib.rc_context(rc_for(graph)):
        fig, ax, leg, points = figure(table, graph, overlays)
        g = geometry(fig, ax, leg)
        buf = io.StringIO()
        fig.savefig(buf, format="svg", metadata={"Date": None, "Creator": "Datum Plot"})
    return {"svg": buf.getvalue(), "points": [p if all(math.isfinite(v) for v in p[1:3]) else None for p in points], **g}


LETTERS = {"A": lambda i: chr(65 + i), "a": lambda i: chr(97 + i), "(a)": lambda i: f"({chr(97 + i)})", "none": lambda i: ""}


def page(layout, panels, fmt="svg", path=None, dpi=300, cmyk=False):
    """A page layout (F1, F2): graphs, text and panel letters at their places in millimetres.
    `panels` maps a graph id (as text) to {table, graph, overlays}. Each graph is drawn twice: once on
    its own at its panel size (constrained layout finds where its axes go), then into its place on the
    page with those positions, so the page stays vector (SVG, PDF, EPS) with text as text."""
    from matplotlib.gridspec import GridSpec
    W, H = max(20.0, float(layout.get("width") or 180)), max(20.0, float(layout.get("height") or 120))
    base = {"font": layout.get("font") or "Arial", "fontSize": layout.get("fontSize") or 8}
    fig = Figure(figsize=(W * MM, H * MM), dpi=72)
    FigureCanvasAgg(fig)
    fig.patch.set_facecolor("white")
    style, n = LETTERS.get(layout.get("letters", "A"), LETTERS["A"]), 0
    items = sorted(layout.get("items") or [], key=lambda it: bool(it.get("inset")))  # insets on top
    def strip(f, it):
        """A stacked panel above another keeps its X axis but drops its title and numbers (D12)."""
        if it.get("hideX"):
            for a in f.axes:
                a.set_xlabel("")
                a.tick_params(axis="x", which="both", labelbottom=False)
    # Pass 1: each graph alone at its panel size; constrained layout says where its axes go.
    done = []
    for it in items:
        x, y, w, h = (float(it.get(k) or 0) for k in ("x", "y", "w", "h"))
        p = panels.get(str(it.get("graph"))) if it.get("kind") != "text" else None
        if it.get("kind") == "text" or not p or w < 10 or h < 10:
            done.append((it, None, None))
            continue
        g = {**p["graph"], "width": w, "height": h}
        if it.get("inset"):  # smaller text in an inset
            g["fontSize"] = max(5.0, float(g.get("fontSize") or 10) * 0.75)
        with matplotlib.rc_context(rc_for(g)):
            one, *_ = figure(p["table"], g, p.get("overlays", []))
            strip(one, it)
            one.canvas.draw()
        done.append((it, g, [list(a.get_position().bounds) for a in one.axes]))
    # Align the plot frames of panels in the same column (left and right) and row (bottom and top).
    if layout.get("align", True):
        frames = [(it, pos) for it, g, pos in done if pos and not it.get("inset")]
        def margins(it, pos):
            x0 = min(b[0] for b in pos); x1 = max(b[0] + b[2] for b in pos); y0 = min(b[1] for b in pos); y1 = max(b[1] + b[3] for b in pos)
            return x0 * it["w"], (1 - x1) * it["w"], y0 * it["h"], (1 - y1) * it["h"], (x0, x1, y0, y1)
        m = {id(it): margins(it, pos) for it, pos in frames}
        target = {}
        for key, idx in ((lambda it: (round(it["x"]), round(it["w"])), (0, 1)), (lambda it: (round(it["y"]), round(it["h"])), (2, 3))):
            groups = {}
            for it, _ in frames:
                groups.setdefault(key(it), []).append(it)
            for grp in groups.values():
                for i in idx:
                    v = max(m[id(it)][i] for it in grp)
                    for it in grp:
                        target.setdefault(id(it), list(m[id(it)][:4]))[i] = v
        for it, pos in frames:
            l, r, b_, t = target[id(it)]
            x0, x1, y0, y1 = m[id(it)][4]
            nx0, nx1, ny0, ny1 = l / it["w"], 1 - r / it["w"], b_ / it["h"], 1 - t / it["h"]
            sx, sy = (nx1 - nx0) / max(x1 - x0, 1e-9), (ny1 - ny0) / max(y1 - y0, 1e-9)
            for bb in pos:
                bb[:] = [nx0 + (bb[0] - x0) * sx, ny0 + (bb[1] - y0) * sy, bb[2] * sx, bb[3] * sy]
    # Pass 2: every item into its place on the page.
    for it, g, pos in done:
        x, y, w, h = (float(it.get(k) or 0) for k in ("x", "y", "w", "h"))
        if it.get("kind") == "text":
            with matplotlib.rc_context(rc_for(base)):
                fig.text(x / W, 1 - y / H, it.get("text", ""), ha="left", va="top", fontsize=float(it.get("size") or base["fontSize"]), fontweight="bold" if it.get("bold") else "normal", wrap=True)
            continue
        if pos is None:
            continue
        p = panels[str(it.get("graph"))]
        with matplotlib.rc_context(rc_for(g)):
            sf = fig.add_subfigure(GridSpec(1, 1, figure=fig)[0])
            sf.bbox_relative.set_points(np.array([[x / W, 1 - (y + h) / H], [(x + w) / W, 1 - y / H]]))  # its place on the page
            figure(p["table"], g, p.get("overlays", []), fig=sf)
            if it.get("inset"):  # a white card over the graph below
                sf.patch.set_alpha(1); sf.patch.set_facecolor("white"); sf.patch.set_edgecolor("#3A4655"); sf.patch.set_linewidth(0.6)
            else:
                sf.patch.set_alpha(0)
            strip(sf, it)
            for a, b in zip(sf.axes, pos):
                a.set_position(b)
            lab = "" if it.get("inset") else style(n)
            if lab:
                sf.text(0.0, 1.0, lab, ha="left", va="top", fontsize=float(layout.get("letterSize") or 10), fontweight="bold")
            n += 0 if it.get("inset") else 1
    with matplotlib.rc_context(rc_for(base)):
        buf = io.BytesIO() if fmt != "svg" or path else io.StringIO()
        save_fmt = "png" if fmt == "tiff" and cmyk else fmt
        fig.savefig(buf, format=save_fmt, dpi=dpi, metadata={"Creator": "Datum Plot"} if save_fmt in ("png", "svg", "pdf") else None,
                    **({"pil_kwargs": {"compression": "tiff_lzw"}} if save_fmt == "tiff" else {}))
    if fmt == "svg" and not path:
        return {"svg": buf.getvalue(), "w": W / 25.4 * 72, "h": H / 25.4 * 72}
    data = buf.getvalue()
    if fmt == "tiff" and cmyk:
        data = cmyk_tiff(data, dpi)
    if path:
        with open(path, "wb") as f:
            f.write(data)
        return {"path": path, "bytes": len(data)}
    return {"data": base64.b64encode(data).decode()}


def cmyk_tiff(png, dpi):
    """A CMYK TIFF (LZW) from a PNG, as many journals ask for print (G3)."""
    from PIL import Image
    im = Image.open(io.BytesIO(png)).convert("RGB").convert("CMYK")
    out = io.BytesIO()
    im.save(out, format="TIFF", compression="tiff_lzw", dpi=(dpi, dpi))
    return out.getvalue()


def export(table, graph, fmt, path=None, dpi=300, transparent=False, overlays=(), cmyk=False):
    """Writes the graph as png, svg, pdf, eps or tiff; without a path returns base64 (for the clipboard)."""
    with matplotlib.rc_context(rc_for(graph)):
        fig, *_ = figure(table, graph, overlays)
        if not transparent:
            fig.patch.set_alpha(1)
            fig.patch.set_facecolor("white")
        meta = {"Creator": "Datum Plot"} if fmt in ("png", "svg", "pdf") else None
        buf = io.BytesIO()
        fig.savefig(buf, format="png" if fmt == "tiff" and cmyk else fmt, dpi=dpi, transparent=transparent and not cmyk, metadata=meta, **({"pil_kwargs": {"compression": "tiff_lzw"}} if fmt == "tiff" and not cmyk else {}))
    data = buf.getvalue()
    if fmt == "tiff" and cmyk:
        data = cmyk_tiff(data, dpi)
    if path:
        with open(path, "wb") as f:
            f.write(data)
        return {"path": path, "bytes": len(data)}
    return {"data": base64.b64encode(data).decode()}
