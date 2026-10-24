"""Turns noisy per-frame predictions into FINALIZED ones.

Contract: speech is triggered only by a prediction with final == True.
A sign becomes final after being the same recognized label for `hold_frames`
consecutive frames. After that:
  * the same sign is not finalized again until the hand has left the frame for
    `rearm_no_hand_frames` frames (holding a sign never repeats speech);
  * any finalized sign starts a `cooldown_frames` window with no new finals;
  * a DIFFERENT sign can finalize once its own hold completes and the cooldown
    has passed.
One Stabilizer per browser session. State is in memory only, so an application
restart simply starts a clean session.
"""


class Stabilizer:
    def __init__(self, hold_frames=8, cooldown_frames=10, rearm_no_hand_frames=6):
        self.hold = max(1, int(hold_frames))
        self.cooldown_frames = int(cooldown_frames)
        self.rearm = int(rearm_no_hand_frames)
        self.reset()

    def reset(self):
        self.cand = None
        self.streak = 0
        self.cool = 0
        self.last_final = None
        self.no_hand_run = 0

    def update(self, pred):
        """pred: dict from recognizer.predict(). Returns pred + final + progress."""
        out = dict(pred)
        out["final"] = False
        out["progress"] = 0.0
        if self.cool > 0:
            self.cool -= 1

        if pred["label"] == "NO_HAND":
            self.no_hand_run += 1
            self.cand, self.streak = None, 0
            if self.no_hand_run >= self.rearm:
                self.last_final = None
            return out
        self.no_hand_run = 0

        if not pred["recognized"]:  # UNKNOWN pose: breaks any streak, never re-arms
            self.cand, self.streak = None, 0
            return out

        if pred["label"] == self.cand:
            self.streak += 1
        else:
            self.cand, self.streak = pred["label"], 1
        out["progress"] = round(min(1.0, self.streak / self.hold), 2)

        if (self.streak >= self.hold and self.cool == 0
                and pred["label"] != self.last_final):
            out["final"] = True
            self.last_final = pred["label"]
            self.cool = self.cooldown_frames
        return out
