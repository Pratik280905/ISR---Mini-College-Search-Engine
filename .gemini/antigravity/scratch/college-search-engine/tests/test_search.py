"""
Unit and Integration Tests for Inverted Index, TF-IDF Retrieval, and Ranking Engine.
"""

import unittest
from ir_engine.indexer import InvertedIndex
from ir_engine.tfidf_engine import TfidfRetrievalEngine
from ir_engine.ranking import RankingEngine
from ir_engine.query_processor import QueryProcessor

class TestSearchAndRanking(unittest.TestCase):
    def setUp(self):
        self.sample_docs = [
            {
                "doc_id": "test_01",
                "title": "Computer Engineering Admission Criteria",
                "url": "https://college.edu/comp-adm",
                "category": "Admission",
                "content": "Students applying for Computer Engineering admission must meet eligibility cutoffs."
            },
            {
                "doc_id": "test_02",
                "title": "Mechanical Engineering Department Workshop",
                "url": "https://college.edu/mech-dept",
                "category": "Department",
                "content": "Mechanical engineering workshop includes machining, CAD/CAM, and thermal labs."
            },
            {
                "doc_id": "test_03",
                "title": "Hostel Facilities and Accommodation",
                "url": "https://college.edu/hostel",
                "category": "Facilities",
                "content": "Hostel accommodation is available for computer engineering and other branch students."
            }
        ]

        self.indexer = InvertedIndex()
        self.indexer.build_index(self.sample_docs)
        self.tfidf = TfidfRetrievalEngine(self.indexer)
        self.tfidf.build_model()
        self.ranker = RankingEngine(self.indexer, self.tfidf)
        self.qp = QueryProcessor()

    def test_inverted_index_postings(self):
        # 'comput' should appear in test_01 and test_03
        postings = self.indexer.get_postings('comput')
        self.assertIn('test_01', postings)
        self.assertIn('test_03', postings)
        self.assertNotIn('test_02', postings)
        self.assertEqual(self.indexer.get_doc_frequency('comput'), 2)

    def test_tfidf_cosine_search(self):
        query_tokens = ['comput', 'engin']
        results = self.tfidf.search_candidates(query_tokens)
        self.assertIn('test_01', results)
        self.assertGreater(results['test_01']['cosine_sim'], 0.0)

    def test_title_match_boost(self):
        # For query 'computer engineering admission', test_01 has exact title match and should rank highest
        orig_tokens, query_tokens, _ = self.qp.process_query("computer engineering admission", enable_expansion=False)
        ranked = self.ranker.rank_documents("computer engineering admission", query_tokens)
        self.assertGreater(len(ranked), 0)
        self.assertEqual(ranked[0]['doc_id'], 'test_01')
        self.assertGreater(ranked[0]['title_score'], 0.5)

    def test_category_filter(self):
        orig_tokens, query_tokens, _ = self.qp.process_query("computer engineering", enable_expansion=False)
        # Filter for Facilities only
        ranked = self.ranker.rank_documents("computer engineering", query_tokens, filter_category="Facilities")
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]['doc_id'], 'test_03')

    def test_query_expansion(self):
        orig, exp, meta = self.qp.process_query("fees", enable_expansion=True)
        self.assertTrue(meta['is_expanded'])
        self.assertIn('tuition', meta['synonyms_added'])
        # Expanded tokens should contain stemmed synonyms
        self.assertIn('tuition', exp)

    def test_snippet_generation(self):
        snippet = self.ranker.generate_snippet(
            "This is a paragraph where computer engineering students learn programming.",
            ['comput', 'engin']
        )
        self.assertIn("search-highlight", snippet)

if __name__ == '__main__':
    unittest.main()