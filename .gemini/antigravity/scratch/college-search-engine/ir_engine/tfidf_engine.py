"""
TF-IDF Retrieval and Vector Space Model (VSM) Engine.
Calculates Term Frequency (TF), Inverse Document Frequency (IDF),
Document/Query TF-IDF vectors, and Cosine Similarities.
"""

import math
from collections import defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from ir_engine.preprocessing import preprocess_text, preprocess_to_string

class TfidfRetrievalEngine:
    def __init__(self, indexer):
        self.indexer = indexer
        # Caches for fast scoring
        self.idf_cache = {}
        self.doc_vectors = {}      # doc_id -> { term: normalized_tfidf }
        self.doc_vector_norms = {} # doc_id -> Euclidean norm
        
        # Scikit-learn backup/verification vectorizer
        self.sklearn_vectorizer = None
        self.sklearn_matrix = None
        self.sklearn_doc_ids = []

    def build_model(self):
        """Precomputes IDF values and normalized document TF-IDF vectors."""
        if not self.indexer.is_loaded or self.indexer.total_docs == 0:
            return False

        n_docs = self.indexer.total_docs
        self.idf_cache = {}
        self.doc_vectors = defaultdict(dict)
        self.doc_vector_norms = defaultdict(float)

        # 1. Compute IDF for all terms in vocabulary
        # IDF(t) = log10((N + 1) / (DF(t) + 1)) + 1
        for term in self.indexer.vocabulary:
            df = self.indexer.get_doc_frequency(term)
            self.idf_cache[term] = math.log10((n_docs + 1) / (df + 1)) + 1.0

        # 2. Compute TF-IDF for all documents using the inverted index
        raw_doc_vectors = defaultdict(dict)
        for term, postings in self.indexer.inverted_index.items():
            idf = self.idf_cache.get(term, 1.0)
            for doc_id, tf_count in postings.items():
                # Sublinear TF: 1 + log10(tf)
                tf_weight = 1.0 + math.log10(tf_count) if tf_count > 0 else 0.0
                weight = tf_weight * idf
                raw_doc_vectors[doc_id][term] = weight

        # 3. Normalize document vectors to unit length (L2 norm)
        for doc_id, vector in raw_doc_vectors.items():
            norm_sq = sum(w * w for w in vector.values())
            norm = math.sqrt(norm_sq) if norm_sq > 0 else 1.0
            self.doc_vector_norms[doc_id] = norm
            self.doc_vectors[doc_id] = {term: w / norm for term, w in vector.items()}

        # 4. Fit Scikit-Learn TfidfVectorizer for cross-verification
        try:
            corpus = []
            self.sklearn_doc_ids = []
            for doc_id, doc in self.indexer.documents.items():
                full_text = f"{doc['title']} {doc['title']} {doc.get('category', '')} {doc['content']}"
                corpus.append(preprocess_to_string(full_text))
                self.sklearn_doc_ids.append(doc_id)

            if corpus:
                self.sklearn_vectorizer = TfidfVectorizer(norm='l2', smooth_idf=True, sublinear_tf=True)
                self.sklearn_matrix = self.sklearn_vectorizer.fit_transform(corpus)
        except Exception:
            pass

        return True

    def compute_query_vector(self, query_tokens):
        """
        Computes the normalized TF-IDF vector for a query.
        Returns: { term: normalized_weight }
        """
        if not query_tokens:
            return {}

        # Count query term frequencies
        q_tf = defaultdict(int)
        for t in query_tokens:
            q_tf[t] += 1

        raw_q_vector = {}
        for term, count in q_tf.items():
            idf = self.idf_cache.get(term, 0.0)
            if idf > 0:
                tf_weight = 1.0 + math.log10(count) if count > 0 else 0.0
                raw_q_vector[term] = tf_weight * idf

        # L2 normalize query vector
        norm_sq = sum(w * w for w in raw_q_vector.values())
        norm = math.sqrt(norm_sq) if norm_sq > 0 else 1.0
        return {t: w / norm for t, w in raw_q_vector.items()}

    def search_candidates(self, query_tokens):
        """
        Traverses inverted index postings for query tokens to find candidate documents
        and calculates exact Cosine Similarity.
        Returns: dict { doc_id: { 'cosine_sim': float, 'matched_terms': list } }
        """
        if not query_tokens or not self.doc_vectors:
            return {}

        query_vec = self.compute_query_vector(query_tokens)
        if not query_vec:
            return {}

        candidate_scores = defaultdict(float)
        matched_terms = defaultdict(set)

        # Inverted index traversal: only score documents that contain at least one query term
        for term, q_weight in query_vec.items():
            postings = self.indexer.get_postings(term)
            for doc_id in postings.keys():
                doc_vec = self.doc_vectors.get(doc_id, {})
                if term in doc_vec:
                    # Dot product of unit vectors = Cosine similarity
                    candidate_scores[doc_id] += q_weight * doc_vec[term]
                    matched_terms[doc_id].add(term)

        results = {}
        for doc_id, score in candidate_scores.items():
            # Bound cosine similarity between 0.0 and 1.0
            bounded_score = min(max(float(score), 0.0), 1.0)
            results[doc_id] = {
                'cosine_sim': round(bounded_score, 4),
                'matched_terms': sorted(list(matched_terms[doc_id]))
            }

        return results

    def get_related_documents(self, target_doc_id, top_n=3):
        """
        Finds related documents using Cosine Similarity between document vectors.
        """
        target_vec = self.doc_vectors.get(target_doc_id)
        if not target_vec:
            return []

        similarities = []
        for doc_id, vec in self.doc_vectors.items():
            if doc_id == target_doc_id:
                continue
            # Dot product of normalized vectors
            sim = sum(w * vec.get(term, 0.0) for term, w in target_vec.items())
            if sim > 0:
                doc = self.indexer.get_document(doc_id)
                if doc:
                    similarities.append({
                        'doc_id': doc_id,
                        'title': doc['title'],
                        'category': doc['category'],
                        'url': doc['url'],
                        'similarity': round(min(max(float(sim), 0.0), 1.0), 4)
                    })

        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities[:top_n]