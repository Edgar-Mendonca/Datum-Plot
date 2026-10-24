# Datum Plot: notes for Claude

Read `docs/MEMORY.md` first. It is the project's memory: architecture, decisions, roadmap, and a log of every session.
Datum Plot is the second app of the Datum family. Follow `docs/FAMILY.md` in `Edgar-Mendonca/Datum-Plan` exactly (add that repo read-only); Datum Plan's code is the reference implementation: copy from it rather than reinventing anything.

At the end of every session that changes anything, update `docs/MEMORY.md`:
- tick the roadmap
- add a session-log entry
- record any new decisions
- refresh the architecture section if files moved

User preferences:
- Rust and Tauri 2, small and efficient code, Windows first. No Python inside the app.
- Ship in small numbered releases (0.1.0, 0.1.1, …), always three numbers. Every release appears in the in-app updater.
- The family look with the **Teal** accent (FAMILY §3): MS Office ribbon, Cairn-style sidebar, IBM Plex, square controls, light/dark/auto themes.
- Prism's linked chain (data table → analysis → results → graph → layout) with OriginPro's power.
- Keep code compact and match the surrounding style. Engine logic (statistics, fitting, scales, ticks) belongs in `crates/core` (pure Rust, unit-tested against NIST/R values), not in the UI.
- The UI is SolidJS + Vite in `ui/src/*.tsx` (built to `ui/dist`). State lives in `ui/src/store.ts`; the engine computes all values, the window only shows them.
- Big asks get a `docs/PLAN-x.y.md` with questions first; build after the answers. Report in plain language.

Identity: "Datum Plot", `.dplot`, `com.edgarmendonca.datumplot`, `REPO = "Edgar-Mendonca/Datum-Plot"` in `src-tauri/src/update.rs`, installer `DatumPlot-x.y.z-setup.exe`.

Checks before pushing:
- `cargo clippy --workspace --all-targets -- -D warnings`
- `cargo test --workspace`
- `npm run check:ui`
- UI tests: `npm run test:ui` (Playwright against `ui/dist` with the `dump` fixture)

Releasing:
1. Bump the version in `src-tauri/Cargo.toml` and `crates/core/Cargo.toml`.
2. Add a CHANGELOG section (`## x.y.z — date`, a one-line summary, bold sections in plain language).
3. Push the tag `vX.Y.Z`, or run `release.yml` with workflow_dispatch when tag pushes are blocked. The workflow creates the tag and publishes the installer and `SHA256SUMS.txt`.
