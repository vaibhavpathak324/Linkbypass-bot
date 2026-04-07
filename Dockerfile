FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including curl/SSL for curl_cffi)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc curl libcurl4-openssl-dev libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY . .

# Create data directory
RUN mkdir -p data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000}/health || exit 1

# Run
CMD ["python", "-m", "bot.main"]
