# Interface contract (agreed by all four members)

| Item | Decision |
|---|---|
| Camera ownership | **Member 1** — the browser opens the camera once (`Camera` + MediaPipe Hands in `index.html`). The backend never opens a camera. |
| Model input | **Landmarks**, not frames: 21 points `[x, y, z]`, normalised 0–1, one hand. |
| Transport | Local Flask server, HTTP `POST /api/predict` (JSON). Chosen over WebSocket for zero extra dependencies and easy `curl` debugging; localhost latency is a few ms and the page sends ≤15/s. |
| Prediction output | `label`, `confidence`, `recognized` (+ `final`, `progress`, see below) |
| Unknown sign | Explicit result: `{"label":"UNKNOWN","confidence":0.0,"recognized":false}` |
| No hand | Explicit result: `{"label":"NO_HAND","confidence":0.0,"recognized":false}` |
| Duplicate speech | Speak **finalized** predictions only (`final: true`), once per held sign |
| Supported vocabulary | Only the classes in `backend/labels.json` |

## Request
`POST /api/predict`
```json
{"session": "k3j2h1", "landmarks": [[0.5,0.9,0.0], "... 21 points total ..."]}
```
`landmarks: null` means no hand was visible. `session` is any string the page generates once per load.

## Response (actual example format — the label is always a real class)
```json
{"label": "pinky", "confidence": 0.8, "recognized": true, "final": true, "progress": 1.0}
```
* `label`, `confidence`, `recognized` — the three agreed fields.
* `final` — additive: `true` exactly once when a sign has been held `hold_frames` frames. **Only this triggers text + speech.**
* `progress` — additive: 0–1 hold progress, drives the yellow bar.
* `confidence` is a hand-set rule score, not a probability.

## Errors
`400` with `{"error": "<code>", "message": "..."}` for `bad_json`, `no_session`, `bad_landmarks`.
The page counts failures; after 3 consecutive ones (or timeouts >1.5 s) it falls back to in-browser rules and retries
`/api/health` every 5 s.

## Other endpoints
* `GET /api/health` → `{ok, model, classes[], hold_frames}` — the page refuses the backend if it reports a class the page doesn't know.
* `POST /api/reset` `{"session": ...}` — called when the camera is stopped.

## Quick manual check
```bash
curl -s localhost:8000/api/health
curl -s -X POST localhost:8000/api/predict -H 'Content-Type: application/json' -d '{"session":"x","landmarks":null}'
```

## Changing the vocabulary (touch all three, then run the tests)
1. `backend/labels.json` → add the id to `classes`
2. `backend/recognizer.py` → add the rule (and a pose in `tests/handgen.py`)
3. `frontend/index.html` → add the entry to `SIGNS` (+ Hindi name in `HN`) and the same rule in the JS `recognize()`


---
# ISL word model (added)

A second recogniser, trained on your own recordings (`backend/models/signsetu-isl-model.json`, 19 words,
10-frame clips, nearest-neighbour). The page has a **Recognise** switch: *ISL words* (default) or *Hand shapes*.

## `POST /api/predict_word`
```json
{"session": "k3j2h1-w", "t": 123456.7, "hands": [[[x,y,z] x21], [[x,y,z] x21]]}
```
* `hands`: 0, 1 or 2 hands (any order). `null` / `[]` = no hand. `t` = page time in ms (used to resample the ~1.5 s clip).
* Response is the same shape as `/api/predict`: `{label, confidence, recognized, final, progress}` plus `distance`
  (smaller = closer match). `label` is one of `words` in `/api/health`, or `UNKNOWN` / `NO_HAND`.
* `final` is `true` once per word, after `word_hold_frames` identical predictions; the same word fires again only after the hands leave the frame.
* Errors: `400` `bad_json` / `no_session` / `bad_landmarks`; `503` `no_word_model` if the model file is missing.
* `/api/health` now also returns `words[]`; `/api/reset` clears both the shape and the word session of that id.

## Model features (92 per frame, int8)
`[0:2]` hand-present flags (24) | `[2:44]` hand A, `[44:86]` hand B: 21 points (x,y) minus wrist, divided by hand size
(wrist to middle knuckle) x 16 | `[86:90]` wrists x 32 | `[90:92]` (B wrist - A wrist) / hand size x 16.
Hand A = the hand with the smaller wrist x. The query is also tried mirrored, so camera mirroring and left/right-handed signers both work.
Layout was inferred from the recordings; see `backend/words.py`.

## Changing the word vocabulary
1. Record new clips into the model JSON (same format) 2. add the word to `labels.json` `words` 3. add it to `WORDS` (+ Hindi) in `frontend/index.html`. `tests/test_contract.py` checks all three agree.
