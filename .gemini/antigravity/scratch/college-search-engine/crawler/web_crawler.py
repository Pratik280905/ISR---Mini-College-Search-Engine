"""
Polite Multi-page Web Crawler for College Website Search Engine.
Features:
- Breadth-first search (BFS) crawling with depth control
- Same-domain restriction
- URL normalization & deduplication
- Polite delay to prevent server overload
- Automated category classification based on URL/title
- Safe extraction and direct SQLite ingestion
"""

import time
import os
import re
from urllib.parse import urlparse, urljoin
from collections import deque
import requests
from crawler.html_parser import HTMLParser
import config

class WebCrawler:
    def __init__(self, db_manager=None, timeout=None, delay=None):
        self.db_manager = db_manager
        self.timeout = timeout or config.CRAWLER_TIMEOUT
        self.delay = delay or config.CRAWLER_DELAY
        self.headers = {
            'User-Agent': 'MiniCollegeSearchEngineBot/1.0 (+http://localhost:5000/about)'
        }
        self.ignored_extensions = {
            '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.zip', '.rar',
            '.tar', '.gz', '.mp4', '.avi', '.mp3', '.css', '.js', '.json', '.xml'
        }

    def is_same_domain(self, target_url, base_domain):
        """Checks if the target URL belongs to the same base domain."""
        target_netloc = urlparse(target_url).netloc.lower()
        base_netloc = base_domain.lower()

        # Handle port numbers if present
        target_netloc = target_netloc.split(':')[0]
        base_netloc = base_netloc.split(':')[0]

        return target_netloc == base_netloc or target_netloc.endswith('.' + base_netloc)

    def normalize_url(self, url):
        """Normalizes URL by stripping fragments and trailing slashes."""
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        if not path:
            path = '/'
        query = f"?{parsed.query}" if parsed.query else ""
        return f"{parsed.scheme}://{parsed.netloc}{path}{query}"

    def guess_category(self, url, title):
        """Infers the college category based on URL path and page title."""
        text = f"{url} {title}".lower()
        if any(w in text for w in ['admiss', 'eligib', 'fee', 'cutoff', 'seat', 'apply']):
            return 'Admission'
        elif any(w in text for w in ['comput', 'mechan', 'civil', 'electr', 'it', 'dept', 'depart', 'faculty', 'curriculum', 'syllab']):
            return 'Department'
        elif any(w in text for w in ['exam', 'timetabl', 'result', 'grade', 'reval']):
            return 'Examination'
        elif any(w in text for w in ['place', 'recruit', 'intern', 'packag', 'compani', 'career']):
            return 'Placement'
        elif any(w in text for w in ['hostel', 'mess', 'librar', 'sport', 'gymkhana', 'canteen']):
            return 'Facilities'
        elif any(w in text for w in ['ragging', 'grievanc', 'scholarship', 'servic', 'counsel']):
            return 'Student Services'
        elif any(w in text for w in ['principal', 'director', 'trust', 'govern', 'board', 'committe']):
            return 'Governance'
        elif any(w in text for w in ['notice', 'circular', 'event', 'announc', 'news']):
            return 'Notices'
        return 'General'

    def crawl(self, start_url, max_pages=30, max_depth=2, log_callback=None):
        """
        Crawls pages starting from start_url up to max_pages and max_depth.
        Returns: { 'crawled_count': int, 'pages': list, 'errors': list, 'logs': list }
        """
        logs = []
        def log(msg):
            logs.append(msg)
            if log_callback:
                log_callback(msg)

        start_url = self.normalize_url(start_url)
        base_parsed = urlparse(start_url)
        base_domain = base_parsed.netloc

        if not base_domain:
            log(f"Invalid starting URL: {start_url}")
            return {'crawled_count': 0, 'pages': [], 'errors': ['Invalid URL'], 'logs': logs}

        log(f"Starting crawl from: {start_url} (Domain: {base_domain}, Max Pages: {max_pages}, Max Depth: {max_depth})")

        visited = set()
        queue = deque([(start_url, 0)]) # (url, current_depth)
        crawled_pages = []
        errors = []

        while queue and len(crawled_pages) < max_pages:
            url, depth = queue.popleft()
            if url in visited:
                continue

            visited.add(url)

            # Skip disallowed extensions
            parsed_path = urlparse(url).path.lower()
            if any(parsed_path.endswith(ext) for ext in self.ignored_extensions):
                continue

            try:
                time.sleep(self.delay)
                response = requests.get(url, headers=self.headers, timeout=self.timeout, allow_redirects=True)
                
                content_type = response.headers.get('Content-Type', '').lower()
                if 'text/html' not in content_type:
                    continue

                if response.status_code != 200:
                    errors.append(f"HTTP {response.status_code} on {url}")
                    continue

                parsed_data = HTMLParser.parse(response.text, base_url=url)
                title = parsed_data['title']
                content = parsed_data['content']

                # Avoid empty pages
                if not content or len(content) < 50:
                    continue

                # Generate unique doc_id from url
                clean_path = re.sub(r'[^a-zA-Z0-9_]', '_', urlparse(url).path.strip('/'))
                doc_id = f"crawl_{len(crawled_pages) + 1:03d}_{clean_path[:20]}"
                category = self.guess_category(url, title)

                page_record = {
                    'doc_id': doc_id,
                    'title': title,
                    'url': url,
                    'category': category,
                    'content': content
                }
                crawled_pages.append(page_record)

                if self.db_manager:
                    self.db_manager.insert_or_update_document(
                        doc_id=doc_id,
                        title=title,
                        url=url,
                        category=category,
                        content=content
                    )

                log(f"[{len(crawled_pages)}/{max_pages}] Crawled: {title[:40]} ({category}) - Depth {depth}")

                # Queue child links if depth limit not reached
                if depth < max_depth:
                    for link in parsed_data['links']:
                        clean_link = self.normalize_url(link)
                        if clean_link not in visited and self.is_same_domain(clean_link, base_domain):
                            queue.append((clean_link, depth + 1))

            except Exception as e:
                err_msg = f"Failed to crawl {url}: {str(e)}"
                errors.append(err_msg)
                log(err_msg)

        log(f"Crawl completed. Successfully indexed {len(crawled_pages)} pages.")
        return {
            'crawled_count': len(crawled_pages),
            'pages': crawled_pages,
            'errors': errors,
            'logs': logs
        }