"""OpenDocument files, written directly (no extra library): a spreadsheet (.ods), a document (.odt) and slides
(.odp). Each is a zip of XML parts: an uncompressed `mimetype` first, the manifest, content, styles and pictures.
Text is always text: a cell starting with = never becomes a formula (formulas are a separate attribute)."""
import zipfile
from xml.sax.saxutils import escape

from .files import atomic

NS = ('xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
      'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
      'xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" '
      'xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" '
      'xmlns:presentation="urn:oasis:names:tc:opendocument:xmlns:presentation:1.0" office:version="1.3"')
MIME = {"ods": "application/vnd.oasis.opendocument.spreadsheet", "odt": "application/vnd.oasis.opendocument.text", "odp": "application/vnd.oasis.opendocument.presentation"}
FONT = '<office:font-face-decls><style:font-face style:name="Arial" svg:font-family="Arial"/></office:font-face-decls>'
TEAL, PALE, LINE = "#0E8C7F", "#E3F5F2", "#B9BFC2"


def x(s):
    """Text for XML: escaped, and without the control characters XML cannot hold."""
    return escape("".join(c for c in str(s) if c in "\t\n" or ord(c) >= 32))


def p(text, style=None):
    return f'<text:p{f" text:style-name=\"{style}\"" if style else ""}>{x(text)}</text:p>'


def save(path, kind, content, styles, pictures=()):
    """Writes the package atomically: content and styles are the inner XML of their documents."""
    files = "".join(f'<manifest:file-entry manifest:full-path="Pictures/{n}" manifest:media-type="image/png"/>' for n, _ in pictures)
    manifest = (f'<?xml version="1.0" encoding="UTF-8"?><manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3">'
                f'<manifest:file-entry manifest:full-path="/" manifest:version="1.3" manifest:media-type="{MIME[kind]}"/>'
                '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>'
                f'<manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>{files}</manifest:manifest>')
    with atomic(path) as tmp:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(zipfile.ZipInfo("mimetype"), MIME[kind], compress_type=zipfile.ZIP_STORED)
            z.writestr("META-INF/manifest.xml", manifest)
            z.writestr("content.xml", f'<?xml version="1.0" encoding="UTF-8"?><office:document-content {NS}>{FONT}{content}</office:document-content>')
            z.writestr("styles.xml", f'<?xml version="1.0" encoding="UTF-8"?><office:document-styles {NS}>{FONT}{styles}</office:document-styles>')
            for n, data in pictures:
                z.writestr(f"Pictures/{n}", data, compress_type=zipfile.ZIP_STORED)


def cell(v, style=None):
    """A table cell: numbers as numbers, everything else as text."""
    st = f' table:style-name="{style}"' if style else ""
    if v is None or v == "":
        return f"<table:table-cell{st}/>"
    if isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and abs(v) != float("inf"):
        return f'<table:table-cell{st} office:value-type="float" office:value="{v!r}"><text:p>{v:g}</text:p></table:table-cell>'
    return f'<table:table-cell{st} office:value-type="string">{p(v)}</table:table-cell>'


def table(name, rows, widths=(), head=False):
    """A table: rows of values or (value, cell style) pairs; `widths` are column style names."""
    n = max((len(r) for r in rows), default=1)
    cols = "".join(f'<table:table-column table:style-name="{w}"/>' for w in widths[:n]) + (f'<table:table-column table:number-columns-repeated="{n - len(widths)}"/>' if n > len(widths) else "")
    body = "".join("<table:table-row>" + "".join(cell(*(c if isinstance(c, tuple) else (c, "th" if head and i == 0 else None))) for c in r) + "</table:table-row>" for i, r in enumerate(rows))
    return f'<table:table table:name="{x(name)}">{cols}{body}</table:table>'


# ---------- spreadsheet ----------
def write_ods(path, sheets):
    """`sheets`: [(name, rows)], each row a list of values or (value, style) with style head, bold, title or excl."""
    auto = ('<office:automatic-styles>'
            '<style:style style:name="wide" style:family="table-column"><style:table-column-properties style:column-width="6cm"/></style:style>'
            f'<style:style style:name="head" style:family="table-cell"><style:table-cell-properties fo:background-color="{PALE}"/><style:text-properties fo:font-weight="bold"/></style:style>'
            '<style:style style:name="bold" style:family="table-cell"><style:text-properties fo:font-weight="bold"/></style:style>'
            '<style:style style:name="title" style:family="table-cell"><style:text-properties fo:font-weight="bold" fo:font-size="13pt"/></style:style>'
            '<style:style style:name="excl" style:family="table-cell"><style:text-properties fo:font-style="italic" fo:color="#1F6FD0"/></style:style>'
            '</office:automatic-styles>')
    body = "".join(table(name, rows, ("wide",) if wide else ()) for name, rows, wide in sheets)
    save(path, "ods", f"{auto}<office:body><office:spreadsheet>{body}</office:spreadsheet></office:body>", "")
    return {"path": path, "sheets": len(sheets)}


