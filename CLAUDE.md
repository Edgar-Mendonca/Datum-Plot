# Datum Plot: notes for Claude

Read `docs/MEMORY.md` first. It is the project's memory: architecture, decisions, roadmap, and a log of every session.
Datum Plot is the second app of the Datum family. Follow `docs/FAMILY.md` in `Edgar-Mendonca/Datum-Plan` exactly (add that repo read-only); Datum Plan's code is the reference implementation: copy from it rather than reinventing anything.

At the end of every session that changes anything, update `docs/MEMORY.md`:
- tick the roadmap
- add a session-log entry
- record any new decisions
- refresh the architecture section if files moved

User preferences:
- Rust and Tauri 2 for the shell and the project engine, SolidJS for the window, **Python (numpy, SciPy, matplotlib) inside the app** for every calculation and graph (the user's decision; it overrides FAMILY §2 for Datum Plot). Small, efficient, robust code. Windows first; the installer bundles embeddable CPython 3.13.
- Ship in **consecutive releases** (0.2.0, 0.2.1, 0.2.2 … no jumped numbers), always three numbers; every release appears in the in-app updater. Since session 8 the user wants **small steps again** (one to four features per release, to save tokens and finish quickly); the order is in `docs/PLAN-0.2.md` §12 and the MEMORY roadmap. Check `git fetch` before releasing: another session may have shipped the next number.
- The family look with the **Teal** accent (FAMILY §3): MS Office ribbon, Cairn-style sidebar, IBM Plex, square controls, light/dark/auto themes.
- Prism's linked chain (data table → analysis → results → graph → layout) with OriginPro's power.
- Keep code compact and match the surrounding style. The project model, edit ops, undo and files belong in `crates/core` (Rust, unit-tested). Statistics, fitting and drawing belong in `py/datum` (Python, unit-tested against NIST/R values). Never in the UI.
- The UI is SolidJS + Vite in `ui/src/*.tsx` (built to `ui/dist`). State lives in `ui/src/store.ts`; the engine computes all values, the window only shows them.
- Big asks get a `docs/PLAN-x.y.md` with questions first; build after the answers. Report in plain language.
- The feature catalogue lives in `docs/PLAN-0.2.md` (IDs A1–J5; release order in §12) and in the app in `ui/src/features.ts` (Help › Roadmap; planned commands open their card). When a feature ships: set its release in `features.ts` to the shipping version (and `VERSION_NOW`), replace its planned command with the real one, tick it in PLAN-0.2 and the MEMORY roadmap. New ideas get an ID in both.
- When `py/requirements.txt` changes, bump `py/runtime.txt` so installed apps download the new Python runtime pack.

Identity: "Datum Plot", `.dplot`, `com.edgarmendonca.datumplot`, `REPO = "Edgar-Mendonca/Datum-Plot"` in `src-tauri/src/update.rs`, installer `DatumPlot-x.y.z-setup.exe`.

Checks before pushing:
- `python -m unittest discover -s py/tests` (needs `pip install -r py/requirements.txt`)
- `cargo clippy --workspace --all-targets -- -D warnings`
- `cargo test --workspace`
- `npm run check:ui`
- UI tests: `npm run test:ui` (Playwright against `ui/dist` with the `dump` fixture)
- `cargo deny check` (advisories, licences, sources; `deny.toml`, also a CI job)

Releasing:
1. Bump the version in `src-tauri/Cargo.toml` and `crates/core/Cargo.toml`.
2. Add a CHANGELOG section (`## x.y.z — date`, a one-line summary, bold sections in plain language).
   Update `docs/site.json` (FAMILY §10: about, steps, highlights, roadmap with Next/Soon/Later/Goal) together with the MEMORY roadmap. Public text (CHANGELOG, README, site.json) never names, compares with or claims to copy a commercial product (FAMILY §13); name file formats by extension. Bump `version` and `date-released` in `CITATION.cff`.
3. Push the tag `vX.Y.Z`, or run `release.yml` with workflow_dispatch when tag pushes are blocked. The workflow creates the tag and publishes **one** installer (`DatumPlot-x.y.z-setup.exe`, Python inside) and `SHA256SUMS.txt`. No extra update or runtime files (the user's rule).
