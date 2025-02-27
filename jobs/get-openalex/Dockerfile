# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install --no-cache-dir poetry==1.6.1

# Copy project files
COPY pyproject.toml poetry.lock* README.md ./
COPY src ./src

# Configure poetry and install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --extras api

# Create data directory for SQLite
RUN mkdir -p /app/data /app/logs

# Set environment variables
ENV PYTHONPATH=/app
ENV JOB_DATABASE_URL=sqlite:////app/data/openalex_jobs.db
ENV OPENALEX_POSTGRES_URL=postgresql://postgres:postgres@postgres:5432/openalex

# Expose API port
EXPOSE 8000

# Run API
CMD ["uvicorn", "polus.aithena.jobs.getopenalex.api.app:app", "--host", "0.0.0.0", "--port", "8000"]