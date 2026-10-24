"""ISL word recognizer (trained on your own recordings, nearest-neighbour).

Model file: backend/models/signsetu-isl-model.json
  {"app","v","nf":10,"d":92,"s":[[word, recording_id, base64_int8[nf*d]], ...]}

Per-frame feature layout (92 int8 values) - inferred from the recordings:
  [0]      1st hand present flag (24 or 0)      [1]  2nd hand present flag (24 or 0)
  [2:44]   hand A: 21 points (x,y) minus its wrist, / hand size * 16   (wrist = 0,0)
  [44:86]  hand B: same layout (zeros if absent)
  [86:88]  hand A wrist (x,y) * 32      [88:90] hand B wrist (x,y) * 32
  [90:92]  (B wrist - A wrist) / hand size(A) * 16   (zeros unless two hands)
Hand A is the hand with the smaller wrist x; a single hand is always A.
Hand size = 2D distance wrist(0) -> middle knuckle(9). Values are clipped to int8.

A sign is a short clip resampled to nf frames. Matching = mean per-frame
Euclidean distance to every stored sample; the best sample of each word is its
score. The query is also tried mirrored (x flipped) so left/right-handed
signers and camera mirroring both work.
"""
import base64
import json
import math
import os

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(_HERE, "models", "signsetu-isl-model.json")
NO_HAND, UNKNOWN = "NO_HAND", "UNKNOWN"
POS_SCALE, REL_SCALE = 32.0, 16.0


def frame_features(hands):
    """hands: list of 0-2 landmark lists ([[x,y,z]*21]). -> float32[92] or None if no hand."""
    hands = [h for h in (hands or []) if h]
    if not hands:
        return None
    hands = sorted(hands[:2], key=lambda h: h[0][0])
    f = np.zeros(92, np.float32)
    wrists, sizes = [], []
    for i, lm in enumerate(hands):
        p = np.asarray([[q[0], q[1]] for q in lm], np.float64)
        sc = math.hypot(*(p[9] - p[0])) or 1.0
        rel = np.clip(np.round((p - p[0]) / sc * REL_SCALE), -127, 127)
        f[i] = 24
        f[2 + 42 * i:44 + 42 * i] = rel.reshape(-1)
        f[86 + 2 * i:88 + 2 * i] = np.clip(np.round(p[0] * POS_SCALE), -127, 127)
        wrists.append(p[0])
        sizes.append(sc)
    if len(hands) == 2:
        f[90:92] = np.clip(np.round((wrists[1] - wrists[0]) / sizes[0] * REL_SCALE), -127, 127)
    return f


def mirror(seq):
    """Flip x of a (n,92) feature clip. Hand order is swapped so A stays the left-most hand."""
    out = seq.copy()
    out[:, 2:86:2] *= -1                      # relative x
    out[:, 86:90:2] = np.where(out[:, 86:90:2] != 0, POS_SCALE - out[:, 86:90:2], 0)
    out[:, 90] *= -1
    two = out[:, 1] > 0
    a, b = out[:, 2:44].copy(), out[:, 44:86].copy()
    out[two, 2:44], out[two, 44:86] = b[two], a[two]
    wa, wb = out[:, 86:88].copy(), out[:, 88:90].copy()
    out[two, 86:88], out[two, 88:90] = wb[two], wa[two]
    return out


def resample(frames, nf):
    """frames: list of (t_ms, float32[92]|None). Linear resample to nf frames by time; None -> zeros."""
    arr = np.stack([f if f is not None else np.zeros(92, np.float32) for _, f in frames])
    if len(arr) == 1:
        return np.repeat(arr, nf, 0)
    t = np.asarray([t for t, _ in frames], np.float64)
    if t[-1] <= t[0]:
        t = np.arange(len(arr), dtype=np.float64)
    tt = np.linspace(t[0], t[-1], nf)
    idx = np.clip(np.searchsorted(t, tt, side="right") - 1, 0, len(arr) - 2)
    w = ((tt - t[idx]) / np.maximum(t[idx + 1] - t[idx], 1e-9))[:, None].astype(np.float32)
    return arr[idx] * (1 - w) + arr[idx + 1] * w


class WordModel:
    def __init__(self, path=MODEL_PATH):
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        self.nf, self.d = int(raw["nf"]), int(raw["d"])
        assert self.d == 92, "unsupported feature size %s" % self.d
        self.words = sorted({s[0] for s in raw["s"]})
        self.labels = np.array([s[0] for s in raw["s"]])
        self.rec = np.array([s[1] for s in raw["s"]])
        self.X = np.stack([np.frombuffer(base64.b64decode(s[2]), np.int8).astype(np.float32)
                           .reshape(self.nf, self.d) for s in raw["s"]])

    def distances(self, clip, exclude_rec=None):
        """clip (nf,92) -> {word: best distance}, trying the mirrored clip too."""
        X, lab = self.X, self.labels
        if exclude_rec is not None:
            keep = self.rec != exclude_rec
            X, lab = X[keep], lab[keep]
        best = np.minimum(np.linalg.norm(X - clip, axis=-1).mean(-1),
                          np.linalg.norm(X - mirror(clip), axis=-1).mean(-1))
        return {w: float(best[lab == w].min()) for w in self.words if (lab == w).any()}

    def classify(self, clip, max_dist, min_margin):
        """-> (label or None, confidence 0-1, distance, runner_up_distance)."""
        ds = sorted(self.distances(clip).items(), key=lambda kv: kv[1])
        (w1, d1), d2 = ds[0], (ds[1][1] if len(ds) > 1 else float("inf"))
        if d1 > max_dist or d2 - d1 < min_margin:
            return None, 0.0, d1, d2
        conf = 0.5 + 0.49 * max(0.0, 1.0 - d1 / max_dist)
        return w1, round(conf, 2), d1, d2


class WordSession:
    """Per-browser-session sliding window: frames in -> {label,confidence,recognized,distance} out."""

    def __init__(self, model, window_ms=1500, min_span_ms=700, max_dist=120.0, min_margin=4.0,
                 no_hand_clear=6):
        self.m, self.window_ms, self.min_span = model, window_ms, min_span_ms
        self.max_dist, self.min_margin, self.no_hand_clear = max_dist, min_margin, no_hand_clear
        self.reset()

    def reset(self):
        self.buf, self.miss, self.n = [], 0, 0

    def update(self, hands, t_ms):
        f = frame_features(hands)
        self.n += 1
        if f is None:
            self.miss += 1
            if self.miss >= self.no_hand_clear:
                self.buf = []
            return {"label": NO_HAND, "confidence": 0.0, "recognized": False, "distance": None}
        self.miss = 0
        self.buf.append((float(t_ms), f))
        cut = t_ms - self.window_ms
        self.buf = [x for x in self.buf if x[0] >= cut]
        if self.buf[-1][0] - self.buf[0][0] < self.min_span:      # still collecting the clip
            return {"label": UNKNOWN, "confidence": 0.0, "recognized": False, "distance": None}
        label, conf, d1, _ = self.m.classify(resample(self.buf, self.m.nf), self.max_dist, self.min_margin)
        if label is None:
            return {"label": UNKNOWN, "confidence": 0.0, "recognized": False, "distance": round(d1, 1)}
        return {"label": label, "confidence": conf, "recognized": True, "distance": round(d1, 1)}
