//! Graphs embedded in documents, slides and workbooks (0.3.18, with `datum-ole`): **Copy Embedded**, and the
//! window Windows opens when such a graph is double-clicked there (**Update Document** hands the new graph back).
use crate::{base64_decode, graph_req, out, Engine, St, R};
use serde_json::json;
use std::sync::{mpsc, PoisonError};
use tauri::{AppHandle, Emitter, Manager, State};

/// Runs `f` on the window's thread (where OLE lives) and waits for its answer.
fn on_main<T: Send + 'static>(app: &AppHandle, f: impl FnOnce() -> R<T> + Send + 'static) -> R<T> {
    let (tx, rx) = mpsc::channel();
    app.run_on_main_thread(move || {
        let _ = tx.send(f());
    })
    .map_err(|e| e.to_string())?;
    rx.recv().map_err(|e| e.to_string())?
}

/// The graph's picture for a document (PNG at 300 dpi, decoded), at its size in millimetres.
fn picture(app: &AppHandle, st: &State<St>, id: u32) -> R<datum_ole::Picture> {
    let mut q = graph_req(st, id, "export")?;
    q["fmt"] = json!("png");
    q["dpi"] = json!(300);
    let mm = {
        let a = st.0.lock().unwrap_or_else(PoisonError::into_inner);
        let g = a.doc.p.graph(id).ok_or("That graph no longer exists.")?;
        (g.settings.width, g.settings.height)
    };
    let r = app.state::<Engine>().0.lock().unwrap_or_else(PoisonError::into_inner).ask(app, &q)?;
    let png = base64_decode(r["data"].as_str().unwrap_or(""))?;
    let img = tauri::image::Image::from_bytes(&png).map_err(|e| format!("Could not read the picture: {e}"))?;
    Ok(datum_ole::Picture { rgba: img.rgba().to_vec(), width: img.width(), height: img.height(), mm, png })
}

/// Graph › Copy Embedded: a graph a document can open again in Datum Plot.
#[tauri::command]
pub async fn copy_embedded(app: AppHandle, st: State<'_, St>, id: u32) -> R<()> {
    let data = {
        let a = st.0.lock().unwrap_or_else(PoisonError::into_inner);
        let p = a.doc.p.graph_only(id).ok_or("That graph no longer exists.")?;
        serde_json::to_vec(&p).map_err(|e| e.to_string())?
    };
    let pic = picture(&app, &st, id)?;
    on_main(&app, move || datum_ole::copy_embedded(&data, &pic))
}

/// **Update Document**: the document receives the project and the picture of its (first) graph.
#[tauri::command]
pub async fn ole_update(app: AppHandle, st: State<'_, St>) -> R<()> {
    let (data, id) = {
        let a = st.0.lock().unwrap_or_else(PoisonError::into_inner);
        if a.embedded.is_none() {
            return Err("This window is not editing an embedded graph.".into());
        }
        let id = a.doc.p.graphs.first().map(|g| g.id).ok_or("Keep at least one graph: the document shows the first one.")?;
        (serde_json::to_vec(&a.doc.p).map_err(|e| e.to_string())?, id)
    };
    let pic = picture(&app, &st, id)?;
    on_main(&app, move || datum_ole::update(data, pic))?;
    let mut a = st.0.lock().unwrap_or_else(PoisonError::into_inner);
    a.doc.dirty = false;
    a.rev += 1;
    Ok(())
}

/// The editing window closes: the document lets the object go, and this Datum Plot ends.
#[tauri::command]
pub fn ole_close(app: AppHandle) {
    let _ = on_main(&app, || {
        datum_ole::closed();
        Ok(())
    });
    app.exit(0);
}

/// What a document asks of this Datum Plot (started with `-Embedding`).
struct Host(AppHandle);

impl datum_ole::Host for Host {
    fn open(&self, data: Vec<u8>, container: String) {
        let st = self.0.state::<St>();
        let mut a = st.0.lock().unwrap_or_else(PoisonError::into_inner);
        match std::str::from_utf8(&data).map_err(|e| e.to_string()).and_then(datum_core::Project::from_json) {
            Ok(p) => {
                a.doc = datum_core::doc::Doc::new(p);
                a.embedded = Some(if container.trim().is_empty() { "the document".into() } else { container });
                a.rev += 1;
                let _ = self.0.emit("ole-open", out(&a));
            }
            Err(e) => {
                let _ = self.0.emit("ole-error", format!("The embedded graph could not be read: {e}"));
            }
        }
        drop(a);
        if let Some(w) = self.0.get_webview_window("main") {
            let _ = w.show();
            let _ = w.unminimize();
            let _ = w.set_focus();
        }
    }
    fn close(&self) {
        self.0.exit(0);
    }
}

/// At start: OLE on the window's thread, "Datum Plot Graph" registered for this user, and when a document
/// started us, the object offered to it (the window stays hidden until the document asks to show the graph).
pub fn start(app: &tauri::App) {
    if let Err(e) = datum_ole::init() {
        eprintln!("OLE: {e}");
    }
    if let Ok(exe) = std::env::current_exe() {
        let _ = datum_ole::register(&exe);
    }
    if datum_ole::embedding_launch() {
        if let Some(w) = app.get_webview_window("main") {
            let _ = w.hide();
        }
        if let Err(e) = datum_ole::serve(Box::new(Host(app.handle().clone()))) {
            eprintln!("OLE: {e}");
        }
    }
}
