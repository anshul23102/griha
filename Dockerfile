# Griha, single container: the built React app and the API on one port. Used by the hosted demo (small Ubuntu VM).
FROM node:24-slim AS web
RUN npm install -g pnpm@11.4.0
WORKDIR /w
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.14-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN useradd -m -u 1000 griha
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/griha ./griha
COPY backend/policy ./policy
COPY backend/artifacts ./artifacts
COPY --from=web /w/dist /app/static
RUN mkdir -p /data && chown griha /data
USER griha
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYDANTIC_AI_NO_BANNER=1 \
    GRIHA_STATIC_DIR=/app/static GRIHA_DATA_DIR=/data GRIHA_ORCHESTRATOR=inline GRIHA_PUBLIC_DEMO=1 GRIHA_RETENTION_HOLD=0
EXPOSE 7860
# The real client address is worked out inside the app from X-Forwarded-For (griha/clientip.py); uvicorn's own proxy-header handling is off because it
# trusts the leftmost value, which a client can forge.
CMD ["uvicorn", "griha.api:app", "--host", "0.0.0.0", "--port", "7860"]
