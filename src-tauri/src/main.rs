//! Datum Plot desktop shell: owns the open project, files, options and recovery, talks to the
//! window, and passes graphs to the Python engine.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
mod py;
mod runtime;
mod update;

use datum_core::{doc::{write_atomic, Doc, Op}, templates, DataSet, Entry, GraphSettings, Project, Table};
use py::{Calc, Engine, Py};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::{path::{Path, PathBuf}, sync::{Mutex, PoisonError}};
use tauri::{AppHandle, Emitter, Manager, State, WindowEvent};
use tauri_plugin_clipboard_manager::ClipboardExt;
use tauri_plugin_dialog::DialogExt;

#[derive(Clone, Serialize, Deserialize)]
#[serde(default, rename_all = "camelCase")]
struct Options {
    /// auto, light or dark.
    theme: String,
    /// Minutes between recovery saves; 0 turns them off.
    autosave: u32,
    /// Offer beta (pre-release) versions in Check for updates.
    beta: bool,
    /// Reopen the last project at start.
    open_last: bool,
    /// Decimal places shown in data tables (-1 = as typed).
    decimals: i32,
    /// New tables: replicates per data set and how values are entered.
    reps: usize,
    entry: String,
    /// New graphs: error bars, size (mm), font, style.
    error: String,
    width: f64,
    height: f64,
    font: String,
    font_size: f64,
    style: String,
    /// Picture export resolution.
    dpi: u32,
    /// Printing and branding.
    paper: String,
    landscape: bool,
    company: String,
    logo: String,
    /// Graph styles the user saved (name → settings), for Graph › Styles.
    styles: Value,
    /// My Analyses (H2): console code the user saved (name → code). Kept with the app, never in projects,
    /// so opening someone else's project never runs code.
    snippets: Value,
}

impl Default for Options {
    fn default() -> Self {
        Self {
            theme: "auto".into(), autosave: 5, beta: false, open_last: false, decimals: -1, reps: 3, entry: "rep".into(), error: "sd".into(), width: 80.0, height: 60.0,
            font: "Arial".into(), font_size: 10.0, style: "prism".into(), dpi: 300, paper: "A4".into(), landscape: false, company: String::new(), logo: String::new(), styles: json!({}), snippets: json!({}),
        }
    }
}

impl Options {
    /// Graph settings for a new graph.
    fn graph(&self) -> GraphSettings {
        GraphSettings { error: self.error.clone(), width: self.width, height: self.height, font: self.font.clone(), font_size: self.font_size, style: self.style.clone(), ..Default::default() }
    }
    fn table(&self) -> Table {
        let entry = match self.entry.as_str() { "msn" => Entry::MeanSdN, "mesn" => Entry::MeanSemN, _ => Entry::Replicates };
        Table { sets: vec![DataSet { title: "Data set A".into(), entry, reps: self.reps.clamp(1, 50), ..Default::default() }], ..Default::default() }
    }
}

struct App {
    doc: Doc,
    opts: Options,
    rev: u64,
}

struct St(Mutex<App>);
type R<T> = Result<T, String>;

/// What the window gets after every change.
#[derive(Serialize)]
struct Out<'a> {
    project: &'a Project,
    path: Option<String>,
    dirty: bool,
    undo: bool,
    redo: bool,
    rev: u64,
}

fn out(a: &App) -> Value {
    let d = &a.doc;
    serde_json::to_value(Out { project: &d.p, path: d.path.as_ref().map(|p| p.display().to_string()), dirty: d.dirty, undo: d.can_undo(), redo: d.can_redo(), rev: a.rev }).unwrap_or_default()
}

fn dir(app: &AppHandle, data: bool) -> Option<PathBuf> {
    let d = if data { app.path().app_data_dir() } else { app.path().app_config_dir() }.ok()?;
    std::fs::create_dir_all(&d).ok()?;
    Some(d)
}

#[tauri::command]
fn state(st: State<St>) -> Value {
    out(&st.0.lock().unwrap_or_else(PoisonError::into_inner))
}

#[tauri::command]
fn apply(st: State<St>, op: Op) -> R<Value> {
    let mut a = st.0.lock().unwrap_or_else(PoisonError::into_inner);
    // New tables and graphs without settings follow the options.
    let op = match op {
        Op::AddGraph { table, settings: None } => Op::AddGraph { table, settings: Some(Box::new(a.opts.graph())) },
        Op::Import { name, entry, reps, header, rows, graph: None } => Op::Import { name, entry, reps, header, rows, graph: Some(Box::new(a.opts.graph())) },
        o => o,
    };
    guard(|| a.doc.apply(op))?;
    a.rev += 1;
    Ok(out(&a))
}

/// A small settings file (options, recent files, recovery details): read only if under 8 MB.
fn read_small(f: &Path) -> Option<String> {
    (std::fs::metadata(f).ok()?.len() < 8 << 20).then(|| std::fs::read_to_string(f).ok()).flatten()
}

/// Runs `f`, turning a panic into an error message (the document is untouched: edits work on a copy);
/// the panic hook has written the details to crash.log.
fn guard<T>(f: impl FnOnce() -> R<T>) -> R<T> {
    std::panic::catch_unwind(std::panic::AssertUnwindSafe(f)).unwrap_or_else(|_| Err("Something went wrong inside Datum Plot, so that step was not done; your project is as it was. Details are in crash.log in the app's data folder.".into()))
}

