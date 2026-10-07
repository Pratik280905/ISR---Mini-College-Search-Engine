"""
Unit Tests for Information Retrieval Evaluation Metrics (P@K, R@K, F1, MRR, MAP).
"""

import unittest
from ir_engine.evaluation import IREvaluator

class TestEvaluation(unittest.TestCase):
    def test_precision_recall_f1(self):
        # Retrieved: ['d1', 'd2', 'd3', 'd4', 'd5']
        # Relevant:  ['d2', 'd4']  (total 2 relevant)
        retrieved = ['d1', 'd2', 'd3', 'd4', 'd5']
        relevant = ['d2', 'd4']

        # At K = 4:
        # Top 4 retrieved: ['d1', 'd2', 'd3', 'd4'] -> 2 relevant ('d2', 'd4')
        # Precision@4 = 2 / 4 = 0.50
        # Recall@4 = 2 / 2 = 1.00
        # F1 = 2 * (0.5 * 1.0) / (0.5 + 1.0) = 1.0 / 1.5 = 0.6667
        metrics = IREvaluator.calculate_query_metrics(retrieved, relevant, k=4)
        self.assertAlmostEqual(metrics['precision_at_k'], 0.50, places=3)
        self.assertAlmostEqual(metrics['recall_at_k'], 1.00, places=3)
        self.assertAlmostEqual(metrics['f1_at_k'], 0.6667, places=3)

    def test_reciprocal_rank(self):
        # Relevant doc 'd2' is at rank 2
        # RR = 1 / 2 = 0.5
        retrieved = ['d1', 'd2', 'd3']
        relevant = ['d2']
        metrics = IREvaluator.calculate_query_metrics(retrieved, relevant, k=3)
        self.assertAlmostEqual(metrics['reciprocal_rank'], 0.5, places=3)

        # Relevant doc 'd1' is at rank 1
        # RR = 1 / 1 = 1.0
        retrieved_first = ['d1', 'd2']
        metrics_first = IREvaluator.calculate_query_metrics(retrieved_first, relevant, k=2)
        self.assertAlmostEqual(metrics_first['reciprocal_rank'], 0.5, places=3)

        # No relevant doc retrieved
        metrics_zero = IREvaluator.calculate_query_metrics(['x', 'y', 'z'], relevant, k=3)
        self.assertAlmostEqual(metrics_zero['reciprocal_rank'], 0.0, places=3)

    def test_average_precision(self):
        # Retrieved: ['d1', 'd2', 'd3', 'd4', 'd5']
        # Relevant: ['d1', 'd3']
        # Rank 1: d1 relevant -> P@1 = 1/1 = 1.0
        # Rank 2: d2 not relevant
        # Rank 3: d3 relevant -> P@3 = 2/3 = 0.6667
        # Average Precision = (1.0 + 0.6667) / 2 = 0.8333
        retrieved = ['d1', 'd2', 'd3', 'd4', 'd5']
        relevant = ['d1', 'd3']
        metrics = IREvaluator.calculate_query_metrics(retrieved, relevant, k=5)
        self.assertAlmostEqual(metrics['average_precision'], 0.8333, places=3)

    def test_system_macro_evaluation(self):
        evaluator = IREvaluator()
        queries = [
            {'query': 'comp admission', 'relevant_documents': ['d1']},
            {'query': 'placement', 'relevant_documents': ['d2']}
        ]
        # Mock search function returning fixed lists
        def mock_search(q):
            if 'comp' in q:
                return [{'doc_id': 'd1'}, {'doc_id': 'd3'}]
            return [{'doc_id': 'd2'}, {'doc_id': 'd4'}]

        summary = evaluator.evaluate_engine(mock_search, queries_list=queries, k=2)
        self.assertEqual(summary['total_queries'], 2)
        self.assertAlmostEqual(summary['mrr'], 1.0, places=3)
        self.assertAlmostEqual(summary['map'], 1.0, places=3)

if __name__ == '__main__':
    unittest.main()