"""Graphs with matplotlib in the Prism style: what the window shows (SVG) and what is exported.

`render(table, graph)` returns the SVG plus where the plot area, the axes and the legend are
(in points from the top-left), so the window can map the mouse to data and open the right
part of Format Graph on a double-click.
"""
import base64
import io
import math

import matplotlib

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


def style_of(graph, k):
    """A data set's look: saved settings over the defaults for its position."""
    s = (graph.get("sets") or [])[k] if k < len(graph.get("sets") or []) else {}
    return {"show": s.get("show", True), "color": s.get("color") or OKABE_ITO[k % 8], "symbol": s.get("symbol") or SYMBOL_ORDER[k % 8],
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


def figure(table, graph):
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
    summary = stats.summarize(table)
    err, each, conn = graph.get("error", "sd"), graph.get("points") == "each", graph.get("line", False)
    direction = graph.get("errorDir", "both")
    points = []
    for k, (s, pts) in enumerate(zip(table["sets"], summary)):
        st = style_of(graph, k)
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
    for which, a, title, units in (("x", graph.get("x") or {}, table.get("xTitle", ""), table.get("xUnits", "")), ("y", graph.get("y") or {}, table.get("yTitle", ""), table.get("yUnits", ""))):
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
    if graph.get("title") and graph.get("showTitle", True):
        ax.set_title(graph["title"], fontweight="bold", fontsize=size * 1.15)
    leg = None
    lg = graph.get("legend") or {}
    if lg.get("show", True) and len([1 for k in range(len(table["sets"])) if style_of(graph, k)["show"] and summary[k]]) > 1:
        if lg.get("loc") == "outside":
            leg = ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), frameon=False, borderaxespad=0)
        else:
            leg = ax.legend(loc=LEGEND.get(lg.get("loc", "best"), "best"), frameon=False)
    if not points:
        ax.text(0.5, 0.5, "Enter X and Y values in the data table", transform=ax.transAxes, ha="center", va="center", color="#8D9AAB")
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


def render(table, graph):
    """SVG text and geometry for the window."""
    with matplotlib.rc_context(rc_for(graph)):
        fig, ax, leg, points = figure(table, graph)
        g = geometry(fig, ax, leg)
        buf = io.StringIO()
        fig.savefig(buf, format="svg", metadata={"Date": None, "Creator": "Datum Plot"})
    return {"svg": buf.getvalue(), "points": [p if all(math.isfinite(v) for v in p[1:3]) else None for p in points], **g}


def export(table, graph, fmt, path=None, dpi=300, transparent=False):
    """Writes the graph as png, svg, pdf, eps or tiff; without a path returns base64 (for the clipboard)."""
    with matplotlib.rc_context(rc_for(graph)):
        fig, *_ = figure(table, graph)
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