/// A new, empty data table (XY from the options, a column or a grouped table) with its graph.
/// A new table's graph: the options' look with what suits its kind.
fn graph_for(kind: &str, g: GraphSettings) -> GraphSettings {
    match kind {
        "column" | "multi" => GraphSettings { points: "each".into(), ..g },
        "grouped" => GraphSettings { column: "bars".into(), ..g },
        "survival" => GraphSettings { error: "none".into(), ..g },
        "nested" => GraphSettings { error: "sd".into(), ..g },
        "matrix" => GraphSettings { column: "contour".into(), palette: "viridis".into(), ..g },
        "parts" => GraphSettings { column: "pie".into(), error: "none".into(), ..g },
        "contingency" => GraphSettings { column: "percent".into(), error: "none".into(), ..g },
        _ => g,
    }
}

/// Adds imported tables (a .pzfx project, a plate, several runs), each with its graph, as one step (A13, A14).
#[tauri::command]
fn import_tables(st: State<St>, tables: Vec<Table>) -> R<Value> {
    let mut a = st.0.lock().unwrap_or_else(PoisonError::into_inner);
    let g = a.opts.graph();
    let ops = tables.into_iter().map(|t| Op::NewTable { graph: Some(Box::new(graph_for(&t.kind, g.clone()))), table: Box::new(t) }).collect();
    guard(|| a.doc.apply(Op::Batch(ops)))?;
    a.rev += 1;
    Ok(out(&a))
}

/// File › Import Several Files: one run per file, joined when they share X (A14); with `separate`, one table
/// per file (Tools › Batch Process).
#[tauri::command]
async fn import_files(app: AppHandle, st: State<'_, St>, separate: Option<bool>) -> R<Option<Value>> {
    let Some(files) = app.dialog().file().add_filter("Data files", &["csv", "tsv", "txt", "dat", "prn", "xlsx", "xlsm"]).blocking_pick_files() else { return Ok(None) };
    let paths: Vec<String> = files.into_iter().filter_map(|f| f.into_path().ok()).map(|p| p.display().to_string()).collect();
    let q = json!({ "cmd": "read_many", "paths": paths, "separate": separate.unwrap_or(false) });
    let h = app.clone();
    let r = tauri::async_runtime::spawn_blocking(move || h.state::<Engine>().0.lock().unwrap_or_else(PoisonError::into_inner).ask(&h, &q)).await.map_err(|e| e.to_string())??;
    let tables: Vec<Table> = serde_json::from_value(r["tables"].clone()).map_err(|e| e.to_string())?;
    import_tables(st, tables).map(Some)
}

/// Tools › Python Console (H1): runs the user's code on the project's tables; tables it makes are added
/// (one undo step). `reset` clears the console's variables.
#[tauri::command]
async fn console(app: AppHandle, st: State<'_, St>, code: String, reset: Option<bool>) -> R<Value> {
    let q = { let a = st.0.lock().unwrap_or_else(PoisonError::into_inner); json!({ "cmd": "console", "project": a.doc.p, "code": code, "reset": reset.unwrap_or(false) }) };
    let h = app.clone();
    let mut r = tauri::async_runtime::spawn_blocking(move || h.state::<Calc>().0.lock().unwrap_or_else(PoisonError::into_inner).ask(&h, &q)).await.map_err(|e| e.to_string())?
        .map_err(|e| if e.contains("longer than") { format!("The code ran for more than a minute, so the engine was restarted and the console's variables were cleared ({e}).") } else { e })?;
    let tables: Vec<Table> = serde_json::from_value(r["tables"].take()).unwrap_or_default();
    if !tables.is_empty() {
        import_tables(st, tables)?;
    }
    r["state"] = state(app.state::<St>());
    Ok(r)
}

/// Tools › Notebook: the project as a Jupyter notebook (.ipynb) (H5).
#[tauri::command]
async fn export_notebook(app: AppHandle, st: State<'_, St>) -> R<Option<String>> {
    let (name, project) = { let a = st.0.lock().unwrap_or_else(PoisonError::into_inner); (a.doc.p.name.clone(), serde_json::to_value(&a.doc.p).map_err(|e| e.to_string())?) };
    let Some(path) = app.dialog().file().add_filter("Jupyter notebook", &["ipynb"]).set_file_name(format!("{name}.ipynb")).blocking_save_file().and_then(|f| f.into_path().ok()) else { return Ok(None) };
    let q = json!({ "cmd": "notebook", "project": project, "path": path.display().to_string() });
    let h = app.clone();
    tauri::async_runtime::spawn_blocking(move || h.state::<Calc>().0.lock().unwrap_or_else(PoisonError::into_inner).ask(&h, &q)).await.map_err(|e| e.to_string())??;
    Ok(Some(path.display().to_string()))
}

