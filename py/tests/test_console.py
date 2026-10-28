"""The Python console (H1) and notebook export (H5): tables as DataFrames, printed output and the last
value, figures, new tables, errors reported with their line, a namespace that lasts, and a notebook that
is valid JSON. Run: python -m unittest discover -s py/tests"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datum import console  # noqa: E402

T = {"id": 1, "name": "Growth", "kind": "xy", "xTitle": "Time", "rows": 4, "rowTitles": [], "excluded": [],
     "sets": [{"title": "Control", "entry": "rep", "reps": 2}, {"title": "Drug", "entry": "rep", "reps": 1}],
     "cols": [[0, 1, 2, None], [1.0, 2.0, 4.0, None], [1.2, 2.2, 3.8, None], [1.0, 1.5, 2.0, None]]}
P = {"name": "P", "tables": [T], "graphs": [], "analyses": [{"id": 2, "table": 1, "name": "Fit", "kind": "linear", "sets": [], "options": {}}]}


class Console(unittest.TestCase):
    def setUp(self):
        console.reset()

    def test_tables_output_and_last_value(self):
        r = console.run(P, "df = tables['Growth']\nprint(list(df.columns))\ndf['Control 1'].sum()")
        self.assertFalse(r["error"])
        self.assertIn("['Time', 'Control 1', 'Control 2', 'Drug']", r["out"])
        self.assertIn("7.0", r["out"])  # rows with no value at all are left out
        self.assertEqual(console.run(P, "len(table(0))")["out"].strip(), "3")
        self.assertIn("slope", console.run(P, "result('Fit')['answer']")["out"])

    def test_namespace_lasts_figures_and_new_tables(self):
        console.run(P, "a = 21")
        self.assertEqual(console.run(P, "a * 2")["out"].strip(), "42")
        r = console.run(P, "plt.plot([1, 2], [3, 4])\nnew_table('Doubled', {'x': [1, 2, 3], 'y': np.array([2, 4, 6])})")
        self.assertEqual(len(r["figures"]), 1)
        self.assertTrue(r["figures"][0].lstrip().startswith("<?xml") or "<svg" in r["figures"][0])
        t = r["tables"][0]
        self.assertEqual((t["name"], t["kind"], t["xTitle"], t["cols"], t["sets"][0]["title"]), ("Doubled", "xy", "x", [[1.0, 2.0, 3.0], [2.0, 4.0, 6.0]], "y"))
        self.assertEqual(console.reset()["error"], False)
        self.assertIn("NameError", console.run(P, "a")["out"])

    def test_errors_keep_the_engine_alive(self):
        r = console.run(P, "x = 1\n1 / 0")
        self.assertTrue(r["error"])
        self.assertIn("Line 2: ZeroDivisionError", r["out"])
        self.assertIn("Line 1:", console.run(P, "def (")["out"])
        self.assertIn("No table is called", console.run(P, "tables['Nope']")["out"])
        self.assertIn("SystemExit", console.run(P, "import sys\nsys.exit()")["out"])
        self.assertIn("not shown", console.run(P, "print('x' * 200000)")["out"])


class Notebook(unittest.TestCase):
    def test_notebook_is_valid_and_has_the_data_and_analyses(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "p.ipynb")
            r = console.notebook(P, p)
            nb = json.load(open(p, encoding="utf-8"))
        self.assertEqual((nb["nbformat"], r["cells"]), (4, len(nb["cells"])))
        src = "\n".join(c["source"] for c in nb["cells"])
        for words in ("t1 = pd.DataFrame", "Control 1", "## Fit", "sm.OLS"):
            self.assertNotIn("[...]", src)
            self.assertIn(words, src)
        for c in nb["cells"]:
            if c["cell_type"] == "code" and "pd.DataFrame" in c["source"]:
                compile(c["source"], "cell", "exec")
