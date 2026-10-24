# Bug / risk list

Roles assumed (rename if yours differ): **M1** camera pipeline · **M2** model/recognition · **M3** front end & speech · **M4** integration.
Severity: H = could break the demo, M = visible quality issue, L = polish.

| ID | Sev | Issue | Owner | Status |
|---|---|---|---|---|
| 1 | H | **Never tested with real hands on a live webcam.** All automated tests use synthetic landmarks. Rules may misfire on real hands (checklist B3) | M2 + M4 | **VERIFIED** (tested by team with real hands on a live webcam) |
| 2 | H | MediaPipe loads from a CDN → no Wi-Fi means no camera | M1 | **FIXED** (MediaPipe vendored in `frontend/vendor/`, served by the backend; no internet needed) |
| 3 | M | Rules assume an upright hand; sideways/rotated hand misclassifies | M2 | **WON'T FIX for demo** (rules unchanged after real-hand testing passed; documented: hold hand upright) |
| 4 | M | Confidence is fixed per rule (0.8–0.9), not measured; shown as "%" in the badge | M2 | **FIXED** (badge now says "rule score") |
| 5 | M | Signs are static shapes chosen for detectability, not real ISL; pitch must not claim otherwise | M2 / presenter | **BY DESIGN** (documented in README and pitch) |
| 6 | M | Changing the place chip or language **re-speaks the last sign and adds another history entry**. Intentional for translation, but conflicts with "speak finalized predictions only" | M3 | **FIXED** (place/language change re-renders text silently: no speech, no new history entry) |
| 7 | M | Sign-guide/dictionary clicks report confidence 100% (manual input, not a prediction) | M3 | **FIXED** (manual clicks show no confidence bar) |
| 8 | M | Hindi voice depends on the device; Chrome on some laptops has none | M3 | **MITIGATED** (on-screen warning when a Hindi sentence has no voice; depends on the device) |
| 9 | L | Only the first hand is used (`maxNumHands:1`); two hands pick whichever MediaPipe ranks first | M1 | **FIXED** (both hands recognised independently, one session per hand) |
| 10 | L | Backend pill is the only visible hint when running in fallback mode | M3 | **FIXED** (camera badge shows "browser mode" when the backend is off) |
| 11 | — | `hands` model was re-created on every Start camera (memory growth on repeated restarts) | M1 | **FIXED** (reused) |
| 12 | — | Generic camera error text for every failure | M1 | **FIXED** (denied / not found / busy / unplugged messages) |
| 13 | — | Hand-leaves-frame did not clear the "detected" dictionary highlight | M3 | **FIXED** |
