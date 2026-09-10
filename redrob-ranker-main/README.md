# Redrob Intelligent Candidate Discovery & Ranking System

A production-quality talent intelligence system for the Redrob Hackathon.

## Architecture Overview

```
OFFLINE PIPELINE (Pre-computation)
───────────────────────────────────
candidates.jsonl
    │
    ├─► Data Validation & Honeypot Detection
    │
    ├─► Feature Engineering (5 families)
    │   ├── Skills Features (semantic match, depth, breadth)
    │   ├── Career Features (trajectory, stability, relevance)
    │   ├── Experience Features (years, recency, domain)
    │   ├── Education Features (tier, field, degree)
    │   └── Behavioral Features (engagement, trust, availability)
    │
    ├─► Multi-View Embedding Generation
    │   ├── Career Summary Embeddings
    │   ├── Skills Title Embeddings
    │   └── Responsibility Embeddings
    │
    ├─► Index Building
    │   ├── BM25 Sparse Index
    │   └── FAISS Dense Index (per view)
    │
    └─► LTR Model Training (LightGBM LambdaRank)
        └── Produces: models/, indexes/, embeddings/


ONLINE PIPELINE (Ranking - must run in <5 min, CPU, 16GB)
───────────────────────────────────────────────────────────
job_description.docx
    │
    ├─► JD Parser & Feature Generator
    │
    ├─► Metadata Pre-Filter (location, experience, availability)
    │
    ├─► Stage 1: Sparse Retrieval (BM25) → Top 2000
    │
    ├─► Stage 2: Dense Retrieval (FAISS multi-view) → Top 2000
    │
    ├─► Stage 3: Reciprocal Rank Fusion → Top 500
    │
    ├─► Stage 4: Feature Join + Trust Score Filter
    │
    ├─► Stage 5: LTR Ranker (LightGBM) → Top 100
    │
    ├─► Stage 6: Calibration & Score Normalization
    │
    └─► Stage 7: Deterministic Reasoning Generator
            │
            └─► submission.csv
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run offline pipeline (pre-computation) — can exceed 5 min
python -m src.pipelines.offline --candidates ./data/candidates.jsonl

# Run online ranking (must complete in <5 min)
python rank.py --candidates ./data/candidates.jsonl --out ./submission.csv

# Launch the Streamlit demo
streamlit run app.py

# Or run the FastAPI backend
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

## Single Reproduce Command

```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```

## Project Structure

```
src/
├── core/           # Base classes, type definitions
├── config/         # All configuration (thresholds, weights, paths)
├── validators/     # Data validation, honeypot detection
├── features/       # Feature engineering (5 families)
├── embeddings/     # Multi-view embedding generation
├── retrieval/      # BM25 + FAISS retrieval
├── ranking/        # LTR model (LightGBM LambdaRank)
├── reasoning/      # Deterministic explanation engine
├── evaluation/     # Offline evaluation (NDCG, MAP, P@K)
├── pipelines/      # Offline & Online orchestrators
├── models/         # Model wrappers
└── utils/          # Shared utilities
```

## Design Decisions

1. **Retrieval ≠ Ranking**: Maximize recall first (BM25 + dense), then maximize precision (LTR).
2. **Multi-view embeddings**: Career, Skills, Responsibilities encoded separately for fine-grained matching.
3. **Feature Registry**: All features are named, typed, versioned, and independently toggleable.
4. **Trust Score**: Composite integrity signal catches honeypots and keyword stuffers.
5. **Deterministic Reasoning**: Template-driven from top contributing features — no hallucination possible.
6. **Career Graph**: Models promotions, lateral moves, stability — not just flat job list.

## Compute Budget

| Stage | Complexity | Expected Time (100K candidates) |
|-------|-----------|------|
| Pre-filter | O(N) | ~2s |
| BM25 | O(N × query_terms) | ~5s |
| FAISS | O(log N) per view | ~3s |
| RRF | O(K log K) | <1s |
| Feature Join | O(K) | <1s |
| LTR Predict | O(K × trees) | <1s |
| Reasoning | O(100) | <1s |
| **Total Online** | | **~15s** |
