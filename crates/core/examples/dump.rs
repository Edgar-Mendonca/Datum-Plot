//! Writes the JSON the window gets for a sample project, for the UI tests:
//! cargo run -p datum-core --example dump > tests_ui/fixture.json
fn main() {
    let id = std::env::args().nth(1).unwrap_or_else(|| "growth".into());
    let p = datum_core::templates::build(Some(&id)).unwrap();
    let out = serde_json::json!({
        "state": { "project": p, "path": null, "dirty": false, "undo": false, "redo": false, "rev": 1 },
        "templates": datum_core::templates::list(),
    });
    println!("{}", serde_json::to_string(&out).unwrap());
}
