"""
Mini Search Engine for College Website using Information Retrieval (ISR).
Flask Backend Application.
Coordinates Database, Preprocessing, Inverted Indexing, TF-IDF Cosine Retrieval,
Multi-Factor Ranking, Evaluation, Analytics, and Web Crawling.
"""

import os
import json
import time
import math
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash

import config
from database.db_manager import DatabaseManager
from ir_engine.preprocessing import preprocess_text, preprocess_to_string
from ir_engine.indexer import InvertedIndex
from ir_engine.tfidf_engine import TfidfRetrievalEngine
from ir_engine.query_processor import QueryProcessor
from ir_engine.ranking import RankingEngine
from ir_engine.evaluation import IREvaluator
from crawler.web_crawler import WebCrawler

app = Flask(__name__)
app.secret_key = "college-search-engine-isr-secret-key"

# Initialize Core Services
db = DatabaseManager()
indexer = InvertedIndex()
tfidf_engine = TfidfRetrievalEngine(indexer)
query_processor = QueryProcessor()
ranking_engine = RankingEngine(indexer, tfidf_engine, db_manager=db)
evaluator = IREvaluator()
crawler = WebCrawler(db_manager=db)

def load_or_build_index():
    """Attempts to load saved index or builds it from database documents."""
    global indexer, tfidf_engine, ranking_engine

    # Check if index exists on disk
    if indexer.load_index():
        tfidf_engine.build_model()
        ranking_engine = RankingEngine(indexer, tfidf_engine, db_manager=db)
        return True

    # If not on disk, check if database has documents
    docs = db.get_all_documents()
    if not docs:
        # Auto-bootstrap with sample documents if DB is fresh
        bootstrap_sample_data()
        docs = db.get_all_documents()

    if docs:
        stats = indexer.build_index(docs)
        indexer.save_index()
        tfidf_engine.build_model()
        ranking_engine = RankingEngine(indexer, tfidf_engine, db_manager=db)
        db.update_index_metadata(stats['vocabulary_size'], stats['document_count'], stats['total_postings'])
        return True
    return False

