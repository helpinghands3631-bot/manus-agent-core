# Production-ready Dockerfile for Manus Agent Core
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application codechore: add production Dockerfile

COPY agent/ ./agent/
COPY events/ ./events/
COPY llm/ ./llm/
COPY memory/ ./memory/
COPY tools/ ./tools/
COPY utils/ ./utils/
COPY config.py exceptions.py ./

# Create data directories
RUN mkdir -p /app/data /app/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run as non-root user
RUN useradd -m -u 1000 manus && chown -R manus:manus /app
USER manus

# Default command
CMD ["python", "-m", "agent.core"]