/// The region tool (E5): statistics of each curve between two X values (and Y values, for a box).
#[tauri::command]
async fn region(app: AppHandle, st: State<'_, St>, table: u32, x0: f64, x1: f64, y0: Option<f64>, y1: Option<f64>) -> R<Value> {
    let q = {
        let a = st.0.lock().unwrap_or_else(PoisonError::into_inner);
        json!({ "cmd": "region", "table": a.doc.p.table(table).ok_or("That data table no longer exists.")?, "x0": x0, "x1": x1, "y0": y0, "y1": y1 })
    };
    tauri::async_runtime::spawn_blocking(move || app.state::<Calc>().0.lock().unwrap_or_else(PoisonError::into_inner).ask(&app, &q)).await.map_err(|e| e.to_string())?
}

/// Tools › Slides (.pptx, one graph per slide) or Word Report (.docx: graphs, results, methods) (G5).
#[tauri::command]
async fn export_report(app: AppHandle, st: State<'_, St>, kind: String) -> R<Option<String>> {
    let (name, project) = { let a = st.0.lock().unwrap_or_else(PoisonError::into_inner); (a.doc.p.name.clone(), serde_json::to_value(&a.doc.p).map_err(|e| e.to_string())?) };
    let (label, ext) = if kind == "slides" { ("Slides", "pptx") } else { ("Report", "docx") };
    let Some(path) = app.dialog().file().add_filter(label, &[ext]).set_file_name(format!("{name}.{ext}")).blocking_save_file().and_then(|f| f.into_path().ok()) else { return Ok(None) };
    let q = json!({ "cmd": "report", "kind": kind, "project": project, "path": path.display().to_string() });
    let h = app.clone();
    tauri::async_runtime::spawn_blocking(move || h.state::<Calc>().0.lock().unwrap_or_else(PoisonError::into_inner).ask(&h, &q)).await.map_err(|e| e.to_string())??;
    Ok(Some(path.display().to_string()))
}

#[tauri::command]
fn new_table(st: State<St>, kind: Option<String>) -> R<Value> {
    let mut a = st.0.lock().unwrap_or_else(PoisonError::into_inner);
    let t = match kind.as_deref() { Some("column") => Table::column(3), Some("grouped") => Table::grouped(3, 2), Some("contingency") => Table::contingency(2, 2), Some("parts") => Table::parts(4, 1), Some("multi") => Table::multi(3, 12), Some("survival") => Table::survival(2), Some("nested") => Table::nested(2, 3), Some("sheet") => Table::sheet(3), Some("matrix") => Table::matrix(10, 5), _ => a.opts.table() };
    let g = graph_for(&t.kind, a.opts.graph());
    let (table, graph) = (Box::new(Table { name: String::new(), ..t }), Some(Box::new(g)));
    a.doc.apply(Op::NewTable { table, graph })?;
    a.rev += 1;
    Ok(out(&a))
}

#[tauri::command]
fn history(st: State<St>, redo: bool) -> Value {
    let mut a = st.0.lock().unwrap_or_else(PoisonError::into_inner);
    if redo { a.doc.redo() } else { a.doc.undo() }
    a.rev += 1;
    out(&a)
}

#[tauri::command]
fn templates() -> Vec<templates::Tpl> {
    templates::list()
}

#[tauri::command]
fn new_project(st: State<St>, template: Option<String>) -> R<Value> {
    let mut a = st.0.lock().unwrap_or_else(PoisonError::into_inner);
    let mut p = if template.is_none() {
        let mut p = Project::new("Project1");
        p.add_table(a.opts.table(), Some(a.opts.graph()));
        p
    } else {
        templates::build(template.as_deref()).ok_or("Unknown template.")?
    };
    if template.is_some() {
        let s = a.opts.graph();
        for g in &mut p.graphs {
            let t = g.settings.clone();
            g.settings = GraphSettings { x: t.x, y: t.y, line: t.line, error: t.error, overlays: t.overlays, points: t.points, column: t.column, sets: t.sets, palette: t.palette, legend: t.legend, ..s.clone() };
        }
    }
    a.doc = Doc::new(p);
    a.rev += 1;
    Ok(out(&a))
}

fn pick(app: &AppHandle, name: &str, exts: &[&str]) -> Option<PathBuf> {
    app.dialog().file().add_filter(name, exts).blocking_pick_file().and_then(|f| f.into_path().ok())
}

#[tauri::command]
async fn open(app: AppHandle, st: State<'_, St>, path: Option<String>) -> R<Option<Value>> {
    let Some(path) = path.map(PathBuf::from).or_else(|| pick(&app, "Datum Plot", &["dplot"])) else { return Ok(None) };
    let d = guard(|| Doc::open(&path))?;
    remember(&app, &path);
    let mut a = st.0.lock().unwrap_or_else(PoisonError::into_inner);
    a.doc = d;
    a.rev += 1;
    Ok(Some(out(&a)))
}

#[tauri::command]
async fn save(app: AppHandle, st: State<'_, St>, as_new: bool) -> R<Option<Value>> {
    let (known, name) = {
        let a = st.0.lock().unwrap_or_else(PoisonError::into_inner);
        (a.doc.path.clone().filter(|_| !as_new), a.doc.p.name.clone())
    };
    let path = match known {
        Some(p) => p,
        None => match app.dialog().file().add_filter("Datum Plot", &["dplot"]).set_file_name(format!("{name}.dplot")).blocking_save_file() {
            Some(f) => f.into_path().map_err(|e| e.to_string())?,
            None => return Ok(None),
        },
    };
    let mut a = st.0.lock().unwrap_or_else(PoisonError::into_inner);
    if a.doc.path.is_none() || as_new {
        if let Some(stem) = path.file_stem() {
            a.doc.p.name = stem.to_string_lossy().into_owned();
        }
    }
    a.doc.save(&path)?;
    remember(&app, &path);
    clear_recovery(&app);
    a.rev += 1;
    Ok(Some(out(&a)))
}

