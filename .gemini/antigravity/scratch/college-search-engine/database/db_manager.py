import sqlite3
import os
from datetime import datetime
import config

class DatabaseManager:
    def __init__(self, db_path=None):
        self.db_path = db_path or config.DATABASE_PATH
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('CREATE TABLE IF NOT EXISTS documents (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                doc_id TEXT UNIQUE NOT NULL,\n                title TEXT NOT NULL,\n                url TEXT NOT NULL,\n                category TEXT NOT NULL,\n                content TEXT NOT NULL,\n                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n            )')
            cursor.execute('CREATE TABLE IF NOT EXISTS search_logs (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                query TEXT NOT NULL,\n                expanded_query TEXT,\n                results_count INTEGER NOT NULL,\n                execution_time_ms REAL DEFAULT 0,\n                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n            )')
            cursor.execute('CREATE TABLE IF NOT EXISTS click_logs (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                query TEXT NOT NULL,\n                document_id TEXT NOT NULL,\n                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n            )')
            cursor.execute('CREATE TABLE IF NOT EXISTS relevance_feedback (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                query TEXT NOT NULL,\n                document_id TEXT NOT NULL,\n                is_relevant INTEGER DEFAULT 1,\n                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n            )')
            cursor.execute('CREATE TABLE IF NOT EXISTS index_metadata (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                vocabulary_size INTEGER NOT NULL,\n                document_count INTEGER NOT NULL,\n                total_postings INTEGER NOT NULL,\n                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n            )')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_doc_id ON documents (doc_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_search_query ON search_logs (query)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_click_doc ON click_logs (document_id)')
            conn.commit()

    def insert_or_update_document(self, doc_id, title, url, category, content):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO documents (doc_id, title, url, category, content)\n                VALUES (?, ?, ?, ?, ?)\n                ON CONFLICT(doc_id) DO UPDATE SET\n                    title=excluded.title,\n                    url=excluded.url,\n                    category=excluded.category,\n                    content=excluded.content,\n                    created_at=CURRENT_TIMESTAMP', (doc_id, title, url, category, content))
            conn.commit()

    def get_all_documents(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM documents ORDER BY id ASC')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_document_by_id(self, doc_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM documents WHERE doc_id = ?', (doc_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_document_count(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as count FROM documents')
            row = cursor.fetchone()
            return row['count'] if row else 0

    def clear_documents(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM documents')
            conn.commit()

    def log_search(self, query, results_count, execution_time_ms=0.0, expanded_query=None):
        if not query or not query.strip():
            return
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO search_logs (query, results_count, execution_time_ms, expanded_query)\n                VALUES (?, ?, ?, ?)', (query.strip(), results_count, execution_time_ms, expanded_query))
            conn.commit()

    def log_click(self, query, document_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO click_logs (query, document_id)\n                VALUES (?, ?)', (query.strip(), document_id))
            conn.commit()

    def log_feedback(self, query, document_id, is_relevant=1):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO relevance_feedback (query, document_id, is_relevant)\n                VALUES (?, ?, ?)', (query.strip(), document_id, is_relevant))
            conn.commit()

    def get_relevant_doc_ids_for_query(self, query):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT document_id FROM relevance_feedback\n                WHERE query = ? AND is_relevant = 1', (query.strip(),))
            rows = cursor.fetchall()
            return [r['document_id'] for r in rows]

    def update_index_metadata(self, vocabulary_size, document_count, total_postings):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM index_metadata')
            cursor.execute('INSERT INTO index_metadata (vocabulary_size, document_count, total_postings)\n                VALUES (?, ?, ?)', (vocabulary_size, document_count, total_postings))
            conn.commit()

    def get_index_metadata(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM index_metadata ORDER BY id DESC LIMIT 1')
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {'vocabulary_size': 0, 'document_count': 0, 'total_postings': 0, 'last_updated': 'Never'}

    def get_analytics_summary(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) as total, AVG(execution_time_ms) as avg_time, AVG(results_count) as avg_results FROM search_logs')
            stats_row = cursor.fetchone()
            total_searches = stats_row['total'] or 0
            avg_time = round(stats_row['avg_time'] or 0, 2)
            avg_results = round(stats_row['avg_results'] or 0, 1)

            cursor.execute('SELECT query, COUNT(*) as count \n                FROM search_logs \n                GROUP BY query \n                ORDER BY count DESC \n                LIMIT 10')
            top_queries = [{'query': r['query'], 'count': r['count']} for r in cursor.fetchall()]

            cursor.execute('SELECT query, COUNT(*) as count \n                FROM search_logs \n                WHERE results_count = 0 \n                GROUP BY query \n                ORDER BY count DESC \n                LIMIT 10')
            zero_results = [{'query': r['query'], 'count': r['count']} for r in cursor.fetchall()]

            cursor.execute('SELECT c.document_id, d.title, COUNT(*) as click_count\n                FROM click_logs c\n                LEFT JOIN documents d ON c.document_id = d.doc_id\n                GROUP BY c.document_id\n                ORDER BY click_count DESC \n                LIMIT 10')
            top_clicked = [{
                'doc_id': r['document_id'], 
                'title': r['title'] or r['document_id'], 
                'count': r['click_count']
            } for r in cursor.fetchall()]

            cursor.execute('SELECT category, COUNT(*) as count \n                FROM documents \n                GROUP BY category \n                ORDER BY count DESC')
            categories = [{'category': r['category'], 'count': r['count']} for r in cursor.fetchall()]

            cursor.execute('SELECT COUNT(*) as count FROM click_logs')
            total_clicks = cursor.fetchone()['count'] or 0

            return {
                'total_searches': total_searches,
                'avg_time_ms': avg_time,
                'avg_results': avg_results,
                'total_clicks': total_clicks,
                'top_queries': top_queries,
                'zero_results': zero_results,
                'top_clicked': top_clicked,
                'categories': categories
            }

    def clear_search_logs(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM search_logs')
            cursor.execute('DELETE FROM click_logs')
            cursor.execute('DELETE FROM relevance_feedback')
            conn.commit()
