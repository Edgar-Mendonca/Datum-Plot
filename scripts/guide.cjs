// Builds the Datum Plot Guide PDFs (docs/guide/pdf/DatumPlot-Guide-{en,zh,fr}.pdf) from
// docs/guide/{en,zh,fr}.md and the screenshots in docs/guide/img (tests_ui/guide_shots.cjs).
// Run: NODE_PATH=$(npm root -g) node scripts/guide.cjs   (needs Playwright's Chromium)
// The release attaches the three PDFs; Help › Guide in the app downloads them.
const { chromium } = require("playwright");
const fs = require("fs"), path = require("path");
const dir = path.join(__dirname, "../docs/guide"), nm = path.join(__dirname, "../node_modules");
const version = fs.readFileSync(path.join(__dirname, "../src-tauri/Cargo.toml"), "utf8").match(/^version = "(.+)"/m)[1];
const logo = fs.readFileSync(path.join(__dirname, "../docs/brand/datum-plot-icon.svg"), "utf8");

const esc = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
// Code spans are kept as typed: a * or [[ inside them (=A1*2) is not formatting.
const inline = s => esc(s).split(/(`[^`]+`)/).map((x, i) => (i % 2 ? `<code>${x.slice(1, -1)}</code>` : x.replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>").replace(/\*([^*]+)\*/g, "<i>$1</i>").replace(/\[\[([^\]]+)\]\]/g, "<kbd>$1</kbd>"))).join("");
let anchors = 0;
/** A small Markdown subset: # ## ### headings, paragraphs, - and 1. lists, > tips, | tables |, ![caption](img), --- page breaks. */
function md(src) {
  const out = [], toc = [];
  const lines = src.replace(/\r\n/g, "\n").split("\n");
  for (let i = 0; i < lines.length;) {
    const l = lines[i];
    if (!l.trim()) { i++; continue; }
    let m;
    if (l.trim() === "---") { out.push('<div class="break"></div>'); i++; continue; }
    if ((m = l.match(/^(#{1,3}) (.*)/))) {
      const n = m[1].length, id = `s${++anchors}`;
      if (n === 2) toc.push([id, m[2]]);
      out.push(`<h${n} id="${id}">${inline(m[2])}</h${n}>`); i++; continue;
    }
    if ((m = l.match(/^!\[(.*)\]\((.*)\)/))) {
      const img = fs.readFileSync(path.join(dir, m[2])).toString("base64");
      out.push(`<figure><img src="data:image/png;base64,${img}"><figcaption>${inline(m[1])}</figcaption></figure>`); i++; continue;
    }
    if (l.startsWith(">")) {
      const b = []; while (i < lines.length && lines[i].startsWith(">")) b.push(lines[i++].replace(/^>\s?/, ""));
      out.push(`<div class="tip">${b.map(x => `<p>${inline(x)}</p>`).join("")}</div>`); continue;
    }
    if (l.startsWith("|")) {
      const rows = []; while (i < lines.length && lines[i].startsWith("|")) rows.push(lines[i++]);
      const cells = r => r.trim().replace(/^\||\|$/g, "").split("|").map(c => c.trim());
      out.push(`<table><thead><tr>${cells(rows[0]).map(c => `<th>${inline(c)}</th>`).join("")}</tr></thead><tbody>${rows.slice(2).map(r => `<tr>${cells(r).map(c => `<td>${inline(c)}</td>`).join("")}</tr>`).join("")}</tbody></table>`); continue;
    }
    if (/^(-|\d+\.) /.test(l)) {
      const ol = /^\d+\./.test(l), items = [];
      while (i < lines.length && /^(-|\d+\.) /.test(lines[i])) { let t = lines[i++].replace(/^(-|\d+\.) /, ""); while (i < lines.length && /^ {2,}\S/.test(lines[i])) t += " " + lines[i++].trim(); items.push(t); }
      out.push(`<${ol ? "ol" : "ul"}>${items.map(t => `<li>${inline(t)}</li>`).join("")}</${ol ? "ol" : "ul"}>`); continue;
    }
    const p = []; while (i < lines.length && lines[i].trim() && !/^(#|!\[|>|\||-|\d+\. |---)/.test(lines[i])) p.push(lines[i++]);
    if (!p.length) p.push(lines[i++]);
    out.push(`<p>${inline(p.join(" "))}</p>`);
  }
  return { html: out.join("\n"), toc };
}

const css = (zh) => `
@page { size: A4; margin: 18mm 17mm 20mm; }
:root { --ink: #1B2A3A; --muted: #5B6B7C; --blue: #0E8C7F; --pale: #E3F5F2; --line: #D7DEE7; --amber: #F2B233; }
html { font: 10.5pt/1.6 ${zh ? "'Noto Sans SC', 'IBM Plex Sans'" : "'IBM Plex Sans', 'Noto Sans SC'"}, sans-serif; color: var(--ink); }
body { margin: 0; }
h1 { font-size: 26pt; line-height: 1.2; margin: 0 0 6mm; color: var(--ink); }
h2 { font-size: 17pt; color: var(--blue); margin: 0 0 4mm; padding-bottom: 2mm; border-bottom: 2px solid var(--blue); break-before: page; break-after: avoid; }
h3 { font-size: 12.5pt; margin: 6mm 0 2mm; break-after: avoid; }
p { margin: 0 0 3mm; }
ul, ol { margin: 0 0 3mm; padding-left: 6mm; } li { margin: 0 0 1.2mm; }
code { font: 9pt 'IBM Plex Mono', monospace; background: #F1F4F8; padding: 0 1.2mm; border-radius: 1mm; }
kbd { font: 600 8.5pt 'IBM Plex Mono', monospace; border: 1px solid #B9C4D1; border-bottom-width: 2px; border-radius: 1.2mm; padding: 0 1.4mm; background: #fff; }
b { color: #0B4E47; }
figure { margin: 3mm 0 5mm; break-inside: avoid; }
figure img { width: 100%; border: 1px solid var(--line); border-radius: 1.5mm; }
figcaption { font-size: 9pt; color: var(--muted); margin-top: 1.5mm; }
.tip { border-left: 4px solid var(--amber); background: #FFF8E6; padding: 2.5mm 4mm; margin: 0 0 4mm; border-radius: 0 1.5mm 1.5mm 0; break-inside: avoid; }
.tip p { margin: 0 0 1mm; } .tip p:last-child { margin: 0; }
table { width: 100%; border-collapse: collapse; margin: 0 0 4mm; font-size: 9.5pt; break-inside: auto; }
th { background: var(--pale); text-align: left; } th, td { border: 1px solid var(--line); padding: 1.5mm 2.5mm; vertical-align: top; }
tr { break-inside: avoid; }
.break { break-after: page; }
.cover { height: 250mm; display: flex; flex-direction: column; justify-content: center; }
.cover svg { width: 34mm; height: 34mm; margin-bottom: 10mm; }
.cover .sub { font-size: 14pt; color: var(--muted); margin-bottom: 18mm; }
.cover .meta { font: 10pt 'IBM Plex Mono', monospace; color: var(--muted); border-top: 2px solid var(--blue); padding-top: 4mm; }
.cover .bar { height: 3mm; width: 40mm; background: var(--amber); margin-bottom: 8mm; }
.toc { break-after: page; } .toc h2 { break-before: auto; }
.toc ol { list-style: none; padding: 0; counter-reset: ch; } .toc li { counter-increment: ch; padding: 1.6mm 0; border-bottom: 1px dotted var(--line); font-size: 11pt; }
.toc li::before { content: counter(ch) "  "; color: var(--blue); font-weight: 700; } .toc a { color: var(--ink); text-decoration: none; }
`;

(async () => {
  const b = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  for (const [lang, title, sub, tocName] of [["en", "Datum Plot Guide", "Analyse your data and make publication-ready graphs, step by step.", "Contents"], ["zh", "Datum Plot 使用指南", "一步一步：分析数据，制作可发表的图表。", "目录"], ["fr", "Guide Datum Plot", "Analysez vos données et créez des graphiques prêts à publier, pas à pas.", "Sommaire"]]) {
    anchors = 0;
    const src = fs.readFileSync(path.join(dir, `${lang}.md`), "utf8");
    const { html, toc } = md(src.replace(/^# .*\n/, ""));
    const fonts = ["ibm-plex-sans/400.css", "ibm-plex-sans/600.css", "ibm-plex-sans/700.css", "ibm-plex-mono/400.css", "ibm-plex-mono/600.css", ...(lang === "zh" ? ["noto-sans-sc/400.css", "noto-sans-sc/700.css"] : ["noto-sans-sc/400.css"])]
      .map(f => `<link rel="stylesheet" href="file://${nm}/@fontsource/${f}">`).join("");
    const date = new Date().toISOString().slice(0, 10);
    const page = `<!doctype html><html lang="${{ zh: "zh-CN", fr: "fr-FR" }[lang] ?? "en"}"><head><meta charset="utf-8"><title>${title}</title>${fonts}<style>${css(lang === "zh")}</style></head><body>
      <section class="cover">${logo}<div class="bar"></div><h1>${title}</h1><div class="sub">${sub}</div>
        <div class="meta">Datum Plot ${version} · ${date}<br>github.com/Edgar-Mendonca/Datum-Plot</div></section>
      <section class="toc"><h2>${tocName}</h2><ol>${toc.map(([id, t]) => `<li><a href="#${id}">${inline(t)}</a></li>`).join("")}</ol></section>
      ${html}</body></html>`;
    const tmp = path.join(dir, `.${lang}.html`);
    fs.writeFileSync(tmp, page);
    const p = await b.newPage();
    await p.goto(`file://${tmp}`);
    await p.evaluate(() => document.fonts.ready);
    await p.waitForTimeout(500);
    const out = path.join(dir, "pdf", `DatumPlot-Guide-${lang}.pdf`);
    await p.pdf({ path: out, format: "A4", printBackground: true, displayHeaderFooter: true, preferCSSPageSize: true,
      headerTemplate: "<span></span>",
      footerTemplate: `<div style="width:100%;font:8px sans-serif;color:#7A8796;padding:0 17mm;display:flex;justify-content:space-between"><span>Datum Plot ${version}</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>` });
    await p.close();
    fs.unlinkSync(tmp);
    console.log(`${out}: ${(fs.statSync(out).size / 1048576).toFixed(1)} MB`);
  }
  await b.close();
})();