#[tauri::command]
async fn save_file(app: AppHandle, name: String, data: String) -> R<Option<String>> {
    let ext = name.rsplit('.').next().unwrap_or("txt").to_string();
    let Some(path) = app.dialog().file().add_filter(ext.to_uppercase(), &[&ext]).set_file_name(&name).blocking_save_file().and_then(|f| f.into_path().ok()) else { return Ok(None) };
    write_atomic(&path, data.as_bytes())?;
    Ok(Some(path.display().to_string()))
}

const B64: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
fn base64(bytes: &[u8]) -> String {
    let mut s = String::with_capacity(bytes.len() * 4 / 3 + 4);
    for ch in bytes.chunks(3) {
        let n = (ch[0] as u32) << 16 | (*ch.get(1).unwrap_or(&0) as u32) << 8 | *ch.get(2).unwrap_or(&0) as u32;
        for k in 0..4 {
            s.push(if k <= ch.len() { B64[(n >> (18 - 6 * k) & 63) as usize] as char } else { '=' });
        }
    }
    s
}

/// Reads a picture for page headers and returns it as a data URL.
#[tauri::command]
async fn pick_logo(app: AppHandle) -> R<Option<String>> {
    let Some(path) = pick(&app, "Pictures", &["png", "jpg", "jpeg", "svg", "gif"]) else { return Ok(None) };
    if std::fs::metadata(&path).map_err(|e| e.to_string())?.len() > 1_500_000 {
        return Err("Choose a picture smaller than 1.5 MB.".into());
    }
    let bytes = std::fs::read(&path).map_err(|e| e.to_string())?;
    let mime = match path.extension().and_then(|e| e.to_str()).unwrap_or("").to_lowercase().as_str() { "svg" => "image/svg+xml", "jpg" | "jpeg" => "image/jpeg", "gif" => "image/gif", _ => "image/png" };
    Ok(Some(format!("data:{mime};base64,{}", base64(&bytes))))
}

// ---------- graphs: drawn by the Python engine ----------

/// The engine's request for a graph: its settings and its table's data.
fn graph_req(st: &State<St>, id: u32, cmd: &str) -> R<Value> {
    let a = st.0.lock().unwrap_or_else(PoisonError::into_inner);
    let g = a.doc.p.graph(id).ok_or("That graph no longer exists.")?;
    let t = a.doc.p.table(g.table).ok_or("The graph's data table no longer exists.")?;
    let overlays: Vec<Value> = g.settings.overlays.iter().filter_map(|o| a.doc.p.analysis(*o)).map(|x| json!({ "kind": x.kind, "sets": x.sets, "options": x.options })).collect();
    Ok(json!({ "cmd": cmd, "table": t, "graph": g.settings, "overlays": overlays }))
}

/// The engine's request for a page layout: the layout and, for each of its graphs, the graph's
/// settings, table and fitted curves.
fn page_req(st: &State<St>, id: u32) -> R<Value> {
    let a = st.0.lock().unwrap_or_else(PoisonError::into_inner);
    let p = &a.doc.p;
    let l = p.layouts.iter().find(|l| l.id == id).ok_or("That layout no longer exists.")?;
    let mut panels = serde_json::Map::new();
    for i in l.items.iter().filter(|i| i.kind == "graph") {
        let Some(g) = p.graph(i.graph) else { continue };
        let Some(t) = p.table(g.table) else { continue };
        let overlays: Vec<Value> = g.settings.overlays.iter().filter_map(|o| p.analysis(*o)).map(|x| json!({ "kind": x.kind, "sets": x.sets, "options": x.options })).collect();
        panels.insert(g.id.to_string(), json!({ "table": t, "graph": g.settings, "overlays": overlays }));
    }
    Ok(json!({ "cmd": "page", "layout": l, "panels": panels, "fmt": "svg" }))
}

/// A page layout drawn by the engine (SVG and its size), cached like graphs.
#[tauri::command]
async fn render_page(app: AppHandle, st: State<'_, St>, id: u32) -> R<Value> {
    let q = page_req(&st, id)?;
    tauri::async_runtime::spawn_blocking(move || app.state::<Engine>().0.lock().unwrap_or_else(PoisonError::into_inner).render(&app, q)).await.map_err(|e| e.to_string())?
}

