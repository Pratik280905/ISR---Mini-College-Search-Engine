"""
Advanced Ranking and Snippet Generation Module.
Combines TF-IDF Cosine Similarity with Title Match, Category Match, and Relevance Feedback:
Final Score = 0.70 * TF-IDF Cosine + 0.20 * Title Match + 0.10 * Category Match + Feedback Bonus
Also extracts highlighted query snippets securely without XSS vulnerabilities.
"""

import re
import html
import config
from ir_engine.preprocessing import preprocess_text

class RankingEngine:
    def __init__(self, indexer, tfidf_engine, db_manager=None):
        self.indexer = indexer
        self.tfidf_engine = tfidf_engine
        self.db_manager = db_manager
        self.weight_tfidf = config.WEIGHT_TFIDF
        self.weight_title = config.WEIGHT_TITLE
        self.weight_field = config.WEIGHT_FIELD
        self.snippet_length = config.SNIPPET_LENGTH

    def compute_title_score(self, query_str, query_tokens, title_str):
        """
        Calculates title match score (0.0 to 1.0):
        - Exact query substring match gives 1.0
        - Otherwise ratio of matched query tokens in title
        """
        if not title_str or not query_tokens:
            return 0.0

        q_clean = query_str.lower().strip()
        t_clean = title_str.lower().strip()

        # Check full phrase match
        if q_clean in t_clean:
            return 1.0

        # Token overlap ratio
        title_tokens = set(preprocess_text(title_str))
        q_token_set = set(query_tokens)
        matched = q_token_set.intersection(title_tokens)
        overlap = len(matched) / len(q_token_set) if q_token_set else 0.0
        return round(float(overlap), 4)

    def compute_category_score(self, query_str, query_tokens, category_str):
        """
        Calculates category match score (0.0 to 1.0)
        """
        if not category_str or not query_tokens:
            return 0.0

        c_clean = category_str.lower().strip()
        if c_clean in query_str.lower():
            return 1.0

        category_tokens = set(preprocess_text(category_str))
        q_token_set = set(query_tokens)
        matched = q_token_set.intersection(category_tokens)
        overlap = len(matched) / len(q_token_set) if q_token_set else 0.0
        return round(float(overlap), 4)

    def generate_snippet(self, content, query_tokens, max_length=None):
        """
        Generates a snippet of ~150-250 characters centered around the highest concentration
        of matching query terms, safely escaping text and highlighting keywords.
        """
        max_length = max_length or self.snippet_length
        if not content:
            return "No content preview available."

        # Clean HTML tags and normalize whitespace for snippet analysis
        clean_text = re.sub(r'<[^>]+>', ' ', content)
        clean_text = ' '.join(clean_text.split())

        # If text is shorter than max length, use whole text
        if len(clean_text) <= max_length:
            best_window = clean_text
            is_start = True
            is_end = True
        else:
            # Split into words to find best window
            words = clean_text.split()
            best_score = -1
            best_idx = 0
            window_word_count = max(20, max_length // 7)

            # Preprocessed query tokens for matching
            q_stems = set(query_tokens)

            for i in range(0, max(1, len(words) - window_word_count + 1), 4):
                window_words = words[i:i + window_word_count]
                window_stems = preprocess_text(' '.join(window_words))
                match_count = sum(1 for w in window_stems if w in q_stems)
                if match_count > best_score:
                    best_score = match_count
                    best_idx = i

            selected_words = words[best_idx:best_idx + window_word_count]
            best_window = ' '.join(selected_words)
            is_start = (best_idx == 0)
            is_end = (best_idx + window_word_count >= len(words))

        # Safe HTML escaping first
        safe_snippet = html.escape(best_window)

        # Highlight query terms safely
        if query_tokens:
            for token in set(query_tokens):
                # Pattern to match token root in word boundaries
                pattern = re.compile(rf'(\b{re.escape(token)}[a-zA-Z]*)', re.IGNORECASE)
                safe_snippet = pattern.sub(r'<mark class="search-highlight">\1</mark>', safe_snippet)

        prefix = "" if is_start else "... "
        suffix = "" if is_end else " ..."
        return f"{prefix}{safe_snippet}{suffix}"

    def rank_documents(self, raw_query, query_tokens, filter_category=None, sort_by='relevance'):
        """
        Main retrieval and ranking pipeline:
        1. Query candidate documents from TF-IDF vector space
        2. Compute Title Match and Category Match scores
        3. Add Relevance Feedback bonus if applicable
        4. Calculate Final Composite Score
        5. Generate snippets
        6. Apply filters and sorting
        """
        candidate_map = self.tfidf_engine.search_candidates(query_tokens)
        if not candidate_map:
            return []

        # Get relevant documents from user feedback if db_manager available
        feedback_docs = set()
        if self.db_manager:
            try:
                feedback_docs = set(self.db_manager.get_relevant_doc_ids_for_query(raw_query))
            except Exception:
                pass

        ranked_results = []
        for doc_id, stats in candidate_map.items():
            doc = self.indexer.get_document(doc_id)
            if not doc:
                continue

            # Category filter
            if filter_category and filter_category != 'All' and doc.get('category') != filter_category:
                continue

            tfidf_sim = stats['cosine_sim']
            title_score = self.compute_title_score(raw_query, query_tokens, doc['title'])
            category_score = self.compute_category_score(raw_query, query_tokens, doc.get('category', ''))

            # Relevance Feedback Bonus (+0.10 if user previously marked relevant)
            feedback_bonus = 0.10 if doc_id in feedback_docs else 0.0

            # Final composite score
            # Score = 0.70 * TF-IDF + 0.20 * Title + 0.10 * Category + Bonus
            composite_score = (
                self.weight_tfidf * tfidf_sim +
                self.weight_title * title_score +
                self.weight_field * category_score +
                feedback_bonus
            )
            composite_score = min(max(round(composite_score, 4), 0.0), 1.0)

            # Generate highlighted snippet
            snippet = self.generate_snippet(doc['content'], query_tokens)

            ranked_results.append({
                'doc_id': doc_id,
                'title': doc['title'],
                'url': doc['url'],
                'category': doc.get('category', 'General'),
                'content': doc['content'],
                'snippet': snippet,
                'tfidf_score': tfidf_sim,
                'title_score': title_score,
                'category_score': category_score,
                'feedback_bonus': feedback_bonus,
                'final_score': composite_score,
                'matched_terms': stats['matched_terms'],
                'is_feedback_marked': doc_id in feedback_docs
            })

        # Apply sorting
        if sort_by == 'title':
            ranked_results.sort(key=lambda x: x['title'].lower())
        elif sort_by == 'category':
            ranked_results.sort(key=lambda x: (x['category'].lower(), -x['final_score']))
        else: # relevance default
            ranked_results.sort(key=lambda x: x['final_score'], reverse=True)

        return ranked_results