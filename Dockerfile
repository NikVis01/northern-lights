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

# Create non-root user for Cloud Run
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY src/ ./src/
COPY pyproject.toml* ./

# Set PATH to include user local bin
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app/src

# Change ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set working directory to src for uvicorn
WORKDIR /app/src

# Expose port (Cloud Run uses PORT env var)
ENV PORT=8080
EXPOSE 8080

# Health check (Cloud Run handles this via startup/liveness probes)
# HEALTHCHECK removed - Cloud Run uses configured probes instead

# Run uvicorn (Cloud Run sets PORT env var)
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]