# ---------- document ----------
DOC_STYLES = (f'<office:styles><style:default-style style:family="paragraph"><style:paragraph-properties fo:margin-bottom="0.2cm"/><style:text-properties style:font-name="Arial" fo:font-size="11pt"/></style:default-style></office:styles>'
              '<office:automatic-styles><style:page-layout style:name="pm"><style:page-layout-properties fo:page-width="21cm" fo:page-height="29.7cm" fo:margin-top="2cm" fo:margin-bottom="2cm" fo:margin-left="2cm" fo:margin-right="2cm"/></style:page-layout></office:automatic-styles>'
              '<office:master-styles><style:master-page style:name="Standard" style:page-layout-name="pm"/></office:master-styles>')
DOC_AUTO = ('<office:automatic-styles>'
            '<style:style style:name="Title" style:family="paragraph"><style:paragraph-properties fo:margin-bottom="0.4cm"/><style:text-properties fo:font-size="22pt" fo:font-weight="bold"/></style:style>'
            f'<style:style style:name="H1" style:family="paragraph"><style:paragraph-properties fo:margin-top="0.6cm" fo:margin-bottom="0.25cm"/><style:text-properties fo:font-size="16pt" fo:font-weight="bold" fo:color="{TEAL}"/></style:style>'
            '<style:style style:name="H2" style:family="paragraph"><style:paragraph-properties fo:margin-top="0.4cm" fo:margin-bottom="0.15cm"/><style:text-properties fo:font-size="12.5pt" fo:font-weight="bold"/></style:style>'
            '<style:style style:name="Info" style:family="paragraph"><style:text-properties fo:font-style="italic" fo:color="#5B6878"/></style:style>'
            '<style:style style:name="Cap" style:family="paragraph"><style:text-properties fo:font-size="9.5pt"/></style:style>'
            '<style:style style:name="B" style:family="text"><style:text-properties fo:font-weight="bold"/></style:style>'
            '<style:style style:name="Small" style:family="paragraph"><style:paragraph-properties fo:margin-bottom="0cm"/><style:text-properties fo:font-size="9pt"/></style:style>'
            f'<style:style style:name="td" style:family="table-cell"><style:table-cell-properties fo:padding="0.06cm" fo:border="0.5pt solid {LINE}"/></style:style>'
            f'<style:style style:name="th" style:family="table-cell"><style:table-cell-properties fo:padding="0.06cm" fo:border="0.5pt solid {LINE}" fo:background-color="{PALE}"/></style:style>'
            '<style:style style:name="fr" style:family="graphic"><style:graphic-properties style:wrap="none" style:vertical-pos="top" style:horizontal-pos="center" style:horizontal-rel="paragraph"/></style:style>'
            '</office:automatic-styles>')


def image(name, w_cm, h_cm, anchor="as-char"):
    return (f'<draw:frame draw:style-name="fr" draw:name="{name}" text:anchor-type="{anchor}" svg:width="{w_cm:.2f}cm" svg:height="{h_cm:.2f}cm">'
            f'<draw:image xlink:href="Pictures/{name}" xlink:type="simple" xlink:show="embed" xlink:actuate="onLoad"/></draw:frame>')


