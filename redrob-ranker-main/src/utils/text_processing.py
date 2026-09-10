"""
Text processing utilities.
"""
import re
from typing import List


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    if not text:
        return ""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters that break CSV
    text = text.replace('"', "'")
    text = text.replace('\n', ' ')
    text = text.replace('\r', '')
    return text.strip()


def extract_keywords(text: str) -> List[str]:
    """Extract meaningful keywords from text."""
    text = text.lower()
    # Remove common stop words
    stopwords = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'for', 'and', 'nor', 'but', 'or', 'yet',
        'so', 'at', 'by', 'in', 'of', 'on', 'to', 'from', 'with',
        'as', 'into', 'through', 'during', 'this', 'that', 'i', 'we',
    }
    # Tokenize
    tokens = re.split(r'[^a-z0-9]+', text)
    return [t for t in tokens if len(t) > 2 and t not in stopwords]


def compute_text_overlap(text_a: str, text_b: str) -> float:
    """Compute keyword overlap ratio between two texts."""
    keywords_a = set(extract_keywords(text_a))
    keywords_b = set(extract_keywords(text_b))

    if not keywords_a or not keywords_b:
        return 0.0

    intersection = keywords_a & keywords_b
    union = keywords_a | keywords_b

    return len(intersection) / len(union)
