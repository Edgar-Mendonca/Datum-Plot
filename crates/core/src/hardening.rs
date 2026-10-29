//! The hardening standard (FAMILY §11): failed edits change nothing; random documents and random edit
//! sequences never panic and keep their invariants; damaged files open or give an error; a speed gate on a
//! large document; hostile values are clamped on loading.
use crate::doc::{Doc, Op};
use crate::*;

/// A small repeatable generator (no extra crate).
struct Rng(u64);
impl Rng {
    fn next(&mut self) -> u64 {
        self.0 = self.0.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        self.0 >> 33
    }
    fn below(&mut self, n: u64) -> u64 {
        self.next() % n.max(1)
    }
    fn pick<'a, T>(&mut self, v: &'a [T]) -> &'a T {
        &v[self.below(v.len() as u64) as usize]
    }
    fn value(&mut self) -> serde_json::Value {
        match self.below(6) {
            0 => serde_json::Value::Null,
            1 => serde_json::json!(-1e308),
            2 => serde_json::json!(u32::MAX),
            _ => serde_json::json!(self.below(1000) as f64 / 7.0),
        }
    }
}

/// Everything the window and the engine rely on.
fn invariants(p: &Project) {
    let mut ids: Vec<u32> = p.tables.iter().map(|t| t.id).chain(p.graphs.iter().map(|g| g.id)).chain(p.analyses.iter().map(|a| a.id)).chain(p.layouts.iter().map(|l| l.id)).collect();
    let n = ids.len();
    ids.sort_unstable();
    ids.dedup();
    assert_eq!(ids.len(), n, "ids are unique");
    assert!(ids.iter().all(|&i| i > 0 && i < p.next_id && i < ID_LIMIT), "ids below next_id");
    for t in &p.tables {
        assert!(t.rows >= 1 && t.rows <= MAX_ROWS && t.sets.len() <= MAX_SETS && t.rows * t.width() <= MAX_CELLS.max(t.width()));
        assert_eq!(t.cols.len(), t.width());
        assert!(t.cols.iter().all(|c| c.len() == t.rows) && t.row_titles.len() == t.rows);
        assert!(t.sets.iter().all(|s| (1..=50).contains(&s.reps)));
        assert!(t.excluded.iter().all(|[r, c]| *r < t.rows && *c < t.width()));
    }
    for g in &p.graphs {
        assert!(p.table(g.table).is_some(), "a graph's table exists");
        assert!(g.settings.overlays.iter().all(|o| p.analyses.iter().any(|a| a.id == *o && a.table == g.table)));
        assert!(g.settings.width.is_finite() && (10.0..=1000.0).contains(&g.settings.width) && (4.0..=96.0).contains(&g.settings.font_size));
    }
    assert!(p.analyses.iter().all(|a| p.table(a.table).is_some() && a.options.is_object()));
    for l in &p.layouts {
        assert!((20.0..=2000.0).contains(&l.width) && l.items.iter().all(|i| i.kind != "graph" || p.graphs.iter().any(|g| g.id == i.graph)));
    }
}

/// A random, often nonsensical project as JSON (what a damaged or hand-made file could hold).
fn random_doc(r: &mut Rng) -> String {
    let kinds = ["xy", "column", "grouped", "contingency", "parts", "multi", "survival", "nested", "sheet", "matrix", "nonsense"];
    let entries = ["rep", "msn", "mesn"];
    let ids: Vec<u32> = (0..8).map(|_| *r.pick(&[0, 1, 2, 3, 7, u32::MAX, u32::MAX - 1, 1 << 30])).collect();
    let tables: Vec<serde_json::Value> = (0..r.below(4)).map(|i| {
        let sets: Vec<serde_json::Value> = (0..r.below(5)).map(|_| serde_json::json!({ "title": "S", "entry": r.pick(&entries), "reps": *r.pick(&[0u64, 1, 3, 51, 1 << 40]) })).collect();
        let cols: Vec<serde_json::Value> = (0..r.below(8)).map(|_| serde_json::Value::Array((0..r.below(9)).map(|_| r.value()).collect())).collect();
        serde_json::json!({ "id": ids[i as usize], "name": "T", "kind": r.pick(&kinds), "rows": if r.below(40) == 0 { *r.pick(&[3_000_000, u32::MAX as u64]) } else { *r.pick(&[0u64, 1, 5, 40]) }, "sets": sets, "cols": cols,
            "excluded": [[r.below(9), r.below(9)], [u32::MAX, 0]], "rowTitles": ["a"] })
    }).collect();
    let graphs: Vec<serde_json::Value> = (0..r.below(4)).map(|i| serde_json::json!({ "id": ids[4 + i as usize], "table": r.pick(&ids), "name": "G",
        "settings": { "width": *r.pick(&[-5.0, 0.0, 80.0, 1e300]), "fontSize": *r.pick(&[0.0, 10.0, 1e9]), "overlays": [r.pick(&ids), 99], "levels": u32::MAX, "elev": 1e300 } })).collect();
    let analyses = vec![serde_json::json!({ "id": r.pick(&ids), "table": r.pick(&ids), "name": "A", "kind": "linear", "options": *r.pick(&[serde_json::json!(5), serde_json::json!({})]) })];
    let layouts = vec![serde_json::json!({ "id": r.pick(&ids), "name": "L", "width": *r.pick(&[-1.0, 0.0, 1e12]), "items": [{ "kind": "graph", "graph": r.pick(&ids) }] })];
    serde_json::json!({ "name": "R", "nextId": r.pick(&ids), "tables": tables, "graphs": graphs, "analyses": analyses, "layouts": layouts }).to_string()
}

