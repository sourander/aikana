# Architecture: Ports and Adapters in Aikana

This document explains the architecture of the Aikana codebase. A student might find this interesting. This document uses the repository's own code as the case study, so you can open every file mentioned here and see the concept in working code. The binding contract is [src/aikana/architecture.sdd](src/aikana/architecture.sdd); this document is the guided tour.

## The problem: the "everything in the route" app

The simplest possible web app mixes everything in one function:

```python
@app.post("/holidays")
def add_holiday(day: str, title: str):
    db.execute("INSERT INTO holidays ...")   # SQL...
    if not title.strip():                    # ...business rules...
        return Div("Title required")         # ...and HTML, all in one place
```

This works, but three things hurt very quickly:

1. **You can't test the rules without HTTP and a database.** Checking that "an empty title is rejected" means spinning up a server and a database.
2. **You can't swap a technology.** Moving from SQLite to something else means rewriting the business rules, because they are tangled into the SQL.
3. **The rules scatter.** "A date carries at most one holiday" ends up half in a route, half in a SQL query, half in a template.

Ports and Adapters (also called *Hexagonal Architecture*) is a way of organizing code that avoids all three.

## The idea in one sentence

The **core** of the application — the entities and the business rules — sits in the middle and knows *nothing* about the web or the database; **adapters** at the edges translate between the core and each outside technology, and every dependency arrow points *inward*, toward the core.

## The big picture

```
                              DRIVING SIDE (requests come IN)
             Browser (HTMX)                     AI agent (MCP)
                   |                                  |
                   v                                  v
           feature/routes.py                mcp_server/server.py
           (FastHTML HTTP endpoints)        (MCP SDK, one tool per op.)
                   |                                  |
                   |   ,~~~~~~~~~~~~~~~~~~~~~~~~~~~,  |
                   |  ,'       THE HEXAGON        ,'   |
                   +--|        services.py         |<--+
                      |   use cases, validation    |
                      |   (plain Python)           |
                      |            |               |
                      |            v               |
                      |        domain.py           |
                      |   entities, business rules |
                      |        ^         ^         |
                      |        |         |         |
                      |     ports.py ----+         |
                      |   typing.Protocol          |
                      |   interfaces ("ports")     |
                      '            |             ,'
                        '~~~~~~~~  |  ~~~~~~~~~'
                                 | implemented by
                          repository_sqlite.py
                             (fastlite/SQL)
                                 |
                                 v
                        SQLite at /data/app.db
                              DRIVEN SIDE (the core calls OUT)
```

- The **driving side** (left/top) is where requests arrive: a browser talking HTTP, or an AI agent talking MCP.
- The **driven side** (bottom) is what the application itself calls out to: the database.
- The **hexagon** in the middle is the core: `domain.py`, `services.py` and `ports.py` of each feature package.

`main.py` sits outside all of this: it is the **composition root**, the one place that constructs every adapter and plugs them into the core.

## The vocabulary, mapped to real files

| Ports & Adapters term    | In this codebase                        | Concrete example                     |
|--------------------------|-----------------------------------------|--------------------------------------|
| Core ("inside")          | `domain.py` + `services.py` + `ports.py` | `src/aikana/holidays/`              |
| Domain entity            | a frozen dataclass in `domain.py`       | `Holiday`                            |
| Use case                 | a method on a `*Service` class          | `HolidayService.add_holiday`         |
| Port (driven)            | a `typing.Protocol` in `ports.py`       | `HolidayRepository`                  |
| Driven adapter           | `repository_sqlite.py`                  | `SqliteHolidayRepository`            |
| Driving adapter          | `routes.py`, `mcp_server/server.py`     | `day_dialog/routes.py`               |
| Renderer                 | `view.py` (FastHTML components)         | `semester/view.py`                   |
| Composition root         | `main.py`                               | `create_app(db)`                     |

A **port** is just an interface the core itself defines: "this is what I need from the outside world." An **adapter** is an implementation of that interface for one specific technology. *Driving* adapters drive the application (requests come in through them); *driven* adapters are driven by the application (the core calls out through them).

## Inside the hexagon

Everything in the core is plain Python. The rule is strict: `domain.py` and `services.py` must not import `fasthtml`, `starlette`, `fastlite` or the `mcp` SDK. You can verify this yourself:

```sh
grep -rn "fasthtml\|starlette\|fastlite\|mcp" src/aikana/*/domain.py src/aikana/*/services.py
# (prints nothing)
```

