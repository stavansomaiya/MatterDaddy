import unittest
from backend import recognizer
from tests.handgen import POSES, UNSUPPORTED, hand_for, make_hand


class RecognizerTests(unittest.TestCase):
    def test_every_supported_class_is_recognized(self):
        for label in POSES:
            with self.subTest(label=label):
                p = recognizer.predict(hand_for(label))
                self.assertEqual(p["label"], label)
                self.assertTrue(p["recognized"])
                self.assertGreater(p["confidence"], 0.7)

    def test_all_classes_in_labels_json_are_testable(self):
        self.assertEqual(set(POSES), set(recognizer.CLASSES))

    def test_no_hand_is_explicit(self):
        self.assertEqual(recognizer.predict(None),
                         {"label": "NO_HAND", "confidence": 0.0, "recognized": False})

    def test_unsupported_sign_returns_explicit_unknown(self):
        p = recognizer.predict(make_hand(*UNSUPPORTED))
        self.assertEqual(p, {"label": "UNKNOWN", "confidence": 0.0, "recognized": False})

    def test_min_confidence_rejects_weak_rules(self):
        self.assertEqual(recognizer.predict(hand_for("fist"), min_confidence=0.95)["label"], "UNKNOWN")

    def test_hand_size_does_not_matter(self):
        for label in ("palm", "peace", "ok", "horns"):
            big = hand_for(label)
            small = [[0.5 + (x - 0.5) * 0.4, 0.5 + (y - 0.5) * 0.4, z] for x, y, z in big]
            self.assertEqual(recognizer.predict(small)["label"], label)


if __name__ == "__main__":
    unittest.main()
