import unittest
from backend.stabilizer import Stabilizer

HAND = lambda l: {"label": l, "confidence": 0.85, "recognized": True}
NONE = {"label": "NO_HAND", "confidence": 0.0, "recognized": False}
UNK = {"label": "UNKNOWN", "confidence": 0.0, "recognized": False}


def run(stab, seq):
    return [stab.update(p) for p in seq]


class StabilizerTests(unittest.TestCase):
    def mk(self):
        return Stabilizer(hold_frames=4, cooldown_frames=3, rearm_no_hand_frames=3)

    def finals(self, outs):
        return [o["label"] for o in outs if o["final"]]

    def test_final_only_after_hold(self):
        outs = run(self.mk(), [HAND("palm")] * 4)
        self.assertEqual([o["final"] for o in outs], [False, False, False, True])
        self.assertEqual(outs[1]["progress"], 0.5)

    def test_holding_a_sign_speaks_once(self):
        self.assertEqual(self.finals(run(self.mk(), [HAND("palm")] * 60)), ["palm"])

    def test_flicker_never_finalizes(self):
        seq = [HAND("palm"), HAND("fist")] * 20
        self.assertEqual(self.finals(run(self.mk(), seq)), [])

    def test_unknown_pose_breaks_streak(self):
        seq = [HAND("palm")] * 3 + [UNK] + [HAND("palm")] * 3
        self.assertEqual(self.finals(run(self.mk(), seq)), [])

    def test_same_sign_again_needs_hand_to_leave(self):
        s = self.mk()
        seq = [HAND("palm")] * 4 + [NONE] * 3 + [HAND("palm")] * 4
        self.assertEqual(self.finals(run(s, seq)), ["palm", "palm"])

    def test_brief_hand_loss_does_not_repeat(self):
        seq = [HAND("palm")] * 4 + [NONE] * 2 + [HAND("palm")] * 10
        self.assertEqual(self.finals(run(self.mk(), seq)), ["palm"])

    def test_unknown_pose_does_not_rearm(self):
        seq = [HAND("palm")] * 4 + [UNK] * 10 + [HAND("palm")] * 10
        self.assertEqual(self.finals(run(self.mk(), seq)), ["palm"])

    def test_different_sign_finalizes_after_its_own_hold(self):
        seq = [HAND("palm")] * 4 + [HAND("fist")] * 10
        self.assertEqual(self.finals(run(self.mk(), seq)), ["palm", "fist"])

    def test_reset_clears_state(self):
        s = self.mk()
        run(s, [HAND("palm")] * 4)
        s.reset()
        self.assertEqual(self.finals(run(s, [HAND("palm")] * 4)), ["palm"])


if __name__ == "__main__":
    unittest.main()
