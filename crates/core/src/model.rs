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
    /// Page layouts: graphs, text and panel letters on a page of a given size.
    pub layouts: Vec<Layout>,
    pub next_id: u32,
    /// Window settings saved with the file (page setup, open item…).
    pub ui: serde_json::Value,
}

impl Default for Project {
    fn default() -> Self {
        Self { format: FORMAT, name: "Project1".into(), info: Info::default(), tables: vec![], graphs: vec![], analyses: vec![], layouts: vec![], next_id: 1, ui: serde_json::json!({}) }
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
    /// Worksheet columns: "x", "" (Y), "yerr" (the error of the Y column before it) or "skip".
    pub role: String,
    pub units: String,
    pub comment: String,
    /// A column formula (A11), worked out by Python; its values are kept in the column.
    pub formula: String,
}

impl Default for DataSet {
    fn default() -> Self {
        Self { title: String::new(), entry: Entry::Replicates, reps: 3, role: String::new(), units: String::new(), comment: String::new(), formula: String::new() }
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
/// the other, replicates side by side) "contingency" (counts: rows × outcomes, one value per cell), "multi" (many variables: one row per sample), "survival" (time in X, 1 = event or 0 = censored in the subject's group), "nested" (sub-columns are subgroups, replicates down the rows), "sheet" (a worksheet: free columns with roles), "matrix" (Z on an X–Y grid: X down the rows, Y values as the data sets' titles) or "parts"
/// (parts of a whole: parts in the rows, one whole per data set);
/// only XY, survival and matrix tables use the X column (the others keep it hidden).
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
        let sets = (0..groups).map(|k| DataSet { title: format!("Group {}", crate::doc::set_letter(k)), entry: Entry::Replicates, reps: 1, ..Default::default() }).collect();
        let mut t = Table { kind: "column".into(), x_title: String::new(), y_title: "Value".into(), sets, ..Default::default() };
        t.normalize();
        t
    }
    /// An empty grouped table: `rows` rows (named in the row titles), `groups` data sets of 3 replicates.
    pub fn grouped(rows: usize, groups: usize) -> Self {
        let sets = (0..groups).map(|k| DataSet { title: format!("Data set {}", crate::doc::set_letter(k)), entry: Entry::Replicates, reps: 3, ..Default::default() }).collect();
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
    /// An empty table of many variables: one row per sample (named in the row titles), one data set
    /// per variable with one value per cell. Graphs put the first variable on X.
    pub fn multi(vars: usize, rows: usize) -> Self {
        let sets = (0..vars).map(|k| DataSet { title: format!("Variable {}", crate::doc::set_letter(k)), entry: Entry::Replicates, reps: 1, ..Default::default() }).collect();
        let mut t = Table { kind: "multi".into(), x_title: String::new(), y_title: "Value".into(), sets, rows: rows.max(1), ..Default::default() };
        t.normalize();
        t
    }
    /// An empty worksheet (A9): free columns, one value per row, the first one X.
    pub fn sheet(cols: usize) -> Self {
        let sets = (0..cols).map(|k| DataSet { title: crate::doc::set_letter(k), entry: Entry::Replicates, reps: 1, role: if k == 0 { "x".into() } else { String::new() }, ..Default::default() }).collect();
        let mut t = Table { kind: "sheet".into(), x_title: String::new(), y_title: String::new(), sets, rows: 12, ..Default::default() };
        t.normalize();
        t
    }
    /// An empty matrix (A10): Z values on an X–Y grid. X runs down the rows (the X column), Y across:
    /// each data set is one Y value, its title the number.
    pub fn matrix(rows: usize, cols: usize) -> Self {
        let sets = (0..cols).map(|k| DataSet { title: format!("{}", k + 1), entry: Entry::Replicates, reps: 1, ..Default::default() }).collect();
        let mut t = Table { kind: "matrix".into(), x_title: "X".into(), y_title: "Z".into(), sets, rows: rows.max(2), ..Default::default() };
        t.normalize();
        t
    }
    /// An empty nested table: `groups` data sets with `subs` sub-columns each (one per subgroup:
    /// a batch, an animal), replicates down the rows.
    pub fn nested(groups: usize, subs: usize) -> Self {
        let sets = (0..groups).map(|k| DataSet { title: format!("Group {}", crate::doc::set_letter(k)), entry: Entry::Replicates, reps: subs.max(1), ..Default::default() }).collect();
        let mut t = Table { kind: "nested".into(), x_title: String::new(), y_title: "Value".into(), sets, ..Default::default() };
        t.normalize();
        t
    }
    /// An empty survival table: one row per subject, the time in X, and in its group's column 1 for an
    /// event (death, failure) or 0 for censored.
    pub fn survival(groups: usize) -> Self {
        let sets = (0..groups).map(|k| DataSet { title: format!("Group {}", crate::doc::set_letter(k)), entry: Entry::Replicates, reps: 1, ..Default::default() }).collect();
        let mut t = Table { kind: "survival".into(), x_title: "Time".into(), y_title: "Percent survival".into(), sets, ..Default::default() };
        t.normalize();
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
        // Limits that keep a damaged or hostile file from exhausting memory: 1000 data sets of at most
        // 50 replicates, a million rows, and no more than 20 million cells in all.
        self.sets.truncate(MAX_SETS);
        for s in &mut self.sets {
            s.reps = s.reps.clamp(1, 50);
        }
        let w = self.width();
        self.rows = self.rows.clamp(1, (MAX_CELLS / w.max(1)).clamp(1, MAX_ROWS));
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

pub const MAX_ROWS: usize = 1_000_000;
pub const MAX_SETS: usize = 1000;
pub const MAX_CELLS: usize = 20_000_000;

/// A page layout (F1): items placed in millimetres from the top-left of a `width` × `height` page.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default, rename_all = "camelCase")]
pub struct Layout {
    pub id: u32,
    pub name: String,
    pub width: f64,
    pub height: f64,
    /// Panel letters on the graphs: A, a, (a) or none.
    pub letters: String,
    pub letter_size: f64,
    pub font: String,
    pub font_size: f64,
    /// Line up the plot frames of graphs in the same column and row (D12).
    pub align: bool,
    pub items: Vec<LayoutItem>,
}

impl Default for Layout {
    fn default() -> Self {
        Self { id: 0, name: "Layout 1".into(), width: 180.0, height: 120.0, letters: "A".into(), letter_size: 10.0, font: "Arial".into(), font_size: 8.0, align: true, items: vec![] }
    }
}

/// A graph (by id) or a text block on a layout; a graph can be an inset (a small graph on a white
/// card over another) or drop its X axis title and numbers (stacked panels sharing X).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default, rename_all = "camelCase")]
pub struct LayoutItem {
    pub kind: String,
    pub graph: u32,
    pub x: f64,
    pub y: f64,
    pub w: f64,
    pub h: f64,
    pub text: String,
    pub size: f64,
    pub bold: bool,
    pub inset: bool,
    pub hide_x: bool,
}

impl Default for LayoutItem {
    fn default() -> Self {
        Self { kind: "graph".into(), graph: 0, x: 0.0, y: 0.0, w: 80.0, h: 60.0, text: String::new(), size: 0.0, bold: false, inset: false, hide_x: false }
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
    /// Annotations drawn on the graph (text, arrows, lines, boxes), in data coordinates.
    pub notes: Vec<Note>,
    /// The second Y axis (right), for data sets marked `right`.
    pub y2: Axis,
    /// Colour scheme: okabe, tableau, bright, muted, dark, pastel, viridis, cividis, magma, grey, or "#hex, #hex…".
    pub palette: String,
    /// XY graphs drawn on polar axes (X is the angle in degrees).
    pub polar: bool,
    /// Matrix graphs: contour levels (0 = automatic) and the 3D view (elevation and azimuth in degrees).
    pub levels: u32,
    pub elev: f64,
    pub azim: f64,
}

impl Default for GraphSettings {
    fn default() -> Self {
        Self {
            error: "sd".into(), error_dir: "both".into(), points: "mean".into(), line: true, cap: 3.0, width: 80.0, height: 60.0, font: "Arial".into(), font_size: 10.0,
            bold_titles: true, style: "prism".into(), title: String::new(), show_title: true, legend: Legend::default(), x: Axis::default(), y: Axis::default(), sets: vec![], overlays: vec![],
            column: "scatter".into(), palette: String::new(), y2: Axis::default(), notes: vec![], polar: false, levels: 0, elev: 28.0, azim: -60.0,
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
#[serde(default, rename_all = "camelCase")]
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
    /// Y axis break: the values from `break_from` to `break_to` are cut out (both set and from < to).
    pub break_from: Option<f64>,
    pub break_to: Option<f64>,
}

impl Default for Axis {
    fn default() -> Self {
        Self { title: String::new(), scale: "lin".into(), auto: true, min: None, max: None, step: None, minor: false, grid: false, break_from: None, break_to: None }
    }
}

/// An annotation: `kind` text, arrow, line or box; (x, y) is where it starts (the text's place),
/// (x2, y2) where an arrow points, a line ends or the box's opposite corner is (data coordinates).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub struct Note {
    pub kind: String,
    pub x: f64,
    pub y: f64,
    pub x2: f64,
    pub y2: f64,
    pub text: String,
    /// Empty: dark grey.
    pub color: String,
    /// Font size in points; 0 = the graph's size.
    pub size: f64,
    pub bold: bool,
}

impl Default for Note {
    fn default() -> Self {
        Self { kind: "text".into(), x: 0.0, y: 0.0, x2: 0.0, y2: 0.0, text: String::new(), color: String::new(), size: 0.0, bold: false }
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
    /// Drawn against the second Y axis on the right.
    pub right: bool,
}

impl Default for SetStyle {
    fn default() -> Self {
        Self { show: true, color: String::new(), symbol: String::new(), size: 6.0, filled: true, line: None, width: 1.0, right: false }
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
        let gids: Vec<u32> = self.graphs.iter().map(|g| g.id).collect();
        for l in &mut self.layouts {
            l.items.retain(|i| i.kind != "graph" || gids.contains(&i.graph));
            (l.width, l.height) = (l.width.clamp(20.0, 2000.0), l.height.clamp(20.0, 2000.0));
        }
        let top = self.tables.iter().map(|t| t.id).chain(self.graphs.iter().map(|g| g.id)).chain(self.analyses.iter().map(|a| a.id)).chain(self.layouts.iter().map(|l| l.id)).max().unwrap_or(0);
        self.next_id = self.next_id.max(top + 1);
    }
    /// Cells in all the tables (for the undo budget).
    pub fn cells(&self) -> usize {
        self.tables.iter().map(|t| t.rows * t.width()).sum()
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
