"""Browser end-to-end test (optional dev tool).

Drives the REAL page in headless Chromium against the REAL backend process.
Only the webcam/MediaPipe step is replaced: synthetic landmarks are injected where
MediaPipe would deliver them (onResults), and speechSynthesis.speak is recorded so
we can assert exactly what would have been spoken.

    pip install playwright && playwright install chromium
    python scripts/e2e_browser.py            # add --shots to refresh docs/screenshots
"""
import os
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tests.handgen import UNSUPPORTED, hand_for, make_hand  # noqa: E402

PORT = 8123
URL = "http://localhost:%d/" % PORT
SHOTS = "--shots" in sys.argv
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(("PASS  " if ok else "FAIL  ") + name + (("   -> " + str(detail)) if not ok else ""))


def start_server():
    p = subprocess.Popen([sys.executable, "-m", "backend.server", "--port", str(PORT)], cwd=ROOT,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            urllib.request.urlopen(URL + "api/health", timeout=0.5)
            return p
        except Exception:
            time.sleep(0.2)
    p.kill()
    raise SystemExit("server did not start")


def stop(p):
    p.terminate()
    p.wait(5)


INIT = """
window.__spoken=[];
window.HAND_CONNECTIONS=[];window.drawConnectors=()=>{};window.drawLandmarks=()=>{};
try{speechSynthesis.speak=u=>{window.__spoken.push(u.text)};}catch(e){}
"""


def main():
    server = start_server()
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        page = br.new_page(viewport={"width": 1400, "height": 1000})
        page.route("**/*", lambda r: r.continue_() if r.request.url.startswith("http://localhost") else r.abort())
        page.add_init_script(INIT)
        page.goto(URL)
        page.evaluate("window.__feed=(lm)=>onResults({image:{width:640,height:480},"
                      "multiHandLandmarks:lm?[lm.map(p=>({x:p[0],y:p[1],z:p[2]}))]:[]})")

        page.evaluate("window.__feed2=(a,b)=>!a?0:onResults({image:{width:640,height:480},"
                      "multiHandLandmarks:[a,b].map(l=>l.map(p=>({x:p[0],y:p[1],z:p[2]}))),"
                      "multiHandedness:[{label:'Left'},{label:'Right'}]})")

        def feed2(a, b, n, gap=75):
            for _ in range(n):
                page.evaluate("([a,b])=>window.__feed2(a,b)", [a, b])
                page.wait_for_timeout(gap)

        def feed(lm, n, gap=75):
            for _ in range(n):
                page.evaluate("lm=>window.__feed(lm)", lm)
                page.wait_for_timeout(gap)

        spoken = lambda: page.evaluate("window.__spoken")
        text = lambda: page.inner_text("#txt")

        page.wait_for_function("beOK===true", timeout=5000)
        check("1 start app: page connects to backend", "Backend on" in page.inner_text("#bet"))

        feed(hand_for("palm"), 4)
        check("2a half-way through hold: nothing spoken yet", spoken() == [], spoken())
        feed(hand_for("palm"), 8)
        check("2b supported sign -> text displayed", text() == "Hello", text())
        check("2c ...and speech played with the same text", spoken() == ["Hello"], spoken())
        check("2d history + transcript updated together",
              page.locator("#hist li").count() == 1 and "Hello" in page.inner_text("#tr"))
        if SHOTS:
            page.screenshot(path=os.path.join(ROOT, "docs/screenshots/01_sign_recognized_en.png"))

        feed(hand_for("palm"), 30)
        check("3 holding the same sign does NOT repeat speech", spoken() == ["Hello"], spoken())

        feed(None, 8)
        feed(hand_for("palm"), 12)
        check("4 hand leaves then same sign again -> spoken again", spoken() == ["Hello", "Hello"], spoken())

        before = list(spoken())
        feed(make_hand(*UNSUPPORTED), 20)
        check("5 unsupported sign -> nothing spoken", spoken() == before and "not a supported" in page.inner_text("#badge"),
              (spoken(), page.inner_text("#badge")))
        feed(None, 10)
        check("6 no hands -> nothing spoken, badge says no hand",
              spoken() == before and "no hand" in page.inner_text("#badge"), page.inner_text("#badge"))

        page.click("[data-s=bank]")
        feed(None, 8)
        feed(hand_for("ell"), 12)
        check("7 context: 'L' sign at Bank -> withdraw sentence", "withdraw" in text().lower(), text())
        if SHOTS:
            page.screenshot(path=os.path.join(ROOT, "docs/screenshots/02_bank_context.png"))

        page.click("#lHi")
        feed(None, 8)
        feed(hand_for("pinky"), 12)
        check("8 Hindi mode: sign -> Hindi text spoken", "पानी" in text() and "पानी" in spoken()[-1], (text(), spoken()[-1]))
        if SHOTS:
            page.screenshot(path=os.path.join(ROOT, "docs/screenshots/03_hindi_water.png"))
        page.click("#lEn")

        # --- two hands at once (backend on): each hand recognised independently ---
        feed(None, 8)
        n = len(spoken())
        feed2(hand_for("palm"), hand_for("pinky"), 14)
        got = spoken()[n:]
        check("14 two hands, backend on: both signs spoken", any("Hello" in t for t in got) and any("water" in t.lower() for t in got), got)
        feed(None, 8)
        n = len(spoken())
        feed2(hand_for("palm"), hand_for("palm"), 14)
        check("14b two hands, same sign: spoken once", len(spoken()) - n == 1, spoken()[n:])
        feed(None, 8)

        # --- backend dies mid-session -> automatic fallback to in-browser rules ---
        stop(server)
        feed(None, 8)
        n = len(spoken())
        feed(hand_for("fist"), 30)
        check("9 backend killed: page falls back and still works",
              "Backend off" in page.inner_text("#bet") and len(spoken()) == n + 1 and "Yes" in text(),
              (page.inner_text("#bet"), spoken()[-2:]))
        if SHOTS:
            page.screenshot(path=os.path.join(ROOT, "docs/screenshots/04_backend_offline_fallback.png"))

        # --- application restart: backend returns, page reconnects by itself ---
        server = start_server()
        page.wait_for_function("beOK===true", timeout=12000)
        check("10 backend restarted: page reconnects automatically", "Backend on" in page.inner_text("#bet"))
        feed(None, 8)
        n = len(spoken())
        feed(hand_for("thumb"), 12)
        check("11 after restart a sign works again", len(spoken()) == n + 1 and "Thank you" in text(), text())

        # --- camera failure messages ---
        page.evaluate("""window.Hands=function(){this.setOptions=()=>{};this.onResults=()=>{}};
                         window.__camErr='NotAllowedError';
                         window.Camera=function(){this.start=()=>Promise.reject(Object.assign(new Error('x'),{name:window.__camErr}))};""")
        for err, expect in [("NotAllowedError", "permission"), ("NotFoundError", "No camera"), ("NotReadableError", "busy")]:
            page.evaluate("e=>{window.__camErr=e}", err)
            page.click("#go")
            page.wait_for_timeout(150)
            m = page.inner_text("#msg")
            check("12 camera failure %s -> clear message, Start re-enabled" % err,
                  expect.lower() in m.lower() and page.is_enabled("#go"), m)
        if SHOTS:
            page.screenshot(path=os.path.join(ROOT, "docs/screenshots/05_camera_error.png"))

        # --- manual fallback: click a sign in the guide (no camera needed) ---
        n = len(spoken())
        page.click("#signs button:nth-child(5)")
        check("13 Sign-guide click works with no camera/backend", len(spoken()) == n + 1, spoken()[-1:])

        feed(None, 8)
        n = len(spoken())
        feed2(hand_for("palm"), hand_for("pinky"), 20, gap=40)
        got = spoken()[n:]
        check("15 two hands, browser mode: both signs spoken", any("Hello" in t for t in got) and any("water" in t.lower() for t in got), got)

        br.close()
    stop(server)
    print("\n%d/%d checks passed" % (sum(results), len(results)))
    sys.exit(0 if all(results) else 1)


main()
