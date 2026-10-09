# Aikana

Aikana (_"time" or "within time" in Finnish_) is a small time-keeping app for teachers. One admin records courses, course realizations,
lessons and holidays. Students can view the calendar without logging in.

Built with Python, FastHTML, HTMX, SQLite and hand-written vanilla CSS.

New to the codebase? [ARCHITECTURE.md](ARCHITECTURE.md) explains how it is organized.

Views:

- **Semester view**: one column per month of the semester on a single screen, one row per day, lessons as small
  colored squares.
- **Realization view**: the weekly table of one CourseRealization, one row per week with Lessons and Notes columns.

> **Status:** early development. Both calendar views render persisted data and the admin can create Semesters;
> admin editing of Courses, CourseRealizations, Lessons and Holidays is being added incrementally. Progress is
> tracked in the `Tasks` sections of the `.sdd` specs.

## Configuration

| Variable            | Purpose                                                                       |
|---------------------|-------------------------------------------------------------------------------|
| `AIKANA_PASSWD`     | Password of the single admin. Login is disabled if unset                      |
| `AIKANA_MCP_TOKEN`  | Bearer token for MCP write tools. MCP writes are disabled if unset            |

The app always listens on port `80`. `docker compose` publishes it on host port `8000`, and Dokku proxies to it.

The SQLite database is stored at `/data/app.db`. Mount a volume at `/data` to persist it.

## MCP server (connect an AI agent)

Aikana exposes an [MCP](https://modelcontextprotocol.io) server at `/mcp` (Streamable HTTP transport), so an AI
agent can read the calendar and, with a token, maintain it. Dates on the wire are ISO `yyyy-mm-dd`, times `HH:MM`.

- **Without credentials** an agent can list and read semesters, courses, course realizations, lessons, holidays,
  no-teach weeks and conferences.
- **With the `AIKANA_MCP_TOKEN` bearer token** it can also create, update and delete every entity. If the token
  is not configured on the server, the endpoint is read-only.

### OpenCode

Add the server to `~/.config/opencode/opencode.json` (global) or `opencode.json` in a project:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "aikana": {
      "type": "remote",
      "url": "https://aikana.munpaas.com/mcp",
      "enabled": true
    }
  }
}
```

For write access, add the token as a header. Keep the token in your shell environment
(`export AIKANA_MCP_TOKEN=...`) and reference it with `{env:...}` so it is not written into the config file;
`oauth: false` stops OpenCode's OAuth discovery so the header is used as-is:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "aikana": {
      "type": "remote",
      "url": "https://aikana.munpaas.com/mcp",
      "enabled": true,
      "oauth": false,
      "headers": {
        "Authorization": "Bearer {env:AIKANA_MCP_TOKEN}"
      }
    }
  }
}
```

Other agent tools configure remote MCP servers differently, but the same two ingredients apply everywhere: the
`/mcp` URL and an optional `Authorization: Bearer <token>` header.

For a locally running container the URL is `http://localhost:8000/mcp`.

## Run locally with Docker

```sh
mkdir -p data
AIKANA_PASSWD=change-me docker compose up --build
```

Then open [localhost:8000](http://localhost:8000). The `./data` directory is mounted at `/data` in the container, so the database
survives restarts. Stop the app with `docker compose down`.

`docker compose` builds the `prod` stage, so you run locally exactly the image that gets deployed.

## Run the tests in Docker

```sh
docker build --target test -t aikana:test .    # builds the app and runs the suite
docker run --rm aikana:test pytest             # run it again without rebuilding
```

## Develop without Docker

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync                    # create .venv and install locked dependencies
uv run pytest              # run the tests in tests/
uv run python -m aikana.main
```

The stylesheet (`src/aikana/shared/static/app.css`) is hand-written and committed to the repository, so this run mode
needs no build step.
## Deployment

Production is hosted on the maintainer's Dokku server at `ssh.munpaas.com` as the Dokku app `aikana`, served at
[aikana.munpaas.com](https://aikana.munpaas.com). The server-side setup is done: the app has been created
(`dokku apps:create aikana`), HTTPS has been enabled with the `letsencrypt` plugin
(`dokku letsencrypt:enable aikana`), the admin password is configured
(`dokku config:set aikana AIKANA_PASSWD=...`), and persistent storage is mounted at `/data`
(`dokku storage:ensure-directory aikana --chown root` and
`dokku storage:mount aikana /var/lib/dokku/data/storage/aikana:/data`). The image definition is named `Dockerfile`, so
no `dockerfile-path` setting is needed. Since the app listens on port `80`, the proxy target must be set to it
(`dokku proxy:port-set aikana 80`).

The MCP write token is configured the same way, for example
`dokku config:set aikana AIKANA_MCP_TOKEN=$(openssl rand -hex 32)`. Leave it unset to keep the MCP endpoint
read-only.

No code has been pushed to Dokku yet. Deployment is currently manual: the maintainer adds the Dokku git remote once,
then pushes `main`.

```sh
git remote add dokku dokku@ssh.munpaas.com:aikana   # once
git push dokku main
```

An automated CI/CD pipeline is planned to replace the manual push.

Deployment is run by the maintainer and is out of scope for this repository's tooling. The app deploys as a Docker
image: a plain `docker build .` builds the last stage of `Dockerfile` (`prod`), which contains no development
dependencies. The SQLite database lives in the mounted `/data` volume on the server
(`/var/lib/dokku/data/storage/aikana`), so production data survives redeploys and restarts.

To build the production image by hand:

```sh
docker build --target prod -t aikana:prod .    # same as a plain `docker build .`
```

## Contributing

See [CONTRIBUTE.md](CONTRIBUTE.md).
