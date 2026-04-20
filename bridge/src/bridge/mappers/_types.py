from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Operation = Literal["create", "update"]


@dataclass(frozen=True)
class MappedResource:
    """A FHIR resource produced by a mapper, plus how to persist it.

    `identifier_query` is the `system|value` form used for conditional
    create/update so replays stay idempotent.
    """

    resource: Any
    operation: Operation = "create"
    identifier_query: str | None = None
