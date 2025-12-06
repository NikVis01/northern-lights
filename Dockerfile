# Multi-stage build for Cloud Run
FROM python:3.13-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies for pdf2image (poppler-utils) and Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for Cloud Run
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Install Playwright browsers (as appuser)
USER appuser
RUN playwright install chromium
USER root

# Copy application code
COPY app/ ./app/
COPY pyproject.toml* ./

# Set PATH to include user local bin
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app

# Change ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set working directory
WORKDIR /app

# Expose port (Cloud Run uses PORT env var)
ENV PORT=8080
EXPOSE 8080

# Health check (Cloud Run handles this via startup/liveness probes)
# HEALTHCHECK removed - Cloud Run uses configured probes instead

# Run uvicorn (Cloud Run sets PORT env var)
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]

