//! An open project: edit operations, undo/redo and .dplot files.
use crate::model::*;
use serde::Deserialize;
use std::path::{Path, PathBuf};

const UNDO_LIMIT: usize = 200;

#[derive(Debug, Clone, Deserialize)]
pub enum Op {
    /// Adds a data table (its id is assigned here), with a graph of it when `graph` is given.
    NewTable { table: Box<Table>, graph: Option<Box<GraphSettings>> },
    /// Deletes a table (with its graphs) or a graph.
    Delete { id: u32 },
    Rename { id: u32, name: String },
    /// Copies a table (with its data) or a graph.
    Duplicate { id: u32 },
    /// Typed values: (row, grid column, text); column -1 is the row title. Empty text clears.
    /// Cells that cannot take the text are skipped; it fails only when none could be set.
    Cells { table: u32, cells: Vec<(usize, i64, String)> },
    /// Pasted rows from Excel at a cell. A first row of words becomes the column titles; the
    /// table grows (rows, and data sets like the last one) to fit.
    Paste { table: u32, row: usize, col: i64, rows: Vec<Vec<String>> },
    /// A new table from imported rows (CSV, Excel): column 0 is X, then the Y columns, `reps` (or
    /// 3 for mean/SD/N) per data set. With `header`, the first row holds the titles.
    Import { name: String, entry: Entry, reps: usize, header: bool, rows: Vec<Vec<String>>, graph: Option<Box<GraphSettings>> },
    Exclude { table: u32, cells: Vec<(usize, usize)>, on: bool },
    /// name, xTitle, xUnits, yTitle, yUnits or notes.
    TableSet { table: u32, field: String, value: String },
    /// Adds (k = None), replaces or (set = None) removes a data set.
    SetDef { table: u32, k: Option<usize>, set: Option<DataSet> },
    /// Inserts `count` rows at `at`, or deletes them when `count` is negative.
    Rows { table: u32, at: usize, count: i64 },
    /// Text formatting of cells ("row:col" → style; empty clears).
    Style { table: u32, cells: Vec<(String, String)> },
    AddGraph { table: u32, settings: Option<Box<GraphSettings>> },
    /// Adds an analysis (its id is assigned here); with `overlay`, its fitted curves are drawn on
    /// the table's graphs (whose joining lines are switched off).
    AddAnalysis { analysis: Box<Analysis>, overlay: bool },
    /// Changes an analysis's data sets, options or name.
    SetAnalysis { analysis: Box<Analysis> },
    /// Shows or hides an analysis's curves on a graph.
    Overlay { graph: u32, analysis: u32, on: bool },
    GraphSet { graph: u32, settings: Box<GraphSettings> },
    Info { info: Info },
    ProjectName { name: String },
    /// Stores window settings under a key.
    Ui { key: String, value: serde_json::Value },
    Batch(Vec<Op>),
}

pub struct Doc {
    pub p: Project,
    pub path: Option<PathBuf>,
    pub dirty: bool,
    undo: Vec<Project>,
    redo: Vec<Project>,
}

impl Doc {
    pub fn new(p: Project) -> Self {
        Self { p, path: None, dirty: false, undo: vec![], redo: vec![] }
    }
    pub fn can_undo(&self) -> bool { !self.undo.is_empty() }
    pub fn can_redo(&self) -> bool { !self.redo.is_empty() }

    /// Applies `op` to a copy and keeps it only if it worked and changed something.
    pub fn apply(&mut self, op: Op) -> Result<(), String> {
        let mut q = self.p.clone();
        exec(&mut q, op)?;
        q.normalize();
        if q == self.p {
            return Ok(());
        }
        self.undo.push(std::mem::replace(&mut self.p, q));
        if self.undo.len() > UNDO_LIMIT {
            self.undo.remove(0);
        }
        self.redo.clear();
        self.dirty = true;
        Ok(())
    }
    pub fn undo(&mut self) {
        if let Some(p) = self.undo.pop() {
            self.redo.push(std::mem::replace(&mut self.p, p));
            self.dirty = true;
        }
    }
    pub fn redo(&mut self) {
        if let Some(p) = self.redo.pop() {
            self.undo.push(std::mem::replace(&mut self.p, p));
            self.dirty = true;
        }
    }
    pub fn open(path: &Path) -> Result<Self, String> {
        let text = std::fs::read_to_string(path).map_err(|e| format!("Could not open {}: {e}", path.display()))?;
        let p = Project::from_json(&text).map_err(|e| format!("This is not a Datum Plot file ({e})."))?;
        let mut d = Self::new(p);
        d.path = Some(path.into());
        Ok(d)
    }
    pub fn save(&mut self, path: &Path) -> Result<(), String> {
        std::fs::write(path, self.json()).map_err(|e| format!("Could not save {}: {e}", path.display()))?;
        self.path = Some(path.into());
        self.dirty = false;
        Ok(())
    }
    pub fn json(&self) -> String {
        serde_json::to_string_pretty(&self.p).unwrap_or_default()
    }
}

