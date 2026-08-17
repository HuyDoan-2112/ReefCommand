"""LLM client with schema-constrained output.

Every call in this system requests structured output against a Pydantic model.
There is no free-text call path, deliberately: a text response has nowhere to go
in this architecture.
"""

from __future__ import annotations

from pydantic import BaseModel


def complete_structured[T: BaseModel](
    system: str,
    user: str,
    schema: type[T],
    max_retries: int = 2,
) -> T:
    """Call the model and parse into `schema`.

    On a validation failure, retry with the validation error appended so the model
    can correct itself. After `max_retries`, raise rather than returning a
    partially-repaired object.
    """
    raise NotImplementedError
