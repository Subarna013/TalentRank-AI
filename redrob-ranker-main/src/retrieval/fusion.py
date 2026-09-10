"""
Reciprocal Rank Fusion (RRF).

Combines ranked lists from multiple retrieval systems into a single
fused ranking. RRF is score-agnostic — it uses only rank positions,
which makes it robust when combining BM25 scores with cosine similarities.

Formula: RRF_score(d) = sum(1 / (k + rank_i(d))) for each system i
where k is a constant (typically 60) that dampens top-rank influence.
"""
from collections import defaultdict
from typing import Dict, List, Tuple


class ReciprocalRankFusion:
    """Fuse multiple ranked lists using RRF."""

    def __init__(self, k: int = 60):
        """
        Args:
            k: RRF constant. Higher k = more uniform weighting across ranks.
               Standard value is 60 (from the original Cormack et al. paper).
        """
        self.k = k

    def fuse(
        self,
        ranked_lists: Dict[str, List[Tuple[str, float]]],
        weights: Dict[str, float] = None,
        top_k: int = None,
    ) -> List[Tuple[str, float]]:
        """
        Fuse multiple ranked lists into a single ranking.

        Args:
            ranked_lists: Dict of system_name -> [(candidate_id, score), ...]
                         Each list should be sorted by score descending.
            weights: Optional weights per system (default: equal weight)
            top_k: Return only top-K results (default: all)

        Returns:
            Fused ranking as [(candidate_id, rrf_score), ...] sorted by score descending.
        """
        if weights is None:
            weights = {name: 1.0 for name in ranked_lists}

        # Normalize weights
        total_weight = sum(weights.values())
        weights = {name: w / total_weight for name, w in weights.items()}

        # Compute RRF scores
        rrf_scores: Dict[str, float] = defaultdict(float)

        for system_name, ranked_list in ranked_lists.items():
            system_weight = weights.get(system_name, 1.0 / len(ranked_lists))

            for rank, (candidate_id, _score) in enumerate(ranked_list, start=1):
                rrf_score = system_weight / (self.k + rank)
                rrf_scores[candidate_id] += rrf_score

        # Sort by fused score
        fused = sorted(rrf_scores.items(), key=lambda x: -x[1])

        if top_k:
            fused = fused[:top_k]

        return fused