/// Saves a page layout at its real size: PDF, SVG, EPS, PNG or TIFF (CMYK if asked) (F2, G3).
#[tauri::command]
async fn export_page(app: AppHandle, st: State<'_, St>, id: u32, fmt: String, dpi: u32, cmyk: bool) -> R<Option<String>> {
    if !["png", "svg", "pdf", "tiff", "eps"].contains(&fmt.as_str()) {
        return Err("Unknown picture format.".into());
    }
    let mut q = page_req(&st, id)?;
    let name = st.0.lock().unwrap_or_else(PoisonError::into_inner).doc.p.layouts.iter().find(|l| l.id == id).map(|l| l.name.clone()).unwrap_or_default();
    let Some(path) = app.dialog().file().add_filter(fmt.to_uppercase(), &[&fmt]).set_file_name(format!("{name}.{fmt}")).blocking_save_file().and_then(|f| f.into_path().ok()) else { return Ok(None) };
    q["fmt"] = json!(fmt);
    q["dpi"] = json!(dpi.clamp(72, 2400));
    q["cmyk"] = json!(cmyk && fmt == "tiff");
    q["path"] = json!(path.display().to_string());
    tauri::async_runtime::spawn_blocking(move || app.state::<Engine>().0.lock().unwrap_or_else(PoisonError::into_inner).ask(&app, &q).map(|_| Some(path.display().to_string()))).await.map_err(|e| e.to_string())?
}

#[tauri::command]
async fn render(app: AppHandle, st: State<'_, St>, eng: State<'_, Engine>, id: u32) -> R<Value> {
    let q = graph_req(&st, id, "render")?;
    let _ = &eng;
    tauri::async_runtime::spawn_blocking(move || app.state::<Engine>().0.lock().unwrap_or_else(PoisonError::into_inner).render(&app, q)).await.map_err(|e| e.to_string())?
}

/// An analysis's results, computed by Python (cached while nothing changes).
#[tauri::command]
async fn result(app: AppHandle, st: State<'_, St>, id: u32) -> R<Value> {
    let q = {
        let a = st.0.lock().unwrap_or_else(PoisonError::into_inner);
        let x = a.doc.p.analysis(id).ok_or("That analysis no longer exists.")?;
        let t = a.doc.p.table(x.table).ok_or("The analysis's data table no longer exists.")?;
        json!({ "cmd": "analyze", "kind": x.kind, "table": t, "sets": x.sets, "options": x.options })
    };
    tauri::async_runtime::spawn_blocking(move || app.state::<Calc>().0.lock().unwrap_or_else(PoisonError::into_inner).render(&app, q)).await.map_err(|e| e.to_string())?
}

/// Column formulas (A11): sets data set `k`'s formula to `text` (when given) and works out every formula
/// column of the table in Python. With `merge` the values join the last change (one undo step), as after an edit.
#[tauri::command]
async fn formula(app: AppHandle, st: State<'_, St>, table: u32, k: Option<usize>, text: Option<String>, merge: bool) -> R<Value> {
    let q = {
        let a = st.0.lock().unwrap_or_else(PoisonError::into_inner);
        let t = a.doc.p.table(table).ok_or("That data table no longer exists.")?;
        if k.is_none() && t.sets.iter().all(|s| s.formula.is_empty()) {
            return Ok(out(&a));
        }
        json!({ "cmd": "formula", "table": t, "k": k, "text": text })
    };
    let r = tauri::async_runtime::spawn_blocking({ let app = app.clone(); move || app.state::<Calc>().0.lock().unwrap_or_else(PoisonError::into_inner).render(&app, q) }).await.map_err(|e| e.to_string())??;
    let sets: Vec<(usize, Vec<Option<f64>>)> = serde_json::from_value(r["sets"].clone()).map_err(|e| e.to_string())?;
    let mut a = st.0.lock().unwrap_or_else(PoisonError::into_inner);
    let op = Op::Formula { table, k, formula: text, sets };
    guard(|| if merge { a.doc.merge(op) } else { a.doc.apply(op) })?;
    a.rev += 1;
    Ok(out(&a))
}

/// The curve-fitting model library: [id, name, equation, description].
#[tauri::command]
async fn models(app: AppHandle) -> R<Value> {
    tauri::async_runtime::spawn_blocking(move || app.state::<Calc>().0.lock().unwrap_or_else(PoisonError::into_inner).render(&app, json!({ "cmd": "models" }))).await.map_err(|e| e.to_string())?
}

