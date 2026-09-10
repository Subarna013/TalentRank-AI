#!/usr/bin/env python3
"""
Redrob Intelligent Candidate Discovery & Ranking System.

Single-command entry point that produces submission.csv from candidates.jsonl.
Must complete within 5 minutes on CPU with 16GB RAM and no network access.

Usage:
    python rank.py --candidates ./candidates.jsonl --out ./submission.csv
"""
import argparse
import logging
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.pipelines.online_ranker import OnlineRanker
from src.config.settings import get_settings


def setup_logging(verbose: bool = True):
    """Configure logging."""
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    parser = argparse.ArgumentParser(
        description="Redrob Candidate Ranking System"
    )
    parser.add_argument(
        "--candidates",
        type=str,
        required=True,
        help="Path to candidates.jsonl (or .jsonl.gz)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="./submission.csv",
        help="Output path for submission CSV",
    )
    parser.add_argument(
        "--dense",
        action="store_true",
        default=False,
        help="Enable dense retrieval (requires pre-computed embeddings)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Validate inputs
    candidates_path = Path(args.candidates)
    if not candidates_path.exists():
        logger.error(f"Candidates file not found: {candidates_path}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Redrob Intelligent Candidate Discovery & Ranking System")
    logger.info("=" * 60)
    logger.info(f"Candidates: {candidates_path}")
    logger.info(f"Output: {args.out}")
    logger.info(f"Dense retrieval: {'enabled' if args.dense else 'disabled (lite mode)'}")
    logger.info("")

    start = time.time()

    # Run the pipeline
    settings = get_settings()
    ranker = OnlineRanker(settings=settings, use_dense=args.dense)
    results = ranker.rank(
        candidates_path=str(candidates_path),
        output_path=args.out,
    )

    elapsed = time.time() - start

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"DONE — {len(results)} candidates ranked in {elapsed:.1f}s")
    logger.info(f"Output written to: {args.out}")
    logger.info("=" * 60)

    # Quick sanity check
    if len(results) != 100:
        logger.warning(f"Expected 100 results, got {len(results)}")
        sys.exit(1)

    # Verify scores are non-increasing
    for i in range(len(results) - 1):
        if results[i].score < results[i + 1].score:
            logger.warning(
                f"Score not non-increasing at rank {results[i].rank}: "
                f"{results[i].score} < {results[i + 1].score}"
            )

    logger.info("Validation passed ✓")


if __name__ == "__main__":
    main()
