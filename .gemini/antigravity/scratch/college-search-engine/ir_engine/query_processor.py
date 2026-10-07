"""
Query Processor and Query Expansion Module for Information Storage and Retrieval.
Handles query parsing, stopword filtering, tokenization, phrase extraction,
and optional college-domain synonym-based query expansion.
"""

import re
import config
from ir_engine.preprocessing import preprocess_text

class QueryProcessor:
    def __init__(self, synonym_dict=None):
        self.synonyms = synonym_dict or config.QUERY_SYNONYMS

    def process_query(self, raw_query, enable_expansion=False):
        """
        Processes a raw query string.
        Returns:
            processed_tokens: list of stemmed tokens for primary matching
            all_tokens: list of tokens (including expanded synonyms if enabled)
            metadata: information about the query processing for the UI
        """
        if not raw_query:
            return [], [], {'is_expanded': False, 'synonyms_added': [], 'phrases': []}

        # Check for phrase queries enclosed in quotes
        phrases = re.findall(r'"([^"]+)"', raw_query)

        # Primary query tokens
        original_tokens = preprocess_text(raw_query)

        synonyms_added = []
        expanded_tokens = list(original_tokens)

        if enable_expansion:
            # Check individual query words for synonym expansions
            raw_words = re.findall(r'[a-zA-Z]+', raw_query.lower())
            for word in raw_words:
                if word in self.synonyms:
                    for syn in self.synonyms[word]:
                        syn_tokens = preprocess_text(syn)
                        for st in syn_tokens:
                            if st not in expanded_tokens:
                                expanded_tokens.append(st)
                                if syn not in synonyms_added:
                                    synonyms_added.append(syn)

        metadata = {
            'original_query': raw_query,
            'is_expanded': bool(enable_expansion and synonyms_added),
            'synonyms_added': synonyms_added,
            'phrases': phrases,
            'original_tokens': original_tokens,
            'expanded_tokens': expanded_tokens
        }

        return original_tokens, expanded_tokens, metadata