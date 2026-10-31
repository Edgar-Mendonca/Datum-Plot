"""Ternary, bubble, waterfall and radar graphs (D19). Each returns (fig, ax, legend, points) like the other
figures in graph.py, whose helpers it uses.
  ternary   — a many-variables table: the first three variables of each row, as shares of their sum, on a triangle;
  bubble    — a many-variables table: X, Y, then the bubble's area (and a fourth variable as its colour);
  waterfall — an XY table: each data set's curve lifted above the previous one, labelled at its right end;
  radar     — a grouped table: the rows are the spokes, each data set a closed outline through its means."""
import math

import numpy as np

from . import stats


def variables(table, n):
    """The first n variables of a many-variables table as columns of floats (rows with all n values only), with their names."""
    ex = {tuple(e) for e in table.get("excluded", [])}
    spans = stats.set_columns(table)[:n]
    if len(spans) < n:
        raise ValueError(f"This graph needs {n} variables (columns) in the table; it has {len(spans)}.")
    rows = []
    for r in range(table["rows"]):
        v = [stats.value(table, r, c0, ex) for c0, _ in spans]
        if all(x is not None and math.isfinite(x) for x in v):
            rows.append(v)
    names = [s.get("title") or f"Variable {chr(65 + k)}" for k, s in enumerate(table["sets"][:n])]
    return np.array(rows, float).reshape(-1, n), names


def title(ax, graph, size):
    if graph.get("title") and graph.get("showTitle", True):
        ax.set_title(graph["title"], fontweight="bold", fontsize=size * 1.15)


def ternary_figure(fig, ax, table, graph, colors, size):
    from .graph import style_of
    V, names = variables(table, 3)
    V = V[(V >= 0).all(1) & (V.sum(1) > 0)]
    f = V / V.sum(1, keepdims=True)
    # Corners: first variable at the top, second bottom left, third bottom right.
    corner = np.array([[0.5, math.sqrt(3) / 2], [0.0, 0.0], [1.0, 0.0]])
    xy = f @ corner
    ax.set_aspect("equal")
    ax.axis("off")
    ax.plot(*np.vstack([corner, corner[:1]]).T, color="#333333", lw=0.9)
    for t in np.arange(0.2, 1.0, 0.2):  # grid every 20 %
        for i in range(3):
            j, k = (i + 1) % 3, (i + 2) % 3
            a, b = corner[i] * t + corner[j] * (1 - t), corner[i] * t + corner[k] * (1 - t)
            ax.plot([a[0], b[0]], [a[1], b[1]], color="#D9DDE1", lw=0.5, zorder=0)
            ax.text(*(a + (a - corner[k]) * 0.04), f"{t * 100:.0f}", fontsize=size * 0.6, color="#8A96A3", ha="center", va="center")
    for (x, y), n, (ha, va, dx, dy) in zip(corner, names, [("center", "bottom", 0, 0.04), ("right", "top", -0.02, -0.03), ("left", "top", 0.02, -0.03)]):
        ax.text(x + dx, y + dy, n, fontsize=size, fontweight="bold" if graph.get("boldTitles", True) else "normal", ha=ha, va=va)
    st = style_of(graph, 0, colors)
    from .graph import SYMBOLS
    ax.scatter(xy[:, 0], xy[:, 1], s=(st["size"] * 0.9) ** 2, marker=SYMBOLS.get(st["symbol"], "o") or "o", color=st["color"] if st["filled"] else "white",
               edgecolors=st["color"], linewidths=0.8, zorder=3)
    ax.set_xlim(-0.08, 1.08)
    ax.set_ylim(-0.1, math.sqrt(3) / 2 + 0.1)
    title(ax, graph, size)
    return fig, ax, None, []


def bubble_figure(fig, ax, table, graph, colors, size):
    from .graph import axis_title
    n = 4 if len(table["sets"]) >= 4 else 3
    V, names = variables(table, n)
    x, y, z = V[:, 0], V[:, 1], np.abs(V[:, 2])
    zmax = z.max() if len(z) and z.max() > 0 else 1.0
    area = 600 * z / zmax + 4  # points²: the largest bubble about 25 pt across
    kw = dict(s=area, alpha=0.7, edgecolors="white", linewidths=0.6, zorder=3)
    if n == 4:
        from matplotlib import colormaps
        sc = ax.scatter(x, y, c=V[:, 3], cmap=colormaps["viridis"], **kw)
        cb = fig.colorbar(sc, ax=ax, location="top", pad=0.02, fraction=0.05, aspect=30)  # above, so the size key has the right side
        cb.set_label(names[3], fontsize=size * 0.85)
        cb.ax.tick_params(labelsize=size * 0.75)
    else:
        ax.scatter(x, y, color=colors[0], **kw)
    xa, ya = graph.get("x") or {}, graph.get("y") or {}
    ax.set_xlabel(axis_title(xa, names[0], ""), fontsize=size, fontweight="bold" if graph.get("boldTitles", True) else "normal")
    ax.set_ylabel(axis_title(ya, names[1], ""), fontsize=size, fontweight="bold" if graph.get("boldTitles", True) else "normal")
    ax.tick_params(labelsize=size * 0.85)
    ax.margins(0.12)
    # A key of three bubble sizes.
    ref = [v for v in (zmax, zmax / 2, zmax / 4)]
    handles = [ax.scatter([], [], s=600 * v / zmax + 4, color="#B8C0CA", edgecolors="white") for v in ref]
    leg = ax.legend(handles, [f"{v:.3g}" for v in ref], title=names[2], title_fontsize=size * 0.8, fontsize=size * 0.75, frameon=False, loc="upper left",
                    bbox_to_anchor=(1.02, 1), labelspacing=1.4, borderaxespad=0) if (graph.get("legend") or {}).get("show", True) else None
    title(ax, graph, size)
    return fig, ax, leg, [[k, float(a), float(b), 0, 0, 0, 0] for k, (a, b) in enumerate(zip(x, y))]