fn random_op(r: &mut Rng, p: &Project) -> Op {
    let t = p.tables.first().map_or(1, |t| t.id);
    let big = *r.pick(&[0usize, 1, 3, 12, 999, usize::MAX]);
    let col = *r.pick(&[-1i64, 0, 1, 2, 7, 5000, i64::MAX]);
    match r.below(12) {
        0 => Op::Cells { table: t, cells: vec![(big % 40, col, (*r.pick(&["1", "x", "", "1e400", "-0", "12%", "NaN"])).into())] },
        1 => Op::Paste { table: t, row: big % 50, col, rows: vec![vec!["Time".into(), "A".into()], vec!["1".into(), "2".into()]] },
        2 => Op::Rows { table: t, at: big, count: *r.pick(&[-3i64, 2, i64::MIN, 50]) },
        3 => Op::Sort { table: t, col: big % 9, desc: r.below(2) == 1 },
        4 => Op::Exclude { table: t, cells: vec![(big % 30, big % 9)], on: true },
        5 => Op::SetDef { table: t, k: [None, Some(0), Some(big)][r.below(3) as usize], set: if r.below(3) == 0 { None } else { Some(DataSet { reps: big.min(80), ..Default::default() }) } },
        6 => Op::NewTable { table: Box::new(Table::column(1 + r.below(3) as usize)), graph: Some(Box::new(GraphSettings::default())) },
        7 => Op::Delete { id: *r.pick(&[t, 0, 99]) },
        8 => Op::Duplicate { id: *r.pick(&[t, 0, 99]) },
        9 => Op::Formula { table: t, k: Some(big % 4), formula: Some("A".into()), sets: vec![(big % 4, vec![Some(1.0); big % 7])] },
        10 => Op::AddAnalysis { analysis: Box::new(Analysis { table: t, kind: "linear".into(), ..Default::default() }), overlay: r.below(2) == 1 },
        _ => Op::Batch(vec![Op::Rename { id: t, name: "B".into() }, Op::Rows { table: t, at: 0, count: 1 }]),
    }
}

#[test]
fn a_failed_edit_leaves_the_document_as_it_was() {
    let mut d = Doc::new(templates::build(Some("growth")).unwrap());
    let (before, undo) = (d.json(), d.can_undo());
    let id = d.p.tables[0].id;
    for op in [Op::Sort { table: id, col: 999, desc: false }, Op::Delete { id: 4242 }, Op::Rows { table: id, at: 0, count: -1_000_000 },
               Op::Batch(vec![Op::Rename { id, name: "half".into() }, Op::Delete { id: 4242 }]), Op::Formula { table: id, k: None, formula: None, sets: vec![(77, vec![])] }] {
        assert!(d.apply(op).is_err());
        assert_eq!((d.json(), d.can_undo()), (before.clone(), undo), "nothing changed, not even half a batch");
    }
}

#[test]
fn random_documents_never_panic_and_keep_their_invariants() {
    let mut r = Rng(7);
    for _ in 0..300 {
        let text = random_doc(&mut r);
        if let Ok(p) = Project::from_json(&text) {
            invariants(&p);
            let again = Project::from_json(&serde_json::to_string(&p).unwrap()).unwrap();
            assert_eq!(again, p, "a loaded project saves and loads unchanged");
        }
    }
}

#[test]
fn random_edit_sequences_keep_the_invariants_and_undo_all_the_way() {
    let mut r = Rng(11);
    for _ in 0..30 {
        let mut d = Doc::new(templates::build(Some(*r.pick(&["growth", "groups", "twoway", "worksheet", "hardmap", "corrosion"]))).unwrap());
        let start = d.json();
        for _ in 0..40 {
            let op = random_op(&mut r, &d.p);
            let _ = d.apply(op);
            invariants(&d.p);
        }
        while d.can_undo() {
            d.undo();
        }
        assert_eq!(d.json(), start, "undo goes back to the start");
    }
}

