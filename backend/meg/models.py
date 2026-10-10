"""Validated data contracts shared by ingest, recall, API, and MCP layers."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from meg.db import validate_tenant_id


class Sensitivity(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"


class Outcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"


class EventType(StrEnum):
    READ = "read"
    EDIT = "edit"
    COMMAND = "command"
    SEARCH = "search"
    OTHER = "other"


class AgentInput(BaseModel):
    id: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    role: str = Field(min_length=1, max_length=100)


class TraceEvent(BaseModel):
    type: EventType
    path: str | None = None
    text: str | None = None
    summary: str | None = None
    exit_code: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Trace(BaseModel):
    tenant_id: str
    agent: AgentInput
    task: str = Field(min_length=1)
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    events: list[TraceEvent] = Field(min_length=1)
    outcome: Outcome

    @field_validator("tenant_id")
    @classmethod
    def tenant_id_is_safe(cls, value: str) -> str:
        return validate_tenant_id(value)


class PolicyInput(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    effect: str
    action: str
    agent_role: str
    max_sensitivity: Sensitivity


class StoredProcedure(BaseModel):
    id: str
    title: str
    summary: str
    sensitivity: Sensitivity
    owner_agent: str
    success_count: int = 0
    fail_count: int = 0
    created_at: datetime
    last_used_at: datetime
