"""
Inverted Index Module for Information Storage and Retrieval.
Builds, maintains, serializes, and queries an inverted index structure:
Term -> Posting List { doc_id: term_frequency }
Also tracks document frequency, document lengths, and index metadata.
"""

import os
import pickle
from collections import defaultdict
import config
from ir_engine.preprocessing import preprocess_text

class InvertedIndex:
    def __init__(self, index_file_path=None):
        self.index_file_path = index_file_path or config.INDEX_STORAGE_PATH
        # Inverted index: term -> { doc_id: raw_term_frequency }
        self.inverted_index = defaultdict(dict)
        # Document frequency: term -> number of docs containing term
        self.doc_frequency = defaultdict(int)
        # Total tokens per document: doc_id -> int
        self.doc_lengths = {}
        # Document metadata: doc_id -> { 'title': ..., 'url': ..., 'category': ..., 'content': ... }
        self.documents = {}
        # Set of unique terms
        self.vocabulary = set()
        self.total_docs = 0
        self.is_loaded = False

    def build_index(self, doc_records):
        """
        Builds the inverted index from a list of document dicts.
        Each doc dict: { 'doc_id': ..., 'title': ..., 'url': ..., 'category': ..., 'content': ... }
        """
        self.inverted_index = defaultdict(dict)
        self.doc_frequency = defaultdict(int)
        self.doc_lengths = {}
        self.documents = {}
        self.vocabulary = set()
        self.total_docs = len(doc_records)

        for doc in doc_records:
            doc_id = doc['doc_id']
            self.documents[doc_id] = {
                'doc_id': doc_id,
                'title': doc['title'],
                'url': doc['url'],
                'category': doc['category'],
                'content': doc['content']
            }

            # Combined content with higher weight on title words
            title_tokens = preprocess_text(doc['title'])
            content_tokens = preprocess_text(doc['content'])
            category_tokens = preprocess_text(doc.get('category', ''))

            # Full token stream (title repeated 2x in stream to naturally emphasize title terms in TF)
            all_tokens = title_tokens + title_tokens + category_tokens + content_tokens
            self.doc_lengths[doc_id] = len(all_tokens)

            # Compute term frequencies in this document
            tf_counts = defaultdict(int)
            for token in all_tokens:
                tf_counts[token] += 1

            # Populate inverted index postings
            for term, count in tf_counts.items():
                self.inverted_index[term][doc_id] = count
                self.vocabulary.add(term)

        # Compute document frequencies
        for term, postings in self.inverted_index.items():
            self.doc_frequency[term] = len(postings)

        self.is_loaded = True
        return self.get_stats()

    def get_postings(self, term):
        """Returns { doc_id: term_frequency } for a given term, or empty dict."""
        return self.inverted_index.get(term, {})

    def get_doc_frequency(self, term):
        """Returns document frequency for term."""
        return self.doc_frequency.get(term, 0)

    def get_document(self, doc_id):
        """Returns document metadata dictionary."""
        return self.documents.get(doc_id)

    def save_index(self, file_path=None):
        """Serializes index state to disk."""
        target_path = file_path or self.index_file_path
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        data = {
            'inverted_index': dict(self.inverted_index),
            'doc_frequency': dict(self.doc_frequency),
            'doc_lengths': self.doc_lengths,
            'documents': self.documents,
            'vocabulary': self.vocabulary,
            'total_docs': self.total_docs
        }
        with open(target_path, 'wb') as f:
            pickle.dump(data, f)
        return True

    def load_index(self, file_path=None):
        """Loads index state from disk."""
        target_path = file_path or self.index_file_path
        if not os.path.exists(target_path):
            return False
        try:
            with open(target_path, 'rb') as f:
                data = pickle.load(f)
            self.inverted_index = defaultdict(dict, data['inverted_index'])
            self.doc_frequency = defaultdict(int, data['doc_frequency'])
            self.doc_lengths = data['doc_lengths']
            self.documents = data['documents']
            self.vocabulary = set(data['vocabulary'])
            self.total_docs = data['total_docs']
            self.is_loaded = True
            return True
        except Exception:
            return False

    def get_stats(self):
        """Returns summary statistics for the index."""
        total_postings = sum(len(p) for p in self.inverted_index.values())
        return {
            'vocabulary_size': len(self.vocabulary),
            'document_count': self.total_docs,
            'total_postings': total_postings,
            'is_ready': self.is_loaded and self.total_docs > 0
        }