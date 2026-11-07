# Plan 0.3.18: embedded graphs (Copy Embedded)

Session 13. Users (GitHub #12 and others) asked to paste a graph into a document, slides or a workbook and edit it
again later from there. Datum Plot 0.3.4 tried linked picture files, which documents treat as plain pictures, and was
removed in 0.3.5. The user asked how this could be done properly, then decided: OLE embedding, a separate command
called **Copy Embedded** beside Copy Picture, tested by the user and a tester in their office programs on Windows.

## 1. How it works

| Step | What happens |
|---|---|
| Copy Embedded | The clipboard gets a "Datum Plot Graph" object: the graph's own small project (its table, settings and the analyses drawn on it) and its picture (enhanced metafile, metafile picture, DIB, PNG) |
| Paste | The document stores the object: our two streams (`DatumPlot`, `DatumPlotPicture`) and the picture Windows caches for it |
| Double-click | Windows starts Datum Plot with `-Embedding`; the window stays hidden until the document asks to show the graph, then opens on it with a bar: "Editing a graph embedded in …" |
| Update | The window saves into the document (through its client site) and tells it the picture changed |
| Close | Update and Close, or Close without Updating; the document is told and Datum Plot ends |

Windows only: on a Mac or in a browser the document shows the picture.

## 2. Pieces

- `crates/ole` (Rust, windows-rs): the object (IOleObject, IDataObject, IPersistStorage), the class factory, the
  clipboard copy, the per-user registration (HKCU\Software\Classes, written at every start). Four tests run on
  Windows CI: save and load, every picture format, paste through `OleCreateFromData` with drawing, saving and loading
  as a document would, and the clipboard.
- `src-tauri/src/embed.rs`: Copy Embedded, Update, close, and the `-Embedding` start.
- `crates/core`: `Project::graph_only`.
- The window: Share › Copy Embedded and the right-click menus, the editing bar, Update (and Ctrl+S), the close prompt.
- The uninstaller removes the registration.

## 3. What the testers check (each office program they use, on Windows)

1. Copy Embedded in Datum Plot, paste into a document, slides and a workbook: does it look right, at the right size?
2. Save the document, close it, open it again: is the graph still there?
3. Double-click the graph: does Datum Plot open on it? How long does it take?
4. Change something, Update: does the graph in the document change? Then close Datum Plot.
5. Same, but close the window and choose Update and Close.
6. Copy the document to another computer with Datum Plot: does the double-click work there?
7. Anything odd: a screenshot of the message, and which program and version.

## 4. Then

0.3.19 is kept for the fixes the testers report; wavelets and the rest of the roadmap move by two.
