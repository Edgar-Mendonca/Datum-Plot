# Contributing

Thank you for helping. Datum Plot is MIT-licensed; by contributing you agree your work is shared under the same licence.

## Layout

- `crates/core`: the project model, edits, undo and files (Rust, unit-tested; `src/hardening.rs` holds the robustness tests).
- `py/datum`: every calculation, fit and graph (Python with numpy, SciPy and matplotlib; tested against NIST and R values).
- `src-tauri`: the Windows shell (Tauri 2) that joins the two and runs the Python engine.
- `ui/src`: the window (SolidJS + Vite). It only shows what the engines compute.

## Checks before a pull request

```
pip install -r py/requirements.txt
python -m unittest discover -s py/tests
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
npm ci && npm run check:ui && npm run build:ui
npm run test:ui
cargo deny check
npm audit --audit-level=high
pip-audit -r py/requirements.txt
```

## Style

Small, compact code that matches what is around it. New statistics go in `py/datum` with a test against a published
reference value; new edits go in `crates/core` as an `Op` with a test, so they are undoable. Report security problems
privately, as `SECURITY.md` explains.
