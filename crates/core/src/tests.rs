use crate::doc::{number, Doc, Op};
use crate::*;

fn doc() -> (Doc, u32) {
    let d = Doc::new(templates::build(None).unwrap());
    let id = d.p.tables[0].id;
    (d, id)
}
fn cells(t: u32, v: &[(usize, i64, &str)]) -> Op {
    Op::Cells { table: t, cells: v.iter().map(|(r, c, s)| (*r, *c, s.to_string())).collect() }
}

#[test]
fn numbers_as_people_type_them() {
    for (s, v) in [("1.5", 1.5), ("-2", -2.0), ("1e-3", 0.001), ("1,234.5", 1234.5), ("−4", -4.0), (" 7 ", 7.0), ("12%", 0.12), ("12,345,678", 12345678.0)] {
        assert_eq!(number(s), Some(v), "{s}");
    }
    for s in ["", "abc", "1,2", "1.2.3", "NaN", "inf", "12,34"] {
        assert_eq!(number(s), None, "{s}");
    }
}

#[test]
fn new_project_has_a_table_and_its_graph() {
    let (d, id) = doc();
    let t = &d.p.tables[0];
    assert_eq!((t.kind.as_str(), t.rows, t.width(), t.cols.len()), ("xy", 20, 4, 4));
    assert_eq!(d.p.graphs.len(), 1);
    assert_eq!(d.p.graphs[0].table, id);
    assert!(d.p.next_id > d.p.graphs[0].id);
}

#[test]
fn typing_values_grows_rows_and_data_sets() {
    let (mut d, id) = doc();
    d.apply(cells(id, &[(0, 0, "1"), (0, 1, "2.5"), (25, 0, "9"), (0, 6, "4")])).unwrap();
    let t = &d.p.tables[0];
    assert_eq!(t.rows, 26);
    assert_eq!(t.sets.len(), 2, "column 6 needs a second data set of 3 replicates");
    assert_eq!(t.sets[1].title, "Data set B");
    assert_eq!((t.get(0, 1), t.get(25, 0), t.get(0, 6)), (Some(2.5), Some(9.0), Some(4.0)));
    let e = d.apply(cells(id, &[(1, 1, "abc")])).unwrap_err();
    assert!(e.contains("not a number"), "{e}");
    d.apply(cells(id, &[(0, 1, ""), (2, -1, "Mouse 1")])).unwrap();
    assert_eq!(d.p.tables[0].get(0, 1), None);
    assert_eq!(d.p.tables[0].row_titles[2], "Mouse 1");
}

#[test]
fn paste_with_headings_sets_titles() {
    let (mut d, id) = doc();
    let rows = vec![vec!["Time".into(), "Control".into(), "".into(), "".into(), "Drug".into()], vec!["0".into(), "1".into(), "1.1".into(), "0.9".into(), "2".into()]];
    d.apply(Op::Paste { table: id, row: 0, col: 0, rows }).unwrap();
    let t = &d.p.tables[0];
    assert_eq!((t.x_title.as_str(), t.sets[0].title.as_str(), t.sets[1].title.as_str()), ("Time", "Control", "Drug"));
    assert_eq!((t.get(0, 0), t.get(0, 3), t.get(0, 4)), (Some(0.0), Some(0.9), Some(2.0)));
}

#[test]
fn changing_replicates_keeps_values_and_exclusions_in_place() {
    let (mut d, id) = doc();
    d.apply(Op::SetDef { table: id, k: None, set: Some(DataSet { title: "B".into(), ..Default::default() }) }).unwrap();
    d.apply(cells(id, &[(0, 1, "1"), (0, 3, "3"), (0, 4, "10"), (0, 6, "30")])).unwrap();
    d.apply(Op::Exclude { table: id, cells: vec![(0, 4)], on: true }).unwrap();
    // Set A goes from 3 to 2 replicates: its third value is dropped, set B moves one column left.
    d.apply(Op::SetDef { table: id, k: Some(0), set: Some(DataSet { title: "A".into(), entry: Entry::Replicates, reps: 2, ..Default::default() }) }).unwrap();
    let t = &d.p.tables[0];
    assert_eq!(t.width(), 6);
    assert_eq!((t.get(0, 1), t.get(0, 2), t.get(0, 3), t.get(0, 5)), (Some(1.0), None, Some(10.0), Some(30.0)));
    assert_eq!(t.excluded, vec![[0, 3]]);
    // Mean/SD/N always has three columns; removing set A moves B to column 1.
    d.apply(Op::SetDef { table: id, k: Some(0), set: None }).unwrap();
    assert_eq!((d.p.tables[0].get(0, 1), d.p.tables[0].excluded.clone()), (Some(10.0), vec![[0, 1]]));
    assert!(d.apply(Op::SetDef { table: id, k: Some(0), set: None }).is_err(), "the last data set stays");
}

#[test]
fn inserting_and_deleting_rows_moves_data() {
    let (mut d, id) = doc();
    d.apply(cells(id, &[(0, 0, "1"), (1, 0, "2"), (2, 0, "3")])).unwrap();
    d.apply(Op::Exclude { table: id, cells: vec![(2, 0)], on: true }).unwrap();
    d.apply(Op::Rows { table: id, at: 1, count: 2 }).unwrap();
    let t = &d.p.tables[0];
    assert_eq!((t.rows, t.get(0, 0), t.get(1, 0), t.get(3, 0), t.get(4, 0)), (22, Some(1.0), None, Some(2.0), Some(3.0)));
    assert_eq!(t.excluded, vec![[4, 0]]);
    d.apply(Op::Rows { table: id, at: 0, count: -4 }).unwrap();
    assert_eq!((d.p.tables[0].rows, d.p.tables[0].get(0, 0), d.p.tables[0].excluded.clone()), (18, Some(3.0), vec![[0, 0]]));
}

#[test]
fn undo_redo_and_unchanged_edits() {
    let (mut d, id) = doc();
    d.apply(cells(id, &[(0, 0, "5")])).unwrap();
    assert!(d.dirty && d.can_undo());
    d.apply(cells(id, &[(0, 0, "5")])).unwrap();
    d.undo();
    assert_eq!(d.p.tables[0].get(0, 0), None, "a repeated edit adds no undo step");
    d.redo();
    assert_eq!(d.p.tables[0].get(0, 0), Some(5.0));
}

