import streamlit as st
from utils.api_client import health, get_config, is_backend_available
import os


def render():
    st.markdown("""
    <div class="welcome-header">
        <div class="welcome-text">
            <h2>📡 API Documentation</h2>
            <p>REST API reference for the RedRob AI Ranking Engine.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # API Base URL
    api_url = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000/api")
    backend_online = st.session_state.get("backend_online", False)

    col_status, col_link = st.columns([2, 1])
    with col_status:
        if backend_online:
            st.success(f"🟢 API is online at `{api_url}`")
        else:
            st.error(f"🔴 API is offline — Expected at `{api_url}`")
    with col_link:
        st.markdown(f"[📖 Open Swagger Docs →](http://127.0.0.1:8000/docs)")

    st.divider()

    # ─── Endpoints ───
    st.markdown("### Available Endpoints")

    # Health
    with st.expander("🟢 GET /api/health — System health check", expanded=False):
        st.markdown("Returns the current status of the ranking engine.")
        st.code("""curl http://127.0.0.1:8000/api/health""", language="bash")
        st.markdown("**Response:**")
        st.code("""{
      "status": "healthy",
      "version": "2.0.0",
      "engine": "loaded",
      "features": 45,
      "canonical_categories": 22
    }""", language="json")

        if backend_online:
            if st.button("▶ Try it", key="try_health"):
                data = health()
                st.json(data)

    # Config
    with st.expander("🔧 GET /api/config — Scoring configuration", expanded=False):
        st.markdown("Returns the current JD requirements and scoring architecture.")
        st.code("""curl http://127.0.0.1:8000/api/config""", language="bash")

        if backend_online:
            if st.button("▶ Try it", key="try_config"):
                data = get_config()
                st.json(data)

    # Rank
    with st.expander("🏆 POST /api/rank — Rank candidates", expanded=True):
        st.markdown("""
        The main ranking endpoint. Accepts a list of candidate profiles and returns
        them ranked by fit score with full reasoning.

        **Request Body:**
        """)
        st.code("""{
      "candidates": [
        {
          "candidate_id": "CAND_001",
          "profile": {
            "headline": "ML Engineer",
            "summary": "...",
            "location": "Bangalore",
            "country": "India",
            "years_of_experience": 6.0,
            "current_title": "Senior ML Engineer",
            "current_company": "TechCo",
            "current_company_size": "Large",
            "current_industry": "Technology"
          },
          "career_history": [...],
          "education": [...],
          "skills": [
            {"name": "Python", "proficiency": "advanced", "endorsements": 50, "duration_months": 60}
          ],
          "certifications": [...],
          "languages": [...],
          "redrob_signals": {...}
        }
      ],
      "top_k": 100
    }""", language="json")

        st.markdown("**Response:**")
        st.code("""{
      "results": [
        {
          "candidate_id": "CAND_001",
          "rank": 1,
          "score": 0.5121,
          "reasoning": "Senior ML Engineer with 6.0 yrs...",
          "title": "Senior ML Engineer",
          "company": "TechCo",
          "years_of_experience": 6.0,
          "location": "Bangalore",
          "country": "India",
          "is_honeypot": false,
          "trust_score": 1.0,
          "features": {}
        }
      ],
      "metadata": {
        "total_input": 1,
        "candidates_ranked": 1,
        "honeypots_filtered": 0,
        "runtime_seconds": 0.004,
        "top_k": 100
      }
    }""", language="json")

    # Explain
    with st.expander("🧠 POST /api/explain — Deep explainability", expanded=False):
        st.markdown("""
        Get a detailed feature breakdown and explanation for a single candidate.

        **Request Body:**
        ```json
        {"candidate": { ... single candidate object ... }}
        ```

        **Response includes:**
        - `overall_score` — composite score (0-1)
        - `reasoning` — human-readable explanation
        - `feature_breakdown` — scores per category (skills, career, experience, behavioral, location)
        - `honeypot_analysis` — trust assessment
        - `canonical_skills` — skill taxonomy coverage
        - `mutual_interest` — engagement/response probability
        """)

    # Compare
    with st.expander("⚖ POST /api/compare — Compare candidates", expanded=False):
        st.markdown("""
        Side-by-side comparison of 2-20 candidates.

        **Request Body:**
        ```json
        {"candidates": [ ... list of candidate objects ... ]}
        ```

        **Response:**
        ```json
        {
          "candidates": [
            {
              "candidate_id": "...",
              "score": 0.51,
              "technical_fit": 0.5,
              "career_evidence": 0.3,
              "mutual_interest": 0.4,
              "trust": 1.0,
              "is_honeypot": false
            }
          ],
          "count": 2
        }
        ```
        """)

    # Stats
    with st.expander("📊 POST /api/stats — Quick statistics", expanded=False):
        st.markdown("""
        Get quick dataset statistics without running full ranking.
        Returns top skills, locations, industries, and averages.

        **Request Body:**
        ```json
        {"candidates": [...], "top_k": 100}
        ```
        """)

    st.divider()

    # ─── SDK / Usage Guide ───
    st.markdown("### 🐍 Python SDK Usage")

    st.code("""
    import requests

    API = "http://127.0.0.1:8000/api"

    # Rank candidates
    response = requests.post(f"{API}/rank", json={
        "candidates": candidates_list,
        "top_k": 100
    })
    result = response.json()

    # Get explanation for top candidate
    explain = requests.post(f"{API}/explain", json={
        "candidate": candidates_list[0]
    }).json()

    # Compare top 3
    compare = requests.post(f"{API}/compare", json={
        "candidates": candidates_list[:3]
    }).json()
    """, language="python")

    st.divider()

    # ─── Running the API ───
    st.markdown("### 🚀 Running the API Server")
    st.code("""
    # Development
    uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload

    # Production
    uvicorn api.server:app --host 0.0.0.0 --port 8000 --workers 4
    """, language="bash")
