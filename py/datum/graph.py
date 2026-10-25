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
    """Significance brackets over a column graph: stars (or P values), stacked so they never overlap."""
    from .analysis import pv, stars
    show = o.get("brackets", "sig")
    br = [(pos[a], pos[b], p) for a, b, p in brackets if a in pos and b in pos and show != "none" and (show == "all" or p < 0.05)]
    if not br:
        return
    lo, hi = ax.get_ylim()
    h = hi - lo
    placed, top = [], hi
    for x1, x2, p in sorted(br, key=lambda t: (abs(t[1] - t[0]), min(t[:2]))):
        x1, x2 = sorted((x1, x2))
        y = max(tops[i] for i in range(x1, x2 + 1)) + 0.06 * h
        for a, b, yy in placed:
            if a <= x2 and x1 <= b:
                y = max(y, yy + 0.09 * h)
        ax.plot([x1, x1, x2, x2], [y - 0.025 * h, y, y, y - 0.025 * h], color="#222222", linewidth=0.9, zorder=4)
        text = stars(p) if o.get("ptext") != "p" else (f"P {pv(p)}" if pv(p).startswith("<") else f"P = {pv(p)}")
        ax.text((x1 + x2) / 2, y + 0.005 * h, text, ha="center", va="bottom", fontsize=size * 0.85, zorder=4)
        placed.append((x1, x2, y))
        top = max(top, y + 0.09 * h)
    ax.set_ylim(lo, top)


def draw_overlays(ax, table, graph, overlays, size, colors=OKABE_ITO, pos=None, tops=None):
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
            if o.get("label", True) and c.get("label"):
                labels.append((c["label"], col))
    if not labels:
        return
    # The corner with the fewest data points gets the equations.
    ax.autoscale_view()
    pts = np.concatenate([np.column_stack([ln.get_xdata(), ln.get_ydata()]) for ln in ax.get_lines() if len(ln.get_xdata())] or [np.zeros((0, 2))])
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


def figure(table, graph, overlays=()):
    """Builds the matplotlib figure (call inside `rc_context(rc_for(graph))`); returns (fig, ax, legend, points)."""
    size = float(graph.get("fontSize") or 10)
    frame = graph.get("style") == "frame"
    fig = Figure(figsize=(max(20, graph.get("width") or 80) * MM, max(20, graph.get("height") or 60) * MM), dpi=72, layout="constrained")
    FigureCanvasAgg(fig)
    ax = fig.add_subplot()
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)
    if not frame:
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    colors = palette(graph, len(table["sets"]))
    if table.get("kind") == "column":
        return column_figure(fig, ax, table, graph, overlays, colors, size)
    summary = stats.summarize(table)
    err, each, conn = graph.get("error", "sd"), graph.get("points") == "each", graph.get("line", False)
    direction = graph.get("errorDir", "both")
    points = []
    for k, (s, pts) in enumerate(zip(table["sets"], summary)):
        st = style_of(graph, k, colors)
        if not st["show"] or not pts:
            continue
        xs, ys = [p["x"] for p in pts], [p["mean"] for p in pts]
        mk, col = SYMBOLS.get(st["symbol"], "o"), st["color"]
        face = col if st["filled"] else "white"
        line = st["line"] if st["line"] is not None else conn
        label = s.get("title") or f"Data set {chr(65 + k)}"
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
    axes(ax, table, graph, points)
    if graph.get("title") and graph.get("showTitle", True):
        ax.set_title(graph["title"], fontweight="bold", fontsize=size * 1.15)
    leg = None
    lg = graph.get("legend") or {}
    if lg.get("show", True) and len([1 for k in range(len(table["sets"])) if style_of(graph, k, colors)["show"] and summary[k]]) > 1:
        if lg.get("loc") == "outside":
            leg = ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), frameon=False, borderaxespad=0)
        else:
            leg = ax.legend(loc=LEGEND.get(lg.get("loc", "best"), "best"), frameon=False)
    if overlays and points:
        draw_overlays(ax, table, graph, overlays, size, colors)
    if not points:
        ax.text(0.5, 0.5, "Enter X and Y values in the data table", transform=ax.transAxes, ha="center", va="center", color="#8D9AAB")
    return fig, ax, leg, points


