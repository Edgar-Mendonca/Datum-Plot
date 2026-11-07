//! Datum Plot graphs embedded in other programs' files (Windows OLE, 0.3.18).
//!
//! **Copy Embedded** puts a "Datum Plot Graph" object on the clipboard: the graph's own small project (data,
//! settings, analyses) and its picture. A document, slide or workbook that pastes it keeps both. Double-clicking it
//! there starts Datum Plot with `-Embedding`; Datum Plot shows the graph, and **Update** (or closing the window)
//! hands the new project and picture back, so the pasted graph changes.
//!
//! Everything here runs on the thread that called `OleInitialize` (the window's main thread): COM calls arrive
//! through its message loop. Other platforms get the same functions as no-ops that say why.

#[cfg(windows)]
mod win;
#[cfg(windows)]
pub use win::*;

/// A graph's picture: RGBA pixels, its size on paper in millimetres, and (for the clipboard) the PNG itself.
#[derive(Clone, Debug, Default)]
pub struct Picture {
    pub rgba: Vec<u8>,
    pub width: u32,
    pub height: u32,
    pub mm: (f64, f64),
    pub png: Vec<u8>,
}

/// What the window does when a document asks for its embedded graph.
pub trait Host {
    /// Show the graph (`data` is the project the document holds) for editing; `container` names the program.
    fn open(&self, data: Vec<u8>, container: String);
    /// The document closed the object (or no longer needs Datum Plot): close quietly.
    fn close(&self);
}

/// True when Windows started Datum Plot for a document (`-Embedding` or `/Embedding`).
pub fn embedding_launch() -> bool {
    std::env::args().skip(1).any(|a| a.eq_ignore_ascii_case("-embedding") || a.eq_ignore_ascii_case("/embedding"))
}

#[cfg(not(windows))]
mod other {
    use super::{Host, Picture};
    const NO: &str = "Embedded graphs need Windows: documents on other systems show the picture only.";
    pub fn init() -> Result<(), String> { Ok(()) }
    pub fn log_to(_path: std::path::PathBuf) {}
    pub fn log(_msg: &str) {}
    pub fn self_test() -> Result<String, String> { Err(NO.into()) }
    pub fn register(_exe: &std::path::Path) -> Result<(), String> { Ok(()) }
    pub fn unregister() {}
    pub fn copy_embedded(_data: &[u8], _pic: &Picture) -> Result<(), String> { Err(NO.into()) }
    pub fn serve(_host: Box<dyn Host>) -> Result<(), String> { Err(NO.into()) }
    pub fn update(_data: Vec<u8>, _pic: Picture) -> Result<(), String> { Err(NO.into()) }
    pub fn closed() {}
}
#[cfg(not(windows))]
pub use other::*;