def bootstrap_sample_data():
    """Populates database with sample college documents from data/sample_documents."""
    sample_dir = config.SAMPLE_DOCS_DIR
    if not os.path.exists(sample_dir):
        return 0

    count = 0
    for filename in sorted(os.listdir(sample_dir)):
        if filename.endswith('.json'):
            file_path = os.path.join(sample_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    doc = json.load(f)
                    db.insert_or_update_document(
                        doc_id=doc['doc_id'],
                        title=doc['title'],
                        url=doc['url'],
                        category=doc.get('category', 'General'),
                        content=doc['content']
                    )
                    count += 1
            except Exception as e:
                print(f"Error loading {filename}: {e}")
    return count

# Initialize index on application start
load_or_build_index()

@app.context_processor
def inject_global_vars():
    """Injects index status and document count into all templates."""
    stats = indexer.get_stats()
    return {
        'doc_count': stats['document_count'],
        'index_ready': stats['is_ready'],
        'categories_list': config.CATEGORIES
    }

# ==========================================
# 1. HOME & SEARCH ROUTES
# ==========================================

@app.route('/')
def index():
    """Homepage: hero search interface."""
    return render_template('index.html')

@app.route('/search')
def search():
    """
    Search results route:
    Accepts query 'q', 'category', 'sort', 'expand', 'page'.
    Performs preprocessing, TF-IDF cosine ranking, snippet highlighting, and pagination.
    """
    raw_query = request.args.get('q', '').strip()
    if not raw_query:
        return redirect(url_for('index'))

    start_time = time.time()
    selected_category = request.args.get('category', 'All')
    sort_by = request.args.get('sort', 'relevance')
    enable_expansion = request.args.get('expand', '1') == '1'
    page = int(request.args.get('page', 1))
    per_page = 8

    # Query Processing & Expansion
    orig_tokens, query_tokens, expansion_info = query_processor.process_query(
        raw_query, 
        enable_expansion=enable_expansion
    )

    # Retrieval and Multi-Factor Ranking
    ranked_results = ranking_engine.rank_documents(
        raw_query=raw_query,
        query_tokens=query_tokens,
        filter_category=selected_category,
        sort_by=sort_by
    )

    # Compute execution time
    execution_time_ms = round((time.time() - start_time) * 1000, 2)

    # Log search in SQLite
    expanded_str = ', '.join(expansion_info['synonyms_added']) if expansion_info['is_expanded'] else None
    db.log_search(
        query=raw_query,
        results_count=len(ranked_results),
        execution_time_ms=execution_time_ms,
        expanded_query=expanded_str
    )

    # Category counts for sidebar facet
    all_matching = ranking_engine.rank_documents(
        raw_query=raw_query,
        query_tokens=query_tokens,
        filter_category='All',
        sort_by='relevance'
    )
    category_counts = {}
    for r in all_matching:
        cat = r['category']
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # Pagination slicing
    total_results = len(ranked_results)
    total_pages = math.ceil(total_results / per_page) if total_results > 0 else 1
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_results = ranked_results[start_idx:end_idx]

    return render_template(
        'results.html',
        query=raw_query,
        results=paginated_results,
        total_results=total_results,
        execution_time_ms=execution_time_ms,
        selected_category=selected_category,
        category_counts=category_counts,
        all_count=len(all_matching),
        sort_by=sort_by,
        is_expanded=enable_expansion,
        expansion_info=expansion_info,
        query_tokens=orig_tokens,
        current_page=page,
        total_pages=total_pages
    )

@app.route('/document/<doc_id>')
def view_document(doc_id):
    """
    Document details view:
    Shows full text, source URL, metadata, and related pages computed via TF-IDF cosine.
    """
    doc = db.get_document_by_id(doc_id)
    if not doc:
        flash(f"Document with ID '{doc_id}' not found.", "error")
        return redirect(url_for('index'))

    return_query = request.args.get('q', '')

    # Compute related documents using TF-IDF cosine similarity
    related = tfidf_engine.get_related_documents(doc_id, top_n=3)

    # Highlight query terms in document content if user came from a search
    highlighted_content = doc['content']
    if return_query:
        q_tokens = preprocess_text(return_query)
        for tok in set(q_tokens):
            import re
            pattern = re.compile(rf'(\b{re.escape(tok)}[a-zA-Z]*)', re.IGNORECASE)
            highlighted_content = pattern.sub(r'<mark class="search-highlight">\1</mark>', highlighted_content)

    token_count = len(doc['content'].split())

    return render_template(
        'document.html',
        doc=doc,
        highlighted_content=highlighted_content,
        related_docs=related,
        return_query=return_query,
        token_count=token_count
    )

# ==========================================
# 2. REST APIS: AUTOCOMPLETE & FEEDBACK
# ==========================================

@app.route('/api/suggest')
def api_suggest():
    """Autocomplete suggestions from document titles and indexed vocabulary."""
    prefix = request.args.get('q', '').strip().lower()
    if not prefix or len(prefix) < 2:
        return jsonify({'suggestions': []})

    suggestions = []
    # 1. Check matching document titles
    for doc_id, doc in indexer.documents.items():
        title = doc['title']
        if prefix in title.lower():
            if title not in suggestions:
                suggestions.append(title)
        if len(suggestions) >= 4:
            break

    # 2. Check indexed vocabulary tokens
    for term in sorted(indexer.vocabulary):
        if term.startswith(prefix) and term not in suggestions:
            suggestions.append(term)
        if len(suggestions) >= 7:
            break

    return jsonify({'suggestions': suggestions[:6]})

@app.route('/api/feedback', methods=['POST'])
def api_feedback():
    """Logs relevance feedback from user clicks."""
    data = request.get_json(silent=True) or {}
    query = data.get('query', '').strip()
    doc_id = data.get('doc_id', '').strip()
    is_rel = data.get('is_relevant', 1)

    if query and doc_id:
        db.log_feedback(query, doc_id, is_relevant=is_rel)
        return jsonify({'status': 'success', 'message': 'Feedback recorded'})
    return jsonify({'status': 'error', 'message': 'Invalid parameters'}), 400

@app.route('/api/click', methods=['POST'])
def api_click():
    """Logs result click for analytics."""
    data = request.get_json(silent=True) or {}
    query = data.get('query', '').strip()
    doc_id = data.get('doc_id', '').strip()

    if query and doc_id:
        db.log_click(query, doc_id)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'ignored'})

