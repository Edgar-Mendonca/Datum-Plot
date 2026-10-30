//! Writes the JSON the window gets for a sample project, for the UI tests:
//! cargo run -p datum-core --example dump > tests_ui/fixture.json
//! `dump all` writes every template's project instead, for the engine smoke test (py/tests/smoke.py);
//! `dump guide` a project with several samples and a figure, for the guide's screenshots (tests_ui/guide_shots.cjs).
use datum_core::model::*;

/// Several samples in one project (ids renumbered), a curve fit on the first and a two-panel figure.
fn guide() -> Project {
    let mut p = datum_core::templates::build(Some("growth")).unwrap();
    p.name = "Strain study".into();
    let (t0, g0) = (p.tables[0].id, p.graphs[0].id);
    let a = p.take_id();
    p.analyses.push(Analysis { id: a, table: t0, name: "Logistic fit".into(), kind: "fit".into(), sets: vec![], options: serde_json::json!({ "model": "logistic" }) });
    p.graphs[0].settings.overlays.push(a);
    let mut panels = vec![g0];
    for id in ["groups", "hardmap", "trial"] {
        let q = datum_core::templates::build(Some(id)).unwrap();
        let mut map = std::collections::HashMap::new();
        for t in &q.tables {
            let mut t = t.clone();
            t.id = p.take_id();
            map.insert(q.tables.iter().find(|x| x.name == t.name).unwrap().id, t.id);
            p.tables.push(t);
        }
        for x in &q.analyses {
            let n = p.take_id();
            map.insert(x.id, n);
            p.analyses.push(Analysis { id: n, table: map[&x.table], ..x.clone() });
        }
        for g in &q.graphs {
            let mut g = g.clone();
            g.id = p.take_id();
            g.table = map[&g.table];
            g.settings.overlays = g.settings.overlays.iter().map(|o| map[o]).collect();
            if id == "groups" { panels.push(g.id); }
            p.graphs.push(g);
        }
    }
    let lid = p.take_id();
    p.layouts.push(serde_json::from_value(serde_json::json!({ "id": lid, "name": "Figure 1", "width": 174, "height": 70, "letters": "A", "letterSize": 10, "font": "Arial", "fontSize": 8,
        "items": [{ "kind": "graph", "graph": panels[0], "x": 0, "y": 0, "w": 85, "h": 70 }, { "kind": "graph", "graph": panels[1], "x": 89, "y": 0, "w": 85, "h": 70 }] })).unwrap());
    p.normalize();
    p
}

fn main() {
    let id = std::env::args().nth(1).unwrap_or_else(|| "growth".into());
    if id == "guide" {
        let out = serde_json::json!({
            "state": { "project": guide(), "path": "C:\\Users\\you\\Documents\\Strain study.dplot", "dirty": false, "undo": true, "redo": false, "rev": 1 },
            "templates": datum_core::templates::list(),
        });
        return println!("{}", serde_json::to_string(&out).unwrap());
    }
    if id == "all" {
        let all: Vec<_> = datum_core::templates::list().iter().map(|t| datum_core::templates::build(Some(t.id)).unwrap()).collect();
        return println!("{}", serde_json::to_string(&all).unwrap());
    }
    let p = datum_core::templates::build(Some(&id)).unwrap();
    let out = serde_json::json!({
        "state": { "project": p, "path": null, "dirty": false, "undo": false, "redo": false, "rev": 1 },
        "templates": datum_core::templates::list(),
    });
    println!("{}", serde_json::to_string(&out).unwrap());
}
