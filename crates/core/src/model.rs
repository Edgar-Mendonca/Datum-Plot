//! The project file: data tables, graphs and the Info sheet. Saved as JSON in `.dplot` files.
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

pub const FORMAT: u32 = 1;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default, rename_all = "camelCase")]
pub struct Project {
    pub format: u32,
    pub name: String,
    pub info: Info,
    pub tables: Vec<Table>,
    pub graphs: Vec<Graph>,
    /// Analyses (results): settings only; Python computes the results when they are shown.
    pub analyses: Vec<Analysis>,
    pub next_id: u32,
    /// Window settings saved with the file (page setup, open item…).
    pub ui: serde_json::Value,
}

impl Default for Project {
    fn default() -> Self {
        Self { format: FORMAT, name: "Project1".into(), info: Info::default(), tables: vec![], graphs: vec![], analyses: vec![], next_id: 1, ui: serde_json::json!({}) }
    }
}

/// The Info sheet: what the experiment is, for the reader and for page headers.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(default, rename_all = "camelCase")]
pub struct Info {
    pub title: String,
    pub experiment: String,
    pub researcher: String,
    pub organisation: String,
    pub date: String,
    pub notes: String,
}

/// How a data set's values are entered: replicates, or a mean with SD or SEM and N.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum Entry {
    #[default]
    #[serde(rename = "rep")]
    Replicates,
    #[serde(rename = "msn")]
    MeanSdN,
    #[serde(rename = "mesn")]
    MeanSemN,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default, rename_all = "camelCase")]
pub struct DataSet {
    pub title: String,
    pub entry: Entry,
    /// Replicate sub-columns (Replicates only; the other entries always have 3).
    pub reps: usize,
}

impl Default for DataSet {
    fn default() -> Self {
        Self { title: String::new(), entry: Entry::Replicates, reps: 3 }
    }
}

impl DataSet {
    pub fn width(&self) -> usize {
        if self.entry == Entry::Replicates { self.reps.clamp(1, 50) } else { 3 }
    }
}

/// A data table: an X column, then each data set's sub-columns. `cols` is that flat list
/// (column 0 is X); every column has `rows` cells. `kind` is "xy", "column" (one group per data
/// set, values down the rows) "grouped" (rows are one factor, named by the row titles, data sets
/// the other, replicates side by side) "contingency" (counts: rows × outcomes, one value per cell) or "parts"
/// (parts of a whole: parts in the rows, one whole per data set);
/// only XY tables use the X column (the others keep it hidden).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default, rename_all = "camelCase")]
pub struct Table {
    pub id: u32,
    pub name: String,
    pub kind: String,
    pub x_title: String,
    pub x_units: String,
    pub y_title: String,
    pub y_units: String,
    pub rows: usize,
    pub row_titles: Vec<String>,
    pub sets: Vec<DataSet>,
    pub cols: Vec<Vec<Option<f64>>>,
    /// Cells left out of graphs and analyses, as [row, column].
    pub excluded: Vec<[usize; 2]>,
    /// Text formatting of cells ("row:col" → style string, as in Datum Plan's fmt.ts).
    pub style: BTreeMap<String, String>,
    pub notes: String,
}

impl Default for Table {
    fn default() -> Self {
        Self {
            id: 0, name: "Data 1".into(), kind: "xy".into(), x_title: "X".into(), x_units: String::new(), y_title: "Y".into(), y_units: String::new(), rows: 20,
            row_titles: vec![], sets: vec![DataSet { title: "Data set A".into(), ..Default::default() }], cols: vec![], excluded: vec![], style: BTreeMap::new(), notes: String::new(),
        }
    }
}

