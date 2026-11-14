//! An open project: edit operations, undo/redo and .dplot files.
use crate::model::*;
use serde::Deserialize;
use std::path::{Path, PathBuf};

const UNDO_LIMIT: usize = 200;
/// Cells kept across all undo steps (about 1 GB of values at most).
const UNDO_CELLS: usize = 60_000_000;

#[derive(Debug, Clone, Deserialize)]
pub enum Op {
    /// Adds a data table (its id is assigned here), with a graph of it when `graph` is given.
    NewTable { table: Box<Table>, graph: Option<Box<GraphSettings>> },
    /// Deletes a table (with its graphs) or a graph.
    Delete { id: u32 },
    Rename { id: u32, name: String },
    /// The X column as numbers or dates (0.3.11): `format` "", "date" or "datetime"; `display` how dates are shown.
    XFormat { table: u32, format: String, display: String },
    /// Copies a table (with its data) or a graph.
    /// A copy of a table (with its graphs and results, or alone with `only`), graph, result or layout.
    Duplicate { id: u32, #[serde(default)] only: bool },
    /// Typed values: (row, grid column, text); column -1 is the row title. Empty text clears.
    /// Cells that cannot take the text are skipped; it fails only when none could be set.
    Cells { table: u32, cells: Vec<(usize, i64, String)> },
    /// Pasted rows (from a spreadsheet or elsewhere) at a cell. A first row of words becomes the column titles; the
    /// table grows (rows, and data sets like the last one) to fit.
    Paste { table: u32, row: usize, col: i64, rows: Vec<Vec<String>> },
    /// A new table from imported rows (CSV, .xlsx): column 0 is X, then the Y columns, `reps` (or
    /// 3 for mean/SD/N) per data set. With `header`, the first row holds the titles. `dates` ("date", "datetime")
    /// reads the X column as dates (0.3.12: the Import dialog offers it when the X column looks like dates).
    Import { name: String, entry: Entry, reps: usize, header: bool, rows: Vec<Vec<String>>, graph: Option<Box<GraphSettings>>, #[serde(default)] dates: String },
    /// 0.4.1 (E8): points clicked on a picture of a graph become an XY table (values worked out in `digitize`).
    Digitize { name: String, calib: crate::digitize::Calib, sets: Vec<crate::digitize::Traced>, graph: Option<Box<GraphSettings>> },
    Exclude { table: u32, cells: Vec<(usize, usize)>, on: bool },
    /// name, xTitle, xUnits, yTitle, yUnits or notes.
    TableSet { table: u32, field: String, value: String },
    /// Adds (k = None), replaces or (set = None) removes a data set.
    SetDef { table: u32, k: Option<usize>, set: Option<DataSet> },
    /// Sorts the rows by a grid column (empty cells last); row titles, exclusions and formats move with them.
    Sort { table: u32, col: usize, desc: bool },
    /// Gives graphs `to` the look of graph `from` (style, sizes, fonts, colours, error bars),
    /// keeping their own titles, axis titles and ranges and fitted curves.
    CopyLook { from: u32, to: Vec<u32> },
    /// Inserts `count` rows at `at`, or deletes them when `count` is negative.
    Rows { table: u32, at: usize, count: i64 },
    /// Text formatting of cells ("row:col" → style; empty clears).
    Style { table: u32, cells: Vec<(String, String)> },
    AddGraph { table: u32, settings: Option<Box<GraphSettings>> },
    /// Adds an analysis (its id is assigned here); with `overlay`, its fitted curves are drawn on
    /// the table's graphs (whose joining lines are switched off).
    /// A new analysis; with `overlay` it is drawn on `graph` (0.3.15: only that graph), or on every graph of its table.
    AddAnalysis { analysis: Box<Analysis>, overlay: bool, #[serde(default)] graph: Option<u32> },
    /// Changes an analysis's data sets, options or name.
    SetAnalysis { analysis: Box<Analysis> },
    /// Shows or hides an analysis's curves on a graph.
    Overlay { graph: u32, analysis: u32, on: bool },
    GraphSet { graph: u32, settings: Box<GraphSettings> },
    /// Adds a page layout (its id is assigned here; an empty name becomes "Layout n").
    AddLayout { layout: Box<Layout> },
    /// Replaces a layout's page, items and letters (its id stays).
    LayoutSet { layout: Box<Layout> },
    Info { info: Info },
    ProjectName { name: String },
    /// Stores window settings under a key.
    Ui { key: String, value: serde_json::Value },
    /// A data set's formula and the values it gave (`sets`: [(data set, values by row)]); `formula`
    /// sets the formula of `k` first (empty clears it).
    Formula { table: u32, k: Option<usize>, formula: Option<String>, sets: Vec<(usize, Vec<Option<f64>>)> },
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
        // Each undo step is a whole copy: big projects keep fewer (at least 10), so memory stays bounded.
        let keep = (UNDO_CELLS / self.p.cells().max(1)).clamp(10, UNDO_LIMIT);
        if self.undo.len() > keep {
            self.undo.drain(..self.undo.len() - keep);
        }
        self.redo.clear();
        self.dirty = true;
        Ok(())
    }
    /// Applies `op` as part of the last change (one undo step): formulas recalculated after an edit.
    pub fn merge(&mut self, op: Op) -> Result<(), String> {
        let mut q = self.p.clone();
        exec(&mut q, op)?;
        q.normalize();
        if q != self.p {
            self.p = q;
            self.dirty = true;
        }
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
        // A project is text; more than 1 GB is not one of ours (and would not fit in memory twice).
        if std::fs::metadata(path).map_err(|e| format!("Could not open {}: {e}", path.display()))?.len() > 1 << 30 {
            return Err(format!("{} is larger than 1 GB, too large to be a Datum Plot project.", path.display()));
        }
        let text = std::fs::read_to_string(path).map_err(|e| format!("Could not open {}: {e}", path.display()))?;
        let p = Project::from_json(&text).map_err(|e| format!("This is not a Datum Plot file ({e})."))?;
        let mut d = Self::new(p);
        d.path = Some(path.into());
        Ok(d)
    }
    pub fn save(&mut self, path: &Path) -> Result<(), String> {
        write_atomic(path, self.json().as_bytes())?;
        self.path = Some(path.into());
        self.dirty = false;
        Ok(())
    }
    pub fn json(&self) -> String {
        serde_json::to_string_pretty(&self.p).unwrap_or_default()
    }
}

/// Writes a file so that a crash or a full disk never leaves it half written: a temporary file next to
/// it, flushed to disk, then renamed over it.
pub fn write_atomic(path: &Path, data: &[u8]) -> Result<(), String> {
    use std::io::Write;
    let fail = |e: std::io::Error| format!("Could not save {}: {e}", path.display());
    let name = path.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
    let tmp = path.with_file_name(format!(".{name}.{}.tmp", std::process::id()));
    let r = (|| {
        let mut f = std::fs::File::create(&tmp)?;
        f.write_all(data)?;
        f.sync_all()?;
        drop(f);
        std::fs::rename(&tmp, path)
    })();
    if r.is_err() {
        let _ = std::fs::remove_file(&tmp);
    }
    r.map_err(fail)
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

/// Dates are written day first (05/11/2026 = 5 November) unless the options say month first; the shell sets it.
pub static DAY_FIRST: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(true);

/// Days from 1970-01-01 to a civil date (H. Hinnant's algorithm), or None for an impossible date (31 Feb).
pub fn days_from_civil(y: i64, m: u32, d: u32) -> Option<f64> {
    let leap = (y % 4 == 0 && y % 100 != 0) || y % 400 == 0;
    let dim = [31, if leap { 29 } else { 28 }, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    if !(1..=12).contains(&m) || d == 0 || d > dim[m as usize - 1] || !(1..=9999).contains(&y) {
        return None;
    }
    let y = if m <= 2 { y - 1 } else { y };
    let era = y.div_euclid(400);
    let yoe = y - era * 400;
    let mp = (m as i64 + 9) % 12;
    let doy = (153 * mp + 2) / 5 + d as i64 - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    Some((era * 146097 + doe - 719468) as f64)
}

/// A typed or pasted date (and time) as days since 1970-01-01, the time of day as the fraction:
/// ISO (2026-11-05, 2026-11-05 14:30, 2026-11-05T14:30:00), 05/11/2026 (day first or month first),
/// month names (5-Nov-26, 5 Nov 2026, Nov 5, 2026, 5 November 2026), or a time alone (14:30) as a fraction of a day.
pub fn date_number(s: &str, day_first: bool) -> Option<f64> {
    let s = s.trim().trim_end_matches('Z');
    if s.is_empty() {
        return None;
    }
    // "2:30 pm": take the am/pm off first, so the time is the last part.
    let low = s.to_lowercase();
    let (s, pm) = match () {
        _ if low.ends_with("pm") && s[..s.len() - 2].contains(':') => (s[..s.len() - 2].trim_end(), Some(true)),
        _ if low.ends_with("am") && s[..s.len() - 2].contains(':') => (s[..s.len() - 2].trim_end(), Some(false)),
        _ => (s, None),
    };
    // Split off a time: the last part with a colon.
    let (date, time) = match s.rfind([' ', 'T']) {
        Some(i) if s[i + 1..].contains(':') => (s[..i].trim().trim_end_matches(','), Some(&s[i + 1..])),
        _ if s.contains(':') && !s.contains(['-', '/', '.']) && !s.chars().any(|c| c.is_alphabetic()) => ("", Some(s)),
        _ => (s, None),
    };
    let frac = match time {
        Some(t) => {
            let p: Vec<f64> = t.trim().split(':').map(|x| x.parse::<f64>()).collect::<Result<_, _>>().ok()?;
            let (mut h, mi, se) = (p[0], *p.get(1).unwrap_or(&0.0), *p.get(2).unwrap_or(&0.0));
            if p.len() > 3 || !(0.0..60.0).contains(&mi) || !(0.0..61.0).contains(&se) || !(0.0..24.0).contains(&h) {
                return None;
            }
            if let Some(pm) = pm {
                if !(1.0..=12.0).contains(&h) {
                    return None;
                }
                h = h % 12.0 + if pm { 12.0 } else { 0.0 };
            }
            (h * 3600.0 + mi * 60.0 + se) / 86400.0
        }
        None => 0.0,
    };
    if date.is_empty() {
        return time.map(|_| frac);
    }
    const MONTHS: [&str; 12] = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];
    let parts: Vec<&str> = date.split(['-', '/', '.', ' ', ',']).filter(|p| !p.is_empty()).collect();
    if parts.len() != 3 {
        return None;
    }
    let year = |p: &str| -> Option<i64> { let y: i64 = p.parse().ok()?; Some(if p.len() <= 2 { if y < 70 { 2000 + y } else { 1900 + y } } else { y }) };
    let month = |p: &str| -> Option<u32> { let l = p.to_lowercase(); MONTHS.iter().position(|m| l.len() >= 3 && l.starts_with(m) && m.starts_with(&l[..3])).map(|i| i as u32 + 1) };
    let num = |p: &str| -> Option<u32> { p.parse().ok() };
    let (y, m, d) = if parts[0].len() == 4 && parts[0].chars().all(|c| c.is_ascii_digit()) {
        (year(parts[0])?, num(parts[1]).or_else(|| month(parts[1]))?, num(parts[2])?)
    } else if let Some(m) = month(parts[1]) {
        (year(parts[2])?, m, num(parts[0])?) // 5-Nov-26, 5 Nov 2026
    } else if let Some(m) = month(parts[0]) {
        (year(parts[2])?, m, num(parts[1])?) // Nov 5, 2026
    } else {
        let (a, b) = (num(parts[0])?, num(parts[1])?);
        let (d, m) = if day_first { (a, b) } else { (b, a) };
        (year(parts[2])?, m, d)
    };
    Some(days_from_civil(y, m, d)? + frac)
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
#[cfg(test)]
pub(crate) fn put_for_test(t: &mut Table, r: usize, c: i64, text: &str) -> bool {
    put(t, r, c, text)
}

fn put(t: &mut Table, r: usize, c: i64, text: &str) -> bool {
    if r >= MAX_ROWS || c > MAX_SETS as i64 {
        return false; // beyond what a table can hold
    }
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
    // A date column (0.3.11) reads dates first; a plain number there is a day count.
    if t.cols.get(c).is_none_or(|col| col.len() <= r) {
        t.normalize(); // never index past the columns, whatever made the table
    }
    let date = c == 0 && !t.x_format.is_empty();
    let parsed = if date { date_number(text, DAY_FIRST.load(std::sync::atomic::Ordering::Relaxed)).or_else(|| number(text)) } else { number(text) };
    let v = if text.trim().is_empty() { None } else { match parsed { Some(v) => Some(v), None => return false } };
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
            let n = p.tables.len() + p.graphs.len() + p.analyses.len() + p.layouts.len();
            p.tables.retain(|t| t.id != id);
            p.graphs.retain(|g| g.id != id && g.table != id);
            p.analyses.retain(|a| a.id != id && a.table != id);
            p.layouts.retain(|l| l.id != id);
            if n == p.tables.len() + p.graphs.len() + p.analyses.len() + p.layouts.len() {
                return Err("Nothing to delete.".into());
            }
        }
        Op::XFormat { table, format, display } => {
            let t = p.table_mut(table)?;
            (t.x_format, t.x_display) = (format, display);
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
            } else if let Some(l) = p.layouts.iter_mut().find(|l| l.id == id) {
                l.name = name;
            }
        }
        Op::Duplicate { id, only } => {
            if let Some(t) = p.table(id).cloned() {
                let name = format!("{} copy", t.name);
                let nid = p.add_table(Table { name, ..t }, None);
                if !only {
                    // 0.3.15: the family comes along: graphs and results, the copied graphs drawing the copied results.
                    let mut map = std::collections::HashMap::new();
                    for a in p.analyses.iter().filter(|a| a.table == id).cloned().collect::<Vec<_>>() {
                        let aid = p.take_id();
                        map.insert(a.id, aid);
                        p.analyses.push(Analysis { id: aid, table: nid, name: format!("{} copy", a.name), ..a });
                    }
                    for mut g in p.graphs.iter().filter(|g| g.table == id).cloned().collect::<Vec<_>>() {
                        g.settings.overlays = g.settings.overlays.iter().map(|o| *map.get(o).unwrap_or(o)).collect();
                        g.settings.bracket_opts = std::mem::take(&mut g.settings.bracket_opts).into_iter().map(|(o, v)| (*map.get(&o).unwrap_or(&o), v)).collect();
                        let gid = p.take_id();
                        p.graphs.push(Graph { id: gid, table: nid, name: format!("{} copy", g.name), ..g });
                    }
                }
            } else if let Some(g) = p.graph(id).cloned() {
                let gid = p.take_id();
                p.graphs.push(Graph { id: gid, name: format!("{} copy", g.name), ..g });
            } else if let Some(a) = p.analysis(id).cloned() {
                let aid = p.take_id();
                p.analyses.push(Analysis { id: aid, name: format!("{} copy", a.name), ..a });
            } else if let Some(l) = p.layouts.iter().find(|l| l.id == id).cloned() {
                let lid = p.take_id();
                p.layouts.push(Layout { id: lid, name: format!("{} copy", l.name), ..l });
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
                    let (c, h) = (col.saturating_add(j as i64), h.trim());
                    if c == 0 && !h.is_empty() { t.x_title = h.into(); }
                    if c > 0 && !h.is_empty() {
                        if c as usize >= t.width() && c <= MAX_SETS as i64 { widen(t, c as usize + 1); }
                        if let Some((k, 0)) = t.set_of(c as usize) { t.sets[k].title = h.into(); }
                    }
                }
            }
            for (i, l) in rows.iter().enumerate() {
                for (j, s) in l.iter().enumerate() {
                    put(t, row.saturating_add(i), col.saturating_add(j as i64), s);
                }
            }
        }
        Op::Digitize { name, calib, sets, graph } => {
            let t = crate::digitize::table(&name, &calib, &sets)?;
            p.add_table(t, graph.map(|g| *g));
        }
        Op::Import { name, entry, reps, header, mut rows, graph, dates } => {
            let head = if header && !rows.is_empty() { rows.remove(0) } else { vec![] };
            let set = DataSet { title: String::new(), entry, reps: reps.clamp(1, 50), ..Default::default() };
            let (w, ny) = (set.width(), rows.iter().map(|r| r.len()).max().unwrap_or(1).saturating_sub(1).max(1));
            let n = ny.div_ceil(w);
            let mut t = Table { name, rows: rows.len().max(1), sets: (0..n).map(|k| DataSet { title: format!("Data set {}", set_letter(k)), ..set.clone() }).collect(), ..Default::default() };
            if ["date", "datetime"].contains(&dates.as_str()) {
                t.x_format = dates;
            }
            t.normalize();
            if let Some(x) = head.first().map(|h| h.trim()).filter(|h| !h.is_empty()) { t.x_title = x.into(); }
            for (k, s) in t.sets.iter_mut().enumerate().take(n) {
                if let Some(h) = head.get(1 + k * w).map(|h| h.trim()).filter(|h| !h.is_empty()) { s.title = h.into(); }
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
                (0..at).map(Some).chain((0..(count as usize).min(MAX_ROWS.saturating_sub(n))).map(|_| None)).chain((at..n).map(Some)).collect()
            } else {
                let end = at.saturating_add(count.unsigned_abs() as usize).min(n);
                (0..at).chain(end..n).map(Some).collect()
            };
            if map.is_empty() {
                return Err("A table needs at least one row.".into());
            }
            remap_rows(t, &map);
        }
        Op::Sort { table, col, desc } => {
            let t = p.table_mut(table)?;
            if col >= t.width() {
                return Err("That column does not exist.".into());
            }
            let used = (0..t.rows).rev().find(|&r| (0..t.width()).any(|c| t.get(r, c).is_some()) || !t.row_titles[r].is_empty()).map_or(0, |r| r + 1);
            let mut order: Vec<usize> = (0..used).collect();
            order.sort_by(|&a, &b| match (t.get(a, col), t.get(b, col)) {
                (Some(x), Some(y)) => if desc { y.total_cmp(&x) } else { x.total_cmp(&y) },
                (Some(_), None) => std::cmp::Ordering::Less,
                (None, Some(_)) => std::cmp::Ordering::Greater,
                _ => std::cmp::Ordering::Equal,
            });
            let map: Vec<Option<usize>> = order.into_iter().chain(used..t.rows).map(Some).collect();
            remap_rows(t, &map);
        }
        Op::CopyLook { from, to } => {
            let src = p.graph(from).ok_or("That graph no longer exists.")?.settings.clone();
            for g in p.graphs.iter_mut().filter(|g| to.contains(&g.id) && g.id != from) {
                let s = &g.settings;
                let axis = |a: &Axis, b: &Axis| Axis { title: b.title.clone(), auto: b.auto, min: b.min, max: b.max, step: b.step, break_from: b.break_from, break_to: b.break_to, break_ratio: b.break_ratio, break_step: b.break_step, ..a.clone() };
                g.settings = GraphSettings { title: s.title.clone(), show_title: s.show_title, x: axis(&src.x, &s.x), y: axis(&src.y, &s.y), y2: axis(&src.y2, &s.y2), notes: s.notes.clone(), overlays: s.overlays.clone(), line: s.line, ..src.clone() };
            }
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
        Op::AddAnalysis { mut analysis, overlay, graph } => {
            if p.table(analysis.table).is_none() {
                return Err("That data table no longer exists.".into());
            }
            analysis.id = p.take_id();
            if analysis.name.trim().is_empty() {
                analysis.name = format!("{} · {}", analysis.kind, p.table(analysis.table).map(|t| t.name.clone()).unwrap_or_default());
            }
            if overlay {
                for g in p.graphs.iter_mut().filter(|g| g.table == analysis.table && graph.is_none_or(|k| k == g.id)) {
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
        Op::AddLayout { mut layout } => {
            layout.id = p.take_id();
            if layout.name.trim().is_empty() {
                layout.name = (1..).map(|k| format!("Layout {k}")).find(|n| !p.layouts.iter().any(|l| &l.name == n)).unwrap();
            }
            p.layouts.push(*layout);
        }
        Op::LayoutSet { layout } => {
            let l = p.layouts.iter_mut().find(|l| l.id == layout.id).ok_or("That layout no longer exists.")?;
            *l = *layout;
        }
        Op::Info { info } => p.info = info,
        Op::ProjectName { name } => p.name = name,
        Op::Ui { key, value } => {
            if !p.ui.is_object() {
                p.ui = serde_json::json!({});
            }
            p.ui[key] = value;
        }
        Op::Formula { table, k, formula, sets } => {
            let t = p.table_mut(table)?;
            if let (Some(k), Some(f)) = (k, formula) {
                t.sets.get_mut(k).ok_or("That data set no longer exists.")?.formula = f.trim().to_string();
            }
            let spans = t.spans();
            for (k, vals) in sets {
                let &(c0, w) = spans.get(k).ok_or("That data set no longer exists.")?;
                if w != 1 {
                    return Err("A formula fills a data set with one value per row.".into());
                }
                t.rows = t.rows.max(vals.len());
                t.normalize();
                t.cols[c0] = vals.into_iter().map(|v| v.filter(|x| x.is_finite())).chain(std::iter::repeat(None)).take(t.rows).collect();
            }
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
