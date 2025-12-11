# Create optimized version
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install dependencies in stages to avoid timeout
RUN pip install --no-cache-dir gunicorn Flask Flask-CORS python-dotenv && \
    pip install --no-cache-dir openai langchain-openai langchain-core && \
    pip install --no-cache-dir chromadb && \
    pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch && \
    pip install --no-cache-dir transformers sentence-transformers && \
    pip install --no-cache-dir -r requirements.txt || true

# Copy app
COPY . .

# Create directories
RUN mkdir -p data/chroma_db logs

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Use dynamic PORT from Railway
CMD gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --threads 2 --timeout 120 --access-logfile - --error-logfile - run:app