FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements-demo.txt .
RUN pip install --no-cache-dir -r requirements-demo.txt

# Copy all source code
COPY src/ ./src/
COPY api/ ./api/
COPY utils/ ./utils/
COPY components/ ./components/
COPY views/ ./views/
COPY styles/ ./styles/
COPY data/ ./data/
COPY .streamlit/ ./.streamlit/
COPY app.py .
COPY rank.py .
COPY start.sh .

RUN chmod +x start.sh

# Expose ports: 7860 for Streamlit (HF Spaces default), 8000 for FastAPI
EXPOSE 7860 8000

# Start both services
CMD ["./start.sh"]
