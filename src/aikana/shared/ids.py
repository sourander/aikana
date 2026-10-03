"""@parse_id turns route path and query values into the integer entity ids the services use, per ../architecture.sdd."""


def parse_id(raw: str) -> int | None:
    """The integer id `raw` carries, or `None` when it is empty or not a whole number."""
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None
