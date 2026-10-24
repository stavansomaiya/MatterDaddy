"""Turn a recorded model sample back into synthetic MediaPipe landmarks, so the word
pipeline can be tested without a webcam."""
import numpy as np
from backend.words import POS_SCALE, REL_SCALE


def frame_to_hands(f, hs=0.2):
    hands = []
    for i in range(2):
        if f[i] < 1:
            continue
        rel = f[2 + 42 * i:44 + 42 * i].reshape(21, 2) / REL_SCALE * hs
        w = f[86 + 2 * i:88 + 2 * i] / POS_SCALE
        hands.append([[float(w[0] + r[0]), float(w[1] + r[1]), 0.0] for r in rel])
    return hands


def clip_to_stream(clip, n=25, fps=15, hs=0.2):
    """Linear-interpolate a 10-frame clip to n frames -> [(t_ms, hands)]."""
    idx = np.linspace(0, len(clip) - 1, n)
    out = []
    for k, x in enumerate(idx):
        a = int(np.floor(x)); b = min(a + 1, len(clip) - 1); w = x - a
        f = clip[a] * (1 - w) + clip[b] * w
        f[:2] = clip[a][:2]
        out.append((k * 1000.0 / fps, frame_to_hands(f, hs)))
    return out
