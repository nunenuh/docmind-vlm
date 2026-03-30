# ── Stage 1: Build dependencies ───────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

COPY pyproject.toml poetry.lock* ./
RUN pip install --no-cache-dir poetry \
    && poetry config virtualenvs.in-project true \
    && poetry install --only main --no-root --no-cache

# ── Stage 2: Runtime ──────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy virtualenv from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy source
COPY src/ ./src/
COPY pyproject.toml ./

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8009

CMD ["python", "-m", "uvicorn", "docmind.main:app", "--host", "0.0.0.0", "--port", "8009"]

LABEL org.opencontainers.image.source="https://github.com/nunenuh/docmind-vlm"
LABEL org.opencontainers.image.description="DocMind VLM Backend"
