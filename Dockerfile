# ---- css: compile the Tailwind stylesheet with the standalone CLI (no Node.js/npm toolchain) ----
FROM debian:bookworm-slim AS css

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && case "$(dpkg --print-architecture)" in \
         amd64) tw_arch=x64 ;; \
         arm64) tw_arch=arm64 ;; \
         *) echo "Unsupported architecture: $(dpkg --print-architecture)" >&2; exit 1 ;; \
       esac \
    && curl -sLo /usr/local/bin/tailwindcss \
         "https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-${tw_arch}" \
    && chmod +x /usr/local/bin/tailwindcss

WORKDIR /app
COPY src/ ./src/
RUN tailwindcss -i ./src/aikana/shared/static/input.css -o ./src/aikana/shared/static/app.css --minify


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
COPY --from=css /app/src/aikana/shared/static/app.css ./src/aikana/shared/static/app.css
RUN uv sync --locked


# ---- prod: base plus the application only. Keep this the LAST stage, so that
# a plain `docker build` (as run by Dokku) produces the production image. ----
FROM base AS prod

COPY src/ ./src/
COPY --from=css /app/src/aikana/shared/static/app.css ./src/aikana/shared/static/app.css
RUN uv sync --locked --no-dev

