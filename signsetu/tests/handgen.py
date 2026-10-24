"""Synthetic 21-point hands, so the pipeline can be tested without a webcam."""

# one entry per supported class: (fingers [index, middle, ring, little], thumb, pinch)
POSES = {
    "palm":      ([1, 1, 1, 1], "out", False),
    "four":      ([1, 1, 1, 1], "tucked", False),
    "fist":      ([0, 0, 0, 0], "tucked", False),
    "thumb":     ([0, 0, 0, 0], "up", False),
    "thumbdown": ([0, 0, 0, 0], "down", False),
    "point":     ([1, 0, 0, 0], "tucked", False),
    "peace":     ([1, 1, 0, 0], "tucked", False),
    "three":     ([1, 1, 1, 0], "tucked", False),
    "horns":     ([1, 0, 0, 1], "tucked", False),
    "pinky":     ([0, 0, 0, 1], "tucked", False),
    "call":      ([0, 0, 0, 1], "out", False),
    "ell":       ([1, 0, 0, 0], "out", False),
    "ok":        ([0, 1, 1, 1], "tucked", True),
}
# a pose that matches no class (middle + ring only)
UNSUPPORTED = ([0, 1, 1, 0], "tucked", False)

_KNUCKLE = {5: (0.42, 0.58), 9: (0.50, 0.56), 13: (0.56, 0.58), 17: (0.62, 0.62)}


def make_hand(fingers, thumb, pinch=False):
    lm = [[0.5, 0.5, 0.0] for _ in range(21)]
    lm[0] = [0.5, 0.9, 0.0]
    for base, (x, y) in _KNUCKLE.items():
        i = (base - 5) // 4
        lm[base] = [x, y, 0.0]
        lm[base + 1] = [x, 0.50, 0.0]                       # middle joint
        lm[base + 2] = [x, 0.40 if fingers[i] else 0.55, 0.0]
        lm[base + 3] = [x, 0.30 if fingers[i] else 0.62, 0.0]  # tip: above joint = extended
    lm[1], lm[2], lm[3] = [0.46, 0.82, 0.0], [0.40, 0.75, 0.0], [0.35, 0.70, 0.0]
    lm[4] = {"out": [0.25, 0.59, 0.0], "tucked": [0.50, 0.62, 0.0],
             "up": [0.25, 0.45, 0.0], "down": [0.25, 0.75, 0.0]}[thumb]
    if pinch:  # thumb tip touches index tip
        lm[8] = [0.42, 0.45, 0.0]
        lm[7] = [0.42, 0.40, 0.0]
        lm[6] = [0.42, 0.50, 0.0]
        lm[4] = [0.43, 0.46, 0.0]
    return lm


def hand_for(label):
    return make_hand(*POSES[label])