#[test]
fn deleting_a_table_deletes_its_graphs_and_duplicates_copy_both() {
    let (mut d, id) = doc();
    d.apply(Op::Duplicate { id, only: false }).unwrap();
    assert_eq!((d.p.tables.len(), d.p.graphs.len()), (2, 2));
    assert_eq!(d.p.tables[1].name, "Data 1 copy");
    d.apply(Op::Delete { id }).unwrap();
    assert_eq!((d.p.tables.len(), d.p.graphs.len()), (1, 1));
    assert_eq!(d.p.graphs[0].table, d.p.tables[0].id);
    let ids: Vec<u32> = d.p.tables.iter().map(|t| t.id).chain(d.p.graphs.iter().map(|g| g.id)).collect();
    assert!(ids.iter().all(|i| *i < d.p.next_id));
}

#[test]
fn graph_settings_are_checked() {
    let (mut d, _) = doc();
    let g = d.p.graphs[0].id;
    let s = GraphSettings { width: 5.0, ..Default::default() };
    assert!(d.apply(Op::GraphSet { graph: g, settings: Box::new(s) }).is_err());
    let s = GraphSettings { error: "sem".into(), x: Axis { scale: "log".into(), ..Default::default() }, ..Default::default() };
    d.apply(Op::GraphSet { graph: g, settings: Box::new(s) }).unwrap();
    assert_eq!(d.p.graphs[0].settings.x.scale, "log");
}

