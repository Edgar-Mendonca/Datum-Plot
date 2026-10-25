//! Datum Plot desktop shell: owns the open project, files, options and recovery, talks to the
//! window, and passes graphs to the Python engine.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
mod py;
mod runtime;
mod update;

use datum_core::{doc::{Doc, Op}, templates, DataSet, Entry, GraphSettings, Project, Table};
use py::{Calc, Engine, Py};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::{path::{Path, PathBuf}, sync::Mutex};
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
}

impl Default for Options {
    fn default() -> Self {
        Self {
            theme: "auto".into(), autosave: 5, beta: false, open_last: false, decimals: -1, reps: 3, entry: "rep".into(), error: "sd".into(), width: 80.0, height: 60.0,
            font: "Arial".into(), font_size: 10.0, style: "prism".into(), dpi: 300, paper: "A4".into(), landscape: false, company: String::new(), logo: String::new(), styles: json!({}),
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
        Table { sets: vec![DataSet { title: "Data set A".into(), entry, reps: self.reps.clamp(1, 50) }], ..Default::default() }
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
    out(&st.0.lock().unwrap())
}

#[tauri::command]
fn apply(st: State<St>, op: Op) -> R<Value> {
    let mut a = st.0.lock().unwrap();
    // New tables and graphs without settings follow the options.
    let op = match op {
        Op::AddGraph { table, settings: None } => Op::AddGraph { table, settings: Some(Box::new(a.opts.graph())) },
        Op::Import { name, entry, reps, header, rows, graph: None } => Op::Import { name, entry, reps, header, rows, graph: Some(Box::new(a.opts.graph())) },
        o => o,
    };
    a.doc.apply(op)?;
    a.rev += 1;
    Ok(out(&a))
}

/// A new, empty data table (XY from the options, or a column table) with its graph.
#[tauri::command]
fn new_table(st: State<St>, kind: Option<String>) -> R<Value> {
    let mut a = st.0.lock().unwrap();
    let t = if kind.as_deref() == Some("column") { Table::column(3) } else { a.opts.table() };
    let g = if t.kind == "column" { GraphSettings { points: "each".into(), ..a.opts.graph() } } else { a.opts.graph() };
    let (table, graph) = (Box::new(Table { name: String::new(), ..t }), Some(Box::new(g)));
    a.doc.apply(Op::NewTable { table, graph })?;
    a.rev += 1;
    Ok(out(&a))
}

#[tauri::command]
fn history(st: State<St>, redo: bool) -> Value {
    let mut a = st.0.lock().unwrap();
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
    let mut a = st.0.lock().unwrap();
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
            g.settings = GraphSettings { x: t.x, y: t.y, line: t.line, error: t.error, overlays: t.overlays, points: t.points, column: t.column, sets: t.sets, palette: t.palette, ..s.clone() };
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
    let d = Doc::open(&path)?;
    remember(&app, &path);
    let mut a = st.0.lock().unwrap();
    a.doc = d;
    a.rev += 1;
    Ok(Some(out(&a)))
}

#[tauri::command]
async fn save(app: AppHandle, st: State<'_, St>, as_new: bool) -> R<Option<Value>> {
    let (known, name) = {
        let a = st.0.lock().unwrap();
        (a.doc.path.clone().filter(|_| !as_new), a.doc.p.name.clone())
    };
    let path = match known {
        Some(p) => p,
        None => match app.dialog().file().add_filter("Datum Plot", &["dplot"]).set_file_name(format!("{name}.dplot")).blocking_save_file() {
            Some(f) => f.into_path().map_err(|e| e.to_string())?,
            None => return Ok(None),
        },
    };
    let mut a = st.0.lock().unwrap();
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
    std::fs::write(&path, data).map_err(|e| format!("Could not save {}: {e}", path.display()))?;
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
    let bytes = std::fs::read(&path).map_err(|e| e.to_string())?;
    if bytes.len() > 1_500_000 {
        return Err("Choose a picture smaller than 1.5 MB.".into());
    }
    let mime = match path.extension().and_then(|e| e.to_str()).unwrap_or("").to_lowercase().as_str() { "svg" => "image/svg+xml", "jpg" | "jpeg" => "image/jpeg", "gif" => "image/gif", _ => "image/png" };
    Ok(Some(format!("data:{mime};base64,{}", base64(&bytes))))
}

// ---------- graphs: drawn by the Python engine ----------

/// The engine's request for a graph: its settings and its table's data.
fn graph_req(st: &State<St>, id: u32, cmd: &str) -> R<Value> {
    let a = st.0.lock().unwrap();
    let g = a.doc.p.graph(id).ok_or("That graph no longer exists.")?;
    let t = a.doc.p.table(g.table).ok_or("The graph's data table no longer exists.")?;
    let overlays: Vec<Value> = g.settings.overlays.iter().filter_map(|o| a.doc.p.analysis(*o)).map(|x| json!({ "kind": x.kind, "sets": x.sets, "options": x.options })).collect();
    Ok(json!({ "cmd": cmd, "table": t, "graph": g.settings, "overlays": overlays }))
}

#[tauri::command]
async fn render(app: AppHandle, st: State<'_, St>, eng: State<'_, Engine>, id: u32) -> R<Value> {
    let q = graph_req(&st, id, "render")?;
    let _ = &eng;
    tauri::async_runtime::spawn_blocking(move || app.state::<Engine>().0.lock().unwrap().render(&app, q)).await.map_err(|e| e.to_string())?
}

/// An analysis's results, computed by Python (cached while nothing changes).
#[tauri::command]
async fn result(app: AppHandle, st: State<'_, St>, id: u32) -> R<Value> {
    let q = {
        let a = st.0.lock().unwrap();
        let x = a.doc.p.analysis(id).ok_or("That analysis no longer exists.")?;
        let t = a.doc.p.table(x.table).ok_or("The analysis's data table no longer exists.")?;
        json!({ "cmd": "analyze", "kind": x.kind, "table": t, "sets": x.sets, "options": x.options })
    };
    tauri::async_runtime::spawn_blocking(move || app.state::<Calc>().0.lock().unwrap().render(&app, q)).await.map_err(|e| e.to_string())?
}

/// The curve-fitting model library: [id, name, equation, description].
#[tauri::command]
async fn models(app: AppHandle) -> R<Value> {
    tauri::async_runtime::spawn_blocking(move || app.state::<Calc>().0.lock().unwrap().render(&app, json!({ "cmd": "models" }))).await.map_err(|e| e.to_string())?
}

/// Tools › Export All Graphs: every graph of the project into a chosen folder (G4).
#[tauri::command]
async fn export_all(app: AppHandle, st: State<'_, St>, fmt: String, dpi: u32) -> R<Option<String>> {
    if !["png", "svg", "pdf", "tiff", "eps"].contains(&fmt.as_str()) {
        return Err("Unknown picture format.".into());
    }
    let Some(dir) = app.dialog().file().blocking_pick_folder().and_then(|f| f.into_path().ok()) else { return Ok(None) };
    let ids: Vec<(u32, String)> = st.0.lock().unwrap().doc.p.graphs.iter().map(|g| (g.id, g.name.clone())).collect();
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
    tauri::async_runtime::spawn_blocking(move || qs.iter().try_for_each(|q| h.state::<Engine>().0.lock().unwrap().ask(&h, q).map(|_| ()))).await.map_err(|e| e.to_string())??;
    Ok(Some(format!("{n} graph{} saved in {}", if n == 1 { "" } else { "s" }, dir.display())))
}

/// Tools › Excel Workbook: the data tables and every result as sheets of one .xlsx (G6).
#[tauri::command]
async fn export_excel(app: AppHandle, st: State<'_, St>) -> R<Option<String>> {
    let (name, q) = {
        let a = st.0.lock().unwrap();
        (a.doc.p.name.clone(), json!({ "cmd": "excel", "project": a.doc.p, "analyses": a.doc.p.analyses }))
    };
    let Some(path) = app.dialog().file().add_filter("Excel workbook", &["xlsx"]).set_file_name(format!("{name}.xlsx")).blocking_save_file().and_then(|f| f.into_path().ok()) else { return Ok(None) };
    let mut q = q;
    q["path"] = json!(path.display().to_string());
    let h = app.clone();
    tauri::async_runtime::spawn_blocking(move || h.state::<Calc>().0.lock().unwrap().ask(&h, &q)).await.map_err(|e| e.to_string())??;
    Ok(Some(path.display().to_string()))
}

/// Saves a graph as a picture or vector file chosen in a Save dialog.
#[tauri::command]
async fn export_graph(app: AppHandle, st: State<'_, St>, id: u32, fmt: String, dpi: u32, transparent: bool) -> R<Option<String>> {
    if !["png", "svg", "pdf", "tiff", "eps"].contains(&fmt.as_str()) {
        return Err("Unknown picture format.".into());
    }
    let mut q = graph_req(&st, id, "export")?;
    let name = st.0.lock().unwrap().doc.p.graph(id).map(|g| g.name.clone()).unwrap_or_default();
    let label = match fmt.as_str() { "png" => "PNG picture", "svg" => "SVG vector", "pdf" => "PDF", "tiff" => "TIFF picture", _ => "EPS vector" };
    let Some(path) = app.dialog().file().add_filter(label, &[&fmt]).set_file_name(format!("{name}.{fmt}")).blocking_save_file().and_then(|f| f.into_path().ok()) else { return Ok(None) };
    q["fmt"] = json!(fmt);
    q["dpi"] = json!(dpi.clamp(72, 2400));
    q["transparent"] = json!(transparent);
    q["path"] = json!(path.display().to_string());
    tauri::async_runtime::spawn_blocking(move || app.state::<Engine>().0.lock().unwrap().ask(&app, &q).map(|_| Some(path.display().to_string()))).await.map_err(|e| e.to_string())?
}

/// Puts a PNG of a graph on the Windows clipboard (Word and PowerPoint paste it as a picture).
#[tauri::command]
async fn copy_graph(app: AppHandle, st: State<'_, St>, id: u32, dpi: u32) -> R<()> {
    let mut q = graph_req(&st, id, "export")?;
    q["fmt"] = json!("png");
    q["dpi"] = json!(dpi.clamp(72, 1200));
    let h = app.clone();
    let r = tauri::async_runtime::spawn_blocking(move || h.state::<Engine>().0.lock().unwrap().ask(&h, &q)).await.map_err(|e| e.to_string())??;
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
    let Some(path) = pick(&app, "Data files", &["csv", "tsv", "txt", "dat", "prn", "xlsx", "xlsm"]) else { return Ok(None) };
    let q = json!({ "cmd": "read", "path": path.display().to_string() });
    let h = app.clone();
    let mut r = tauri::async_runtime::spawn_blocking(move || h.state::<Engine>().0.lock().unwrap().ask(&h, &q)).await.map_err(|e| e.to_string())??;
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
        app.state::<Calc>().0.lock().unwrap().restart(&app)?;
        app.state::<Engine>().0.lock().unwrap().restart(&app).map(|_| ())
    })
    .await
    .map_err(|e| e.to_string())?
}

