# Aikana

Aikana (_"time" or "within time" in Finnish_) is a small time-keeping app for teachers. One admin records courses, course realizations,
lessons and holidays. Students can view the calendar without logging in.

Built with Python, FastHTML, HTMX, SQLite and Tailwind CSS (compiled with the Tailwind CLI).

Views:

- **Semester view**: one column per month of the semester on a single screen, one row per day, lessons as small
  colored squares.
- **Realization view**: the weekly table of one CourseRealization, one row per week with Lessons and Notes columns.

> **Status:** early development. Both calendar views render persisted data and the admin can create Semesters;
> admin editing of Courses, CourseRealizations, Lessons and Holidays is being added incrementally. Progress is
> tracked in the `Tasks` sections of the `.sdd` specs.

## Configuration

| Variable         | Purpose                                                  |
|------------------|----------------------------------------------------------|
| `AIKANA_PASSWD` | Password of the single admin. Login is disabled if unset |
| `PORT`           | Port the app listens on (set automatically by Dokku)     |

The SQLite database is stored at `/data/app.db`. Mount a volume at `/data` to persist it.

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

The compiled stylesheet (`src/aikana/shared/static/app.css`) is normally produced by `Dockerfile`'s `css` stage. For
this run mode, generate it once with the [standalone Tailwind CLI](https://tailwindcss.com/blog/standalone-cli):

```sh
tailwindcss -i src/aikana/shared/static/input.css -o src/aikana/shared/static/app.css
```

## Deployment

Deployment is set up and run by the maintainer and is out of scope for this repository's tooling. The app deploys as a
Docker image: a plain `docker build .` builds the last stage of `Dockerfile` (`prod`), which contains no development
dependencies. A persistent volume must be mounted at `/data`, and `AIKANA_PASSWD` must be set.

To build the production image by hand:

```sh
docker build --target prod -t aikana:prod .    # same as a plain `docker build .`
```

## Contributing

See [CONTRIBUTE.md](CONTRIBUTE.md).
