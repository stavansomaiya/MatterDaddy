"""The Python recognizer must agree with the original JS recognize() in the page.
Skipped automatically if Node.js is not installed."""
import json
import os
import random
import re
import shutil
import subprocess
import tempfile
import unittest

from backend import recognizer
from tests.handgen import POSES, UNSUPPORTED, make_hand

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = open(os.path.join(ROOT, "frontend", "index.html"), encoding="utf-8").read()


@unittest.skipUnless(shutil.which("node"), "node not installed")
class ParityTests(unittest.TestCase):
    def test_python_matches_browser_rules(self):
        start = HTML.index("function recognize(lm){")
        end = HTML.index("/*\n * OUTPUT", start)
        js_fn = HTML[start:end]
        rng = random.Random(7)
        cases = [make_hand(*p) for p in POSES.values()] + [make_hand(*UNSUPPORTED)]
        for _ in range(3000):  # random hands: exercises the borderline branches too
            cases.append([[rng.random(), rng.random(), 0.0] for _ in range(21)])
        for _ in range(1500):  # noisy versions of real poses
            base = make_hand(*rng.choice(list(POSES.values())))
            cases.append([[x + rng.gauss(0, .03), y + rng.gauss(0, .03), 0.0] for x, y, _ in base])
        script = js_fn + "\nconst cases=JSON.parse(require('fs').readFileSync(process.argv[2],'utf8'));" \
            "console.log(JSON.stringify(cases.map(c=>recognize(c.map(p=>({x:p[0],y:p[1]}))))));"
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "r.js"), "w", encoding="utf-8").write(script)
            open(os.path.join(d, "c.json"), "w").write(json.dumps(cases))
            out = subprocess.run(["node", os.path.join(d, "r.js"), os.path.join(d, "c.json")],
                                 capture_output=True, text=True, check=True).stdout
        js = json.loads(out)
        mism = []
        for c, (jl, jc) in zip(cases, js):
            pl, pc = recognizer._rule(c)
            if pl != jl or abs(pc - jc) > 1e-9:
                mism.append((jl, pl))
        self.assertEqual(mism, [], "%d of %d cases differ" % (len(mism), len(cases)))
        self.assertGreater(len({l for l, _ in js if l}), 10)  # the test really hit many classes


if __name__ == "__main__":
    unittest.main()
