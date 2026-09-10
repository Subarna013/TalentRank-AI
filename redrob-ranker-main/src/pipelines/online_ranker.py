"""
Online Ranking Pipeline.

The main orchestrator that produces the final top-100 ranking.
Must complete within 5 minutes on CPU with 16GB RAM.

Pipeline stages:
1. Load candidates
2. Data validation + honeypot detection
3. Metadata pre-filter
4. BM25 sparse retrieval
5. Dense retrieval (multi-view)
6. Reciprocal Rank Fusion
7. Feature computation
8. Composite scoring (rule-based or LTR)
9. Final ranking + calibration
10. Reasoning generation
11. Output CSV
"""
import csv
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.config.settings import Settings, get_settings
from src.core.types import Candidate, FeatureVector, RankedCandidate
from src.features.feature_registry import FeatureRegistry
from src.reasoning.explanation_engine import ExplanationEngine
from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.fusion import ReciprocalRankFusion
from src.validators.honeypot_detector import HoneypotDetector

logger = logging.getLogger(__name__)


class OnlineRanker:
    """
    Main ranking pipeline. Produces the final submission CSV.

    This class can operate in two modes:
    1. Full mode: BM25 + Dense + RRF + Features + Scoring
    2. Lite mode: BM25 + Features + Scoring (no dense retrieval)

    Lite mode is the default for the competition because:
    - It runs in ~30 seconds vs ~3 minutes for full mode
    - Dense retrieval requires pre-computed embeddings
    - The feature-based scoring is strong enough on its own
    """

    def __init__(
        self,
        settings: Settings = None,
        use_dense: bool = False,
    ):
        self.settings = settings or get_settings()
        self.use_dense = use_dense

        # Initialize components
        self.honeypot_detector = HoneypotDetector(self.settings)
        self.feature_registry = FeatureRegistry(self.settings)
        self.bm25_retriever = BM25Retriever(self.settings)
        self.rrf = ReciprocalRankFusion(k=self.settings.retrieval.rrf_k)
        self.explanation_engine = ExplanationEngine(self.settings)

        # Dense retriever (optional)
        self.dense_retriever = None

    def rank(
        self,
        candidates_path: str,
        output_path: str,
    ) -> List[RankedCandidate]:
        """
        Execute the full ranking pipeline.

        Args:
            candidates_path: Path to candidates.jsonl
            output_path: Path to write submission.csv

        Returns:
            List of RankedCandidate objects
        """
        start_time = time.time()
        logger.info("Starting online ranking pipeline...")

        # Stage 1: Load candidates
        logger.info("Stage 1: Loading candidates...")
        candidates = self._load_candidates(candidates_path)
        logger.info(f"  Loaded {len(candidates)} candidates")

        # Stage 2: Honeypot detection
        logger.info("Stage 2: Honeypot detection...")
        honeypot_ids = set()
        for candidate in candidates:
            is_honeypot, reasons, penalty = self.honeypot_detector.detect(candidate)
            candidate.is_honeypot = is_honeypot
            candidate.honeypot_reasons = reasons
            candidate.trust_score = max(1.0 + penalty, 0.0)
            if is_honeypot:
                honeypot_ids.add(candidate.candidate_id)
        logger.info(f"  Detected {len(honeypot_ids)} potential honeypots")

        # Stage 3: Metadata pre-filter
        logger.info("Stage 3: Pre-filtering...")
        viable_candidates = self._prefilter(candidates)
        logger.info(f"  {len(viable_candidates)} candidates pass pre-filter")

        # Stage 4: BM25 retrieval
        logger.info("Stage 4: BM25 retrieval...")
        self.bm25_retriever.build_index(viable_candidates)
        jd_query = self.bm25_retriever.build_jd_query()
        bm25_results = self.bm25_retriever.retrieve(
            jd_query, top_k=self.settings.retrieval.bm25_top_k
        )
        logger.info(f"  BM25 retrieved {len(bm25_results)} candidates")

        # Stage 4b: Strategic supplementary retrieval
        # Ensure we don't miss high-signal candidates the BM25 query might not surface
        logger.info("Stage 4b: Strategic retrieval supplement...")
        supplementary_queries = [
            "ranking system recommendation engine search relevance personalization",
            "embeddings vector search FAISS Pinecone Weaviate Qdrant similarity",
            "NLP information retrieval learning rank evaluation NDCG production",
            "senior AI engineer ML engineer applied scientist product company India",
        ]
        bm25_ids = {cid for cid, _ in bm25_results}
        supplement_results = []
        for sq in supplementary_queries:
            sq_results = self.bm25_retriever.retrieve(sq, top_k=500)
            for cid, score in sq_results:
                if cid not in bm25_ids:
                    supplement_results.append((cid, score * 0.8))  # slight discount
                    bm25_ids.add(cid)
        bm25_results.extend(supplement_results)
        logger.info(f"  Supplementary added {len(supplement_results)} candidates (total: {len(bm25_results)})")

        # Stage 5: Dense retrieval (optional)
        dense_results = {}
        if self.use_dense and self.dense_retriever:
            logger.info("Stage 5: Dense retrieval...")
            jd_queries = self.dense_retriever.build_jd_queries()
            dense_results = self.dense_retriever.retrieve(
                jd_queries, top_k=self.settings.retrieval.dense_top_k
            )

        # Stage 6: Fusion
        logger.info("Stage 6: Rank fusion...")
        ranked_lists = {"bm25": bm25_results}
        fusion_weights = {"bm25": 0.4}

        for view_name, view_results in dense_results.items():
            ranked_lists[f"dense_{view_name}"] = view_results
            fusion_weights[f"dense_{view_name}"] = 0.2

        if len(ranked_lists) == 1:
            # No dense retrieval — just use BM25 results directly
            fused_results = [(cid, score) for cid, score in bm25_results[:2000]]
        else:
            fused_results = self.rrf.fuse(
                ranked_lists,
                weights=fusion_weights,
                top_k=self.settings.retrieval.rrf_top_k,
            )
        logger.info(f"  Fused to {len(fused_results)} candidates")

        # Build lookup maps
        candidate_map = {c.candidate_id: c for c in candidates}
        bm25_score_map = {cid: score for cid, score in bm25_results}

        # Stage 7: Feature computation + scoring
        logger.info("Stage 7: Feature computation and scoring...")
        scored_candidates: List[Tuple[str, float, FeatureVector]] = []

        for candidate_id, rrf_score in fused_results:
            candidate = candidate_map.get(candidate_id)
            if candidate is None:
                continue

            # Skip confirmed honeypots
            if candidate.is_honeypot:
                continue

            # Compute features
            fv = self.feature_registry.compute_features(candidate)

            # Add retrieval scores
            fv.bm25_score = bm25_score_map.get(candidate_id, 0.0)
            fv.rrf_score = rrf_score

            # Compute composite score
            score = self.feature_registry.compute_composite_score(fv)

            scored_candidates.append((candidate_id, score, fv))

        # Sort by score descending, then by candidate_id ascending for tie-breaking
        scored_candidates.sort(key=lambda x: (-x[1], x[0]))
        logger.info(f"  Scored {len(scored_candidates)} candidates")

        # Stage 8: Take top 100
        top_100 = scored_candidates[:100]

        # Stage 9: Calibrate scores (normalize to nice range)
        logger.info("Stage 9: Score calibration...")
        top_100 = self._calibrate_scores(top_100)

        # Stage 10: Generate reasoning
        logger.info("Stage 10: Generating reasoning...")
        final_ranking: List[RankedCandidate] = []

        for rank, (candidate_id, score, fv) in enumerate(top_100, start=1):
            candidate = candidate_map[candidate_id]
            reasoning = self.explanation_engine.generate(
                candidate, fv, rank, score
            )
            final_ranking.append(RankedCandidate(
                candidate_id=candidate_id,
                rank=rank,
                score=round(score, 4),
                reasoning=reasoning,
            ))

        # Stage 11: Write output
        logger.info("Stage 11: Writing output...")
        self._write_csv(final_ranking, output_path)

        elapsed = time.time() - start_time
        logger.info(f"Pipeline complete in {elapsed:.1f}s")
        logger.info(f"Output: {output_path} ({len(final_ranking)} candidates)")

        return final_ranking

    def _load_candidates(self, path: str) -> List[Candidate]:
        """Load and parse candidates from JSONL file."""
        candidates = []
        file_path = Path(path)

        opener = open
        if file_path.suffix == '.gz':
            import gzip
            opener = lambda p: gzip.open(p, 'rt', encoding='utf-8')

        with opener(file_path) if file_path.suffix == '.gz' else open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                candidate = self._parse_candidate(data)
                candidates.append(candidate)

        return candidates

    def _parse_candidate(self, data: Dict) -> Candidate:
        """Parse raw JSON into a Candidate object."""
        profile = data.get("profile", {})
        return Candidate(
            candidate_id=data["candidate_id"],
            headline=profile.get("headline", ""),
            summary=profile.get("summary", ""),
            location=profile.get("location", ""),
            country=profile.get("country", ""),
            years_of_experience=profile.get("years_of_experience", 0.0),
            current_title=profile.get("current_title", ""),
            current_company=profile.get("current_company", ""),
            current_company_size=profile.get("current_company_size", ""),
            current_industry=profile.get("current_industry", ""),
            career_history=data.get("career_history", []),
            education=data.get("education", []),
            skills=data.get("skills", []),
            certifications=data.get("certifications", []),
            languages=data.get("languages", []),
            redrob_signals=data.get("redrob_signals", {}),
        )

    def _prefilter(self, candidates: List[Candidate]) -> List[Candidate]:
        """
        Quick pre-filter to remove obviously irrelevant candidates.
        This is intentionally loose — we want high recall.
        """
        viable = []
        for c in candidates:
            # Skip confirmed honeypots
            if c.is_honeypot:
                continue

            # Hard minimum experience filter (very generous)
            if c.years_of_experience < 1.0:
                continue

            # Skip candidates inactive for >12 months with no open_to_work
            signals = c.redrob_signals
            if (not signals.get("open_to_work_flag", False) and
                signals.get("recruiter_response_rate", 0) < 0.05 and
                signals.get("profile_views_received_30d", 0) == 0):
                # Still include them but don't filter aggressively
                pass

            viable.append(c)

        return viable

    def _calibrate_scores(
        self, scored: List[Tuple[str, float, FeatureVector]]
    ) -> List[Tuple[str, float, FeatureVector]]:
        """
        Normalize scores to a clean strictly-descending range.
        Each rank gets a unique score, no ties after rounding.
        """
        if not scored:
            return scored

        n = len(scored)
        calibrated = []

        # Simple approach: assign linearly spaced scores from 0.99 down to 0.20
        # This guarantees strict monotonic decrease and no tie issues
        for i, (cid, _score, fv) in enumerate(scored):
            # Linear interpolation: rank 0 -> 0.99, rank 99 -> 0.20
            normalized = 0.99 - (i / max(n - 1, 1)) * 0.79
            calibrated.append((cid, round(normalized, 4), fv))

        return calibrated

    def _write_csv(self, ranking: List[RankedCandidate], path: str) -> None:
        """Write the final submission CSV."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["candidate_id", "rank", "score", "reasoning"])
            for r in ranking:
                # Clean reasoning (no commas that break CSV, no newlines)
                clean_reasoning = r.reasoning.replace('"', "'").replace('\n', ' ')
                writer.writerow([
                    r.candidate_id,
                    r.rank,
                    f"{r.score:.4f}",
                    clean_reasoning,
                ])
