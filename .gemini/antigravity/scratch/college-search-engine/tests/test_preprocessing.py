"""
Unit Tests for Text Preprocessing Module.
"""

import unittest
from ir_engine.preprocessing import TextPreprocessor, preprocess_text, preprocess_to_string

class TestPreprocessing(unittest.TestCase):
    def setUp(self):
        self.preprocessor = TextPreprocessor()

    def test_clean_html(self):
        html = "<p>Welcome to <strong>Apex College</strong>.<script>alert(1);</script></p>"
        cleaned = self.preprocessor.clean_html(html)
        self.assertNotIn("<p>", cleaned)
        self.assertNotIn("<script>", cleaned)
        self.assertNotIn("alert", cleaned)
        self.assertIn("Welcome to", cleaned)
        self.assertIn("Apex College", cleaned)

    def test_tokenization_and_lowercasing(self):
        text = "Computer Engineering & AI Technologies!"
        tokens = self.preprocessor.tokenize(text)
        self.assertIn("computer", tokens)
        self.assertIn("engineering", tokens)
        self.assertIn("ai", tokens)
        self.assertIn("technologies", tokens)

    def test_stopword_removal(self):
        text = "This is a detailed guide for the students"
        tokens = self.preprocessor.preprocess_text(text, apply_stemming=False)
        self.assertNotIn("this", tokens)
        self.assertNotIn("is", tokens)
        self.assertNotIn("a", tokens)
        self.assertNotIn("for", tokens)
        self.assertNotIn("the", tokens)
        self.assertIn("detailed", tokens)
        self.assertIn("guide", tokens)
        self.assertIn("students", tokens)

    def test_preserved_acronyms(self):
        # AI, CS, IT should never be discarded by stopword or short token filters
        text = "AI and IT department in CS engineering"
        tokens = self.preprocessor.preprocess_text(text, apply_stemming=True)
        self.assertIn("ai", tokens)
        self.assertIn("it", tokens)
        self.assertIn("cs", tokens)

    def test_stemming(self):
        tokens = self.preprocessor.preprocess_text("Engineering admissions", apply_stemming=True)
        self.assertIn("engin", tokens)
        self.assertIn("admiss", tokens)

    def test_empty_input(self):
        self.assertEqual(preprocess_text(""), [])
        self.assertEqual(preprocess_text("   "), [])
        self.assertEqual(preprocess_to_string(""), "")

if __name__ == '__main__':
    unittest.main()