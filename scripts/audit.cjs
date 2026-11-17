// npm audit with a short, dated list of accepted advisories (audit-allow.json). Fails on any high or critical
// advisory not on the list, and on any listed one past its review date, so an exception can never be forgotten.
// Run: node scripts/audit.cjs   (the CI `audit` job runs it; `npm audit --omit=dev` stays strict for what ships)
const { execSync } = require("child_process");
const fs = require("fs"), path = require("path");

const allow = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "audit-allow.json"), "utf8")).advisories;
const today = new Date().toISOString().slice(0, 10);
let failed = false;
for (const a of allow) {
  if (a.until < today) { console.log(`EXPIRED ${a.id} (${a.package}): accepted until ${a.until}; update the package or review the exception.`); failed = true; }
}

let report;
try { report = execSync("npm audit --json", { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }); }
catch (e) { report = e.stdout; }  // npm audit exits with 1 when it finds anything
const vulns = JSON.parse(report).vulnerabilities || {};
const ok = new Set(allow.filter(a => a.until >= today).map(a => a.id));

// The advisories behind a package, following packages that only depend on vulnerable ones.
const roots = (name, seen = new Set()) => {
  if (seen.has(name) || !vulns[name]) return [];
  seen.add(name);
  return vulns[name].via.flatMap(v => typeof v === "string" ? roots(v, seen) : [{ id: (v.url || "").split("/").pop(), severity: v.severity, title: v.title }]);
};
for (const [name, v] of Object.entries(vulns)) {
  if (!["high", "critical"].includes(v.severity)) continue;
  const bad = roots(name).filter(r => ["high", "critical"].includes(r.severity) && !ok.has(r.id));
  for (const r of bad) { console.log(`${v.severity.toUpperCase()} ${name}: ${r.id} ${r.title || ""}`); failed = true; }
}
for (const a of allow) if (a.until >= today) console.log(`accepted until ${a.until}: ${a.id} (${a.package}) — ${a.reason}`);
console.log(failed ? "npm audit: FAILED" : "npm audit: ok");
process.exit(failed ? 1 : 0);
