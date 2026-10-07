"""
HTML Parser Module.
Extracts title, headings, clean textual content, and internal links
while removing scripts, styles, navigations, and footers.
"""

from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

class HTMLParser:
    @staticmethod
    def parse(html_content, base_url=""):
        """
        Parses raw HTML content.
        Returns dict:
            title: str
            headings: list of str
            content: str (clean plain text)
            links: list of normalized absolute URLs
        """
        if not html_content:
            return {'title': '', 'headings': [], 'content': '', 'links': []}

        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove boilerplates, scripts, styles, and navigational elements
        for element in soup(['script', 'style', 'nav', 'footer', 'noscript', 'iframe', 'header']):
            element.decompose()

        # Extract title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        elif soup.find('h1'):
            title = soup.find('h1').get_text(strip=True)
        else:
            title = "Untitled Page"

        # Extract headings (h1, h2, h3, h4)
        headings = []
        for tag in ['h1', 'h2', 'h3', 'h4']:
            for h in soup.find_all(tag):
                h_text = h.get_text(separator=' ', strip=True)
                if h_text and len(h_text) > 2:
                    headings.append(h_text)

        # Extract paragraphs and main textual content
        content_pieces = []
        # Include headings in content for indexing
        if headings:
            content_pieces.append(' '.join(headings))

        # Extract paragraphs, list items, table cells, and article bodies
        body = soup.find('body') or soup
        for p in body.find_all(['p', 'li', 'td', 'blockquote', 'article', 'section']):
            text = p.get_text(separator=' ', strip=True)
            if text and len(text) > 10:
                content_pieces.append(text)

        full_content = ' '.join(content_pieces)
        full_content = ' '.join(full_content.split()) # clean excess whitespace

        # Extract and normalize links
        links = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            # Ignore anchors, javascript, mailto, tel
            if not href or href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:') or href.startswith('tel:'):
                continue

            absolute_url = urljoin(base_url, href)
            # Remove URL fragments (#section)
            parsed = urlparse(absolute_url)
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                clean_url += f"?{parsed.query}"

            # Only accept http / https
            if parsed.scheme in ['http', 'https']:
                links.add(clean_url)

        return {
            'title': title,
            'headings': headings,
            'content': full_content,
            'links': list(links)
        }