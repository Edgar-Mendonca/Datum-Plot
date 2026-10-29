//! Datum Plot core: projects, data tables, graph settings, edits and files. No UI or OS code
//! lives here; statistics and drawing are done by the Python engine (`py/`).
pub mod doc;
pub mod model;
pub mod templates;

pub use model::*;

#[cfg(test)]
mod hardening;
#[cfg(test)]
mod tests;
