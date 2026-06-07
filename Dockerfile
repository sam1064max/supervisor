# syntax=docker/dockerfile:1.7
# ----------------------------------------------------------------------
# Multi-stage build for the Supervisor agent.
# - builder : installs dependencies into a venv via uv
# - runtime : small final image, non-root, healthcheck
# ----------------------------------------------------------------------

ARG PYTHON_VERSION=3.11

FROM python:${PYTHON_VERSION}-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

FROM base AS builder
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "uv>=0.5,<1.0"
WORKDIR /build
COPY pyproject.toml uv.lock* ./
COPY src ./src
RUN uv sync --frozen --no-dev || uv sync --no-dev
RUN uv pip install --no-deps --no-cache-dir .

FROM base AS runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system supervisor \
    && useradd --system --gid supervisor --home /app --shell /sbin/nologin supervisor
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/src /app/src
USER supervisor
ENV SUPERVISOR_ENV=production
VOLUME ["/app/logs"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import supervisor, sys; sys.exit(0 if supervisor.__version__ else 1)" || exit 1
ENTRYPOINT ["/usr/bin/tini", "--", "supervisor"]
CMD ["run"]
