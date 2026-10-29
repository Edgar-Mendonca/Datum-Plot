//! Writes the JSON the window gets for a sample project, for the UI tests:
//! cargo run -p datum-core --example dump > tests_ui/fixture.json
//! `dump all` writes every template's project instead, for the engine smoke test (py/tests/smoke.py).
fn main() {
    let id = std::env::args().nth(1).unwrap_or_else(|| "growth".into());
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
