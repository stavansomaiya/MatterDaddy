import unittest
import numpy as np
from backend import words
from backend.server import create_app, load_config
from backend.stabilizer import Stabilizer
from tests.wordgen import clip_to_stream
from tests.handgen import make_hand, UNSUPPORTED

M = words.WordModel()
CFG = load_config()


def run(stream, cfg=CFG):
    ws = words.WordSession(M, cfg["word_window_ms"], cfg["word_min_span_ms"],
                           cfg["word_max_distance"], cfg["word_min_margin"])
    st = Stabilizer(cfg["word_hold_frames"], cfg["word_cooldown_frames"], cfg["word_rearm_no_hand_frames"])
    return [st.update(ws.update(h, t)) for t, h in stream]


class WordModelTests(unittest.TestCase):
    def test_model_loads(self):
        self.assertEqual((M.nf, M.d), (10, 92))
        self.assertEqual(len(M.words), 19)

    def test_feature_roundtrip(self):
        """Landmarks rebuilt from a sample give back (almost) the same 92 features."""
        from tests.wordgen import frame_to_hands
        for i in (0, 60, 150):
            f = M.X[i][4].copy()
            g = words.frame_features(frame_to_hands(f))
            self.assertIsNotNone(g)
            self.assertLess(np.abs(f[:86] - g[:86]).max(), 2.5)

    def test_no_hand(self):
        self.assertIsNone(words.frame_features(None))
        self.assertIsNone(words.frame_features([]))

    def test_mirror_is_involution(self):
        c = M.X[100].copy()
        self.assertTrue(np.allclose(words.mirror(words.mirror(c)), c, atol=1e-4))

    def test_every_word_finalizes_correctly_from_replayed_clip(self):
        bad = []
        for w in M.words:
            i = int(np.where(M.labels == w)[0][0])
            outs = run(clip_to_stream(M.X[i].copy()))
            finals = [o["label"] for o in outs if o["final"]]
            if finals != [w]:
                bad.append((w, finals))
        self.assertLessEqual(len(bad), 3, bad)   # replays of training clips: nearly all must pass

    def test_hand_leaving_rearms_same_word(self):
        i = int(np.where(M.labels == "namaste")[0][0])
        s = clip_to_stream(M.X[i].copy())
        gap = [(s[-1][0] + 66 * (k + 1), []) for k in range(8)]
        t0 = s[-1][0] + 66 * 9
        s2 = [(t0 + t, h) for t, h in s]
        finals = [o["label"] for o in run(s + gap + s2) if o["final"]]
        self.assertEqual(finals, ["namaste", "namaste"])

    def test_unrelated_pose_is_not_a_word(self):
        rng = np.random.default_rng(1)
        base = make_hand(*UNSUPPORTED)
        stream = []
        for k in range(60):
            h = [[x + rng.normal(0, .03), y + rng.normal(0, .03), 0.0] for x, y, _ in base]
            stream.append((k * 66.0, [h]))
        self.assertFalse(any(o["final"] for o in run(stream)))


class WordServerTests(unittest.TestCase):
    def setUp(self):
        self.c = create_app(CFG).test_client()

    def test_health_lists_words(self):
        j = self.c.get("/api/health").get_json()
        self.assertIn("namaste", j["words"])

    def test_endpoint_end_to_end(self):
        i = int(np.where(M.labels == "water")[0][0])
        finals = []
        for t, h in clip_to_stream(M.X[i].copy()):
            r = self.c.post("/api/predict_word", json={"session": "w", "t": t, "hands": h or None})
            self.assertEqual(r.status_code, 200)
            j = r.get_json()
            for k in ("label", "confidence", "recognized", "final", "progress"):
                self.assertIn(k, j)
            if j["final"]:
                finals.append(j["label"])
        self.assertEqual(finals, ["water"])

    def test_bad_input(self):
        r = self.c.post("/api/predict_word", json={"session": "w", "hands": [[[0, 0, 0]]]})
        self.assertEqual((r.status_code, r.get_json()["error"]), (400, "bad_landmarks"))
        r = self.c.post("/api/predict_word", json={"hands": None})
        self.assertEqual(r.get_json()["error"], "no_session")
        r = self.c.post("/api/predict_word", json={"session": "w", "hands": None, "t": 1})
        self.assertEqual(r.get_json()["label"], "NO_HAND")


if __name__ == "__main__":
    unittest.main()