def axes(ax, table, graph, points, only_y=False):
    """Axis titles, scales, ranges, ticks and grids from the graph settings."""
    for which, a, title, units in (("x", graph.get("x") or {}, table.get("xTitle", ""), table.get("xUnits", "")), ("y", graph.get("y") or {}, table.get("yTitle", ""), table.get("yUnits", ""))):
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


def swarm(v, h):
    """Sideways offsets that keep dots of similar value apart (a simple bee swarm)."""
    order = np.argsort(v)
    off = np.zeros(len(v))
    placed = []
    for i in order:
        y = v[i]
        near = [o for (yy, o) in placed if abs(yy - y) < h]
        for step in [0] + [s * j for j in range(1, 40) for s in (1, -1)]:
            x = step * 0.055
            if all(abs(x - o) > 0.05 for o in near) or abs(x) > 0.38:
                break
        off[i] = max(-0.38, min(0.38, x))
        placed.append((y, off[i]))
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
    h = (np.ptp(allv) or 1.0) / 16
    points, pos, tops = [], {}, []
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
            xs = i + (swarm(v, h) if kind != "paired" else np.zeros(len(v)))
            ax.plot(xs, v, linestyle="none", marker=mk, markersize=st["size"] * (0.75 if kind != "scatter" else 1), markerfacecolor=col if st["filled"] else "white", markeredgecolor=col, alpha=0.9, zorder=3)
        if kind in ("scatter", "bars", "mean") or (kind == "paired" and err != "none"):
            if kind in ("scatter", "paired"):
                ax.hlines(m, i - 0.26, i + 0.26, color="#222222" if kind == "scatter" else col, linewidth=1.6, zorder=4)
            if err != "none":
                ax.errorbar(i, m, yerr=yerr, fmt="none" if kind != "mean" else mk, markersize=st["size"], color="#222222" if kind == "scatter" else col, ecolor="#222222" if kind == "scatter" else col,
                            elinewidth=1.0, capsize=graph.get("cap", 3) * (1.6 if kind != "mean" else 1), capthick=1.0, zorder=4)
            elif kind == "mean":
                ax.plot(i, m, mk, color=col, markersize=st["size"], zorder=4)
        pos[k] = i
        tops.append(top)
        points.append([k, float(i), m, n, sd, sem])
    names = [table["sets"][k].get("title") or f"Data set {chr(65 + k)}" for k, *_ in data]
    ax.set_xticks(range(len(data)), names)
    ax.set_xlim(-0.6, len(data) - 0.4)
    ax.tick_params(axis="x", length=0)
    axes(ax, table, graph, [[0, 0, float(allv.min()) if len(allv) else 0]], only_y=True)
    if sum(len(n) for n in names) * size * 0.55 > (graph.get("width") or 80) * 2.4:
        for lab in ax.get_xticklabels():
            lab.set_rotation(30); lab.set_ha("right")
    if graph.get("title") and graph.get("showTitle", True):
        ax.set_title(graph["title"], fontweight="bold", fontsize=size * 1.15)
    if overlays and points:
        draw_overlays(ax, table, graph, overlays, size, colors, pos, tops)
    if not points:
        ax.text(0.5, 0.5, "Enter values in the data table", transform=ax.transAxes, ha="center", va="center", color="#8D9AAB")
    return fig, ax, None, points


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


def export(table, graph, fmt, path=None, dpi=300, transparent=False, overlays=()):
    """Writes the graph as png, svg, pdf, eps or tiff; without a path returns base64 (for the clipboard)."""
    with matplotlib.rc_context(rc_for(graph)):
        fig, *_ = figure(table, graph, overlays)
        if not transparent:
            fig.patch.set_alpha(1)
            fig.patch.set_facecolor("white")
        meta = {"Creator": "Datum Plot"} if fmt in ("png", "svg", "pdf") else None
        buf = io.BytesIO()
        fig.savefig(buf, format=fmt, dpi=dpi, transparent=transparent, metadata=meta, **({"pil_kwargs": {"compression": "tiff_lzw"}} if fmt == "tiff" else {}))
    data = buf.getvalue()
    if path:
        with open(path, "wb") as f:
            f.write(data)
        return {"path": path, "bytes": len(data)}
    return {"data": base64.b64encode(data).decode()}
