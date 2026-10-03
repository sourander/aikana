# ---- css: compile the Tailwind stylesheet with the standalone CLI (no Node.js/npm toolchain) ----
FROM debian:bookworm-slim AS css

# The CLI is pinned and checksum-verified, so the build never executes an unvetted upstream binary.
# Bump the version and both checksums (from the release's sha256sums.txt) together.
ARG TAILWIND_VERSION=v4.3.3
ARG TAILWIND_SHA256_X64=dc61b3ac6b8c9ca874c0cc4c57b2409791a64c5540404ca5f5367360babc313a
ARG TAILWIND_SHA256_ARM64=55fd0b241214eff3de1e8ee4f22796662f2d2e7a49bcfca7477cfd0bac398195

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && case "$(dpkg --print-architecture)" in \
         amd64) tw_arch=x64; tw_sha256=${TAILWIND_SHA256_X64} ;; \
         arm64) tw_arch=arm64; tw_sha256=${TAILWIND_SHA256_ARM64} ;; \
         *) echo "Unsupported architecture: $(dpkg --print-architecture)" >&2; exit 1 ;; \
       esac \
    && curl -sLo "/tmp/tailwindcss-linux-${tw_arch}" \
         "https://github.com/tailwindlabs/tailwindcss/releases/download/${TAILWIND_VERSION}/tailwindcss-linux-${tw_arch}" \
    && echo "${tw_sha256}  /tmp/tailwindcss-linux-${tw_arch}" | sha256sum -c - \
    && install "/tmp/tailwindcss-linux-${tw_arch}" /usr/local/bin/tailwindcss \
    && rm "/tmp/tailwindcss-linux-${tw_arch}"

WORKDIR /app
COPY src/ ./src/
RUN tailwindcss -i ./src/aikana/shared/static/input.css -o ./src/aikana/shared/static/app.css --minify


# ---- base: setup shared by test and prod ----
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


# ---- test: base plus the application and the development dependency group, then
# run the suite during the build ----
FROM base AS test

# Development dependencies only. This layer is cached until the lock file changes.
RUN uv sync --locked --no-install-project
COPY src/ ./src/
COPY --from=css /app/src/aikana/shared/static/app.css ./src/aikana/shared/static/app.css
RUN uv sync --locked
COPY tests/ ./tests/
RUN pytest


# ---- prod: base plus the application only. Keep this the LAST stage, so that
# a plain `docker build` (as run by Dokku) produces the production image. ----
FROM base AS prod

COPY src/ ./src/
COPY --from=css /app/src/aikana/shared/static/app.css ./src/aikana/shared/static/app.css
RUN uv sync --locked --no-dev

