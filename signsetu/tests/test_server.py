import unittest
from backend.server import create_app, load_config
from tests.handgen import UNSUPPORTED, hand_for, make_hand

CFG = dict(load_config(), hold_frames=4, cooldown_frames=3, rearm_no_hand_frames=3)


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.c = create_app(CFG).test_client()

    def post(self, lm, sid="s1", path="/api/predict"):
        return self.c.post(path, json={"session": sid, "landmarks": lm})

    def test_health_lists_classes(self):
        j = self.c.get("/api/health").get_json()
        self.assertTrue(j["ok"])
        self.assertIn("pinky", j["classes"])

    def test_index_served(self):
        r = self.c.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"SignSetu", r.data)

    def test_response_has_contract_fields(self):
        j = self.post(hand_for("palm")).get_json()
        for k in ("label", "confidence", "recognized", "final", "progress"):
            self.assertIn(k, j)
        self.assertEqual(j["label"], "palm")

    def test_full_sequence_sign_to_final_prediction(self):
        outs = [self.post(hand_for("pinky")).get_json() for _ in range(4)]
        self.assertEqual([o["final"] for o in outs], [False, False, False, True])
        self.assertEqual(outs[-1]["label"], "pinky")

    def test_no_hands(self):
        j = self.post(None).get_json()
        self.assertEqual((j["label"], j["recognized"], j["final"]), ("NO_HAND", False, False))

    def test_unsupported_sign(self):
        for _ in range(10):
            j = self.post(make_hand(*UNSUPPORTED)).get_json()
        self.assertEqual((j["label"], j["recognized"], j["final"]), ("UNKNOWN", False, False))

    def test_repeated_predictions_finalize_once(self):
        finals = [self.post(hand_for("thumb")).get_json()["final"] for _ in range(40)]
        self.assertEqual(sum(finals), 1)

    def test_sessions_are_independent(self):
        for _ in range(3):
            self.post(hand_for("palm"), sid="A")
        self.assertTrue(self.post(hand_for("palm"), sid="A").get_json()["final"])
        self.assertFalse(self.post(hand_for("palm"), sid="B").get_json()["final"])

    def test_reset_then_same_sign_can_finalize_again(self):
        for _ in range(4):
            self.post(hand_for("palm"))
        self.c.post("/api/reset", json={"session": "s1"})
        finals = [self.post(hand_for("palm")).get_json()["final"] for _ in range(4)]
        self.assertTrue(finals[-1])

    def test_bad_inputs_get_clear_errors_not_crashes(self):
        bad = [
            {"session": "s", "landmarks": [[0, 0, 0]] * 20},        # too few points
            {"session": "s", "landmarks": "hand"},                  # wrong type
            {"session": "s", "landmarks": [[0, 0, 0]] * 20 + [[None, 1, 0]]},
            {"landmarks": None},                                    # no session
        ]
        for body in bad:
            with self.subTest(body=str(body)[:40]):
                r = self.c.post("/api/predict", json=body)
                self.assertEqual(r.status_code, 400)
                self.assertIn("error", r.get_json())
        r = self.c.post("/api/predict", data="not json", content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_nan_rejected(self):
        lm = hand_for("palm")
        lm[3][0] = float("nan")
        r = self.c.post("/api/predict", data='{"session":"s","landmarks":' +
                        str(lm).replace("nan", "NaN") + '}', content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_session_table_is_bounded(self):
        app = create_app(dict(CFG, max_sessions=5))
        c = app.test_client()
        for i in range(20):
            self.assertEqual(c.post("/api/predict", json={"session": "x%d" % i, "landmarks": None}).status_code, 200)


if __name__ == "__main__":
    unittest.main()
