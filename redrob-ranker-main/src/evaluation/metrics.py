"""
Evaluation Metrics.

Implements the competition's scoring metrics for offline evaluation:
- NDCG@K (Normalized Discounted Cumulative Gain)
- MAP (Mean Average Precision)
- P@K (Precision at K)

Used for ablation studies and self-evaluation before submission.
"""
import math
from typing import Dict, List, Set


def dcg_at_k(relevance_scores: List[float], k: int) -> float:
    """Compute Discounted Cumulative Gain at position K."""
    dcg = 0.0
    for i, rel in enumerate(relevance_scores[:k]):
        dcg += (2**rel - 1) / math.log2(i + 2)
    return dcg


def ndcg_at_k(
    predicted_ids: List[str],
    relevance_map: Dict[str, float],
    k: int,
) -> float:
    """
    Compute NDCG@K.

    Args:
        predicted_ids: Ordered list of candidate IDs (best first)
        relevance_map: Dict of candidate_id -> relevance score (0-5)
        k: Cutoff position
    """
    # Actual DCG
    actual_rels = [relevance_map.get(cid, 0.0) for cid in predicted_ids[:k]]
    actual_dcg = dcg_at_k(actual_rels, k)

    # Ideal DCG (best possible ordering)
    ideal_rels = sorted(relevance_map.values(), reverse=True)[:k]
    ideal_dcg = dcg_at_k(ideal_rels, k)

    if ideal_dcg == 0:
        return 0.0
    return actual_dcg / ideal_dcg


def precision_at_k(
    predicted_ids: List[str],
    relevant_ids: Set[str],
    k: int,
) -> float:
    """
    Compute Precision@K.

    Args:
        predicted_ids: Ordered list of candidate IDs
        relevant_ids: Set of truly relevant candidate IDs
        k: Cutoff position
    """
    top_k = predicted_ids[:k]
    hits = sum(1 for cid in top_k if cid in relevant_ids)
    return hits / k


def mean_average_precision(
    predicted_ids: List[str],
    relevant_ids: Set[str],
) -> float:
    """
    Compute Mean Average Precision (MAP).

    Args:
        predicted_ids: Ordered list of candidate IDs
        relevant_ids: Set of truly relevant candidate IDs
    """
    if not relevant_ids:
        return 0.0

    hits = 0
    sum_precision = 0.0

    for i, cid in enumerate(predicted_ids):
        if cid in relevant_ids:
            hits += 1
            precision_at_i = hits / (i + 1)
            sum_precision += precision_at_i

    return sum_precision / len(relevant_ids)


def compute_composite_score(
    predicted_ids: List[str],
    relevance_map: Dict[str, float],
    relevant_ids_tier3_plus: Set[str],
) -> float:
    """
    Compute the competition's final composite score.

    Formula: 0.50 × NDCG@10 + 0.30 × NDCG@50 + 0.15 × MAP + 0.05 × P@10
    """
    ndcg_10 = ndcg_at_k(predicted_ids, relevance_map, 10)
    ndcg_50 = ndcg_at_k(predicted_ids, relevance_map, 50)
    map_score = mean_average_precision(predicted_ids, relevant_ids_tier3_plus)
    p_10 = precision_at_k(predicted_ids, relevant_ids_tier3_plus, 10)

    composite = (
        0.50 * ndcg_10 +
        0.30 * ndcg_50 +
        0.15 * map_score +
        0.05 * p_10
    )

    return composite


def evaluate_ranking(
    predicted_ids: List[str],
    relevance_map: Dict[str, float],
) -> Dict[str, float]:
    """
    Full evaluation report.

    Args:
        predicted_ids: Ordered list of predicted candidate IDs
        relevance_map: Dict of candidate_id -> relevance tier (0-5)

    Returns:
        Dict with all metrics
    """
    # Relevant = tier 3 or above
    relevant_ids = {
        cid for cid, rel in relevance_map.items() if rel >= 3
    }

    return {
        "ndcg@5": ndcg_at_k(predicted_ids, relevance_map, 5),
        "ndcg@10": ndcg_at_k(predicted_ids, relevance_map, 10),
        "ndcg@20": ndcg_at_k(predicted_ids, relevance_map, 20),
        "ndcg@50": ndcg_at_k(predicted_ids, relevance_map, 50),
        "ndcg@100": ndcg_at_k(predicted_ids, relevance_map, 100),
        "map": mean_average_precision(predicted_ids, relevant_ids),
        "p@5": precision_at_k(predicted_ids, relevant_ids, 5),
        "p@10": precision_at_k(predicted_ids, relevant_ids, 10),
        "p@20": precision_at_k(predicted_ids, relevant_ids, 20),
        "composite": compute_composite_score(
            predicted_ids, relevance_map, relevant_ids
        ),
    }
