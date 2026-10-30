"""Slides and documents (G5): every graph of a project on its own slide (.pptx or .odp), or a document (.docx or
.odt) with the project's details, every graph with a caption, and every result: its answer, main table and methods
text. The file type follows the extension of the chosen path."""
import base64
import datetime
import io

from . import analysis, graph
from .files import atomic


def parts(project):
    """(graph name, PNG bytes) of every graph, with its fitted curves and brackets."""
    tables = {t["id"]: t for t in project.get("tables", [])}
    out = []
    for gr in project.get("graphs", []):
        t = tables.get(gr["table"])
        if not t:
            continue
        s = gr.get("settings", {})
        ovs = [a for a in project.get("analyses", []) if a["id"] in (s.get("overlays") or [])]
        out.append((gr.get("name") or t.get("name") or "Graph", base64.b64decode(graph.export(t, s, "png", None, 300, False, ovs)["data"]), s))
    return out


def results(project):
    """(name, result) of every analysis that can be worked out."""
    tables = {t["id"]: t for t in project.get("tables", [])}
    out = []
    for a in project.get("analyses", []):
        t = tables.get(a["table"])
        if not t:
            continue
        try:
            out.append((a.get("name") or a["kind"], analysis.run(a["kind"], t, a.get("sets", []), a.get("options", {}))))
        except Exception as e:
            out.append((a.get("name") or a["kind"], {"answer": f"Could not be worked out: {e}", "tabs": [], "methods": ""}))
    return out


def title_of(project):
    info = project.get("info") or {}
    return info.get("title") or project.get("name") or "Datum Plot project"


def byline(project):
    info = project.get("info") or {}
    return " · ".join(x for x in (info.get("researcher"), info.get("organisation"), info.get("date") or datetime.date.today().isoformat()) if x)


def slides(project, path):
    if path.lower().endswith(".odp"):
        from . import odf
        figs = [(name, png, (s.get("width") or 80) / (s.get("height") or 60)) for name, png, s in parts(project)]
        n = odf.write_odp(path, title_of(project), byline(project), figs, [(name, r.get("answer", "")) for name, r in results(project)])
        return {"path": path, "slides": n}
    from pptx import Presentation
    from pptx.util import Emu, Pt
    p = Presentation()
    p.slide_width, p.slide_height = Emu(12192000), Emu(6858000)  # 16:9
    W, H = p.slide_width, p.slide_height
    first = p.slides.add_slide(p.slide_layouts[0])
    first.shapes.title.text = title_of(project)
    info = project.get("info") or {}
    first.placeholders[1].text = " · ".join(x for x in (info.get("researcher"), info.get("organisation"), info.get("date") or datetime.date.today().isoformat()) if x)
    for name, png, s in parts(project):
        sl = p.slides.add_slide(p.slide_layouts[5])  # title only
        sl.shapes.title.text = name
        sl.shapes.title.text_frame.paragraphs[0].font.size = Pt(28)
        top = Emu(int(H * 0.2))
        h = H - top - Emu(int(H * 0.05))
        w = int(h * (s.get("width") or 80) / (s.get("height") or 60))
        if w > W * 0.9:
            w = int(W * 0.9)
            h = Emu(int(w * (s.get("height") or 60) / (s.get("width") or 80)))
        sl.shapes.add_picture(io.BytesIO(png), Emu(int((W - w) / 2)), top, Emu(w), h)
    for name, r in results(project):
        sl = p.slides.add_slide(p.slide_layouts[1])
        sl.shapes.title.text = name
        tf = sl.placeholders[1].text_frame
        tf.text = r.get("answer", "")
        for para in tf.paragraphs:
            para.font.size = Pt(20)
    with atomic(path) as tmp:
        p.save(tmp)
    return {"path": path, "slides": len(p.slides)}


def document_odt(project, path):
    """The document as .odt: the same parts as the .docx."""
    from . import odf
    info = project.get("info") or {}
    blocks = [("title", title_of(project)), ("info", byline(project))] + ([("p", info["experiment"])] if info.get("experiment") else [])
    figs = parts(project)
    if figs:
        blocks.append(("h1", "Figures"))
        for i, (name, png, s) in enumerate(figs):
            w = min(16.0, (s.get("width") or 80) / 10 * 1.6)
            blocks.append(("figure", png, w, w * (s.get("height") or 60) / (s.get("width") or 80), i + 1, name))
    res = results(project)
    if res:
        blocks.append(("h1", "Results"))
        for name, r in res:
            blocks += [("h2", name), ("p", r.get("answer", ""))]
            for tab in (r.get("tabs") or [])[:1]:
                for tb in tab.get("tables", [])[:2]:
                    if tb.get("rows"):
                        n = len(tb["columns"])
                        blocks.append(("table", tb.get("title", ""), [str(c) for c in tb["columns"]], [[str(v) for v in (row[:n] + [""] * n)[:n]] for row in tb["rows"][:40]]))
        methods = [r.get("methods") for _, r in res if r.get("methods")]
        if methods:
            blocks += [("h1", "Methods"), ("p", " ".join(dict.fromkeys(methods)))]
    odf.write_odt(path, blocks)
    return {"path": path, "figures": len(figs), "results": len(res)}


def word(project, path):
    if path.lower().endswith(".odt"):
        return document_odt(project, path)
    from docx import Document
    from docx.shared import Cm, Pt
    d = Document()
    d.styles["Normal"].font.name = "Calibri"
    d.styles["Normal"].font.size = Pt(11)
    d.add_heading(title_of(project), 0)
    info = project.get("info") or {}
    line = " · ".join(x for x in (info.get("researcher"), info.get("organisation"), info.get("date") or datetime.date.today().isoformat()) if x)
    if line:
        d.add_paragraph(line).italic = True
    if info.get("experiment"):
        d.add_paragraph(info["experiment"])
    figs = parts(project)
    if figs:
        d.add_heading("Figures", 1)
        for i, (name, png, s) in enumerate(figs):
            d.add_picture(io.BytesIO(png), width=Cm(min(16.0, (s.get("width") or 80) / 10 * 1.6)))
            cap = d.add_paragraph()
            cap.add_run(f"Figure {i + 1}. ").bold = True
            cap.add_run(name)
    res = results(project)
    if res:
        d.add_heading("Results", 1)
        for name, r in res:
            d.add_heading(name, 2)
            d.add_paragraph(r.get("answer", ""))
            for tab in (r.get("tabs") or [])[:1]:
                for tb in tab.get("tables", [])[:2]:
                    if not tb.get("rows"):
                        continue
                    if tb.get("title"):
                        d.add_paragraph().add_run(tb["title"]).bold = True
                    cols = tb["columns"]
                    w = d.add_table(rows=1, cols=len(cols))
                    w.style = "Light Grid Accent 1"
                    for j, c in enumerate(cols):
                        w.rows[0].cells[j].text = str(c)
                    for row in tb["rows"][:40]:
                        cells = w.add_row().cells
                        for j, v in enumerate(row[:len(cols)]):
                            cells[j].text = str(v)
        methods = [r.get("methods") for _, r in res if r.get("methods")]
        if methods:
            d.add_heading("Methods", 1)
            d.add_paragraph(" ".join(dict.fromkeys(methods)))
    with atomic(path) as tmp:
        d.save(tmp)
    return {"path": path, "figures": len(figs), "results": len(res)}