#[test]
fn damaged_files_open_or_give_an_error() {
    let good = serde_json::to_string(&templates::build(Some("twoway")).unwrap()).unwrap();
    let mut r = Rng(3);
    for i in 0..300 {
        let mut b = good.clone().into_bytes();
        match i % 3 {
            0 => b.truncate(r.below(b.len() as u64) as usize),
            1 => for _ in 0..5 { let k = r.below(b.len() as u64) as usize; b[k] = r.below(256) as u8; },
            _ => { let k = r.below(b.len() as u64) as usize; b.splice(k..k, b"[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[".iter().copied()); }
        }
        if let Ok(p) = Project::from_json(&String::from_utf8_lossy(&b)) {
            invariants(&p);
        }
    }
    let dir = std::env::temp_dir().join(format!("datum-hardening-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    for (name, bytes) in [("empty.dplot", &b""[..]), ("binary.dplot", &[0u8, 159, 146, 150, 255][..]), ("text.dplot", b"hello"), ("newer.dplot", br#"{"format":999}"#)] {
        let f = dir.join(name);
        std::fs::write(&f, bytes).unwrap();
        assert!(Doc::open(&f).is_err(), "{name}");
    }
    assert!(Doc::open(&dir.join("missing.dplot")).is_err());
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn atomic_saves_leave_no_half_file() {
    let dir = std::env::temp_dir().join(format!("datum-atomic-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let f = dir.join("p.dplot");
    let mut d = Doc::new(templates::build(Some("growth")).unwrap());
    d.save(&f).unwrap();
    let first = std::fs::read_to_string(&f).unwrap();
    d.apply(Op::ProjectName { name: "Second".into() }).unwrap();
    d.save(&f).unwrap();
    assert!(Doc::open(&f).unwrap().p.name == "Second" && first != std::fs::read_to_string(&f).unwrap());
    assert_eq!(std::fs::read_dir(&dir).unwrap().count(), 1, "no temporary file left behind");
    assert!(crate::doc::write_atomic(&dir.join("no/such/folder/x"), b"x").is_err());
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn hostile_values_are_clamped_on_loading() {
    let p = Project::from_json(r#"{"name":"h","nextId":4294967295,"tables":[{"id":4294967295,"name":"T","rows":3,"sets":[{"title":"A","entry":"rep","reps":1}]},{"id":4294967295,"name":"U"}],
        "graphs":[{"id":4294967294,"table":4294967295,"settings":{"width":-3,"height":1e308,"fontSize":0,"cap":-1,"levels":4000000000,"elev":1e300,"sets":[{"size":-9,"width":1e9}]}}],
        "layouts":[{"id":0,"width":-5,"height":1e300,"items":[{"kind":"graph","graph":4294967294}]}]}"#).unwrap();
    invariants(&p);
    let mut p = p;
    let a = p.take_id();
    assert!(a < ID_LIMIT && p.next_id > a, "new ids keep counting from a sane place");
    let g = &p.graphs[0].settings;
    assert_eq!((g.width, g.height, g.font_size, g.cap, g.levels, g.elev, g.sets[0].size, g.sets[0].width), (10.0, 1000.0, 4.0, 0.0, 200, 90.0, 0.0, 20.0));
    assert_eq!(p.layouts[0].items.len(), 1, "the layout keeps its graph across the renumbering");
}

#[test]
fn speed_gate_on_a_large_document() {
    // A million-row table: typing a value (a whole copy for undo, then a comparison) must stay quick.
    let mut d = Doc::new(Project::new("big"));
    let mut t = Table::column(2);
    t.rows = MAX_ROWS;
    t.normalize();
    for c in 1..t.cols.len() {
        t.cols[c] = (0..MAX_ROWS).map(|i| Some(i as f64)).collect();
    }
    d.apply(Op::NewTable { table: Box::new(t), graph: None }).unwrap();
    let id = d.p.tables[0].id;
    let start = std::time::Instant::now();
    for i in 0..5 {
        d.apply(Op::Cells { table: id, cells: vec![(i, 1, "42".into())] }).unwrap();
    }
    let each = start.elapsed() / 5;
    let limit = if cfg!(debug_assertions) { 3000 } else { 250 }; // room for slower CI machines
    assert!(each.as_millis() < limit, "one edit of a million-row table took {each:?} (limit {limit} ms)");
    let s = std::time::Instant::now();
    let json = d.json();
    assert!(Project::from_json(&json).is_ok() && s.elapsed().as_secs() < if cfg!(debug_assertions) { 30 } else { 5 }, "saving and opening it took {:?}", s.elapsed());
}
