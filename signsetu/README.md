# SignSetu — Indian Sign Language to speech

Camera → hand landmarks → sign recognition → big text **and** spoken sentence, in English or Hindi,
for hospital / bank / office counters.

> **Two recognisers.** *ISL words* (default): a nearest-neighbour model trained on your own recorded clips of 19 words, run on the Python backend (`backend/words.py`, `backend/models/signsetu-isl-model.json`). *Hand shapes*: the rule-based geometry described below. Switch with the **Recognise** buttons.
>
> **Honest model description (hand shapes).** Recognition is **rule-based finger geometry on MediaPipe hand landmarks.
> It is not a trained ML model**, and the confidence numbers are hand-set rule scores, not probabilities.
> It supports **13 hand shapes** (listed below), not general sign-language understanding.

## Architecture (one camera owner, one source of truth)

```
 Browser (owns the webcam)                         Python backend (localhost:8000)
 ┌──────────────────────────────┐   21 points     ┌───────────────────────────────┐
 │ camera → MediaPipe Hands     │ ──────────────► │ recognizer  (rules → label)   │
 │ draws skeleton               │  POST           │ stabilizer  (hold, no repeats)│
 │ shows text, speaks (browser  │ /api/predict    │ labels.json (class list)      │
 │ speechSynthesis), history    │ ◄────────────── │ serves frontend/index.html    │
 └──────────────────────────────┘  label,conf,    └───────────────────────────────┘
        │ backend down?              recognized,
        └─► falls back to the same rules in JS   final, progress
```

* **Model input = landmarks, not frames.** Only 21 `(x,y,z)` points per frame (~15/s) go to localhost.
  No video leaves the browser.
* **Camera is opened once, by the browser.** The server never touches a camera, so nothing competes for it.
* **Speech only for finalized predictions.** The page speaks/shows text only when `final: true`.
* **Backend optional at runtime.** If it is missing or stops answering, the page switches to its built-in
  rules automatically (badge shows `Backend off`) and reconnects when the server returns.

Full interface spec: [`docs/INTERFACE_CONTRACT.md`](docs/INTERFACE_CONTRACT.md).

## Quick start (new team member: ~2 minutes)

Requirements: Python 3.9+, Chrome or Edge, a webcam, no internet needed (MediaPipe is bundled in `frontend/vendor/`).

```bash
# macOS / Linux                      # Windows
./run.sh                             run.bat
```

Then open **http://localhost:8000** (use `localhost`; browsers only allow the camera on localhost/https).

