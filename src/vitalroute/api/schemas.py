"""HTTP request validation."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

class Trigger(BaseModel):
    scenario: Literal[
        "healthy", "schema_drift", "duplicates", "missing_partition", "invalid_values", "dependency_down"
    ]
    date: date
    agent_mode: Literal["ollama", "runbook"] = "ollama"
    request_key: str | None = Field(default=None, max_length=100)

class Decision(BaseModel):
    digest: str = Field(min_length=64, max_length=64)
    approve: bool
    actor: str = Field(default="Local pipeline owner", min_length=1, max_length=100)