### `domain.py` — entities and rules

A frozen dataclass plus pure functions over it. Nothing else:

```python
# src/aikana/holidays/domain.py
@dataclass(frozen=True)
class Holiday:
    id: int
    date: date
    title: str
```

Richer example with actual rules: `src/aikana/semester/domain.py` computes a Semester's period from its year and term alone (`semester_bounds`) and picks the default Semester for "today" (`default_semester`). No database, no HTTP — you can call these functions in a Python shell.

### `services.py` — use cases

One `*Service` class per feature. It validates, enforces rules, and orchestrates the domain and the port:

```python
# src/aikana/holidays/services.py
class HolidayService:
    def __init__(self, repo: HolidayRepository) -> None:
        self.repo = repo

    def add_holiday(self, holiday_date: date, title: str) -> Holiday:
        self._reject_duplicate(holiday_date)          # a date carries at most one Holiday
        return self.repo.add(holiday_date, self._validated_title(title))
```

Notice what the service knows: *rules* ("reject an empty title", "reject a duplicate date"). Notice what it does not know: whether `self.repo` talks to SQLite, a file, or an in-memory fake. That is the point.

### `ports.py` — the boundary, as a `typing.Protocol`

```python
# src/aikana/holidays/ports.py
class HolidayRepository(Protocol):
    def get(self, holiday_id: int) -> Holiday | None: ...
    def list_for_range(self, start: date, end: date) -> list[Holiday]: ...
    def add(self, holiday_date: date, title: str) -> Holiday: ...
    def update(self, holiday_id: int, holiday_date: date, title: str) -> Holiday: ...
    def delete(self, holiday_id: int) -> None: ...
```

This is **dependency inversion**, the trick the whole architecture stands on. The natural direction would be "service depends on the SQLite repository." Instead, the core declares the interface it *wishes* existed, and the outer adapter conforms to it. The dependency arrow is flipped: it points at the core, never away from it.

A Python detail worth pausing on: `SqliteHolidayRepository` does **not** import or inherit `HolidayRepository`. A `Protocol` is *structural* — any class with the right methods satisfies it (checked by the type checker), so the adapter file never even imports the port.

## The adapters

### Driving adapters: `routes.py` and `server.py`

`routes.py` is the only module in a feature package allowed to invoke the package's use cases from FastHTML handlers. It deals in HTTP concepts — sessions, form strings, redirects — and translates them into plain service calls. `mcp_server/server.py` does the same job for AI agents, translating MCP tool calls into the very same service calls. Two driving adapters, one untouched core: this is the architecture paying rent.

### The renderer: `view.py`

`view.py` turns view-model dataclasses into FastHTML components. It imports the view-model types (they live in
`services.py`, next to the method that builds them) but never invokes a use case and never touches a database.

### The driven adapter: `repository_sqlite.py`

The one place SQL lives. It creates its table at construction and translates between rows and domain dataclasses, so the persistence shape never leaks into the core:

```python
# src/aikana/holidays/repository_sqlite.py
def _to_domain(row: dict) -> Holiday:
    return Holiday(id=row["id"], date=date.fromisoformat(row["date"]), title=row["title"])

class SqliteHolidayRepository:
    def add(self, holiday_date: date, title: str) -> Holiday:
        row = self._table.insert({"date": holiday_date.isoformat(), "title": title})
        return _to_domain(row)
```

Note that dates cross the boundary as ISO strings but exist inside the core as `datetime.date` objects — the translation happens exactly once, at the edge.

### The composition root: `main.py`

`main.py` is the only module that knows both sides. It opens the one shared database connection, constructs every repository, injects each into its service, and registers the routes:

```python
# src/aikana/main.py
def create_app(db: Database) -> FastHTML:
    holiday_service = HolidayService(SqliteHolidayRepository(db))
    ...
```

This wiring style is called **dependency injection**, done here without any framework: constructors simply declare what they need, and the composition root hands it to them.

## The dependency rule

Inside one feature package, arrows may only point inward — toward `domain.py`:

```
   view.py  (renders what routes hand it)
      ^
      |
   routes.py ------> services.py ------> domain.py
                         |    ^             ^
                         v    |             |
                        ports.py -----------+
                          :
                          : satisfies (structurally; no import!)
             repository_sqlite.py --------> domain.py
                          |
                          v
                        SQLite
```

