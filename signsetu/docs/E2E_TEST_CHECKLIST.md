# End-to-end test checklist

**Section A is automated** (`python scripts/e2e_browser.py`, last run: 18/18 pass) using synthetic landmarks.
**Section B must be done by a person with a real webcam** before the demo — it has not been run yet.
Mark each box with initials + time.

## A. Automated (real browser + real backend, synthetic hands)
- [x] A1 App starts, page shows **Backend on**
- [x] A2 Supported sign → nothing before hold completes → text appears → speech plays with the same text
- [x] A3 History and transcript update at the same moment as text
- [x] A4 Holding one sign for 30+ frames speaks **once**
- [x] A5 Hand leaves, same sign again → speaks again
- [x] A6 Unsupported pose → nothing spoken, badge "not a supported sign"
- [x] A7 No hands → nothing spoken, badge "no hand"
- [x] A8 Context change (Bank) and Hindi mode produce the right sentence/voice text
- [x] A9 Backend killed mid-use → page falls back to browser rules and still works
- [x] A10 Backend restarted → page reconnects by itself, signs work again
- [x] A11 Camera denied / not found / busy → clear message, Start button usable again
- [x] A12 Sign-guide click works with no camera and no backend

## B. Manual, live webcam (Member 4 + one other member)
Setup: Chrome, `./run.sh`, http://localhost:8000, room lighting similar to the demo venue.

| # | Step | Expected | Pass | Notes |
|---|---|---|---|---|
| B1 | Start app, open page | Pill "Backend on" | ☐ | |
| B2 | Start camera, allow | Video + yellow skeleton, pill "Live" | ☐ | |
| B3 | Show each of the 13 signs, hold 1 s, one at a time | Correct text + voice each time. Record any that fail in BUG_LIST | ☐ | |
| B4 | Keep hand in frame, hold one sign 10 s | Spoken once, not repeated | ☐ | |
| B5 | Lower hand 1 s, repeat same sign | Spoken again | ☐ | |
| B6 | Remove hand entirely | Badge "no hand", silence | ☐ | |
| B7 | Wave hand / make a random shape | Silence, or badge "not a supported sign"; never a wrong sentence spoken | ☐ | |
| B8 | Two hands in view | Only one hand used, no crash | ☐ | |
| B9 | Dim the room / back-light | Degrades to silence rather than wrong speech | ☐ | |
| B10 | Switch Hospital → Bank → Office on the same sign | Sentence changes per context | ☐ | |
| B11 | Switch to Hindi, show sign | Hindi text; Hindi voice (or message if none) | ☐ | |
| B12 | Voice off, show sign | Text appears, no sound | ☐ | |
| B13 | Press Stop, then Start camera again | Camera light off on Stop; restarts cleanly, no duplicate speech | ☐ | |
| B14 | Unplug USB camera while running | Message "camera was disconnected", Start usable | ☐ | |
| B15 | Block camera permission, reload, Start | Clear permission message | ☐ | |
| B16 | Open Zoom/another app on the camera, then Start | "camera is busy" message | ☐ | |
| B17 | Ctrl+C the server while signing | Pill → "Backend off", signs still work | ☐ | |
| B18 | Start server again | Pill → "Backend on" within ~5 s | ☐ | |
| B19 | Close laptop lid / reopen, or restart whole app | Works after refresh | ☐ | |
| B20 | Full run, cold start, as a new team member using only the README | Reaches spoken sentence in < 5 min | ☐ | |

## C. Pre-demo gate (15 min before)
- [ ] Venue Wi-Fi works **or** the offline plan in `DEMO_AND_FALLBACK.md` is prepared
- [ ] Browser cache already holds MediaPipe (load page once on this network)
- [ ] Speakers volume tested; Hindi voice present (or demo in English)
- [ ] Demo signs rehearsed under demo lighting (B3 results consulted)
- [ ] Backup video open in another window; screenshots on the slide deck
