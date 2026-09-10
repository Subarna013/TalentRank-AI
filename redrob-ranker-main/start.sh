#!/bin/bash
# Start both FastAPI backend and Streamlit frontend for HF Spaces deployment

# Set API base URL for the frontend to reach the backend
export API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000/api}"

echo "Starting FastAPI backend on port 8000..."
python -m uvicorn api.server:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend to start..."
for i in $(seq 1 30); do
    if curl -s http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
        echo "Backend is ready!"
        break
    fi
    sleep 1
done

# Start Streamlit frontend
echo "Starting Streamlit frontend on port 7860..."
exec streamlit run app.py \
    --server.port=7860 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false
