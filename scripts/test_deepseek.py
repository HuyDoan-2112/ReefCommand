"""Send one live structured-output request to the configured DeepSeek provider."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from reefcommand.llm.client import complete_structured


class SmokeOutput(BaseModel):
    """Small response contract used only for the provider smoke test."""

    model_config = ConfigDict(extra="forbid")

    ready: bool
    message: str


def main() -> int:
    """Call DeepSeek once and print only the validated response."""
    result = complete_structured(
        system="You are testing a structured-output API connection.",
        user="Reply with ready=true and a short message confirming the connection.",
        schema=SmokeOutput,
        max_retries=1,
    )
    print(result.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