def waterfall_figure(fig, ax, table, graph, colors, size, summary):
    from .graph import SYMBOLS, axis_title, style_of
    curves = []
    for k, (s, pts) in enumerate(zip(table["sets"], summary)):
        st = style_of(graph, k, colors)
        if st["show"] and pts:
            curves.append((k, s.get("title") or f"Data set {chr(65 + k)}", np.array([p["x"] for p in pts], float), np.array([p["mean"] for p in pts], float), st))
    if not curves:
        return fig, ax, None, []
    span = max(float(np.nanmax(c[3]) - np.nanmin(c[3])) for c in curves) or 1.0
    step = float(graph.get("offset") or 0) or 0.6 * span  # 0 = automatic
    for i, (k, name, x, y, st) in enumerate(curves):
        lift = i * step
        ax.plot(x, y + lift, color=st["color"], linewidth=st["width"] * 1.2, marker=SYMBOLS.get(st["symbol"], "") if graph.get("points") == "each" else None,
                markersize=st["size"] * 0.6, zorder=3 + i)
        j = int(np.nanargmax(x))
        ax.annotate(name, (x[j], y[j] + lift), xytext=(4, 0), textcoords="offset points", fontsize=size * 0.75, color=st["color"], va="center")
    xa, ya = graph.get("x") or {}, graph.get("y") or {}
    bold = "bold" if graph.get("boldTitles", True) else "normal"
    ax.set_xlabel(axis_title(xa, table.get("xTitle", ""), table.get("xUnits", "")), fontsize=size, fontweight=bold)
    ax.set_ylabel(axis_title(ya, table.get("yTitle", ""), table.get("yUnits", "")) + " (offset)", fontsize=size, fontweight=bold)
    ax.set_yticks([])
    ax.tick_params(labelsize=size * 0.85)
    ax.margins(x=0.12)
    title(ax, graph, size)
    return fig, ax, None, []


def radar_figure(fig, ax, table, graph, colors, size):
    from .graph import SYMBOLS, style_of
    ex = {tuple(e) for e in table.get("excluded", [])}
    titles = table.get("rowTitles") or []
    spans = stats.set_columns(table)
    rows = [r for r in range(table["rows"]) if any(stats.value(table, r, c, ex) is not None for c0, w in spans for c in range(c0, c0 + w))]
    if len(rows) < 3:
        raise ValueError("A radar graph needs at least three rows (its spokes).")
    labels = [(titles[r] if r < len(titles) else "") or f"Row {r + 1}" for r in rows]
    ax.remove()
    ax = fig.add_subplot(projection="polar")
    ax.patch.set_alpha(0)
    th = np.linspace(0, 2 * np.pi, len(rows), endpoint=False)
    for k, (s, (c0, w)) in enumerate(zip(table["sets"], spans)):
        st = style_of(graph, k, colors)
        if not st["show"]:
            continue
        w = w if s.get("entry", "rep") == "rep" else 1
        m = [np.nanmean([v for c in range(c0, c0 + w) if (v := stats.value(table, r, c, ex)) is not None] or [np.nan]) for r in rows]
        if all(np.isnan(m)):
            continue
        mm = np.r_[m, m[:1]]
        tt = np.r_[th, th[:1]]
        ax.plot(tt, mm, color=st["color"], linewidth=st["width"] * 1.3, marker=SYMBOLS.get(st["symbol"], "o") or None, markersize=st["size"] * 0.6,
                label=s.get("title") or f"Data set {chr(65 + k)}", zorder=3)
        ax.fill(tt, mm, color=st["color"], alpha=0.12, zorder=2)
    ax.set_xticks(th)
    ax.set_xticklabels(labels, fontsize=size * 0.85)
    ax.tick_params(axis="y", labelsize=size * 0.65, colors="#8A96A3")
    ax.set_rlabel_position(180 / len(rows))  # the scale between the first two spokes, clear of their labels
    ax.grid(True, color="#D9DDE1", linewidth=0.6)
    ya = graph.get("y") or {}
    if not ya.get("auto", True) and ya.get("min") is not None and ya.get("max") is not None and ya["max"] > ya["min"]:
        ax.set_ylim(ya["min"], ya["max"])
    else:
        ax.set_ylim(bottom=min(0.0, ax.get_ylim()[0]))
    title(ax, graph, size)
    lg = graph.get("legend") or {}
    leg = ax.legend(loc="upper left", bbox_to_anchor=(1.1, 1.05), frameon=False, borderaxespad=0, fontsize=size * 0.85) if lg.get("show", True) and len(ax.get_lines()) > 1 else None
    return fig, ax, leg, []
