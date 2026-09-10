"""
Dense Retrieval with Multi-View Embeddings.

Uses sentence-transformers (all-MiniLM-L6-v2) to encode candidates
from multiple views:
1. Career Summary view (headline + summary + career descriptions)
2. Skills Title view (skills + titles)
3. Responsibilities view (career history descriptions)

Each view is a separate FAISS index, retrieved independently, then fused.
"""
import numpy as np
from typing import Dict, List, Optional, Tuple

from src.config.settings import Settings, get_settings
from src.core.types import Candidate


class DenseRetriever:
    """
    Multi-view dense retrieval using sentence-transformers + FAISS.
    Lazy-loads the model to avoid memory pressure during import.
    """

    def __init__(self, settings: Settings = None):
        self.settings = settings or get_settings()
        self.model = None
        self.indexes: Dict[str, object] = {}  # view_name -> FAISS index
        self.candidate_ids: List[str] = []
        self.embeddings: Dict[str, np.ndarray] = {}  # view_name -> embedding matrix

    def _load_model(self):
        """Lazy-load the embedding model."""
        if self.model is None:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(
                self.settings.retrieval.embedding_model
            )

    def build_indexes(self, candidates: List[Candidate]) -> None:
        """Build FAISS indexes for each embedding view."""
        import faiss

        self._load_model()
        self.candidate_ids = [c.candidate_id for c in candidates]

        views = self.settings.retrieval.views
        dim = self.settings.retrieval.embedding_dim

        for view in views:
            # Generate texts for this view
            texts = [self._get_view_text(c, view) for c in candidates]

            # Encode
            embeddings = self.model.encode(
                texts,
                batch_size=256,
                show_progress_bar=True,
                normalize_embeddings=True,
            )
            embeddings = embeddings.astype(np.float32)
            self.embeddings[view] = embeddings

            # Build FAISS index (inner product since we normalized)
            index = faiss.IndexFlatIP(dim)
            index.add(embeddings)
            self.indexes[view] = index

    def retrieve(
        self,
        query_texts: Dict[str, str],
        top_k: int = None,
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        Retrieve top-K candidates for each view.

        Args:
            query_texts: Dict of view_name -> query text
            top_k: Number of candidates to retrieve per view

        Returns:
            Dict of view_name -> [(candidate_id, score), ...]
        """
        import faiss

        if not self.indexes:
            raise RuntimeError("Indexes not built. Call build_indexes() first.")

        self._load_model()
        top_k = top_k or self.settings.retrieval.dense_top_k

        results = {}
        for view, query_text in query_texts.items():
            if view not in self.indexes:
                continue

            # Encode query
            query_emb = self.model.encode(
                [query_text],
                normalize_embeddings=True,
            ).astype(np.float32)

            # Search
            scores, indices = self.indexes[view].search(query_emb, top_k)

            view_results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0:  # FAISS returns -1 for empty results
                    view_results.append((self.candidate_ids[idx], float(score)))
            results[view] = view_results

        return results

    def get_candidate_embedding(
        self, candidate_id: str, view: str
    ) -> Optional[np.ndarray]:
        """Get the precomputed embedding for a specific candidate and view."""
        if view not in self.embeddings:
            return None
        try:
            idx = self.candidate_ids.index(candidate_id)
            return self.embeddings[view][idx]
        except ValueError:
            return None

    def _get_view_text(self, candidate: Candidate, view: str) -> str:
        """Generate the text representation for a specific view."""
        if view == "career_summary":
            parts = [
                candidate.headline,
                candidate.summary,
            ]
            # Add career descriptions (most recent first)
            for job in candidate.career_history[:3]:
                parts.append(f"{job.get('title', '')} at {job.get('company', '')}")
                parts.append(job.get("description", ""))
            return " ".join(filter(None, parts))

        elif view == "skills_title":
            parts = [
                candidate.current_title,
                candidate.headline,
            ]
            # Skills with proficiency
            for skill in candidate.skills:
                name = skill.get("name", "")
                prof = skill.get("proficiency", "")
                parts.append(f"{name} ({prof})")
            # Certifications
            for cert in candidate.certifications:
                parts.append(cert.get("name", ""))
            return " ".join(filter(None, parts))

        elif view == "responsibilities":
            parts = []
            for job in candidate.career_history:
                desc = job.get("description", "")
                if desc:
                    parts.append(desc)
            return " ".join(parts) if parts else candidate.summary

        else:
            # Fallback: full text
            return f"{candidate.headline} {candidate.summary}"

    def build_jd_queries(self) -> Dict[str, str]:
        """
        Build view-specific JD query texts.
        Each view gets a query optimized for what that view captures.
        """
        return {
            "career_summary": (
                "Senior AI Engineer building talent intelligence platform. "
                "Experience with embeddings, retrieval systems, ranking models, "
                "hybrid search, vector databases at product companies. "
                "Shipped production ML systems to real users. "
                "5-9 years applied ML at product companies not pure services. "
                "Comfortable with NLP, information retrieval, recommendation systems."
            ),
            "skills_title": (
                "AI Engineer ML Engineer Senior Applied Scientist NLP Engineer "
                "Python embeddings sentence-transformers FAISS Pinecone Weaviate "
                "Qdrant Milvus OpenSearch Elasticsearch vector database "
                "NLP information retrieval ranking evaluation NDCG MRR "
                "LLM fine-tuning LoRA PEFT learning-to-rank XGBoost LightGBM "
                "distributed systems PyTorch TensorFlow Huggingface"
            ),
            "responsibilities": (
                "Built and deployed production retrieval ranking recommendation systems. "
                "Designed evaluation frameworks for search and ranking quality. "
                "Managed embedding drift and index refresh in production. "
                "Shipped ML models to real users at scale. "
                "Built hybrid search combining sparse and dense retrieval. "
                "Set up A/B testing and online evaluation infrastructure. "
                "Fine-tuned language models for domain-specific tasks."
            ),
        }