/// The engine's versions, or why it could not start.
#[tauri::command]
async fn engine(app: AppHandle) -> Value {
    tauri::async_runtime::spawn_blocking(move || {
        let e = app.state::<Engine>();
        let mut p = e.0.lock().unwrap();
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
    st.0.lock().unwrap().opts.clone()
}

#[tauri::command]
fn set_options(app: AppHandle, st: State<St>, opts: Options) -> Value {
    if let Some(f) = options_file(&app) {
        let _ = std::fs::write(f, serde_json::to_string(&opts).unwrap_or_default());
    }
    let mut a = st.0.lock().unwrap();
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
    let a = st.0.lock().unwrap();
    if let (true, Some((file, meta))) = (a.doc.dirty, recovery_files(&app)) {
        let info = Recovery { name: a.doc.p.name.clone(), path: a.doc.path.as_ref().map(|p| p.display().to_string()), saved: chrono::Local::now().format("%d-%b-%y %H:%M").to_string() };
        let _ = std::fs::write(file, a.doc.json());
        let _ = std::fs::write(meta, serde_json::to_string(&info).unwrap_or_default());
    }
}

#[tauri::command]
fn recovery(app: AppHandle) -> Option<Recovery> {
    let (file, meta) = recovery_files(&app)?;
    file.exists().then_some(())?;
    serde_json::from_str(&std::fs::read_to_string(meta).ok()?).ok()
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
    let mut d = Doc::open(&file)?;
    d.path = info.and_then(|i| i.path).map(PathBuf::from);
    d.dirty = true;
    let mut a = st.0.lock().unwrap();
    a.doc = d;
    a.rev += 1;
    Ok(Some(out(&a)))
}

#[derive(Serialize)]
struct Recent { path: String, name: String, modified: String }

fn recent_paths(app: &AppHandle) -> Vec<String> {
    options_file(app).map(|f| f.with_file_name("recent.json")).and_then(|f| std::fs::read_to_string(f).ok()).and_then(|t| serde_json::from_str(&t).ok()).unwrap_or_default()
}

fn remember(app: &AppHandle, path: &Path) {
    let p = path.display().to_string();
    let mut v = recent_paths(app);
    v.retain(|x| *x != p);
    v.insert(0, p);
    v.truncate(15);
    if let Some(f) = options_file(app).map(|f| f.with_file_name("recent.json")) {
        let _ = std::fs::write(f, serde_json::to_string(&v).unwrap());
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
    let last = || if st.0.lock().unwrap().opts.open_last { recent_paths(&app).into_iter().find(|p| Path::new(p).exists()) } else { None };
    std::env::args().skip(1).find(|a| a.to_lowercase().ends_with(".dplot")).or_else(last)
}

/// Opens one of the project's GitHub pages in the browser (only those).
#[tauri::command]
fn open_url(url: String) -> R<()> {
    if !url.starts_with("https://github.com/Edgar-Mendonca/Datum-Plot") {
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
    let beta = st.0.lock().unwrap().opts.beta;
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
            let opts: Options = options_file(app.handle()).and_then(|f| std::fs::read_to_string(f).ok()).and_then(|t| serde_json::from_str(&t).ok()).unwrap_or_default();
            let mut p = Project::new("Project1");
            p.add_table(opts.table(), Some(opts.graph()));
            app.manage(St(Mutex::new(App { doc: Doc::new(p), opts, rev: 0 })));
            app.manage(Engine(Mutex::new(Py::default())));
            app.manage(Calc(Mutex::new(Py::default())));
            // Start Python now so the first graph appears quickly.
            let h = app.handle().clone();
            std::thread::spawn(move || {
                let e = h.state::<Engine>();
                let mut p = e.0.lock().unwrap();
                let _ = p.ask(&h, &json!({ "cmd": "ping" }));
                let _ = h.emit("engine", json!({ "versions": p.versions, "error": p.error }));
                drop(p);
                // The second engine (results, Excel) starts once the graphs' engine is ready.
                let _ = h.state::<Calc>().0.lock().unwrap().ask(&h, &json!({ "cmd": "ping" }));
            });
            Ok(())
        })
        .on_window_event(|w, e| {
            if let WindowEvent::CloseRequested { api, .. } = e {
                if w.state::<St>().0.lock().unwrap().doc.dirty {
                    api.prevent_close();
                    let _ = w.emit("close-requested", ());
                } else {
                    clear_recovery(w.app_handle());
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            state, apply, new_table, history, new_project, templates, open, save, save_file, pick_logo, render, result, models, export_all, export_excel, export_graph, copy_graph, copy_text, read_clipboard, import_file, restart_engine, engine,
            options, set_options, autosave, recovery, recover, recent, startup_file, version, open_url, quit, check_update, install_update
        ])
        .run(tauri::generate_context!())
        .expect("Datum Plot failed to start");
}