def write_odt(path, blocks):
    """`blocks`: ("title"|"h1"|"h2"|"info"|"p", text), ("figure", png, w_cm, h_cm, number, caption) or ("table", title, columns, rows)."""
    out, pics, nt = [], [], 0
    for b in blocks:
        k = b[0]
        if k == "figure":
            _, png, w, h, n, cap = b
            name = f"figure{n}.png"
            pics.append((name, png))
            out.append(f"<text:p>{image(name, w, h)}</text:p>")
            out.append(f'<text:p text:style-name="Cap"><text:span text:style-name="B">Figure {n}. </text:span>{x(cap)}</text:p>')
        elif k == "table":
            _, title, columns, rows = b
            nt += 1
            if title:
                out.append(f'<text:p><text:span text:style-name="B">{x(title)}</text:span></text:p>')
            sm = lambda v, s: f'<table:table-cell table:style-name="{s}" office:value-type="string">{p(v, "Small")}</table:table-cell>'
            body = "".join("<table:table-row>" + "".join(sm(v, "th" if i == 0 else "td") for v in r) + "</table:table-row>" for i, r in enumerate([columns] + rows))
            out.append(f'<table:table table:name="Table{nt}"><table:table-column table:number-columns-repeated="{len(columns)}"/>{body}</table:table>')
        else:
            out.append(p(b[1], {"title": "Title", "h1": "H1", "h2": "H2", "info": "Info"}.get(k)))
    save(path, "odt", f"{DOC_AUTO}<office:body><office:text>{''.join(out)}</office:text></office:body>", DOC_STYLES, pics)


# ---------- slides ----------
W, H = 28.0, 15.75  # 16:9, in cm
SLIDE_STYLES = ('<office:automatic-styles><style:page-layout style:name="pm"><style:page-layout-properties fo:margin="0cm" fo:page-width="28cm" fo:page-height="15.75cm" style:print-orientation="landscape"/></style:page-layout>'
                '<style:style style:name="dp" style:family="drawing-page"><style:drawing-page-properties draw:fill="solid" draw:fill-color="#FFFFFF"/></style:style></office:automatic-styles>'
                '<office:master-styles><style:master-page style:name="Default" style:page-layout-name="pm" draw:style-name="dp"/></office:master-styles>')
SLIDE_AUTO = ('<office:automatic-styles>'
              '<style:style style:name="box" style:family="graphic"><style:graphic-properties draw:stroke="none" draw:fill="none" draw:textarea-vertical-align="top"/></style:style>'
              '<style:style style:name="T" style:family="paragraph"><style:text-properties style:font-name="Arial" fo:font-size="28pt" fo:font-weight="bold"/></style:style>'
              '<style:style style:name="Big" style:family="paragraph"><style:text-properties style:font-name="Arial" fo:font-size="40pt" fo:font-weight="bold"/></style:style>'
              '<style:style style:name="Sub" style:family="paragraph"><style:text-properties style:font-name="Arial" fo:font-size="18pt" fo:color="#5B6878"/></style:style>'
              '<style:style style:name="Txt" style:family="paragraph"><style:paragraph-properties fo:margin-bottom="0.3cm"/><style:text-properties style:font-name="Arial" fo:font-size="20pt"/></style:style>'
              '</office:automatic-styles>')


def textbox(x0, y0, w, h, paras):
    return f'<draw:frame draw:style-name="box" svg:x="{x0}cm" svg:y="{y0}cm" svg:width="{w}cm" svg:height="{h}cm"><draw:text-box>{paras}</draw:text-box></draw:frame>'


def write_odp(path, title, sub, figures, texts):
    """A title slide, a slide per figure (name, png, aspect w/h) and a slide per result (name, answer)."""
    pages, pics = [textbox(1.5, 5.2, 25, 3, p(title, "Big")) + textbox(1.5, 8.6, 25, 2, p(sub, "Sub"))], []
    for i, (name, png, aspect) in enumerate(figures):
        pic = f"slide{i + 1}.png"
        pics.append((pic, png))
        h = H - 3.4 - 0.8
        w = h * aspect
        if w > W - 2:
            w = W - 2
            h = w / aspect
        pages.append(textbox(1, 0.6, W - 2, 2.2, p(name, "T")) + f'<draw:frame draw:name="{pic}" svg:x="{(W - w) / 2:.2f}cm" svg:y="3.2cm" svg:width="{w:.2f}cm" svg:height="{h:.2f}cm"><draw:image xlink:href="Pictures/{pic}" xlink:type="simple" xlink:show="embed" xlink:actuate="onLoad"/></draw:frame>')
    for name, text in texts:
        pages.append(textbox(1, 0.6, W - 2, 2.2, p(name, "T")) + textbox(1, 3.2, W - 2, H - 4, p(text, "Txt")))
    body = "".join(f'<draw:page draw:name="Slide {i + 1}" draw:master-page-name="Default">{pg}</draw:page>' for i, pg in enumerate(pages))
    save(path, "odp", f"{SLIDE_AUTO}<office:body><office:presentation>{body}</office:presentation></office:body>", SLIDE_STYLES, pics)
    return len(pages)
