# Smart Stock Selector — Multi-stage Dockerfile
# Stage 1: Build React frontend
# Stage 2: Python backend (serves built frontend as static files)

# ─── Stage 1: Frontend build ──────────────────────────────────────────────────
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend/v4

# Install dependencies first (layer cache)
COPY frontend/v4/package*.json ./
RUN npm ci

# Copy source and build
COPY frontend/v4/ ./
RUN npm run build

# ─── Stage 2: Python backend ──────────────────────────────────────────────────
FROM python:3.11-slim AS backend

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY core/ ./core/
COPY backend/ ./backend/
COPY fetch_stocks.py ./

# Bundle the offline demo fixture + seed script so the container self-seeds a
# populated dashboard on first boot (no empty dashboard, no network needed).
COPY scripts/ ./scripts/
COPY data/demo/ ./data/demo/

# Copy built frontend from stage 1
COPY --from=frontend-build /app/frontend/v4/dist ./frontend/v4/dist

# Seed-then-serve entrypoint (strip CR so a CRLF-authored file still runs in sh)
COPY docker-entrypoint.sh ./
RUN sed -i 's/\r$//' docker-entrypoint.sh && chmod +x docker-entrypoint.sh

# Create data directories (override with volumes in production)
RUN mkdir -p /app/data /app/logs

# Environment defaults (override at runtime)
ENV DB_PATH=/app/data/storage.db \
    MODEL_PATH=/app/data/model_sniper.pkl \
    LOG_LEVEL=INFO \
    CORS_ORIGINS=""

EXPOSE 8000

# Seed the bundled offline demo (idempotent), then serve on :8000.
ENTRYPOINT ["./docker-entrypoint.sh"]
