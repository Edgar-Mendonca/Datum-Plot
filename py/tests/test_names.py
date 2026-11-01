"""FAMILY §13: public text never names another company's product. The repository is public, so this covers the app's
own code (what users read in the window and in results), the guide, the changelog, README, site text and the
project's notes. File formats are named by their extension (.pzfx, .xlsx…); test fixtures holding real file content
are not scanned. Run: python -m unittest discover -s py/tests"""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NAMES = re.compile(r"Prism|GraphPad|OriginPro|OriginLab|\bOrigin\b|Excel|PowerPoint|\bWord\b|Microsoft|MS Office|\bOffice\b|SigmaPlot|"
                   r"Tableau|Illustrator|SPSS|Minitab|\bJMP\b|MATLAB|KaleidaGraph|Primavera|MS Project|CentriForge")
SCAN = ["CLAUDE.md", "README.md", "NOTICE", "CHANGELOG.md", "CITATION.cff", "SECURITY.md", "CONTRIBUTING.md", "docs", "ui/src", "ui/index.html",
        "py/datum", "py/worker.py", "src-tauri/src", "crates/core/src", "crates/core/examples"]
TEXT = (".md", ".json", ".ts", ".tsx", ".css", ".html", ".py", ".rs", ".cff", "")


def files():
    for s in SCAN:
        p = os.path.join(ROOT, s)
        if os.path.isfile(p):
            yield p
        for d, _, fs in os.walk(p):
            yield from (os.path.join(d, f) for f in fs if os.path.splitext(f)[1] in TEXT)


class NoProductNames(unittest.TestCase):
    def test_public_text_names_no_commercial_product(self):
        hits = []
        for f in files():
            rel = os.path.relpath(f, ROOT)
            if "/brand/" in rel or rel.endswith((".png", ".pdf", ".svg")):
                continue
            with open(f, encoding="utf-8", errors="ignore") as fh:
                lines = fh.readlines()
            for n, line in enumerate(lines, 1):
                for m in NAMES.finditer(line):
                    if m.group() == "Tableau" and rel.endswith("fr.md"):  # the French word for table
                        continue
                    hits.append(f"{rel}:{n}: {m.group()}")
        self.assertEqual(hits, [], "\n".join(hits[:40]))


if __name__ == "__main__":
    unittest.main()
