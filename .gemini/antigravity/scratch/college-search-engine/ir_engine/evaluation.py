"""
Information Storage & Retrieval (ISR) Evaluation Module.
Implements:
- Precision@K
- Recall@K
- F1-Score@K
- Reciprocal Rank (RR) & Mean Reciprocal Rank (MRR)
- Average Precision (AP) & Mean Average Precision (MAP)
Provides both query-level and macro-level performance metrics.
"""

import json
import os
import config

class IREvaluator:
    def __init__(self, eval_file_path=None):
        self.eval_file_path = eval_file_path or config.EVALUATION_QUERIES_PATH

    def load_benchmark_queries(self, file_path=None):
        """Loads labeled evaluation queries with ground truth relevant document IDs."""
        path = file_path or self.eval_file_path
        if not os.path.exists(path):
            return []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []

    @staticmethod
    def calculate_query_metrics(retrieved_doc_ids, relevant_doc_ids, k=5):
        """
        Calculates P@K, R@K, F1@K, Reciprocal Rank, and Average Precision for a single query.
        """
        relevant_set = set(relevant_doc_ids)
        total_relevant = len(relevant_set)

        if total_relevant == 0:
            return {
                'precision_at_k': 0.0,
                'recall_at_k': 0.0,
                'f1_at_k': 0.0,
                'reciprocal_rank': 0.0,
                'average_precision': 0.0,
                'retrieved_count': len(retrieved_doc_ids),
                'relevant_count': 0,
                'relevant_retrieved_at_k': 0
            }

        # Truncate at K for @K metrics
        top_k = retrieved_doc_ids[:k]
        rel_retrieved_k = [doc_id for doc_id in top_k if doc_id in relevant_set]
        num_rel_retrieved_k = len(rel_retrieved_k)

        # Precision@K = |Retrieved_K ∩ Relevant| / K
        precision_at_k = num_rel_retrieved_k / k if k > 0 else 0.0

        # Recall@K = |Retrieved_K ∩ Relevant| / |Relevant|
        recall_at_k = num_rel_retrieved_k / total_relevant if total_relevant > 0 else 0.0

        # F1@K = 2 * (P * R) / (P + R)
        if (precision_at_k + recall_at_k) > 0:
            f1_at_k = 2 * (precision_at_k * recall_at_k) / (precision_at_k + recall_at_k)
        else:
            f1_at_k = 0.0

        # Reciprocal Rank: 1 / rank of first relevant retrieved document (1-indexed)
        rr = 0.0
        for rank, doc_id in enumerate(retrieved_doc_ids, start=1):
            if doc_id in relevant_set:
                rr = 1.0 / rank
                break

        # Average Precision (AP): Sum(P@r * rel(r)) / total_relevant
        cumulative_rel = 0
        sum_precision = 0.0
        for rank, doc_id in enumerate(retrieved_doc_ids, start=1):
            if doc_id in relevant_set:
                cumulative_rel += 1
                p_at_rank = cumulative_rel / rank
                sum_precision += p_at_rank

        ap = sum_precision / total_relevant if total_relevant > 0 else 0.0

        return {
            'precision_at_k': round(precision_at_k, 4),
            'recall_at_k': round(recall_at_k, 4),
            'f1_at_k': round(f1_at_k, 4),
            'reciprocal_rank': round(rr, 4),
            'average_precision': round(ap, 4),
            'retrieved_count': len(retrieved_doc_ids),
            'relevant_count': total_relevant,
            'relevant_retrieved_at_k': num_rel_retrieved_k
        }

    def evaluate_engine(self, search_func, queries_list=None, k=5):
        """
        Executes benchmark evaluation across all queries.
        search_func takes (query_string) and returns a list of result dicts containing 'doc_id'.
        """
        benchmark = queries_list or self.load_benchmark_queries()
        if not benchmark:
            return {
                'macro_precision': 0.0,
                'macro_recall': 0.0,
                'macro_f1': 0.0,
                'mrr': 0.0,
                'map': 0.0,
                'total_queries': 0,
                'query_results': []
            }

        query_results = []
        p_list = []
        r_list = []
        f1_list = []
        rr_list = []
        ap_list = []

        for item in benchmark:
            query = item['query']
            relevant_docs = item['relevant_documents']

            # Run retrieval
            search_output = search_func(query)
            retrieved_ids = [r['doc_id'] for r in search_output]

            metrics = self.calculate_query_metrics(retrieved_ids, relevant_docs, k=k)
            metrics['query'] = query
            metrics['relevant_documents'] = relevant_docs
            metrics['retrieved_documents'] = retrieved_ids[:k]
            metrics['category'] = item.get('category', 'General')

            query_results.append(metrics)
            p_list.append(metrics['precision_at_k'])
            r_list.append(metrics['recall_at_k'])
            f1_list.append(metrics['f1_at_k'])
            rr_list.append(metrics['reciprocal_rank'])
            ap_list.append(metrics['average_precision'])

        n = len(query_results)
        macro_p = sum(p_list) / n if n > 0 else 0.0
        macro_r = sum(r_list) / n if n > 0 else 0.0
        macro_f1 = sum(f1_list) / n if n > 0 else 0.0
        mrr = sum(rr_list) / n if n > 0 else 0.0
        map_score = sum(ap_list) / n if n > 0 else 0.0

        return {
            'macro_precision': round(macro_p, 4),
            'macro_recall': round(macro_r, 4),
            'macro_f1': round(macro_f1, 4),
            'mrr': round(mrr, 4),
            'map': round(map_score, 4),
            'k': k,
            'total_queries': n,
            'query_results': query_results
        }