# ==========================================
# 3. EVALUATION & ANALYTICS
# ==========================================

@app.route('/evaluation')
def evaluation():
    """Runs IR Evaluation Suite against 20 benchmark test queries."""
    # Define retrieval search function for the evaluator
    def search_wrapper(query_str):
        _, q_tokens, _ = query_processor.process_query(query_str, enable_expansion=False)
        return ranking_engine.rank_documents(raw_query=query_str, query_tokens=q_tokens)

    results = evaluator.evaluate_engine(search_wrapper, k=5)
    return render_template('evaluation.html', eval_results=results)

@app.route('/analytics')
def analytics():
    """Search Analytics Dashboard."""
    summary = db.get_analytics_summary()
    return render_template('analytics.html', summary=summary)

# ==========================================
# 4. ADMIN & CRAWLER MANAGEMENT
# ==========================================

@app.route('/admin')
def admin():
    """Admin dashboard: index status, crawler interface, document table."""
    stats = indexer.get_stats()
    docs = db.get_all_documents()
    return render_template('admin.html', stats=stats, documents=docs)

@app.route('/admin/load-demo', methods=['POST'])
def admin_load_demo():
    """Loads all 40 built-in sample documents and builds index."""
    count = bootstrap_sample_data()
    docs = db.get_all_documents()
    stats = indexer.build_index(docs)
    indexer.save_index()
    tfidf_engine.build_model()
    db.update_index_metadata(stats['vocabulary_size'], stats['document_count'], stats['total_postings'])
    flash(f"Successfully loaded {count} demo documents and rebuilt the Inverted Index ({stats['vocabulary_size']} vocabulary terms).", "success")
    return redirect(url_for('admin'))

@app.route('/admin/rebuild-index', methods=['POST'])
def admin_rebuild_index():
    """Rebuilds the inverted index and TF-IDF matrices from database."""
    docs = db.get_all_documents()
    if not docs:
        flash("No documents in database to index. Please load demo data first.", "warning")
        return redirect(url_for('admin'))

    stats = indexer.build_index(docs)
    indexer.save_index()
    tfidf_engine.build_model()
    db.update_index_metadata(stats['vocabulary_size'], stats['document_count'], stats['total_postings'])
    flash(f"Inverted Index successfully rebuilt! Indexed {stats['document_count']} documents with {stats['vocabulary_size']} unique terms.", "success")
    return redirect(url_for('admin'))

@app.route('/admin/clear-logs', methods=['POST'])
def admin_clear_logs():
    """Clears search and click logs."""
    db.clear_search_logs()
    flash("Search history and click analytics have been cleared.", "info")
    return redirect(url_for('admin'))

@app.route('/admin/crawl', methods=['POST'])
def admin_crawl():
    """AJAX endpoint for web crawler."""
    data = request.get_json(silent=True) or {}
    url = data.get('url', '').strip()
    max_pages = int(data.get('max_pages', 20))
    depth = int(data.get('depth', 2))

    if not url:
        return jsonify({'status': 'error', 'message': 'Missing URL'}), 400

    crawl_res = crawler.crawl(url, max_pages=max_pages, max_depth=depth)

    # Re-index all documents if new pages were crawled
    if crawl_res['crawled_count'] > 0:
        docs = db.get_all_documents()
        stats = indexer.build_index(docs)
        indexer.save_index()
        tfidf_engine.build_model()
        db.update_index_metadata(stats['vocabulary_size'], stats['document_count'], stats['total_postings'])

    return jsonify({
        'status': 'success',
        'crawled_count': crawl_res['crawled_count'],
        'logs': crawl_res['logs'],
        'errors': crawl_res['errors']
    })

if __name__ == '__main__':
    print("==================================================================")
    print("  Apex College Search Engine (Information Storage & Retrieval)   ")
    print("  Running locally on http://127.0.0.1:5000                       ")
    print("==================================================================")
    app.run(host='127.0.0.1', port=5000, debug=True)