/// A number as people type or paste it: 1.5, -2, 1e-3, 1,234.5, −4 (Unicode minus), 12%.
pub fn number(s: &str) -> Option<f64> {
    let t = s.trim().replace('\u{2212}', "-");
    let (t, pct) = match t.strip_suffix('%') { Some(x) => (x.trim().to_string(), true), None => (t, false) };
    let grouped = t.contains(',') && !t.contains(' ') && t.trim_start_matches('-').split('.').next().unwrap_or("").split(',').enumerate().all(|(i, g)| (i == 0 && (1..=3).contains(&g.len())) || g.len() == 3);
    let t = if grouped { t.replace(',', "") } else { t };
    let v: f64 = t.parse().ok().filter(|v: &f64| v.is_finite())?;
    Some(if pct { v / 100.0 } else { v })
}

/// Rebuilds a table's columns from `map` (new column → old column) and moves exclusions and
/// formatting with them.
fn remap_cols(t: &mut Table, map: &[Option<usize>]) {
    let old = std::mem::take(&mut t.cols);
    t.cols = map.iter().map(|o| o.and_then(|c| old.get(c).cloned()).unwrap_or_default()).collect();
    let to = |c: usize| map.iter().position(|o| *o == Some(c));
    t.excluded = t.excluded.iter().filter_map(|[r, c]| to(*c).map(|n| [*r, n])).collect();
    t.style = std::mem::take(&mut t.style).into_iter().filter_map(|(k, v)| { let (r, c) = k.split_once(':')?; Some((format!("{r}:{}", to(c.parse().ok()?)?), v)) }).collect();
}

/// Same for rows: `map` gives new row → old row.
fn remap_rows(t: &mut Table, map: &[Option<usize>]) {
    for c in &mut t.cols {
        let old = std::mem::take(c);
        *c = map.iter().map(|o| o.and_then(|r| old.get(r).copied().flatten())).collect();
    }
    let old = std::mem::take(&mut t.row_titles);
    t.row_titles = map.iter().map(|o| o.and_then(|r| old.get(r).cloned()).unwrap_or_default()).collect();
    t.rows = map.len();
    let to = |r: usize| map.iter().position(|o| *o == Some(r));
    t.excluded = t.excluded.iter().filter_map(|[r, c]| to(*r).map(|n| [n, *c])).collect();
    t.style = std::mem::take(&mut t.style).into_iter().filter_map(|(k, v)| { let (r, c) = k.split_once(':')?; Some((format!("{}:{c}", to(r.parse().ok()?)?), v)) }).collect();
}

/// Adds data sets like the last one until the table has `w` grid columns.
fn widen(t: &mut Table, w: usize) {
    while t.width() < w {
        let mut s = t.sets.last().cloned().unwrap_or_default();
        s.title = format!("Data set {}", set_letter(t.sets.len()));
        t.sets.push(s);
    }
    t.normalize();
}

pub fn set_letter(k: usize) -> String {
    if k < 26 { ((b'A' + k as u8) as char).to_string() } else { format!("{}{}", set_letter(k / 26 - 1), set_letter(k % 26)) }
}

/// Puts text into a cell: a number, nothing, or (row titles) any text.
fn put(t: &mut Table, r: usize, c: i64, text: &str) -> bool {
    if r >= t.rows {
        t.rows = r + 1;
        t.normalize();
    }
    if c < 0 {
        t.row_titles[r] = text.trim().into();
        return true;
    }
    let c = c as usize;
    if c >= t.width() {
        widen(t, c + 1);
    }
    let v = if text.trim().is_empty() { None } else { match number(text) { Some(v) => Some(v), None => return false } };
    t.cols[c][r] = v;
    true
}

