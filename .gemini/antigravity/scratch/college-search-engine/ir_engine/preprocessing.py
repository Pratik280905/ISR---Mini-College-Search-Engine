"""
Text Preprocessing Module for Information Storage and Retrieval (ISR).
Implements lowercase conversion, HTML cleaning, tokenization, stop-word removal,
and Porter stemming while preserving important domain-specific acronyms.
"""

import re
import html
import nltk
from nltk.stem import PorterStemmer

# Quick local check so we don't attempt network downloads if data is already present
def init_nltk():
    for pkg, path in [('stopwords', 'corpora/stopwords'), ('punkt', 'tokenizers/punkt')]:
        try:
            nltk.data.find(path)
        except (LookupError, Exception):
            try:
                nltk.download(pkg, quiet=True)
            except Exception:
                pass

init_nltk()

FALLBACK_STOPWORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and',
    'any', 'are', 'aren', 'arent', 'as', 'at', 'be', 'because', 'been', 'before', 'being',
    'below', 'between', 'both', 'but', 'by', 'can', 'cant', 'cannot', 'could', 'couldnt',
    'did', 'didnt', 'do', 'does', 'doesnt', 'doing', 'dont', 'down', 'during',
    'each', 'few', 'for', 'from', 'further', 'had', 'hadnt', 'has', 'hasnt',
    'have', 'havent', 'having', 'he', 'hed', 'hell', 'hes', 'her', 'here',
    'heres', 'hers', 'herself', 'him', 'himself', 'his', 'how', 'hows', 'i',
    'id', 'ill', 'im', 'ive', 'if', 'in', 'into', 'is', 'isnt', 'it',
    'its', 'itself', 'lets', 'me', 'more', 'most', 'mustnt', 'my',
    'myself', 'no', 'nor', 'not', 'of', 'off', 'on', 'once', 'only', 'or', 'other',
    'ought', 'our', 'ours', 'ourselves', 'out', 'over', 'own', 'same', 'shant',
    'she', 'shed', 'shell', 'shes', 'should', 'shouldnt', 'so', 'some',
    'such', 'than', 'that', 'thats', 'the', 'their', 'theirs', 'them', 'themselves',
    'then', 'there', 'theres', 'these', 'they', 'theyd', 'theyll', 'theyre',
    'theyve', 'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up',
    'very', 'was', 'wasnt', 'we', 'wed', 'well', 'were', 'werent', 'what',
    'whats', 'when', 'whens', 'where', 'wheres', 'which', 'while', 'who',
    'whos', 'whom', 'why', 'whys', 'with', 'wont', 'would', 'wouldnt', 'you',
    'youd', 'youll', 'youre', 'youve', 'your', 'yours', 'yourself', 'yourselves'
}

PRESERVE_TOKENS = {
    'ai', 'it', 'cs', 'ds', 'cse', 'ece', 'me', 'ce', 'ee', 'ug', 'pg',
    'phd', 'mba', 'mca', 'btech', 'mtech', 'be', 'iot', 'gpa', 'cgpa',
    'mrr', 'map', 'f1', 'ir', 'nlp', 'hod', 'lab', 'labs', 'fee', 'fees'
}

class TextPreprocessor:
    def __init__(self):
        try:
            from nltk.corpus import stopwords
            self.stop_words = set(stopwords.words('english'))
        except Exception:
            self.stop_words = set(FALLBACK_STOPWORDS)

        self.stop_words = self.stop_words - PRESERVE_TOKENS
        self.stemmer = PorterStemmer()

    def clean_html(self, text):
        if not text:
            return ''
        text = html.unescape(text)
        text = re.sub(r'<script.*?</script>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style.*?</style>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        return text

    def tokenize(self, text):
        if not text:
            return []
        text = self.clean_html(text).lower().strip()
        tokens = re.findall(r'[a-zA-Z0-9+#]+', text)
        return tokens

    def preprocess_text(self, text, apply_stemming=True):
        raw_tokens = self.tokenize(text)
        processed = []
        for token in raw_tokens:
            token = token.strip('.-_')
            if not token:
                continue
            if token in PRESERVE_TOKENS:
                processed.append(token)
            elif token not in self.stop_words and len(token) >= 2:
                if apply_stemming:
                    try:
                        stemmed = self.stemmer.stem(token)
                        processed.append(stemmed)
                    except Exception:
                        processed.append(token)
                else:
                    processed.append(token)
        return processed

    def preprocess_to_string(self, text, apply_stemming=True):
        tokens = self.preprocess_text(text, apply_stemming=apply_stemming)
        return ' '.join(tokens)

_default_preprocessor = TextPreprocessor()

def preprocess_text(text, apply_stemming=True):
    return _default_preprocessor.preprocess_text(text, apply_stemming=apply_stemming)

def preprocess_to_string(text, apply_stemming=True):
    return _default_preprocessor.preprocess_to_string(text, apply_stemming=apply_stemming)