impl Table {
    /// An empty column table (groups A, B, C, one value per row).
    pub fn column(groups: usize) -> Self {
        let sets = (0..groups).map(|k| DataSet { title: format!("Group {}", crate::doc::set_letter(k)), entry: Entry::Replicates, reps: 1 }).collect();
        let mut t = Table { kind: "column".into(), x_title: String::new(), y_title: "Value".into(), sets, ..Default::default() };
        t.normalize();
        t
    }
    /// An empty grouped table: `rows` rows (named in the row titles), `groups` data sets of 3 replicates.
    pub fn grouped(rows: usize, groups: usize) -> Self {
        let sets = (0..groups).map(|k| DataSet { title: format!("Data set {}", crate::doc::set_letter(k)), entry: Entry::Replicates, reps: 3 }).collect();
        let mut t = Table { kind: "grouped".into(), x_title: String::new(), y_title: "Value".into(), sets, rows: rows.max(1), ..Default::default() };
        t.normalize();
        for r in 0..rows {
            t.row_titles[r] = format!("Row {}", r + 1);
        }
        t
    }
    /// An empty contingency table: `rows` × `groups` counts (one value per cell), rows named in the row titles.
    pub fn contingency(rows: usize, groups: usize) -> Self {
        let mut t = Table::grouped(rows, groups);
        t.kind = "contingency".into();
        t.y_title = "Count".into();
        for (k, s) in t.sets.iter_mut().enumerate() {
            s.reps = 1;
            s.title = format!("Outcome {}", crate::doc::set_letter(k));
        }
        t.normalize();
        t
    }
    /// An empty parts-of-whole table: the parts in the rows (row titles), one whole per data set.
    pub fn parts(rows: usize, groups: usize) -> Self {
        let mut t = Table::contingency(rows, groups);
        t.kind = "parts".into();
        t.y_title = "Value".into();
        for (k, s) in t.sets.iter_mut().enumerate() {
            s.title = format!("Whole {}", crate::doc::set_letter(k));
        }
        for (r, n) in t.row_titles.iter_mut().enumerate() {
            *n = format!("Part {}", r + 1);
        }
        t
    }
    /// (first grid column, width) of each data set.
    pub fn spans(&self) -> Vec<(usize, usize)> {
        let mut c = 1;
        self.sets.iter().map(|s| { let v = (c, s.width()); c += s.width(); v }).collect()
    }
    pub fn width(&self) -> usize {
        1 + self.sets.iter().map(DataSet::width).sum::<usize>()
    }
    pub fn get(&self, r: usize, c: usize) -> Option<f64> {
        self.cols.get(c).and_then(|v| v.get(r)).copied().flatten()
    }
    pub fn is_excluded(&self, r: usize, c: usize) -> bool {
        self.excluded.contains(&[r, c])
    }
    /// The data set a grid column belongs to, and the sub-column within it.
    pub fn set_of(&self, c: usize) -> Option<(usize, usize)> {
        self.spans().iter().enumerate().find(|(_, (c0, w))| c >= *c0 && c < c0 + w).map(|(k, (c0, _))| (k, c - c0))
    }
    /// Makes every column `rows` long and matches the columns to the data sets.
    pub fn normalize(&mut self) {
        self.rows = self.rows.clamp(1, 100_000);
        let w = self.width();
        self.cols.resize(w, vec![]);
        for c in &mut self.cols {
            c.resize(self.rows, None);
        }
        self.row_titles.resize(self.rows, String::new());
        let (rows, w) = (self.rows, self.width());
        self.excluded.retain(|[r, c]| *r < rows && *c < w);
        self.excluded.sort_unstable();
        self.excluded.dedup();
    }
}

/// An analysis of one data table: describe, normality, outliers, linear, fit or arrhenius.
/// `sets` are the data sets it uses (empty = all); `options` are read by py/datum/analysis.py.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(default, rename_all = "camelCase")]
pub struct Analysis {
    pub id: u32,
    pub table: u32,
    pub name: String,
    pub kind: String,
    pub sets: Vec<usize>,
    pub options: serde_json::Value,
}

/// A graph of one data table. Its settings are what the Python graph engine reads.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default, rename_all = "camelCase")]
pub struct Graph {
    pub id: u32,
    pub table: u32,
    pub name: String,
    pub settings: GraphSettings,
}

impl Default for Graph {
    fn default() -> Self {
        Self { id: 0, table: 0, name: "Graph 1".into(), settings: GraphSettings::default() }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default, rename_all = "camelCase")]
pub struct GraphSettings {
    /// sd, sem, ci, range or none.
    pub error: String,
    /// both, up or down.
    pub error_dir: String,
    /// mean (with error bars) or each (every replicate).
    pub points: String,
    /// Connect the points of each data set.
    pub line: bool,
    pub cap: f64,
    /// Size of the whole graph in millimetres.
    pub width: f64,
    pub height: f64,
    pub font: String,
    pub font_size: f64,
    pub bold_titles: bool,
    /// prism (open axes, ticks out) or frame (box, ticks in).
    pub style: String,
    pub title: String,
    pub show_title: bool,
    pub legend: Legend,
    pub x: Axis,
    pub y: Axis,
    pub sets: Vec<SetStyle>,
    /// Analyses whose fitted curves (or significance brackets) are drawn on this graph.
    pub overlays: Vec<u32>,
    /// Column tables: scatter, bars, box, violin, paired or mean.
    pub column: String,
    /// Colour scheme: okabe, tableau, bright, muted, dark, pastel, viridis, cividis, magma, grey, or "#hex, #hex…".
    pub palette: String,
}

