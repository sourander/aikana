# ---- base: setup shared by dev and prod ----
FROM python:3.13-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8000

WORKDIR /app

# Runtime dependencies only. This layer is cached until the lock file changes.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project

RUN mkdir -p /data
EXPOSE 8000
CMD ["python", "-m", "aikana.main"]


# ---- dev: base plus the development dependency group ----
FROM base AS dev

RUN uv sync --locked --no-install-project
COPY src/ ./src/
RUN uv sync --locked


# ---- prod: base plus the application only. Keep this the LAST stage, so that
# a plain `docker build` (as run by Dokku) produces the production image. ----
FROM base AS prod

COPY src/ ./src/
RUN uv sync --locked --no-dev
