# syntax=docker/dockerfile:1.6

# ---------------------------------------------------------------------------
# Base image: slim Python 3.11. Multi-stage keeps build tooling out of the
# final image. Non-root user avoids running the app as root inside the
# container.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps required by psycopg2 at runtime and for healthchecks.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Builder stage: compiles wheels using build headers, then discards them.
# ---------------------------------------------------------------------------
FROM base AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /wheels
COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt

# ---------------------------------------------------------------------------
# Final runtime image.
# ---------------------------------------------------------------------------
FROM base AS runtime

# Dedicated non-root user; UID/GID chosen to be stable across rebuilds.
RUN groupadd --system --gid 1000 django \
    && useradd --system --uid 1000 --gid django --create-home django

WORKDIR /app

COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

COPY --chown=django:django . /app

# Pre-create the STATIC_ROOT so that when compose mounts a named volume
# on top of `/app/staticfiles/` it inherits the correct ownership; without
# this seed directory the fresh volume comes up root-owned and the
# non-root `django` user cannot run collectstatic.
RUN mkdir -p /app/staticfiles /app/media \
    && chown -R django:django /app/staticfiles /app/media

USER django

EXPOSE 8000

# Default command runs migrations then boots Gunicorn. Overridden by
# docker-compose during local development to use `runserver` instead.
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn fhir_portal.wsgi:application --bind 0.0.0.0:8000 --workers 3 --access-logfile - --error-logfile -"]
