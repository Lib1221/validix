# syntax=docker/dockerfile:1
#
# validix — reproducible test + docs environments (library has no long-running app).
#
# Targets:
#   test (default) — installs package + dev deps, runs pytest by default.
#   docs           — installs package + docs deps, serves MkDocs on :8000.
#
# Examples:
#   docker build -t validix:test .
#   docker build -t validix:docs --target docs .
#   docker compose run --rm test

ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim-bookworm AS deps

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE CHANGELOG.md ./
COPY src ./src

RUN pip install --upgrade pip \
    && pip install ".[dev]"


# ---------------------------------------------------------------------------
# Run the full pytest suite (default image target).
# ---------------------------------------------------------------------------
FROM deps AS test

COPY tests ./tests
COPY examples ./examples

CMD ["pytest", "-v"]


# ---------------------------------------------------------------------------
# Local MkDocs preview (Material theme).
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-bookworm AS docs

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE CHANGELOG.md ./
COPY src ./src

RUN pip install --upgrade pip \
    && pip install ".[docs]"

COPY docs ./docs
COPY mkdocs.yml ./

EXPOSE 8000

CMD ["mkdocs", "serve", "-a", "0.0.0.0:8000"]
