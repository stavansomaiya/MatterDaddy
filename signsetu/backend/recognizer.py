"""Landmark -> sign classifier.

This is a line-for-line port of recognize() from the original front end
(frontend/index.html keeps that JS version as the offline fallback).
tests/test_parity.py runs both implementations on the same inputs and checks
they agree.

HONEST DESCRIPTION: rule-based finger geometry on MediaPipe landmarks, not a
trained model. Confidence values are hand-set rule scores, NOT calibrated
probabilities.

Landmark indices: 0 wrist | thumb 1-4 | index 5-8 | middle 9-12 | ring 13-16 | little 17-20.
y grows DOWNWARD in image coordinates, so smaller y = higher on screen.
"""
import json
import math
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "labels.json"), encoding="utf-8") as _f:
    LABELS = json.load(_f)

CLASSES = tuple(LABELS["classes"])
UNKNOWN = "UNKNOWN"
NO_HAND = "NO_HAND"


def _rule(lm):
    """Return (class_id or None, confidence)."""

    def up(t, p):  # fingertip higher than its middle joint -> finger extended
        return lm[t][1] < lm[p][1]

    f = [up(8, 6), up(12, 10), up(16, 14), up(20, 18)]  # index, middle, ring, little

    def d(a, b):
        return math.hypot(lm[a][0] - lm[b][0], lm[a][1] - lm[b][1])

    sc = d(0, 9) or 1  # hand size, so rules work at any distance from the camera
    th = d(4, 17) > d(3, 17) * 1.1  # thumb stretched away from the palm
    knuckles = [lm[5][1], lm[9][1], lm[13][1], lm[17][1]]
    hi, lo = min(knuckles), max(knuckles)
    th_up = th and lm[4][1] < hi
    th_dn = th and lm[4][1] > lo
    pinch = d(4, 8) < sc * 0.28
    n = sum(f)

    if pinch and f[1] and f[2] and f[3]:
        return "ok", 0.85
    if n == 4:
        return ("palm", 0.9) if th else ("four", 0.85)
    if n == 0:
        if th_up:
            return "thumb", 0.85
        if th_dn:
            return "thumbdown", 0.8
        return "fist", 0.8
    if th and not f[0] and not f[1] and not f[2] and f[3]:
        return "call", 0.8
    if th and f[0] and n == 1:
        return "ell", 0.8
    if n == 1 and f[0]:
        return "point", 0.85
    if n == 1 and f[3]:
        return "pinky", 0.8
    if n == 2 and f[0] and f[3]:
        return "horns", 0.85
    if n == 2 and f[0] and f[1]:
        return "peace", 0.85
    if n == 3 and f[0] and f[1] and f[2]:
        return "three", 0.8
    return None, 0.0


def predict(landmarks, min_confidence=0.0):
    """Shared per-frame output contract:

        {"label": str, "confidence": float, "recognized": bool}

    landmarks=None means no hand. A pose matching no class returns the explicit
    UNKNOWN result; it never guesses a nearby class.
    """
    if landmarks is None:
        return {"label": NO_HAND, "confidence": 0.0, "recognized": False}
    label, conf = _rule(landmarks)
    if label is None or conf < min_confidence:
        return {"label": UNKNOWN, "confidence": 0.0, "recognized": False}
    assert label in CLASSES, "recognizer returned a class missing from labels.json: " + label
    return {"label": label, "confidence": round(conf, 2), "recognized": True}
