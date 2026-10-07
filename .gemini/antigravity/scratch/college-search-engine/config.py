import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database
DATABASE_PATH = os.path.join(BASE_DIR, 'database.db')

# Index storage
INDEX_STORAGE_PATH = os.path.join(BASE_DIR, 'ir_engine', 'index_data.pkl')

# Data Directories
SAMPLE_DOCS_DIR = os.path.join(BASE_DIR, 'data', 'sample_documents')
CRAWLED_PAGES_DIR = os.path.join(BASE_DIR, 'data', 'crawled_pages')
EVALUATION_QUERIES_PATH = os.path.join(BASE_DIR, 'data', 'evaluation_queries.json')

# Information Retrieval Ranking Weights
# Final Score = 0.70 * TF-IDF Cosine Similarity + 0.20 * Title Match Score + 0.10 * Field/Category Match Score
WEIGHT_TFIDF = 0.70
WEIGHT_TITLE = 0.20
WEIGHT_FIELD = 0.10

# Snippet Generation
SNIPPET_LENGTH = 220

# Web Crawler Settings
CRAWLER_DEFAULT_MAX_PAGES = 30
CRAWLER_DEFAULT_DEPTH = 2
CRAWLER_TIMEOUT = 5
CRAWLER_DELAY = 0.4

# College Categories
CATEGORIES = [
    'Department',
    'Admission',
    'Examination',
    'Placement',
    'Student Services',
    'Facilities',
    'Governance',
    'Notices',
    'General'
]

# Query Expansion Synonym Dictionary for College Domain
QUERY_SYNONYMS = {
    'fees': ['tuition', 'charges', 'payment', 'dues', 'cost', 'scholarship'],
    'fee': ['tuition', 'charges', 'payment', 'cost'],
    'admission': ['enrollment', 'eligibility', 'application', 'cutoff', 'intake', 'criteria'],
    'admissions': ['enrollment', 'eligibility', 'application', 'cutoff'],
    'placement': ['jobs', 'recruitment', 'salary', 'package', 'campus', 'offers', 'companies', 'internship'],
    'placements': ['jobs', 'recruitment', 'salary', 'package', 'companies'],
    'internship': ['training', 'stipend', 'summer', 'industry', 'placement'],
    'hostel': ['accommodation', 'room', 'mess', 'residence', 'stay'],
    'exam': ['examination', 'timetable', 'schedule', 'results', 'grades', 'test', 'revaluation'],
    'examination': ['exam', 'timetable', 'schedule', 'results', 'grades', 'semester'],
    'faculty': ['professors', 'teachers', 'staff', 'hod', 'instructor', 'dean'],
    'library': ['books', 'journals', 'reading', 'catalog', 'digital', 'study'],
    'sports': ['gymkhana', 'athletics', 'games', 'fitness', 'tournament'],
    'syllabus': ['curriculum', 'subjects', 'course', 'credits', 'structure'],
    'scholarship': ['financial', 'aid', 'freeship', 'concession', 'grant']
}