Across features the rule is: use a neighbor's `services.py` or `ports.py`, never its `repository_sqlite.py`. A reference to another feature's entity is stored as a plain id (`CourseRealization.course_id: int`), never as
an imported object, and `services.py` validates the id through the neighbor's **service** when it needs the entity itself (e.g. `RealizationService` builds display labels from the `Course`), or through the neighbor's
**port** when it only needs to know the id exists (e.g. `LessonService` checks via `CourseRealizationRepository`).

Domain dataclasses are part of a feature's exposed contract, because its services accept and return them. So a consumer that receives those objects — the MCP serializers, the label composition — may import the *type* to
annotate and read it. What it must not do is call another feature's domain *functions* or reach into its persistence.

## A guided tour: the admin adds a holiday

Follow one request through the whole architecture:

```
 Browser --HTMX POST /day/dialog/holiday--> day_dialog/routes.py
       --> HolidayService.add_holiday(date, title)        (the use case)
             --> HolidayRepository.list_for_range(...)    (through the port)
       --> SqliteHolidayRepository                        (the driven adapter)
             --> INSERT INTO holidays ...                 (SQLite)
       --> Holiday(id=7, date=..., title="Itsapi...")     (back as a dataclass)
       --> routes re-render the wall planner via semester/view.py
```

1. **The route** (`day_dialog/routes.py`) checks the admin session, parses the form strings into a `date` and a `title`, and calls the service. It knows HTTP; it has never seen SQL.
2. **The service** (`holidays/services.py`) enforces the rules — non-empty title, one holiday per date — and asks the port to store the result. It knows the rules; it has never seen HTTP or SQL.
3. **The port** (`holidays/ports.py`) is only a `Protocol`: the shape of what "storing holidays" means.
4. **The adapter** (`holidays/repository_sqlite.py`) does the INSERT and converts the row back into a `Holiday` dataclass.
5. **The renderer** (`semester/view.py`) turns the re-read data into HTML for the HTMX swap.

Every layer is small because every layer has exactly one job.

## Testing: what the hexagon buys you

Open [tests/conftest.py](tests/conftest.py): its `services` fixture wires the *entire* service graph on a temporary database, exactly the way `main.py` does it, because `main.py` was written to have no side effects on import:

```python
@pytest.fixture
def db(tmp_path):
    return create_database(tmp_path / "app.db")
```

Domain rules are tested with plain function calls, no fixtures at all (see `tests/test_semester_domain.py`). And because services depend on a `Protocol`, a unit test *could* swap `SqliteHolidayRepository` for a five-line in-memory fake without changing one line of `HolidayService`.

## This repo's own way

Aikana follows the architecture pragmatically, not puritanically. The deliberate simplifications, all documented in [src/aikana/architecture.sdd](src/aikana/architecture.sdd):

- **No primary ports.** Textbook hexagons put an interface in front of the driving side too; here `routes.py`
  calls concrete service classes directly. There is exactly one driving framework, so the extra interface
  would be ceremony without a benefit.
- **View-models live in `services.py`.** When a view aggregates several features (the wall planner, the weekly
  cards), the service that builds the aggregation defines the dataclasses for it (`SemesterViewModel`,
  `RealizationViewModel`, `WeekRow`, ...), keeping `view.py` pure rendering over plain data.
- **Domain types are the cross-feature contract.** Services return domain dataclasses; consumers may annotate
  and read them, but may not invoke another feature's domain functions or persistence.
- **A mutual pair, wired in two phases.** `RealizationService` and `SemesterService` genuinely need each
  other, so `main.py` constructs one first and plugs the gap afterwards:

  ```python
  realization_service = RealizationService(realization_repo, ...)   # no semester_service yet
  semester_service = SemesterService(semester_repo, ..., realization_service)
  realization_service.semester_service = semester_service
  ```

  Each side type-hints the other under `if TYPE_CHECKING:`, so neither module imports the other at runtime.

- **One driven adapter only.** SQLite is the single database technology, yet the port still earns its place: it keeps `fastlite` out of the core and makes the service graph trivially re-wirable in tests.

## Where to look next

1. [src/aikana/architecture.sdd](src/aikana/architecture.sdd) — the binding contract this tour summarizes.
2. [src/aikana/holidays/](src/aikana/holidays/) — the smallest complete slice: four files, about 150 lines
   total, covering domain, port, service and adapter end to end.
3. [src/aikana/main.py](src/aikana/main.py) — the composition root; read it top to bottom once.
4. [tests/conftest.py](tests/conftest.py) — the same wiring reused for tests.
