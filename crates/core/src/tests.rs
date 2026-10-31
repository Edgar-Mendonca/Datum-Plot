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
    d.apply(Op::Duplicate { id }).unwrap();
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
        Op::Delete { id: 12345 }, Op::Rename { id: 12345, name: "x".into() }, Op::Duplicate { id: 12345 },
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
    assert_eq!(l.len(), 24);
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
    d.apply(Op::Import { name: "Tensile".into(), entry: Entry::Replicates, reps: 2, header: true, rows, graph: Some(Box::default()) }).unwrap();
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
    d.apply(Op::AddAnalysis { analysis: Box::new(a), overlay: true }).unwrap();
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
    d.apply(Op::AddAnalysis { analysis: Box::new(Analysis { table: id, kind: "describe".into(), ..Default::default() }), overlay: false }).unwrap();
    d.apply(Op::Duplicate { id }).unwrap();
    let t2 = d.p.tables[1].id;
    d.apply(Op::Delete { id }).unwrap();
    assert!(d.p.analyses.is_empty(), "a table's analyses go with it");
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
    d.apply(Op::Duplicate { id: l.id }).unwrap();
    d.apply(Op::Rename { id: l.id, name: "Figure 1".into() }).unwrap();
    assert_eq!((d.p.layouts.len(), d.p.layouts[0].name.as_str()), (2, "Figure 1"));
    d.apply(Op::Delete { id: gid }).unwrap();
    assert!(d.p.layouts.iter().all(|l| l.items.len() == 1 && l.items[0].kind == "text"), "a deleted graph leaves its layouts");
    d.apply(Op::Delete { id: l.id }).unwrap();
    assert_eq!(d.p.layouts.len(), 1);
}

#[test]
fn linked_pictures_stay_in_their_folder_and_are_never_shared() {
    use crate::model::{pictures_dir, safe_picture};
    assert!(safe_picture("Growth (2).png") && !safe_picture("Courbe d’été.png") && safe_picture("Été.png"));
    for bad in ["../x.png", "..\\x.png", "C:\\x.png", "a/b.png", ".png", " x.png", "x.exe", "x.png.exe", &format!("{}.png", "a".repeat(120))] {
        assert!(!safe_picture(bad), "{bad}");
    }
    assert_eq!(pictures_dir(std::path::Path::new("/data/Strain study.dplot")), std::path::PathBuf::from("/data/Strain study pictures"));
    let mut p = templates::build(Some("growth")).unwrap();
    let id = p.graphs[0].id;
    assert_eq!(p.picture_name(id), "Growth.png");
    p.graphs[0].settings.linked = "Growth.png".into();
    let mut d = Doc::new(p);
    d.apply(Op::Duplicate { id }).unwrap();
    let copy = d.p.graphs.iter().find(|g| g.id != id).unwrap();
    assert_eq!((copy.settings.linked.as_str(), d.p.graphs[0].settings.linked.as_str()), ("", "Growth.png"), "a duplicate does not take over the original's picture");
    assert_eq!(d.p.picture_name(copy.id), "Growth copy.png");
    let hostile = r#"{"name":"h","tables":[{"id":1,"name":"T"}],"graphs":[{"id":2,"table":1,"name":"G","settings":{"linked":"../../evil.png"}},{"id":3,"table":1,"name":"H","settings":{"linked":"ok.png"}},{"id":4,"table":1,"name":"I","settings":{"linked":"OK.png"}}],"nextId":5}"#;
    let p = Project::from_json(hostile).unwrap();
    assert_eq!(p.graphs.iter().map(|g| g.settings.linked.as_str()).collect::<Vec<_>>(), ["", "ok.png", ""], "paths and shared names are dropped on loading");
}