impl Default for GraphSettings {
    fn default() -> Self {
        Self {
            error: "sd".into(), error_dir: "both".into(), points: "mean".into(), line: true, cap: 3.0, width: 80.0, height: 60.0, font: "Arial".into(), font_size: 10.0,
            bold_titles: true, style: "prism".into(), title: String::new(), show_title: true, legend: Legend::default(), x: Axis::default(), y: Axis::default(), sets: vec![], overlays: vec![],
            column: "scatter".into(), palette: String::new(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub struct Legend {
    pub show: bool,
    /// best, upper left, upper right, lower left, lower right or outside.
    pub loc: String,
}

impl Default for Legend {
    fn default() -> Self {
        Self { show: true, loc: "best".into() }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub struct Axis {
    /// Empty: the table's title and units.
    pub title: String,
    /// lin or log.
    pub scale: String,
    pub auto: bool,
    pub min: Option<f64>,
    pub max: Option<f64>,
    /// Major tick step (linear axes); none = automatic.
    pub step: Option<f64>,
    pub minor: bool,
    pub grid: bool,
}

impl Default for Axis {
    fn default() -> Self {
        Self { title: String::new(), scale: "lin".into(), auto: true, min: None, max: None, step: None, minor: false, grid: false }
    }
}

/// The look of one data set; empty values mean the default for its position.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub struct SetStyle {
    pub show: bool,
    pub color: String,
    pub symbol: String,
    pub size: f64,
    pub filled: bool,
    pub line: Option<bool>,
    pub width: f64,
}

impl Default for SetStyle {
    fn default() -> Self {
        Self { show: true, color: String::new(), symbol: String::new(), size: 6.0, filled: true, line: None, width: 1.0 }
    }
}

impl Project {
    pub fn new(name: &str) -> Self {
        Self { name: name.into(), ..Default::default() }
    }
    pub fn table(&self, id: u32) -> Option<&Table> {
        self.tables.iter().find(|t| t.id == id)
    }
    pub fn table_mut(&mut self, id: u32) -> Result<&mut Table, String> {
        self.tables.iter_mut().find(|t| t.id == id).ok_or_else(|| "That data table no longer exists.".into())
    }
    pub fn analysis(&self, id: u32) -> Option<&Analysis> {
        self.analyses.iter().find(|a| a.id == id)
    }
    pub fn graph(&self, id: u32) -> Option<&Graph> {
        self.graphs.iter().find(|g| g.id == id)
    }
    pub fn take_id(&mut self) -> u32 {
        let id = self.next_id.max(1);
        self.next_id = id + 1;
        id
    }
    /// Adds a table (and a graph of it, as Prism does); returns the table's id.
    pub fn add_table(&mut self, mut t: Table, g: Option<GraphSettings>) -> u32 {
        t.id = self.take_id();
        let id = t.id;
        if self.tables.iter().any(|x| x.name == t.name) || t.name.is_empty() {
            t.name = (1..).map(|k| format!("Data {k}")).find(|n| !self.tables.iter().any(|x| &x.name == n)).unwrap();
        }
        let name = t.name.clone();
        self.tables.push(t);
        if let Some(settings) = g {
            let gid = self.take_id();
            self.graphs.push(Graph { id: gid, table: id, name: name.clone(), settings });
        }
        id
    }
    pub fn normalize(&mut self) {
        self.tables.iter_mut().for_each(Table::normalize);
        let ids: Vec<u32> = self.tables.iter().map(|t| t.id).collect();
        self.graphs.retain(|g| ids.contains(&g.table));
        self.analyses.retain(|a| ids.contains(&a.table));
        for a in &mut self.analyses {
            if !a.options.is_object() {
                a.options = serde_json::json!({});
            }
        }
        let an: Vec<(u32, u32)> = self.analyses.iter().map(|a| (a.id, a.table)).collect();
        for g in &mut self.graphs {
            g.settings.overlays.retain(|o| an.contains(&(*o, g.table)));
        }
        let top = self.tables.iter().map(|t| t.id).chain(self.graphs.iter().map(|g| g.id)).chain(self.analyses.iter().map(|a| a.id)).max().unwrap_or(0);
        self.next_id = self.next_id.max(top + 1);
    }
    pub fn from_json(text: &str) -> Result<Self, String> {
        let mut p: Project = serde_json::from_str(text).map_err(|e| e.to_string())?;
        if p.format > FORMAT {
            return Err("it was saved by a newer Datum Plot; update the app to open it".into());
        }
        p.format = FORMAT;
        p.normalize();
        Ok(p)
    }
}