Manual alternative:
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m backend.server            # --port 9000 to change the port
```

### Using it
1. Pick where you are (Hospital / Bank / Office) — the same sign gives a context-specific sentence.
2. **Start camera**, allow permission. The pill should say **Backend on**.
3. Hold one supported sign steady for ~½ second. The yellow bar fills, then the text appears and is spoken.
4. To repeat the same sign: lower your hand for a moment, then sign again.
5. No camera? Click any card in **Sign guide** to demo without one.

## ISL words (trained model)
`account doctor form help i medicine money namaste name no pain please thanks wait want washroom water where yes`.
Recognition uses a ~1.5 s sliding window of one or two hands, matched to the recorded 10-frame clips; a word is spoken once after 5 consistent predictions, and again only after the hands leave the frame. Leave-one-recording-out accuracy on the supplied recordings is about 90% (3 recordings per word, `doctor` has 1), so expect mistakes between similar words (e.g. thanks/please); recording more clips per word improves it. Words need the backend; with it off, the page falls back to hand shapes. Thresholds are in `config.json` (`word_*`).

## Supported classes (hand shapes - the only ones the shape model can output)

| id | Hand shape | Hospital / default meaning |
|---|---|---|
| `palm` | open palm, thumb out | Hello |
| `fist` | closed fist | Yes |
| `thumb` | thumbs up | Thank you |
| `thumbdown` | thumbs down | No. |
| `point` | index up | Please wait a moment |
| `peace` | index + middle (V) | Where is the washroom? |
| `three` | index + middle + ring | Where is the doctor? *(bank/office differ)* |
| `four` | four fingers, thumb tucked | I have an appointment. *(differs)* |
| `horns` | index + little finger | I need a doctor. I need help. *(differs)* |
| `ell` | thumb + index (L) | How much is the fee? *(differs)* |
| `call` | thumb + little finger | Please call my family. |
| `pinky` | little finger only | I need water, please. |
| `ok` | thumb–index circle, other 3 up | I understand. |

Two explicit non-class results: `UNKNOWN` (hand visible, no match) and `NO_HAND`.
The list lives in [`backend/labels.json`](backend/labels.json); `tests/test_contract.py` fails if the page,
the recognizer and that file disagree.

## Known limitations (say these out loud in the pitch)
* **These are static hand shapes chosen for reliable detection — not real ISL signs.** No motion, no two-handed
  or facial grammar. Do not claim ISL fluency.
* Rules assume the hand is **upright** (fingers pointing up); rotated/sideways hands misclassify.
* Both hands are recognised, each on its own (one hand = one sign; no two-handed signs). If both hands show the same sign it is spoken once; two different signs are spoken one after the other. Poor light or a cluttered background lowers MediaPipe's landmark quality.
* Confidence values are fixed per rule, not measured.
* Hindi speech needs a Hindi voice installed on the device (the app tells you if none is found).
* Tested end-to-end with synthetic landmarks (automated) and by the team with real hands on a live webcam.

## Configuration — `config.json`

| key | default | meaning |
|---|---|---|
| `port` / `host` | 8000 / 127.0.0.1 | where the server listens |
| `hold_frames` | 8 | frames (~15/s) a sign must be held → ~0.5 s |
| `cooldown_frames` | 10 | minimum gap between two finalized signs |
| `rearm_no_hand_frames` | 6 | frames with no hand before the *same* sign may fire again |
| `min_confidence` | 0.7 | predictions below this become `UNKNOWN` |

## Testing

```bash
python -m unittest discover -s tests -t . -v     # 49 tests, no extra installs
python scripts/smoke_test.py                     # against a running server, no browser/camera
pip install playwright && playwright install chromium
python scripts/e2e_browser.py                    # full browser + backend run (21 checks)
```
`tests/test_parity.py` runs the Python recognizer and the page's original JavaScript on 4,500 inputs and checks
they agree (needs Node; skipped otherwise).

## Troubleshooting
| Symptom | Fix |
|---|---|
| "Camera permission was denied" | Click the camera icon in the address bar → Allow → Start camera |
| "camera is busy" | Close other apps/tabs using it (Zoom, Meet, another SignSetu tab) |
| "Hand tracking library did not load" | Open via http://localhost:8000 (not the HTML file) and make sure `frontend/vendor/` exists |
| Pill says `Backend off` | Server not running or wrong URL. Start it; the page reconnects within 5 s |
| Opened by double-clicking the HTML | Works in browser-only mode; use http://localhost:8000 for the full pipeline |
| Port in use | `python -m backend.server --port 8001` and open that port |
| No Hindi voice | Install a Hindi voice in OS settings, or demo in English |

## Layout
```
backend/   recognizer.py  words.py  stabilizer.py  server.py  labels.json  models/signsetu-isl-model.json
frontend/  index.html  vendor/ (MediaPipe, offline)         (your front end + integration block, clearly marked)
tests/     unit, contract, parity, server tests + synthetic-hand generator
scripts/   smoke_test.py  e2e_browser.py
docs/      INTERFACE_CONTRACT  E2E_TEST_CHECKLIST  DEMO_AND_FALLBACK  BUG_LIST  screenshots/
config.json  run.sh  run.bat  requirements.txt
```

## License
MIT, see [`LICENSE`](LICENSE). MediaPipe (Apache-2.0) is bundled in `frontend/vendor/`.