fn exec(p: &mut Project, op: Op) -> Result<(), String> {
    match op {
        Op::NewTable { mut table, graph } => {
            table.normalize();
            p.add_table(*table, graph.map(|g| *g));
        }
        Op::Delete { id } => {
            let n = p.tables.len() + p.graphs.len() + p.analyses.len();
            p.tables.retain(|t| t.id != id);
            p.graphs.retain(|g| g.id != id && g.table != id);
            p.analyses.retain(|a| a.id != id && a.table != id);
            if n == p.tables.len() + p.graphs.len() + p.analyses.len() {
                return Err("Nothing to delete.".into());
            }
        }
        Op::Rename { id, name } => {
            let name = name.trim().to_string();
            if name.is_empty() {
                return Err("Type a name.".into());
            }
            if let Some(t) = p.tables.iter_mut().find(|t| t.id == id) {
                t.name = name;
            } else if let Some(g) = p.graphs.iter_mut().find(|g| g.id == id) {
                g.name = name;
            } else if let Some(a) = p.analyses.iter_mut().find(|a| a.id == id) {
                a.name = name;
            }
        }
        Op::Duplicate { id } => {
            if let Some(t) = p.table(id).cloned() {
                let name = format!("{} copy", t.name);
                let nid = p.add_table(Table { name, ..t }, None);
                let gs: Vec<Graph> = p.graphs.iter().filter(|g| g.table == id).cloned().collect();
                for g in gs {
                    let gid = p.take_id();
                    p.graphs.push(Graph { id: gid, table: nid, name: format!("{} copy", g.name), ..g });
                }
            } else if let Some(g) = p.graph(id).cloned() {
                let gid = p.take_id();
                p.graphs.push(Graph { id: gid, name: format!("{} copy", g.name), ..g });
            } else if let Some(a) = p.analysis(id).cloned() {
                let aid = p.take_id();
                p.analyses.push(Analysis { id: aid, name: format!("{} copy", a.name), ..a });
            }
        }
        Op::Cells { table, cells } => {
            let t = p.table_mut(table)?;
            let n = cells.len();
            let ok = cells.iter().filter(|(r, c, s)| put(t, *r, *c, s)).count();
            if ok == 0 && n > 0 {
                return Err(if n == 1 { format!("“{}” is not a number. Type a number such as 1.5, -2 or 1e-3.", cells[0].2.trim()) } else { "None of those values are numbers.".into() });
            }
        }
        Op::Paste { table, row, col, mut rows } => {
            let t = p.table_mut(table)?;
            let words = |l: &Vec<String>| l.iter().any(|s| !s.trim().is_empty()) && l.iter().all(|s| s.trim().is_empty() || number(s).is_none());
            if row == 0 && rows.len() > 1 && words(&rows[0]) {
                let head = rows.remove(0);
                for (j, h) in head.iter().enumerate() {
                    let (c, h) = (col + j as i64, h.trim());
                    if c == 0 && !h.is_empty() { t.x_title = h.into(); }
                    if c > 0 && !h.is_empty() {
                        if c as usize >= t.width() { widen(t, c as usize + 1); }
                        if let Some((k, 0)) = t.set_of(c as usize) { t.sets[k].title = h.into(); }
                    }
                }
            }
            for (i, l) in rows.iter().enumerate() {
                for (j, s) in l.iter().enumerate() {
                    put(t, row + i, col + j as i64, s);
                }
            }
        }
        Op::Import { name, entry, reps, header, mut rows, graph } => {
            let head = if header && !rows.is_empty() { rows.remove(0) } else { vec![] };
            let set = DataSet { title: String::new(), entry, reps: reps.clamp(1, 50) };
            let (w, ny) = (set.width(), rows.iter().map(|r| r.len()).max().unwrap_or(1).saturating_sub(1).max(1));
            let n = ny.div_ceil(w);
            let mut t = Table { name, rows: rows.len().max(1), sets: (0..n).map(|k| DataSet { title: format!("Data set {}", set_letter(k)), ..set.clone() }).collect(), ..Default::default() };
            t.normalize();
            if let Some(x) = head.first().map(|h| h.trim()).filter(|h| !h.is_empty()) { t.x_title = x.into(); }
            for k in 0..n {
                if let Some(h) = head.get(1 + k * w).map(|h| h.trim()).filter(|h| !h.is_empty()) { t.sets[k].title = h.into(); }
            }
            for (i, l) in rows.iter().enumerate() {
                for (j, v) in l.iter().enumerate() {
                    put(&mut t, i, j as i64, v);
                }
            }
            p.add_table(t, graph.map(|g| *g));
        }
        Op::Exclude { table, cells, on } => {
            let t = p.table_mut(table)?;
            let (w, n) = (t.width(), t.rows);
            for (r, c) in cells.into_iter().filter(|&(r, c)| c < w && r < n) {
                t.excluded.retain(|x| *x != [r, c]);
                if on {
                    t.excluded.push([r, c]);
                }
            }
        }
        Op::TableSet { table, field, value } => {
            let t = p.table_mut(table)?;
            match field.as_str() {
                "name" => t.name = value,
                "xTitle" => t.x_title = value,
                "xUnits" => t.x_units = value,
                "yTitle" => t.y_title = value,
                "yUnits" => t.y_units = value,
                "notes" => t.notes = value,
                _ => return Err(format!("Unknown table field {field}.")),
            }
        }
        Op::SetDef { table, k, set } => {
            let t = p.table_mut(table)?;
            let spans = t.spans();
            match (k, set) {
                (None, Some(s)) => {
                    let w = t.width();
                    t.sets.push(s);
                    let map: Vec<Option<usize>> = (0..t.width()).map(|c| (c < w).then_some(c)).collect();
                    remap_cols(t, &map);
                }
                (Some(k), s) if k < t.sets.len() => {
                    let (c0, w0) = spans[k];
                    let w1 = s.as_ref().map_or(0, DataSet::width);
                    if t.sets.len() == 1 && s.is_none() {
                        return Err("A table needs at least one data set.".into());
                    }
                    // Columns of this set keep their place up to the new width; later sets move.
                    let mut map: Vec<Option<usize>> = (0..c0).map(Some).collect();
                    map.extend((0..w1).map(|j| (j < w0).then_some(c0 + j)));
                    map.extend((c0 + w0..t.width()).map(Some));
                    match s { Some(s) => t.sets[k] = s, None => { t.sets.remove(k); } }
                    remap_cols(t, &map);
                }
                _ => return Err("That data set no longer exists.".into()),
            }
        }
        Op::Rows { table, at, count } => {
            let t = p.table_mut(table)?;
            let n = t.rows;
            let at = at.min(n);
            let map: Vec<Option<usize>> = if count >= 0 {
                (0..at).map(Some).chain((0..count as usize).map(|_| None)).chain((at..n).map(Some)).collect()
            } else {
                let end = (at + count.unsigned_abs() as usize).min(n);
                (0..at).chain(end..n).map(Some).collect()
            };
            if map.is_empty() {
                return Err("A table needs at least one row.".into());
            }
            remap_rows(t, &map);
        }
        Op::Style { table, cells } => {
            let t = p.table_mut(table)?;
            for (k, v) in cells {
                if v.is_empty() { t.style.remove(&k); } else { t.style.insert(k, v); }
            }
        }
        Op::AddGraph { table, settings } => {
            let name = p.table(table).ok_or("That data table no longer exists.")?.name.clone();
            let n = p.graphs.iter().filter(|g| g.table == table).count();
            let id = p.take_id();
            p.graphs.push(Graph { id, table, name: if n == 0 { name } else { format!("{name} ({})", n + 1) }, settings: settings.map(|s| *s).unwrap_or_default() });
        }
        Op::AddAnalysis { mut analysis, overlay } => {
            if p.table(analysis.table).is_none() {
                return Err("That data table no longer exists.".into());
            }
            analysis.id = p.take_id();
            if analysis.name.trim().is_empty() {
                analysis.name = format!("{} · {}", analysis.kind, p.table(analysis.table).map(|t| t.name.clone()).unwrap_or_default());
            }
            if overlay {
                for g in p.graphs.iter_mut().filter(|g| g.table == analysis.table) {
                    g.settings.overlays.push(analysis.id);
                    g.settings.line = false;
                }
            }
            p.analyses.push(*analysis);
        }
        Op::SetAnalysis { analysis } => {
            let a = p.analyses.iter_mut().find(|a| a.id == analysis.id).ok_or("That analysis no longer exists.")?;
            *a = Analysis { table: a.table, ..*analysis };
        }
        Op::Overlay { graph, analysis, on } => {
            let g = p.graphs.iter_mut().find(|g| g.id == graph).ok_or("That graph no longer exists.")?;
            g.settings.overlays.retain(|o| *o != analysis);
            if on {
                g.settings.overlays.push(analysis);
            }
        }
        Op::GraphSet { graph, settings } => {
            let g = p.graphs.iter_mut().find(|g| g.id == graph).ok_or("That graph no longer exists.")?;
            if !(10.0..=1000.0).contains(&settings.width) || !(10.0..=1000.0).contains(&settings.height) {
                return Err("A graph must be between 10 and 1000 mm wide and high.".into());
            }
            g.settings = *settings;
        }
        Op::Info { info } => p.info = info,
        Op::ProjectName { name } => p.name = name,
        Op::Ui { key, value } => {
            if !p.ui.is_object() {
                p.ui = serde_json::json!({});
            }
            p.ui[key] = value;
        }
        Op::Batch(ops) => {
            for o in ops {
                exec(p, o)?;
                p.normalize();
            }
        }
    }
    Ok(())
}
