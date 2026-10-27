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
    d.apply(Op::SetDef { table: id, k: Some(0), set: Some(DataSet { title: "A".into(), entry: Entry::Replicates, reps: 2 }) }).unwrap();
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
fn templates_make_sense() {
    let l = templates::list();
    assert_eq!(l.len(), 11);
    for (id, n) in [("modulus", 2), ("arrhenius", 1), ("groups", 1), ("dsc", 1), ("twoway", 1)] {
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
    (s.title, s.overlays) = ("Other".into(), vec![]);
    s.y.title = "Stress".into();
    d.apply(Op::GraphSet { graph: b, settings: Box::new(s) }).unwrap();
    d.apply(Op::CopyLook { from: a, to: vec![b] }).unwrap();
    let g = &d.p.graphs[1].settings;
    assert_eq!((g.font.as_str(), g.font_size, g.palette.as_str(), g.y.scale.as_str()), ("Times New Roman", 7.0, "viridis", "log"));
    assert_eq!((g.title.as_str(), g.y.title.as_str()), ("Other", "Stress"));
}
