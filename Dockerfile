# ─── Stage 1: build the lsc Go binary ──────────────────────────────────
FROM golang:1.23-alpine AS gobuild

WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download || true

COPY cmd ./cmd
COPY internal ./internal
RUN CGO_ENABLED=0 go build -o /out/lsc ./cmd/lsc

# ─── Stage 2: Python runtime serving FastAPI ───────────────────────────
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    REQUIRE_SOURCE_REVISION=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY api_server.py ./
COPY build-info.json ./
COPY LS-SPEC.md ./
COPY contract/contract.json ./contract/
COPY docs/JSON-OUTPUT.md ./docs/
COPY --from=gobuild /out/lsc /app/bin/lsc

RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin appuser
USER appuser

ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn api_server:app --host 0.0.0.0 --port ${PORT}"]
