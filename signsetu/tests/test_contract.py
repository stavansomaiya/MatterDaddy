"""Keeps the three places that know the class list from drifting apart."""
import json
import os
import re
import unittest
from backend import recognizer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = open(os.path.join(ROOT, "frontend", "index.html"), encoding="utf-8").read()


def signs_in_html():
    block = HTML[HTML.index("const SIGNS={"):HTML.index("const HN=")]
    return set(re.findall(r'(?:^|[\s,{])(\w+):\{e:"', block))


def words_in_html():
    block = HTML[HTML.index("const WORDS={"):HTML.index("Object.assign(HN,")]
    return set(re.findall(r'(?:^|[\s,{])(\w+):\{e:"', block))


class ContractTests(unittest.TestCase):
    def test_html_words_equal_labels_json_and_model(self):
        labels = json.load(open(os.path.join(ROOT, "backend", "labels.json"), encoding="utf-8"))
        self.assertEqual(words_in_html(), set(labels["words"]))
        from backend.words import WordModel
        self.assertEqual(set(WordModel().words), set(labels["words"]))

    def test_words_do_not_collide_with_shape_classes(self):
        labels = json.load(open(os.path.join(ROOT, "backend", "labels.json"), encoding="utf-8"))
        self.assertFalse(set(labels["words"]) & set(labels["classes"]))

    def test_every_word_has_hindi(self):
        for w in words_in_html():
            self.assertRegex(HTML, r"\b%s:\{e:\"[^\n]*hi:\{_:\"" % w)

    def test_frontend_words_use_final_only(self):
        self.assertIn("if(p.final&&k)commitMany([[\"W\",k,p.confidence]])", HTML)
        self.assertIn("/api/predict_word", HTML)

    def test_html_signs_equal_labels_json(self):
        labels = set(json.load(open(os.path.join(ROOT, "backend", "labels.json"), encoding="utf-8"))["classes"])
        self.assertEqual(signs_in_html(), labels)

    def test_every_class_has_english_and_hindi_text(self):
        block = HTML[HTML.index("const SIGNS={"):HTML.index("const HN=")]
        self.assertEqual(len(re.findall(r"\ben:\{", block)), len(recognizer.CLASSES))
        self.assertEqual(len(re.findall(r"\bhi:\{", block)), len(recognizer.CLASSES))

    def test_sentinels_do_not_collide_with_classes(self):
        self.assertFalse({"UNKNOWN", "NO_HAND"} & set(recognizer.CLASSES))

    def test_frontend_speaks_only_final_predictions(self):
        self.assertIn("if(p.final&&k)fs.push([h,k,p.confidence])", HTML)

class TestFrontendRegressions(unittest.TestCase):
    def test_two_hands_tracked_separately(self):
        self.assertIn("maxNumHands:2", HTML)
        self.assertIn("hSession(h)", HTML)

    def test_no_cdn_dependency(self):
        self.assertNotIn("cdn.jsdelivr.net", HTML)

    def test_language_and_place_change_are_silent(self):
        self.assertIn("commit(last,null,true,true)", HTML)
        self.assertIn("if(silent)return;", HTML)


if __name__ == "__main__":
    unittest.main()
