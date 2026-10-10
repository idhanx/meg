"""Convert canonical traces and best-effort Claude Code JSONL logs into Trace."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from meg.models import EventType, Trace, TraceEvent


def parse_trace(payload: Trace | dict[str, Any]) -> Trace:
    """Parse the canonical JSON object used by the record endpoint."""
    return payload if isinstance(payload, Trace) else Trace.model_validate(payload)


_CLAUDE_EVENT_TYPES = {"read": EventType.READ, "edit": EventType.EDIT, "write": EventType.EDIT,
                       "bash": EventType.COMMAND, "grep": EventType.SEARCH}


def parse_claude_code_jsonl(lines: Iterable[str], base_trace: dict[str, Any]) -> Trace:
    """Best-effort parser for Claude Code tool records; canonical input remains preferred."""
    events: list[TraceEvent] = []
    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        tool = str(record.get("tool_name") or record.get("name") or "").lower()
        event_type = _CLAUDE_EVENT_TYPES.get(tool)
        if event_type is None:
            continue
        arguments = record.get("input") or record.get("arguments") or {}
        result = record.get("result") or {}
        events.append(TraceEvent(
            type=event_type,
            path=arguments.get("path") or arguments.get("file_path"),
            text=arguments.get("command") or arguments.get("query"),
            summary=arguments.get("summary"),
            exit_code=result.get("exit_code") if isinstance(result, dict) else None,
        ))
    return Trace.model_validate({**base_trace, "events": [event.model_dump() for event in events]})