/// Tools › Export All Graphs: every graph of the project into a chosen folder (G4).
#[tauri::command]
async fn export_all(app: AppHandle, st: State<'_, St>, fmt: String, dpi: u32) -> R<Option<String>> {
    if !["png", "svg", "pdf", "tiff", "eps"].contains(&fmt.as_str()) {
        return Err("Unknown picture format.".into());
    }
    let Some(dir) = app.dialog().file().blocking_pick_folder().and_then(|f| f.into_path().ok()) else { return Ok(None) };
    let ids: Vec<(u32, String)> = st.0.lock().unwrap_or_else(PoisonError::into_inner).doc.p.graphs.iter().map(|g| (g.id, g.name.clone())).collect();
    let mut used = std::collections::HashSet::new();
    let mut qs = vec![];
    for (id, name) in ids {
        let clean: String = name.chars().map(|c| if r#"\/:*?"<>|"#.contains(c) { '_' } else { c }).collect();
        let mut file = format!("{clean}.{fmt}");
        let mut k = 2;
        while !used.insert(file.to_lowercase()) {
            file = format!("{clean} ({k}).{fmt}");
            k += 1;
        }
        let mut q = graph_req(&st, id, "export")?;
        q["fmt"] = json!(fmt);
        q["dpi"] = json!(dpi.clamp(72, 2400));
        q["path"] = json!(dir.join(file).display().to_string());
        qs.push(q);
    }
    let n = qs.len();
    let h = app.clone();
    tauri::async_runtime::spawn_blocking(move || qs.iter().try_for_each(|q| h.state::<Engine>().0.lock().unwrap_or_else(PoisonError::into_inner).ask(&h, q).map(|_| ()))).await.map_err(|e| e.to_string())??;
    Ok(Some(format!("{n} graph{} saved in {}", if n == 1 { "" } else { "s" }, dir.display())))
}

/// Tools › Excel Workbook: the data tables and every result as sheets of one .xlsx (G6).
#[tauri::command]
async fn export_excel(app: AppHandle, st: State<'_, St>) -> R<Option<String>> {
    let (name, q) = {
        let a = st.0.lock().unwrap_or_else(PoisonError::into_inner);
        (a.doc.p.name.clone(), json!({ "cmd": "excel", "project": a.doc.p, "analyses": a.doc.p.analyses }))
    };
    let Some(path) = app.dialog().file().add_filter("Excel workbook", &["xlsx"]).set_file_name(format!("{name}.xlsx")).blocking_save_file().and_then(|f| f.into_path().ok()) else { return Ok(None) };
    let mut q = q;
    q["path"] = json!(path.display().to_string());
    let h = app.clone();
    tauri::async_runtime::spawn_blocking(move || h.state::<Calc>().0.lock().unwrap_or_else(PoisonError::into_inner).ask(&h, &q)).await.map_err(|e| e.to_string())??;
    Ok(Some(path.display().to_string()))
}

/// Saves a graph as a picture or vector file chosen in a Save dialog.
#[tauri::command]
async fn export_graph(app: AppHandle, st: State<'_, St>, id: u32, fmt: String, dpi: u32, transparent: bool, cmyk: Option<bool>) -> R<Option<String>> {
    if !["png", "svg", "pdf", "tiff", "eps"].contains(&fmt.as_str()) {
        return Err("Unknown picture format.".into());
    }
    let mut q = graph_req(&st, id, "export")?;
    let name = st.0.lock().unwrap_or_else(PoisonError::into_inner).doc.p.graph(id).map(|g| g.name.clone()).unwrap_or_default();
    let label = match fmt.as_str() { "png" => "PNG picture", "svg" => "SVG vector", "pdf" => "PDF", "tiff" => "TIFF picture", _ => "EPS vector" };
    let Some(path) = app.dialog().file().add_filter(label, &[&fmt]).set_file_name(format!("{name}.{fmt}")).blocking_save_file().and_then(|f| f.into_path().ok()) else { return Ok(None) };
    q["fmt"] = json!(fmt);
    q["dpi"] = json!(dpi.clamp(72, 2400));
    q["transparent"] = json!(transparent);
    q["cmyk"] = json!(cmyk.unwrap_or(false) && fmt == "tiff");
    q["path"] = json!(path.display().to_string());
    tauri::async_runtime::spawn_blocking(move || app.state::<Engine>().0.lock().unwrap_or_else(PoisonError::into_inner).ask(&app, &q).map(|_| Some(path.display().to_string()))).await.map_err(|e| e.to_string())?
}

/// Puts a PNG of a graph on the Windows clipboard (Word and PowerPoint paste it as a picture).
#[tauri::command]
async fn copy_graph(app: AppHandle, st: State<'_, St>, id: u32, dpi: u32) -> R<()> {
    let mut q = graph_req(&st, id, "export")?;
    q["fmt"] = json!("png");
    q["dpi"] = json!(dpi.clamp(72, 1200));
    let h = app.clone();
    let r = tauri::async_runtime::spawn_blocking(move || h.state::<Engine>().0.lock().unwrap_or_else(PoisonError::into_inner).ask(&h, &q)).await.map_err(|e| e.to_string())??;
    let png = base64_decode(r["data"].as_str().unwrap_or(""))?;
    let img = tauri::image::Image::from_bytes(&png).map_err(|e| format!("Could not read the picture: {e}"))?;
    app.clipboard().write_image(&img).map_err(|e| format!("Could not copy the picture: {e}"))
}

#[tauri::command]
fn copy_text(app: AppHandle, text: String) -> R<()> {
    app.clipboard().write_text(text).map_err(|e| e.to_string())
}

#[tauri::command]
fn read_clipboard(app: AppHandle) -> String {
    app.clipboard().read_text().unwrap_or_default()
}

/// File › Import: a CSV, TXT or Excel file read by Python, for the Import dialog.
#[tauri::command]
async fn import_file(app: AppHandle) -> R<Option<Value>> {
    let Some(path) = pick(&app, "Data files", &["csv", "tsv", "txt", "dat", "prn", "xlsx", "xlsm", "pzfx"]) else { return Ok(None) };
    let q = json!({ "cmd": "read", "path": path.display().to_string() });
    let h = app.clone();
    let mut r = tauri::async_runtime::spawn_blocking(move || h.state::<Engine>().0.lock().unwrap_or_else(PoisonError::into_inner).ask(&h, &q)).await.map_err(|e| e.to_string())??;
    r["name"] = json!(path.file_stem().map(|s| s.to_string_lossy().into_owned()).unwrap_or_default());
    Ok(Some(r))
}

fn base64_decode(s: &str) -> R<Vec<u8>> {
    let val = |c: u8| match c { b'A'..=b'Z' => Some(c - b'A'), b'a'..=b'z' => Some(c - b'a' + 26), b'0'..=b'9' => Some(c - b'0' + 52), b'+' => Some(62), b'/' => Some(63), _ => None };
    let mut out = Vec::with_capacity(s.len() * 3 / 4);
    let (mut acc, mut bits) = (0u32, 0);
    for c in s.bytes().filter(|c| !c.is_ascii_whitespace() && *c != b'=') {
        acc = acc << 6 | val(c).ok_or("The picture data is damaged.")? as u32;
        bits += 6;
        if bits >= 8 {
            bits -= 8;
            out.push((acc >> bits) as u8);
        }
    }
    Ok(out)
}

#[tauri::command]
async fn restart_engine(app: AppHandle) -> R<()> {
    tauri::async_runtime::spawn_blocking(move || {
        app.state::<Calc>().0.lock().unwrap_or_else(PoisonError::into_inner).restart(&app)?;
        app.state::<Engine>().0.lock().unwrap_or_else(PoisonError::into_inner).restart(&app).map(|_| ())
    })
    .await
    .map_err(|e| e.to_string())?
}

/// The engine's versions, or why it could not start.
#[tauri::command]
async fn engine(app: AppHandle) -> Value {
    tauri::async_runtime::spawn_blocking(move || {
        let e = app.state::<Engine>();
        let mut p = e.0.lock().unwrap_or_else(PoisonError::into_inner);
        if p.versions.is_none() {
            let _ = p.ask(&app, &json!({ "cmd": "ping" }));
        }
        json!({ "versions": p.versions, "error": p.error })
    })
    .await
    .unwrap_or_default()
}

// ---------- options, recovery, recent files ----------

fn options_file(app: &AppHandle) -> Option<PathBuf> {
    dir(app, false).map(|d| d.join("options.json"))
}

#[tauri::command]
fn options(st: State<St>) -> Options {
    st.0.lock().unwrap_or_else(PoisonError::into_inner).opts.clone()
}

#[tauri::command]
fn set_options(app: AppHandle, st: State<St>, opts: Options) -> Value {
    if let Some(f) = options_file(&app) {
        let _ = write_atomic(&f, serde_json::to_string(&opts).unwrap_or_default().as_bytes());
    }
    let mut a = st.0.lock().unwrap_or_else(PoisonError::into_inner);
    a.opts = opts;
    out(&a)
}

#[derive(Serialize, Deserialize)]
struct Recovery { name: String, path: Option<String>, saved: String }

fn recovery_files(app: &AppHandle) -> Option<(PathBuf, PathBuf)> {
    dir(app, true).map(|d| (d.join("recovery.dplot"), d.join("recovery.json")))
}

fn clear_recovery(app: &AppHandle) {
    if let Some((a, b)) = recovery_files(app) {
        let _ = std::fs::remove_file(a);
        let _ = std::fs::remove_file(b);
    }
}

#[tauri::command]
fn autosave(app: AppHandle, st: State<St>) {
    let a = st.0.lock().unwrap_or_else(PoisonError::into_inner);
    if let (true, Some((file, meta))) = (a.doc.dirty, recovery_files(&app)) {
        let info = Recovery { name: a.doc.p.name.clone(), path: a.doc.path.as_ref().map(|p| p.display().to_string()), saved: chrono::Local::now().format("%d-%b-%y %H:%M").to_string() };
        let _ = write_atomic(&file, a.doc.json().as_bytes());
        let _ = write_atomic(&meta, serde_json::to_string(&info).unwrap_or_default().as_bytes());
    }
}

#[tauri::command]
fn recovery(app: AppHandle) -> Option<Recovery> {
    let (file, meta) = recovery_files(&app)?;
    file.exists().then_some(())?;
    serde_json::from_str(&read_small(&meta)?).ok()
}

#[tauri::command]
fn recover(app: AppHandle, st: State<St>, keep: bool) -> R<Option<Value>> {
    let info = recovery(app.clone());
    let files = recovery_files(&app);
    if !keep {
        clear_recovery(&app);
        return Ok(None);
    }
    let (file, _) = files.ok_or("No recovered project was found.")?;
    let mut d = guard(|| Doc::open(&file))?;
    d.path = info.and_then(|i| i.path).map(PathBuf::from);
    d.dirty = true;
    let mut a = st.0.lock().unwrap_or_else(PoisonError::into_inner);
    a.doc = d;
    a.rev += 1;
    Ok(Some(out(&a)))
}

#[derive(Serialize)]
struct Recent { path: String, name: String, modified: String }

fn recent_paths(app: &AppHandle) -> Vec<String> {
    options_file(app).map(|f| f.with_file_name("recent.json")).and_then(|f| read_small(&f)).and_then(|t| serde_json::from_str(&t).ok()).unwrap_or_default()
}

fn remember(app: &AppHandle, path: &Path) {
    let p = path.display().to_string();
    let mut v = recent_paths(app);
    v.retain(|x| *x != p);
    v.insert(0, p);
    v.truncate(15);
    if let Some(f) = options_file(app).map(|f| f.with_file_name("recent.json")) {
        let _ = write_atomic(&f, serde_json::to_string(&v).unwrap_or_default().as_bytes());
    }
}

#[tauri::command]
fn recent(app: AppHandle) -> Vec<Recent> {
    recent_paths(&app)
        .into_iter()
        .filter_map(|p| {
            let m = std::fs::metadata(&p).ok()?.modified().ok()?;
            let modified = chrono::DateTime::<chrono::Local>::from(m).format("%d-%b-%y %H:%M").to_string();
            let name = Path::new(&p).file_stem()?.to_string_lossy().into_owned();
            Some(Recent { path: p, name, modified })
        })
        .collect()
}

/// A .dplot path passed on the command line (double-clicked in Explorer), or the last project.
#[tauri::command]
fn startup_file(app: AppHandle, st: State<St>) -> Option<String> {
    let last = || if st.0.lock().unwrap_or_else(PoisonError::into_inner).opts.open_last { recent_paths(&app).into_iter().find(|p| Path::new(p).exists()) } else { None };
    std::env::args().skip(1).find(|a| a.to_lowercase().ends_with(".dplot")).or_else(last)
}

/// Opens one of the project's GitHub pages in the browser (only those).
#[tauri::command]
fn open_url(url: String) -> R<()> {
    let base = "https://github.com/Edgar-Mendonca/Datum-Plot";
    if !(url == base || url.starts_with(&format!("{base}/"))) || url.chars().any(|c| c.is_whitespace() || c.is_control() || "\"'<>^`{|}".contains(c)) {
        return Err("Only the Datum Plot GitHub pages can be opened.".into());
    }
    #[cfg(windows)]
    let r = std::process::Command::new("explorer").arg(&url).spawn();
    #[cfg(not(windows))]
    let r = std::process::Command::new("xdg-open").arg(&url).spawn();
    r.map(|_| ()).map_err(|e| e.to_string())
}

#[tauri::command]
fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

#[tauri::command]
fn quit(app: AppHandle) {
    clear_recovery(&app);
    app.exit(0);
}

#[tauri::command]
async fn check_update(st: State<'_, St>) -> R<update::Info> {
    let beta = st.0.lock().unwrap_or_else(PoisonError::into_inner).opts.beta;
    tauri::async_runtime::spawn_blocking(move || update::check(beta)).await.map_err(|e| e.to_string())?
}

#[tauri::command]
async fn install_update(app: AppHandle, url: String, sums: Option<String>) -> R<()> {
    tauri::async_runtime::spawn_blocking(move || update::install(&app, &url, sums.as_deref())).await.map_err(|e| e.to_string())?
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .setup(|app| {
            // A panic is written to crash.log in the app's data folder before guard() turns it into a message.
            if let Ok(dir) = app.path().app_data_dir() {
                let log = dir.join("crash.log");
                std::panic::set_hook(Box::new(move |info| {
                    let _ = std::fs::create_dir_all(log.parent().unwrap_or(&log));
                    if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(&log) {
                        use std::io::Write;
                        let _ = writeln!(f, "{} Datum Plot {}: {info}", chrono::Local::now().format("%Y-%m-%d %H:%M:%S"), env!("CARGO_PKG_VERSION"));
                    }
                }));
            }
            let opts: Options = options_file(app.handle()).and_then(|f| read_small(&f)).and_then(|t| serde_json::from_str(&t).ok()).unwrap_or_default();
            let mut p = Project::new("Project1");
            p.add_table(opts.table(), Some(opts.graph()));
            app.manage(St(Mutex::new(App { doc: Doc::new(p), opts, rev: 0 })));
            app.manage(Engine(Mutex::new(Py::default())));
            app.manage(Calc(Mutex::new(Py::default())));
            // Start Python now so the first graph appears quickly.
            let h = app.handle().clone();
            std::thread::spawn(move || {
                let e = h.state::<Engine>();
                let mut p = e.0.lock().unwrap_or_else(PoisonError::into_inner);
                let _ = p.ask(&h, &json!({ "cmd": "ping" }));
                let _ = h.emit("engine", json!({ "versions": p.versions, "error": p.error }));
                drop(p);
                // The second engine (results, Excel) starts once the graphs' engine is ready.
                let _ = h.state::<Calc>().0.lock().unwrap_or_else(PoisonError::into_inner).ask(&h, &json!({ "cmd": "ping" }));
            });
            Ok(())
        })
        .on_window_event(|w, e| {
            if let WindowEvent::CloseRequested { api, .. } = e {
                if w.state::<St>().0.lock().unwrap_or_else(PoisonError::into_inner).doc.dirty {
                    api.prevent_close();
                    let _ = w.emit("close-requested", ());
                } else {
                    clear_recovery(w.app_handle());
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            state, apply, new_table, history, new_project, templates, open, save, save_file, pick_logo, render, render_page, export_page, result, models, formula, import_tables, import_files, region, export_report, console, export_notebook, export_all, export_excel, export_graph, copy_graph, copy_text, read_clipboard, import_file, restart_engine, engine,
            options, set_options, autosave, recovery, recover, recent, startup_file, version, open_url, quit, check_update, install_update
        ])
        .run(tauri::generate_context!())
        .expect("Datum Plot failed to start");
}
