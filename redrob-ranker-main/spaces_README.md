---
title: Redrob AI Ranker
emoji: 🎯
colorFrom: indigo
colorTo: purple
sdk: docker
pinned: true
license: mit
---

# Redrob AI Ranker

Intelligent Candidate Discovery & Ranking System for the Redrob Hackathon.

Upload candidates (CSV/JSON/JSONL) and get AI-powered ranking with full explainability.

## Features

- 🤖 AI-powered candidate ranking with 45+ feature dimensions
- 🛡 Automated fraud/honeypot detection
- 📊 Real-time analytics dashboard
- 🧠 Full explainability for every ranking decision
- ⚖ Side-by-side candidate comparison
- 📄 CSV/JSON/Excel export

## Architecture

- **Frontend**: Streamlit (port 7860)
- **Backend**: FastAPI (port 8000)
- **Engine**: Multi-stage ranking with feature engineering, honeypot detection, and explainability
