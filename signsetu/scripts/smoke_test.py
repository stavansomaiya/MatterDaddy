"""30-second check that needs NO browser and NO camera (standard library only).

Terminal 1:  ./run.sh            (or run.bat)
Terminal 2:  python scripts/smoke_test.py [--port 8000]

Sends synthetic hands to the running server over real HTTP and checks the contract.
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.handgen import UNSUPPORTED, hand_for, make_hand  # noqa: E402

port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8000
BASE = "http://localhost:%d" % port
fails = 0


def call(path, body=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=3))


def check(name, ok):
    global fails
    fails += not ok
    print(("PASS  " if ok else "FAIL  ") + name)


try:
    h = call("/api/health")
except Exception as e:
    sys.exit("Cannot reach %s (%s). Is the server running?" % (BASE, e))
check("health lists supported classes", h["ok"] and "palm" in h["classes"])

sid = "smoke"
call("/api/reset", {"session": sid})
outs = [call("/api/predict", {"session": sid, "landmarks": hand_for("horns")}) for _ in range(h["hold_frames"] + 5)]
check("supported sign -> contract fields", all({"label", "confidence", "recognized"} <= set(o) for o in outs))
check("supported sign -> correct label", outs[-1]["label"] == "horns" and outs[-1]["recognized"])
check("exactly one finalized prediction while holding", sum(o["final"] for o in outs) == 1)
u = call("/api/predict", {"session": sid, "landmarks": make_hand(*UNSUPPORTED)})
check("unsupported sign -> explicit UNKNOWN", u["label"] == "UNKNOWN" and not u["recognized"] and not u["final"])
n = call("/api/predict", {"session": sid, "landmarks": None})
check("no hand -> explicit NO_HAND", n["label"] == "NO_HAND" and not n["recognized"] and not n["final"])
print("\n%s" % ("ALL OK" if not fails else "%d FAILED" % fails))
sys.exit(1 if fails else 0)
