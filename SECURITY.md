# Security

## Reporting a problem

Please report security problems privately, through GitHub's **Report a vulnerability** button on the
[Security tab](https://github.com/Edgar-Mendonca/Datum-Plot/security) of this repository, not in a public issue.
Say what you found, how to reproduce it and which version you used. You will get an answer within a week.

Only the latest release is supported: fixes ship as a new release, which the app offers through its updater.

## How Datum Plot protects you

- **Projects never run code.** A `.dplot` file is plain data (JSON). Opening a project from someone else never runs
  anything; the Python console runs only the code you type and press Run on.
- **Files are checked.** Every file the app reads has a size limit; damaged or hostile files open or give an error,
  and values out of range are clamped. Saves are atomic: a crash or a full disk never leaves a half-written file.
- **Exports are safe to open.** Spreadsheet exports never carry live formulas; CSV text that starts with `=`, `+`, `-`
  or `@` is prefixed with `'`.
- **Updates are verified.** The updater downloads only from this repository's releases, accepts only an installer
  named `DatumPlot-x.y.z-setup.exe`, requires the release's `SHA256SUMS.txt`, checks the exact checksum line, caps the
  download size and saves it in a new private folder.
- **The window is locked down.** A strict content security policy (no remote scripts, frames, objects or forms), and
  links open only this repository's pages.
- **Dependencies are audited** on every push: `cargo deny` (Rust advisories, licences, sources), `npm audit` and
  `pip-audit` (the bundled Python packages).
