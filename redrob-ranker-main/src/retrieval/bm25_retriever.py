"""
BM25 Sparse Retrieval.

Builds a BM25 index over candidate text (summary + career descriptions + skills)
and retrieves top-K candidates matching the JD query.
"""
import re
from typing import Dict, List, Tuple

import numpy as np
from rank_bm25 import BM25Okapi

from src.config.settings import Settings, get_settings
from src.core.types import Candidate


class BM25Retriever:
    """Sparse retrieval using BM25 over candidate documents."""

    def __init__(self, settings: Settings = None):
        self.settings = settings or get_settings()
        self.index: BM25Okapi = None
        self.candidate_ids: List[str] = []

    def build_index(self, candidates: List[Candidate]) -> None:
        """
        Build BM25 index from candidate documents.
        Each candidate becomes one document combining their text fields.
        """
        documents = []
        self.candidate_ids = []

        for candidate in candidates:
            doc = self._candidate_to_document(candidate)
            documents.append(self._tokenize(doc))
            self.candidate_ids.append(candidate.candidate_id)

        self.index = BM25Okapi(documents)

    def retrieve(self, query: str, top_k: int = None) -> List[Tuple[str, float]]:
        """
        Retrieve top-K candidates for a query.

        Returns:
            List of (candidate_id, bm25_score) sorted by score descending.
        """
        if self.index is None:
            raise RuntimeError("BM25 index not built. Call build_index() first.")

        top_k = top_k or self.settings.retrieval.bm25_top_k
        tokenized_query = self._tokenize(query)

        scores = self.index.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append((self.candidate_ids[idx], float(scores[idx])))

        return results

    def _candidate_to_document(self, candidate: Candidate) -> str:
        """Convert a candidate to a searchable text document."""
        parts = []

        # Profile text
        parts.append(candidate.headline)
        parts.append(candidate.summary)
        parts.append(candidate.current_title)
        parts.append(candidate.current_industry)

        # Career history
        for job in candidate.career_history:
            parts.append(job.get("title", ""))
            parts.append(job.get("description", ""))
            parts.append(job.get("industry", ""))

        # Skills
        skill_text = " ".join(s.get("name", "") for s in candidate.skills)
        parts.append(skill_text)

        # Education
        for edu in candidate.education:
            parts.append(edu.get("field_of_study", ""))
            parts.append(edu.get("degree", ""))

        # Certifications
        for cert in candidate.certifications:
            parts.append(cert.get("name", ""))

        return " ".join(filter(None, parts))

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization: lowercase, split on non-alphanumeric."""
        text = text.lower()
        tokens = re.split(r'[^a-z0-9]+', text)
        # Remove very short tokens and stopwords
        stopwords = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'shall', 'can',
            'for', 'and', 'nor', 'but', 'or', 'yet', 'so', 'at', 'by',
            'in', 'of', 'on', 'to', 'from', 'with', 'as', 'into',
            'through', 'during', 'before', 'after', 'above', 'below',
            'between', 'under', 'again', 'further', 'then', 'once',
            'this', 'that', 'these', 'those', 'i', 'me', 'my', 'we',
            'our', 'you', 'your', 'he', 'she', 'it', 'they', 'them',
        }
        return [t for t in tokens if len(t) > 2 and t not in stopwords]

    def build_jd_query(self) -> str:
        """
        Construct the BM25 query from JD requirements.
        This should be broad enough to catch hidden gems while still
        prioritizing directly relevant candidates.
        """
        jd = self.settings.jd

        query_parts = []

        # Title keywords (high signal)
        query_parts.extend(jd.title_keywords)
        # Repeat most important ones for BM25 weighting
        query_parts.extend([
            "AI Engineer", "ML Engineer", "NLP Engineer", "Search Engineer",
        ])

        # Required skills
        query_parts.extend(jd.required_skills)

        # Preferred skills
        query_parts.extend(jd.preferred_skills)

        # Key phrases from JD (what they actually DO)
        query_parts.extend([
            "production experience", "embeddings retrieval ranking",
            "vector database hybrid search", "evaluation framework",
            "NDCG MRR MAP", "product company", "startup",
            "recommendation system", "search engine", "search relevance",
            "Python ML NLP information retrieval",
            "shipped deployed production users scale",
            "embedding drift index refresh quality regression",
            "ranking model", "personalization", "semantic search",
            "candidate ranking", "learning rank",
            "fine-tuning LLM LoRA", "vector search",
            "recommendation engine", "retrieval system",
            "search infrastructure", "search backend",
            "model serving deployment inference",
        ])

        return " ".join(query_parts)