#[test]
fn files_round_trip_and_newer_files_are_refused() {
    for id in [None, Some("growth"), Some("standard"), Some("dose"), Some("modulus"), Some("arrhenius")] {
        let p = templates::build(id).unwrap();
        let text = serde_json::to_string(&p).unwrap();
        assert_eq!(Project::from_json(&text).unwrap(), p, "{id:?}");
        assert!(text.contains("\"xTitle\""), "camelCase keys for the window and Python");
    }
    let dir = std::env::temp_dir().join("datum-plot-test.dplot");
    let mut d = Doc::new(templates::build(Some("dose")).unwrap());
    d.save(&dir).unwrap();
    assert!(!d.dirty);
    assert_eq!(Doc::open(&dir).unwrap().p, d.p);
    let _ = std::fs::remove_file(dir);
    assert!(Project::from_json(r#"{"format": 99}"#).unwrap_err().contains("newer"));
    // Missing fields take defaults; short columns are padded.
    let p = Project::from_json(r#"{"tables":[{"id":3,"rows":2,"cols":[[1]]}]}"#).unwrap();
    assert_eq!((p.tables[0].cols.len(), p.tables[0].cols[0].len(), p.next_id), (4, 2, 4));
}

#[test]
fn edits_with_impossible_values_are_refused_not_crashing() {
    let mut d = Doc::new(Project::new("P"));
    d.apply(Op::NewTable { table: Box::new(Table::column(2)), graph: Some(Box::new(GraphSettings::default())) }).unwrap();
    let id = d.p.tables[0].id;
    let ops = vec![
        Op::Cells { table: id, cells: vec![(usize::MAX, 99, "1".into()), (0, -5, "x".into())] },
        Op::Paste { table: id, row: usize::MAX / 2, col: 1, rows: vec![vec!["1".into()]] },
        Op::Rows { table: id, at: usize::MAX, count: i64::MIN },
        Op::Rows { table: id, at: 0, count: i64::MAX },
        Op::Sort { table: id, col: 999, desc: true },
        Op::Exclude { table: id, cells: vec![(usize::MAX, usize::MAX)], on: true },
        Op::SetDef { table: id, k: Some(99), set: None },
        Op::Formula { table: id, k: Some(99), formula: Some("A".into()), sets: vec![] },
        Op::Formula { table: id, k: None, formula: None, sets: vec![(0, vec![Some(1.0); 5_000_000])] },
        Op::Style { table: id, cells: vec![("99999999:99999".into(), "b".into()), ("x".into(), "y".into())] },
        Op::Delete { id: 12345 }, Op::Rename { id: 12345, name: "x".into() }, Op::Duplicate { id: 12345, only: false },
        Op::Overlay { graph: 12345, analysis: 1, on: true }, Op::CopyLook { from: 12345, to: vec![1, 2] },
        Op::AddGraph { table: 12345, settings: None },
        Op::Batch(vec![Op::Rename { id, name: "ok".into() }, Op::Delete { id: 12345 }]),
    ];
    for op in ops {
        let _ = d.apply(op); // an error is fine; a panic or a runaway table is not
        let t = &d.p.tables[0];
        assert!(t.rows <= MAX_ROWS && t.cols.iter().all(|c| c.len() == t.rows), "table stays well formed");
    }
}

#[test]
fn hostile_files_are_kept_in_bounds() {
    // Absurd sizes in a file must not allocate without limit.
    let p = Project::from_json(r#"{"name":"x","tables":[{"id":1,"name":"T","rows":4000000000,"sets":[{"title":"A","entry":"rep","reps":99999999}]}]}"#).unwrap();
    let t = &p.tables[0];
    assert_eq!((t.sets[0].reps, t.width()), (50, 51));
    assert!(t.rows * t.width() <= MAX_CELLS && t.cols.iter().all(|c| c.len() == t.rows));
    let many = format!(r#"{{"name":"x","tables":[{{"id":1,"name":"T","rows":5,"sets":[{}]}}]}}"#, vec![r#"{"title":"A","entry":"rep","reps":1}"#; 3000].join(","));
    assert_eq!(Project::from_json(&many).unwrap().tables[0].sets.len(), MAX_SETS);
    let mut d = Doc::new(Project::new("big"));
    d.apply(Op::NewTable { table: Box::new(Table { rows: 3_000_000, ..Table::column(2) }), graph: None }).unwrap();
    for i in 0..30 {
        d.apply(Op::Rename { id: d.p.tables[0].id, name: format!("T{i}") }).unwrap();
    }
    let mut n = 0;
    while d.can_undo() {
        d.undo();
        n += 1;
    }
    assert_eq!(n, 20, "a 3-million-cell project keeps 60M / 3M = 20 undo steps");
    let big = Table { rows: 2_000_000, ..Table::column(1) };
    let mut b = big;
    b.normalize();
    assert_eq!(b.rows, MAX_ROWS);
}

#[test]
fn worksheets_and_formulas() {
    let mut d = Doc::new(Project::new("P"));
    d.apply(Op::NewTable { table: Box::new(Table::sheet(3)), graph: None }).unwrap();
    let id = d.p.tables[0].id;
    let t = &d.p.tables[0];
    assert_eq!((t.kind.as_str(), t.width(), t.sets[0].role.as_str(), t.sets[1].role.as_str(), t.sets[2].title.as_str()), ("sheet", 4, "x", "", "C"));
    d.apply(Op::Cells { table: id, cells: vec![(0, 1, "2".into()), (1, 1, "4".into())] }).unwrap();
    // Setting a formula and its values is one step; a recalculation merges into the step before it.
    d.apply(Op::Formula { table: id, k: Some(2), formula: Some(" B*2 ".into()), sets: vec![(2, vec![Some(4.0), Some(8.0)])] }).unwrap();
    assert_eq!((d.p.tables[0].sets[2].formula.as_str(), d.p.tables[0].get(1, 3)), ("B*2", Some(8.0)));
    d.apply(Op::Cells { table: id, cells: vec![(1, 1, "5".into())] }).unwrap();
    d.merge(Op::Formula { table: id, k: None, formula: None, sets: vec![(2, vec![Some(4.0), Some(10.0), Some(f64::NAN)])] }).unwrap();
    assert_eq!((d.p.tables[0].get(1, 3), d.p.tables[0].get(2, 3)), (Some(10.0), None));
    d.undo();
    assert_eq!((d.p.tables[0].get(1, 1), d.p.tables[0].get(1, 3)), (Some(4.0), Some(8.0)), "undo takes back the edit and its recalculation together");
    assert!(d.apply(Op::Formula { table: id, k: None, formula: None, sets: vec![(9, vec![])] }).is_err());
    let json = Project::from_json(&d.json()).unwrap();
    assert_eq!(json.tables[0].sets[2].formula, "B*2");
    assert_eq!(Project::from_json(r#"{"name":"old","tables":[{"id":1,"name":"T","sets":[{"title":"A","entry":"rep","reps":2}]}]}"#).unwrap().tables[0].sets[0].role, "");
}

#[test]
fn templates_make_sense() {
    let l = templates::list();
    assert_eq!(l.len(), 26);
    assert!(l.iter().all(|t| templates::GROUPS.contains(&t.group)), "every sample sits under a heading of Home › Samples");
    assert!(l.windows(2).all(|w| templates::GROUPS.iter().position(|g| *g == w[0].group) <= templates::GROUPS.iter().position(|g| *g == w[1].group)), "listed heading by heading");
    assert!(l.iter().all(|t| t.dots.len() >= 2 && t.dots.iter().all(|d| d.0.is_finite() && d.1.is_finite())), "every tile has a picture");
    for (id, n) in [("modulus", 2), ("arrhenius", 1), ("groups", 1), ("dsc", 1), ("twoway", 1), ("spectrum", 1), ("tga", 1), ("fatigue", 1), ("trial", 1), ("surface", 1)] {
        let p = templates::build(Some(id)).unwrap();
        assert_eq!((p.analyses.len(), p.graphs[0].settings.overlays.clone()), (n, vec![p.analyses[0].id]), "{id}");
        assert!(p.next_id > p.analyses[n - 1].id);
    }
    let t = &templates::build(Some("twoway")).unwrap().tables[0];
    assert_eq!((t.kind.as_str(), t.sets.len(), t.width(), t.row_titles[1].as_str(), t.get(2, 6).is_some()), ("grouped", 2, 7, "7075", true));
    let t = &templates::build(Some("counts")).unwrap().tables[0];
    assert_eq!((t.kind.as_str(), t.width(), t.rows, t.get(1, 2)), ("contingency", 3, 2, Some(45.0)));
    let t = &templates::build(Some("phases")).unwrap().tables[0];
    assert_eq!((t.kind.as_str(), t.rows, t.sets.len(), t.get(2, 2)), ("parts", 4, 2, Some(885.0)));
    let p = templates::build(Some("hardness")).unwrap();
    let t = &p.tables[0];
    assert_eq!((t.kind.as_str(), t.rows, t.width(), t.row_titles[23].as_str(), p.analyses[0].kind.as_str()), ("multi", 24, 4, "S24", "multireg"));
    assert!((0..24).all(|r| t.get(r, 3).is_some()) && Table::multi(4, 0).rows == 1);
    let t = &templates::build(Some("worksheet")).unwrap().tables[0];
    assert_eq!((t.kind.as_str(), t.sets[0].role.as_str(), t.sets[2].role.as_str(), t.sets[3].formula.as_str(), t.get(0, 4).zip(t.get(0, 2)).map(|(k, c)| ((k - c) * 100.0).round())), ("sheet", "x", "yerr", "B + 273.15", Some(27315.0)));
    let p = templates::build(Some("hardmap")).unwrap();
    let t = &p.tables[0];
    assert_eq!((t.kind.as_str(), t.rows, t.sets.len(), t.sets[2].title.as_str(), p.analyses[0].kind.as_str(), p.graphs[0].settings.column.as_str()), ("matrix", 21, 9, "3", "surface", "contour"));
    assert_eq!((Table::matrix(0, 3).rows, Table::matrix(4, 3).sets[1].title.as_str()), (2, "2"));
    let p = templates::build(Some("batches")).unwrap();
    let t = &p.tables[0];
    assert_eq!((t.kind.as_str(), t.rows, t.width(), t.sets[2].reps, p.analyses[0].kind.as_str()), ("nested", 5, 10, 3, "nested"));
    assert!((1..10).all(|c| (0..5).all(|r| t.get(r, c).is_some())) && Table::nested(2, 0).sets[0].reps == 1);
    let p = templates::build(Some("corrosion")).unwrap();
    let t = &p.tables[0];
    assert_eq!((t.kind.as_str(), t.rows, t.width(), p.analyses[0].kind.as_str()), ("survival", 28, 3, "survival"));
    assert!((0..28).all(|r| t.get(r, 0).is_some_and(|h| h <= 1000.0) && t.get(r, 1 + r / 14).is_some() && t.get(r, 2 - r / 14).is_none()));
    assert!((0..28).any(|r| t.get(r, 1 + r / 14) == Some(0.0)), "some specimens outlast the test");
    for id in ["groups", "weibull"] {
        let p = templates::build(Some(id)).unwrap();
        assert!(p.tables[0].kind == "column" && p.tables[0].sets.iter().all(|s| s.reps == 1), "{id}");
    }
    assert!(l.iter().all(|t| t.dots.len() >= 2 && t.dots.iter().all(|(x, y)| (0.0..=1.0).contains(x) && (0.0..=1.0).contains(y))));
    let p = templates::build(Some("standard")).unwrap();
    assert_eq!((p.tables[0].sets[0].entry, p.tables[0].width()), (Entry::MeanSdN, 4));
    assert!(templates::build(Some("nope")).is_none());
}

#[test]
fn import_builds_a_table_with_titles_and_sets() {
    let (mut d, _) = doc();
    let rows: Vec<Vec<String>> = [vec!["Strain", "Sample 1", "", "Sample 2", ""], vec!["0", "0", "0.1", "0", "0.2"], vec!["0.01", "70", "72", "68", "x"]]
        .iter().map(|r| r.iter().map(|s| s.to_string()).collect()).collect();
    d.apply(Op::Import { name: "Tensile".into(), entry: Entry::Replicates, reps: 2, header: true, rows, graph: Some(Box::default()), dates: String::new() }).unwrap();
    let t = d.p.tables.last().unwrap();
    assert_eq!((t.name.as_str(), t.x_title.as_str(), t.rows, t.sets.len(), t.width()), ("Tensile", "Strain", 2, 2, 5));
    assert_eq!((t.sets[0].title.as_str(), t.sets[1].title.as_str()), ("Sample 1", "Sample 2"));
    assert_eq!((t.get(1, 0), t.get(1, 2), t.get(1, 4)), (Some(0.01), Some(72.0), None), "text that is not a number stays empty");
    assert_eq!(d.p.graphs.last().unwrap().table, t.id);
}

#[test]
fn analyses_are_linked_to_their_table_and_drawn_on_its_graphs() {
    let (mut d, id) = doc();
    let a = Analysis { table: id, kind: "linear".into(), options: serde_json::json!({ "model": "line" }), ..Default::default() };
    d.apply(Op::AddAnalysis { analysis: Box::new(a), overlay: true, graph: None }).unwrap();
    let aid = d.p.analyses[0].id;
    assert_eq!(d.p.analyses[0].name, "linear · Data 1");
    assert_eq!(d.p.graphs[0].settings.overlays, vec![aid]);
    assert!(!d.p.graphs[0].settings.line, "a fit replaces the joining lines");
    let mut b = d.p.analyses[0].clone();
    b.options = serde_json::json!({ "model": "origin" });
    b.table = 999;
    d.apply(Op::SetAnalysis { analysis: Box::new(b) }).unwrap();
    assert_eq!((d.p.analyses[0].options["model"].as_str(), d.p.analyses[0].table), (Some("origin"), id), "the table cannot change");
    d.apply(Op::Overlay { graph: d.p.graphs[0].id, analysis: aid, on: false }).unwrap();
    assert!(d.p.graphs[0].settings.overlays.is_empty());
    d.apply(Op::Overlay { graph: d.p.graphs[0].id, analysis: aid, on: true }).unwrap();
    d.apply(Op::Delete { id: aid }).unwrap();
    assert!(d.p.analyses.is_empty() && d.p.graphs[0].settings.overlays.is_empty(), "deleting removes the curves too");
    d.apply(Op::AddAnalysis { analysis: Box::new(Analysis { table: id, kind: "describe".into(), ..Default::default() }), overlay: false, graph: None }).unwrap();
    d.apply(Op::Duplicate { id, only: false }).unwrap();
    let t2 = d.p.tables[1].id;
    d.apply(Op::Delete { id }).unwrap();
    assert!(d.p.analyses.iter().all(|a| a.table == t2) && d.p.analyses.len() == 1, "a table's analyses go with it; the copy keeps its own (0.3.15)");
    assert!(d.p.table(t2).is_some());
}

#[test]
fn sort_moves_whole_rows_and_keeps_empty_rows_last() {
    let (mut d, id) = doc();
    d.apply(cells(id, &[(0, -1, "a"), (0, 0, "3"), (0, 1, "30"), (1, -1, "b"), (1, 0, "1"), (1, 1, "10"), (2, 0, "2"), (2, 1, "20"), (3, 1, "99")])).unwrap();
    d.apply(Op::Exclude { table: id, cells: vec![(0, 1)], on: true }).unwrap();
    d.apply(Op::Sort { table: id, col: 0, desc: false }).unwrap();
    let t = &d.p.tables[0];
    assert_eq!((0..4).map(|r| (t.get(r, 0), t.get(r, 1))).collect::<Vec<_>>(), vec![(Some(1.0), Some(10.0)), (Some(2.0), Some(20.0)), (Some(3.0), Some(30.0)), (None, Some(99.0))]);
    assert_eq!((t.row_titles[0].as_str(), t.row_titles[2].as_str(), t.excluded.clone()), ("b", "a", vec![[2, 1]]));
    d.apply(Op::Sort { table: id, col: 1, desc: true }).unwrap();
    assert_eq!(d.p.tables[0].get(0, 1), Some(99.0));
    assert!(d.apply(Op::Sort { table: id, col: 99, desc: false }).is_err());
}

#[test]
fn copy_look_keeps_titles_ranges_and_curves() {
    let (mut d, id) = doc();
    d.apply(Op::AddGraph { table: id, settings: None }).unwrap();
    let (a, b) = (d.p.graphs[0].id, d.p.graphs[1].id);
    let mut s = d.p.graphs[0].settings.clone();
    (s.font, s.font_size, s.palette, s.title, s.y.title, s.y.scale) = ("Times New Roman".into(), 7.0, "viridis".into(), "Mine".into(), "Force".into(), "log".into());
    d.apply(Op::GraphSet { graph: a, settings: Box::new(s) }).unwrap();
    let mut s = d.p.graphs[1].settings.clone();
    (s.title, s.overlays, s.notes) = ("Other".into(), vec![], vec![Note::default()]);
    s.y.title = "Stress".into();
    d.apply(Op::GraphSet { graph: b, settings: Box::new(s) }).unwrap();
    d.apply(Op::CopyLook { from: a, to: vec![b] }).unwrap();
    let g = &d.p.graphs[1].settings;
    assert_eq!((g.font.as_str(), g.font_size, g.palette.as_str(), g.y.scale.as_str()), ("Times New Roman", 7.0, "viridis", "log"));
    assert_eq!((g.title.as_str(), g.y.title.as_str(), g.notes.len()), ("Other", "Stress", 1), "notes stay with their graph");
    let a: Axis = serde_json::from_str(r#"{"breakFrom": 12, "breakTo": 95}"#).unwrap();
    let n: Note = serde_json::from_str(r#"{"kind": "arrow", "x": 1, "y2": 3, "text": "peak"}"#).unwrap();
    assert_eq!((n.kind.as_str(), n.x, n.y2, n.size, n.text.as_str()), ("arrow", 1.0, 3.0, 0.0, "peak"));
    assert_eq!((a.break_from, a.break_to, a.scale.as_str()), (Some(12.0), Some(95.0), "lin"));
}

#[test]
fn layouts_hold_graphs_and_lose_deleted_ones() {
    let (mut d, _) = doc();
    let gid = d.p.graphs[0].id;
    let items = vec![LayoutItem { graph: gid, ..Default::default() }, LayoutItem { kind: "text".into(), text: "Figure 1".into(), ..Default::default() }];
    d.apply(Op::AddLayout { layout: Box::new(Layout { items, ..Default::default() }) }).unwrap();
    let l = d.p.layouts[0].clone();
    assert_eq!((l.name.as_str(), l.items.len(), l.id > gid, l.align), ("Layout 1", 2, true, true));
    let it: LayoutItem = serde_json::from_str(r#"{"graph": 3, "inset": true, "hideX": true}"#).unwrap();
    assert!(it.inset && it.hide_x && it.kind == "graph");
    d.apply(Op::LayoutSet { layout: Box::new(Layout { width: 89.0, ..l.clone() }) }).unwrap();
    assert_eq!(d.p.layouts[0].width, 89.0);
    d.apply(Op::Duplicate { id: l.id, only: false }).unwrap();
    d.apply(Op::Rename { id: l.id, name: "Figure 1".into() }).unwrap();
    assert_eq!((d.p.layouts.len(), d.p.layouts[0].name.as_str()), (2, "Figure 1"));
    d.apply(Op::Delete { id: gid }).unwrap();
    assert!(d.p.layouts.iter().all(|l| l.items.len() == 1 && l.items[0].kind == "text"), "a deleted graph leaves its layouts");
    d.apply(Op::Delete { id: l.id }).unwrap();
    assert_eq!(d.p.layouts.len(), 1);
}

#[test]
fn projects_saved_with_copy_linked_still_open() {
    // 0.3.4 stored a linked picture name in each graph's settings; 0.3.5 removed the feature.
    let p = Project::from_json(r#"{"name":"old","tables":[{"id":1,"name":"T"}],"graphs":[{"id":2,"table":1,"name":"G","settings":{"linked":"G.png","width":90}}],"nextId":3}"#).unwrap();
    assert_eq!((p.graphs.len(), p.graphs[0].settings.width), (1, 90.0));
}

#[test]
fn factorial_designs_are_balanced_and_orthogonal() {
    let t = Table::design(3, false, 2, 3);
    assert_eq!((t.kind.as_str(), t.rows, t.sets.len(), t.sets[3].title.as_str()), ("multi", 19, 4, "Response"));
    for a in 1..=3 {
        let col: Vec<f64> = (0..16).map(|r| t.get(r, a).unwrap()).collect();
        assert_eq!(col.iter().sum::<f64>(), 0.0, "each factor is balanced");
        for b in a + 1..=3 {
            assert_eq!((0..16).map(|r| t.get(r, a).unwrap() * t.get(r, b).unwrap()).sum::<f64>(), 0.0, "factors are orthogonal");
        }
    }
    assert!((16..19).all(|r| (1..=3).all(|a| t.get(r, a) == Some(0.0))) && (0..19).all(|r| t.get(r, 4).is_none()));
    let mut order: Vec<String> = t.row_titles.clone();
    order.sort_by_key(|s| s[4..].parse::<usize>().unwrap());
    assert_eq!(order, (1..=19).map(|i| format!("Run {i}")).collect::<Vec<_>>(), "every run once in the random order");
    let h = Table::design(4, true, 1, 0);
    assert_eq!(h.rows, 8);
    assert!((0..8).all(|r| h.get(r, 4).unwrap() == h.get(r, 1).unwrap() * h.get(r, 2).unwrap() * h.get(r, 3).unwrap()), "D = ABC");
}

#[test]
fn dates_are_days_since_1970() {
    use crate::doc::{date_number, days_from_civil};
    let day = |s: &str| date_number(s, true);
    assert_eq!(days_from_civil(1970, 1, 1), Some(0.0));
    assert_eq!(days_from_civil(2026, 10, 12), Some(20738.0), "Datum Plan's sample: 20738 is 12 Oct 2026");
    for s in ["2026-11-05", "05/11/2026", "5-Nov-26", "5 Nov 2026", "Nov 5, 2026", "5 November 2026", "05.11.2026", "2026/11/05"] {
        assert_eq!(day(s), days_from_civil(2026, 11, 5), "{s}");
    }
    assert_eq!(date_number("11/05/2026", false), days_from_civil(2026, 11, 5), "month first");
    assert_eq!(day("2026-11-05 14:30"), Some(days_from_civil(2026, 11, 5).unwrap() + 14.5 / 24.0));
    assert_eq!(day("2026-11-05T06:00:00"), Some(days_from_civil(2026, 11, 5).unwrap() + 0.25));
    assert_eq!(day("1970-01-02 06:00"), Some(1.25), "the brief's example");
    assert_eq!(day("12:00"), Some(0.5), "a time alone is a fraction of a day");
    assert_eq!(day("2:30 pm"), Some(14.5 / 24.0));
    for bad in ["31 Feb 2026", "2026-02-29", "2026-13-01", "32/01/2026", "hello", "12", "2026-11-05 25:00", "1/2"] {
        assert_eq!(day(bad), None, "{bad}");
    }
    assert_eq!(day("29 Feb 2024"), days_from_civil(2024, 2, 29), "a leap day");
}

#[test]
fn a_date_column_reads_dates_and_old_files_stay_numbers() {
    let old = Project::from_json(r#"{"name":"old","tables":[{"id":1,"name":"T","cols":[[20738]]}],"nextId":2}"#).unwrap();
    assert_eq!(old.tables[0].x_format, "", "no xFormat: numbers, as before");
    let mut d = Doc::new(templates::build(Some("growth")).unwrap());
    let id = d.p.tables[0].id;
    d.apply(Op::XFormat { table: id, format: "date".into(), display: String::new() }).unwrap();
    d.apply(Op::Cells { table: id, cells: vec![(0, 0, "5-Nov-26".into()), (1, 0, "20738".into())] }).unwrap();
    assert_eq!((d.p.tables[0].get(0, 0), d.p.tables[0].get(1, 0)), (crate::doc::days_from_civil(2026, 11, 5), Some(20738.0)));
    d.undo();
    d.undo();
    assert_eq!(d.p.tables[0].x_format, "", "undo restores the number column");
    let hostile = Project::from_json(r#"{"name":"h","tables":[{"id":1,"name":"T","xFormat":"evil","xDisplay":"x"}],"nextId":2}"#).unwrap();
    assert_eq!((hostile.tables[0].x_format.as_str(), hostile.tables[0].x_display.as_str()), ("", ""));
    // Datum Plan's hand-off file opens with its dates flagged.
    let plan = r##"{"format":1,"name":"S","info":{"title":"Project S-curve","notes":"copy"},"tables":[{"id":1,"name":"Project S-curve","kind":"xy","xTitle":"Date","xUnits":"","xFormat":"date","yTitle":"Cumulative progress","yUnits":"%","rows":3,"rowTitles":["2026-10-12","2026-10-19","2026-10-26"],"sets":[{"title":"Planned (baseline)","entry":"rep","reps":1},{"title":"Actual","entry":"rep","reps":1}],"cols":[[20738,20745,20752],[0,12.5,31.0],[0,10.0,null]]}],"graphs":[{"id":2,"table":1,"name":"Project S-curve","settings":{"line":true,"error":"none","width":160,"height":100,"sets":[{"color":"#A3ABB8","symbol":"none","line":true},{"color":"#3B82F6","symbol":"none","line":true}]}}],"analyses":[],"layouts":[],"nextId":3,"ui":{}}"##;
    let p = Project::from_json(plan).unwrap();
    assert_eq!((p.tables[0].x_format.as_str(), p.tables[0].get(2, 0), p.graphs.len()), ("date", Some(20752.0), 1));
}

#[test]
fn date_axis_choices_are_kept_and_imports_read_dates() {
    // 0.3.11 lost the tick-label choice (the Axis had no field for it); 0.3.12 keeps it and the major step.
    let g: GraphSettings = serde_json::from_str(r#"{"x":{"dates":"monthyear","dateStep":"w2"}}"#).unwrap();
    assert_eq!((g.x.dates.as_str(), g.x.date_step.as_str()), ("monthyear", "w2"));
    assert!(serde_json::to_string(&g).unwrap().contains(r#""dateStep":"w2""#));
    let rows = vec![vec!["Date".into(), "DO".into()], vec!["2026-11-05".into(), "8.1".into()], vec!["12 Nov 2026".into(), "7.9".into()]];
    let mut d = Doc::new(Project::default());
    d.apply(Op::Import { name: "River".into(), entry: Entry::Replicates, reps: 1, header: true, rows: rows.clone(), graph: None, dates: "date".into() }).unwrap();
    let t = &d.p.tables[0];
    assert_eq!((t.x_format.as_str(), t.get(0, 0), t.get(1, 0)), ("date", crate::doc::days_from_civil(2026, 11, 5), crate::doc::days_from_civil(2026, 11, 12)));
    d.apply(Op::Import { name: "Numbers".into(), entry: Entry::Replicates, reps: 1, header: true, rows, graph: None, dates: String::new() }).unwrap();
    assert_eq!((d.p.tables[1].x_format.as_str(), d.p.tables[1].get(0, 0)), ("", None), "without the offer, dates stay empty as before");
}

#[test]
fn typing_in_a_table_made_in_code_works() {
    // #26: the start-up table (made from the options, not normalised) panicked on every typed value.
    let mut p = Project::new("P");
    p.add_table(Table { sets: vec![DataSet { title: "A".into(), ..Default::default() }], ..Default::default() }, None);
    let id = p.tables[0].id;
    let mut d = Doc::new(p);
    d.apply(Op::Cells { table: id, cells: vec![(0, 0, "1".into()), (0, 1, "2.5".into()), (3, 2, "7".into())] }).unwrap();
    assert_eq!((d.p.tables[0].get(0, 0), d.p.tables[0].get(0, 1), d.p.tables[0].get(3, 2)), (Some(1.0), Some(2.5), Some(7.0)));
    let mut raw = Table::default();
    raw.cols.clear();
    assert!(crate::doc::put_for_test(&mut raw, 2, 1, "4"), "even a table without columns takes a value");
}

#[test]
fn significance_goes_on_one_graph_and_duplicates_bring_the_family() {
    let mut d = Doc::new(templates::build(Some("groups")).unwrap());
    let t = d.p.tables[0].id;
    d.apply(Op::Duplicate { id: d.p.graphs[0].id, only: false }).unwrap();
    let (g1, g2) = (d.p.graphs[0].id, d.p.graphs[1].id);
    let before = d.p.graph(g2).unwrap().settings.overlays.clone();
    d.apply(Op::AddAnalysis { analysis: Box::new(Analysis { table: t, kind: "ttest".into(), ..Default::default() }), overlay: true, graph: Some(g1) }).unwrap();
    let a = d.p.analyses.last().unwrap().id;
    assert!(d.p.graph(g1).unwrap().settings.overlays.contains(&a), "#33: drawn on the graph it was made from");
    assert_eq!(d.p.graph(g2).unwrap().settings.overlays, before, "#33: and on no other graph of the table");
    // #32: the whole family, results included, the copied graph drawing the copied result; or the table alone.
    let (na, ng, nt) = (d.p.analyses.len(), d.p.graphs.len(), d.p.tables.len());
    d.apply(Op::Duplicate { id: t, only: false }).unwrap();
    let nt_id = d.p.tables.last().unwrap().id;
    assert_eq!((d.p.tables.len(), d.p.graphs.len(), d.p.analyses.len()), (nt + 1, ng * 2, na * 2));
    let copied: Vec<u32> = d.p.analyses.iter().filter(|x| x.table == nt_id).map(|x| x.id).collect();
    assert!(d.p.graphs.iter().filter(|g| g.table == nt_id).all(|g| g.settings.overlays.iter().all(|o| copied.contains(o))));
    d.apply(Op::Duplicate { id: t, only: true }).unwrap();
    let last = d.p.tables.last().unwrap().id;
    assert!(!d.p.graphs.iter().any(|g| g.table == last) && !d.p.analyses.iter().any(|a| a.table == last), "the table alone");
}

#[test]
fn an_embedded_graph_keeps_its_table_and_drawn_analyses() {
    let p = templates::build(Some("modulus")).unwrap();
    let g = &p.graphs[0];
    let e = p.graph_only(g.id).unwrap();
    assert_eq!((e.tables.len(), e.graphs.len(), e.graphs[0].id, e.tables[0].id), (1, 1, g.id, g.table));
    assert_eq!(e.analyses.len(), g.settings.overlays.len());
    assert!(e.analyses.iter().all(|a| a.table == g.table));
    let back = Project::from_json(&serde_json::to_string(&e).unwrap()).unwrap();
    assert_eq!(back.graphs[0].settings, g.settings, "the document's copy opens as it was");
    assert!(p.graph_only(999_999).is_none());
}

#[test]
fn break_position_and_ticks_are_kept_and_checked() {
    let p = Project::from_json(r#"{"name":"b","tables":[{"id":1,"name":"T"}],"graphs":[{"id":2,"table":1,"name":"G","settings":{"y":{"breakFrom":10,"breakTo":90,"breakRatio":7,"breakStep":-1},"x":{"breakRatio":0.25,"breakStep":5},"legend":{"groups":true}}}],"nextId":3}"#).unwrap();
    let s = &p.graphs[0].settings;
    assert_eq!((s.y.break_ratio, s.y.break_step), (Some(0.9), None), "kept within 10–90 %, no negative step");
    assert_eq!((s.x.break_ratio, s.x.break_step, s.legend.groups), (Some(0.25), Some(5.0), true));
    assert!(!Project::from_json(r#"{"name":"o","tables":[{"id":1,"name":"T"}],"graphs":[{"id":2,"table":1,"name":"G","settings":{}}],"nextId":3}"#).unwrap().graphs[0].settings.legend.groups, "older graphs: no group legend");
}

#[test]
fn older_graphs_keep_their_bar_colours_and_new_ones_are_independent() {
    // Before 0.3.21 a bar's fill and border followed the data set's colour: an older file keeps its look.
    let old = Project::from_json(r##"{"name":"o","tables":[{"id":1,"name":"T","kind":"column"}],"graphs":[{"id":2,"table":1,"name":"G","settings":{"sets":[{"color":"#123456"},{"color":"#abcdef","edge":"#000000"},{}]}}],"nextId":3}"##).unwrap();
    let s = &old.graphs[0].settings;
    assert_eq!((s.sets[0].fill.as_str(), s.sets[0].edge.as_str()), ("#123456", "#123456"));
    assert_eq!((s.sets[1].fill.as_str(), s.sets[1].edge.as_str()), ("#abcdef", "#000000"), "a border set by hand stays");
    assert!(s.sets[2].fill.is_empty() && s.colors2);
    // Saved again and reopened: converted once, never again (a symbol colour chosen later leaves the bars alone).
    let mut again = Project::from_json(&serde_json::to_string(&old).unwrap()).unwrap();
    again.graphs[0].settings.sets[2].color = "#ff0000".into();
    let back = Project::from_json(&serde_json::to_string(&again).unwrap()).unwrap();
    assert!(back.graphs[0].settings.sets[2].fill.is_empty(), "#38: the symbol colour no longer changes the bar");
    let alpha = Project::from_json(r##"{"name":"a","tables":[{"id":1,"name":"T"}],"graphs":[{"id":2,"table":1,"name":"G","settings":{"sets":[{"alpha":7}]}}],"nextId":3}"##).unwrap();
    assert_eq!(alpha.graphs[0].settings.sets[0].alpha, Some(1.0));
}

#[test]
fn older_graphs_keep_their_symbols_look() {
    // 0.4.2 (#42, #43): unfilled bars emptied the symbols too, and an automatic symbol border took the symbol's colour.
    let old = Project::from_json(r##"{"name":"o","tables":[{"id":1,"name":"T","kind":"column"}],"graphs":[{"id":2,"table":1,"name":"G","settings":{"colors2":true,"sets":[{"color":"#123456","filled":false},{"color":"#abcdef","markerEdge":"#000000"},{}]}}],"nextId":3}"##).unwrap();
    let s = &old.graphs[0].settings;
    assert_eq!((s.sets[0].marker_filled, s.sets[0].marker_edge.as_str()), (Some(false), "#123456"));
    assert_eq!((s.sets[1].marker_filled, s.sets[1].marker_edge.as_str()), (None, "#000000"), "a border set by hand stays");
    assert!(s.sets[2].marker_edge.is_empty() && s.colors3);
    // Converted once: a symbol colour chosen later leaves the automatic border to the scheme.
    let mut again = Project::from_json(&serde_json::to_string(&old).unwrap()).unwrap();
    again.graphs[0].settings.sets[2].color = "#ff0000".into();
    again.graphs[0].settings.sets[2].filled = false;
    let back = Project::from_json(&serde_json::to_string(&again).unwrap()).unwrap();
    assert!(back.graphs[0].settings.sets[2].marker_edge.is_empty() && back.graphs[0].settings.sets[2].marker_filled.is_none(), "#42, #43");
    let a = Project::from_json(r##"{"name":"a","tables":[{"id":1,"name":"T"}],"graphs":[{"id":2,"table":1,"name":"G","settings":{"sets":[{"edgeAlpha":-1,"markerAlpha":0.4,"markerEdgeAlpha":9,"errColor":"#111111"}]}}],"nextId":3}"##).unwrap();
    let st = &a.graphs[0].settings.sets[0];
    assert_eq!((st.edge_alpha, st.marker_alpha, st.marker_edge_alpha, st.err_color.as_str()), (Some(0.0), Some(0.4), Some(1.0), "#111111"));
}

#[test]
fn older_graphs_keep_their_error_bar_colours() {
    // 0.4.3 (#43): on bars, means and before-after graphs automatic error bars took the symbols' colour; on scatter
    // dot plots they were dark grey (nothing to keep).
    let json = |column: &str| format!(r##"{{"name":"o","tables":[{{"id":1,"name":"T","kind":"column"}}],"graphs":[{{"id":2,"table":1,"name":"G","settings":{{"colors2":true,"colors3":true,"column":"{column}","sets":[{{"color":"#123456"}},{{"color":"#abcdef","errColor":"#000000"}},{{}}]}}}}],"nextId":3}}"##);
    let p = Project::from_json(&json("bars")).unwrap();
    let s = &p.graphs[0].settings;
    assert_eq!((s.sets[0].err_color.as_str(), s.sets[1].err_color.as_str(), s.sets[2].err_color.as_str()), ("#123456", "#000000", ""));
    assert!(s.colors4);
    assert!(Project::from_json(&json("scatter")).unwrap().graphs[0].settings.sets[0].err_color.is_empty());
    // Converted once: a symbol colour chosen later leaves the automatic error bars to the scheme.
    let mut again = p.clone();
    again.graphs[0].settings.sets[2].color = "#ff0000".into();
    let back = Project::from_json(&serde_json::to_string(&again).unwrap()).unwrap();
    assert!(back.graphs[0].settings.sets[2].err_color.is_empty());
}

#[test]
fn symbol_borders_travel_as_marker_edge() {
    let p = Project::from_json(r##"{"name":"m","tables":[{"id":1,"name":"T"}],"graphs":[{"id":2,"table":1,"name":"G","settings":{"sets":[{"markerEdge":"#010203"}]}}],"nextId":3}"##).unwrap();
    assert_eq!(p.graphs[0].settings.sets[0].marker_edge, "#010203");
    assert!(serde_json::to_string(&p).unwrap().contains(r##""markerEdge":"#010203""##));
}

#[test]
fn digitized_points_become_a_table() {
    use crate::digitize::{table, value, Calib, Mark, Traced};
    // A picture where X 0..10 spans pixels 100..600 and Y 0..50 spans pixels 400..100 (pixels grow downwards).
    let c = Calib { x: [Mark { px: 100.0, py: 400.0, value: 0.0 }, Mark { px: 600.0, py: 400.0, value: 10.0 }], y: [Mark { px: 100.0, py: 400.0, value: 0.0 }, Mark { px: 100.0, py: 100.0, value: 50.0 }], xlog: false, ylog: false };
    let sets = vec![Traced { title: "A".into(), points: vec![(350.0, 250.0), (100.0, 400.0)] }, Traced { title: "B".into(), points: vec![(600.0, 100.0)] }];
    let t = table("Paper fig 2", &c, &sets).unwrap();
    assert_eq!((t.rows, t.sets.len(), t.name.as_str()), (3, 2, "Paper fig 2"));
    assert_eq!((t.get(0, 0), t.get(0, 1), t.get(1, 0), t.get(1, 1)), (Some(0.0), Some(0.0), Some(5.0), Some(25.0)), "sorted by X within the set");
    assert_eq!((t.get(2, 0), t.get(2, 1), t.get(2, 2)), (Some(10.0), None, Some(50.0)));
    // A tilted scan (2° turn): a point on the X axis still reads its value.
    let a = std::f64::consts::PI / 90.0;
    let rot = |x: f64, y: f64| (x * a.cos() - y * a.sin(), x * a.sin() + y * a.cos());
    let (p0, p1, q) = (rot(0.0, 0.0), rot(500.0, 0.0), rot(250.0, 0.0));
    let v = value(&Mark { px: p0.0, py: p0.1, value: 0.0 }, &Mark { px: p1.0, py: p1.1, value: 10.0 }, false, q).unwrap();
    assert!((v - 5.0).abs() < 1e-9);
    // A log axis: halfway between 1 and 100 is 10.
    let l = value(&Mark { px: 0.0, py: 0.0, value: 1.0 }, &Mark { px: 100.0, py: 0.0, value: 100.0 }, true, (50.0, 0.0)).unwrap();
    assert!((l - 10.0).abs() < 1e-9);
    // Mistakes say what to do.
    let same = Calib { x: [c.x[0], Mark { value: 0.0, ..c.x[1] }], ..c.clone() };
    assert!(table("", &same, &sets).unwrap_err().contains("different values"));
    let logneg = Calib { xlog: true, ..c.clone() };
    assert!(table("", &logneg, &sets).unwrap_err().contains("above zero"));
    assert!(table("", &c, &[]).unwrap_err().contains("Click some points"));
    let mut d = Doc::new(Project::new("P"));
    d.apply(Op::Digitize { name: "Fig".into(), calib: c, sets, graph: Some(Box::default()) }).unwrap();
    assert_eq!((d.p.tables.len(), d.p.graphs.len()), (1, 1));
}
