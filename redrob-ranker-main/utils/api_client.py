"""
API Client for communicating with the FastAPI backend.
Handles environment-based URL configuration, retries, and error handling.
"""
import os
import time
import requests
from typing import Optional

# For HF Spaces deployment, backend runs on same host
# In development, defaults to localhost:8000
import streamlit as st

API_BASE_URL = os.environ.get(
    "API_BASE_URL",
    "http://127.0.0.1:8000/api"
)

st.write("Current API URL:", API_BASE_URL)
TIMEOUT = int(os.environ.get("API_TIMEOUT", "120"))
MAX_RETRIES = 2
RETRY_DELAY = 1.0


def _get_url(endpoint: str) -> str:
    """Build full API URL."""
    return f"{API_BASE_URL}/{endpoint.lstrip('/')}"


def _request_with_retry(method: str, url: str, **kwargs) -> requests.Response:
    """Make an HTTP request with automatic retry on transient failures."""
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.ConnectionError as e:
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * (attempt + 1))
        except requests.exceptions.Timeout as e:
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
        except requests.exceptions.HTTPError:
            raise  # Don't retry HTTP errors (4xx, 5xx)
    raise last_error


def rank_candidates(payload: dict) -> dict:
    """Send candidates to the backend for ranking."""
    response = _request_with_retry(
        "POST",
        _get_url("rank"),
        json=payload,
        timeout=TIMEOUT,
    )
    return response.json()


def explain_candidate(payload: dict) -> dict:
    """Get deep explainability for a single candidate."""
    response = _request_with_retry(
        "POST",
        _get_url("explain"),
        json=payload,
        timeout=TIMEOUT,
    )
    return response.json()


def compare_candidates(payload: dict) -> dict:
    """Compare multiple candidates side-by-side."""
    response = _request_with_retry(
        "POST",
        _get_url("compare"),
        json=payload,
        timeout=TIMEOUT,
    )
    return response.json()


def health() -> dict:
    """Check backend health."""
    response = _request_with_retry(
        "GET",
        _get_url("health"),
        timeout=10,
    )
    return response.json()


def get_config() -> dict:
    """Get backend scoring configuration."""
    response = _request_with_retry(
        "GET",
        _get_url("config"),
        timeout=10,
    )
    return response.json()


def get_stats(payload: dict) -> dict:
    """Get quick statistics for a batch of candidates."""
    response = _request_with_retry(
        "POST",
        _get_url("stats"),
        json=payload,
        timeout=TIMEOUT,
    )
    return response.json()


def is_backend_available() -> bool:
    """Quick check if backend is reachable (no retry, short timeout)."""
    try:
        resp = requests.get(_get_url("health"), timeout=3)
        return resp.status_code == 200
    except Exception:
        return False
