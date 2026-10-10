"""Normalize successful traces and write shared procedure paths to FalkorDB."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from meg.db import Graph
from meg.ingest.distill import distill
from meg.models import EventType, Outcome, Trace, TraceEvent

_ABSOLUTE_PATH = re.compile(r"(?:/[\w.-]+)+")
_NUMBER = re.compile(r"\b\d+(?:\.\d+){0,3}\b")
_HASH = re.compile(r"\b[a-f0-9]{7,64}\b", re.IGNORECASE)
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class StepCandidate:
    signature: str
    kind: str
    description: str
    command: str | None
    path: str | None


@dataclass(frozen=True)
class RecordResult:
    procedure_id: str | None
    merged_into: str | None
    new_steps: int
    reused_steps: int


def normalize(value: str) -> str:
    """Collapse machine-specific values so equivalent work yields one step node."""
    value = _ABSOLUTE_PATH.sub("<path>", value)
    value = _HASH.sub("<hash>", value)
    value = _NUMBER.sub("<number>", value)
    return _WHITESPACE.sub(" ", value.strip().lower())


def step_candidates(events: list[TraceEvent]) -> list[StepCandidate]:
    candidates: list[StepCandidate] = []
    for event in events:
        source = event.text or event.path or event.summary or event.type.value
        signature = hashlib.sha1(f"{event.type.value}:{normalize(source)}".encode()).hexdigest()
        candidates.append(StepCandidate(signature, event.type.value, event.summary or source, event.text, event.path))
    return candidates


def _rows(result: Any) -> list[Any]:
    return list(getattr(result, "result_set", result or []))


# Existing paths are read first so an exact replay becomes a counter increment.
FIND_PROCEDURES = """
MATCH (p:Procedure)-[hs:HAS_STEP]->(s:Step)
WITH p, hs, s ORDER BY hs.order
WITH p, collect(s.signature) AS signatures
RETURN p.id AS id, signatures
"""

# One Cypher statement creates the complete procedure path, avoiding partial writes.
WRITE_PROCEDURE = """
MERGE (a:Agent {id: $agent.id}) SET a.name = $agent.name, a.role = $agent.role
MERGE (t:Task {id: $task_id}) ON CREATE SET t.description = $task, t.created_at = $now
CREATE (p:Procedure {id: $procedure_id, title: $title, summary: $task,
  sensitivity: $sensitivity, owner_agent: $agent.id, success_count: 1, fail_count: 0,
  created_at: $now, last_used_at: $now})
MERGE (a)-[:RECORDED]->(p)
MERGE (p)-[:SOLVES]->(t)
WITH p
UNWIND $steps AS step
MERGE (s:Step {signature: step.signature})
  ON CREATE SET s.id = step.signature, s.kind = step.kind, s.description = step.description,
                s.command = step.command
MERGE (p)-[:HAS_STEP {order: step.order}]->(s)
FOREACH (path IN CASE WHEN step.path IS NULL THEN [] ELSE [step.path] END |
  MERGE (f:File {path: path}) MERGE (s)-[:TOUCHES]->(f))
WITH p
UNWIND $links AS link
MATCH (from:Step {signature: link.from}), (to:Step {signature: link.to})
MERGE (from)-[:NEXT]->(to)
WITH DISTINCT p
FOREACH (command IN CASE WHEN $verify_command IS NULL THEN [] ELSE [$verify_command] END |
  MERGE (c:Command {text: command}) ON CREATE SET c.expected_exit = 0
  MERGE (p)-[:VERIFIED_BY]->(c))
WITH p
FOREACH (parent_id IN $parents |
  MATCH (parent:Procedure {id: parent_id}) MERGE (p)-[:BUILDS_ON]->(parent))
RETURN p.id AS procedure_id
"""


def _matching_paths(graph: Graph) -> list[tuple[str, list[str]]]:
    return [(row[0], list(row[1])) if not isinstance(row, dict) else (row["id"], list(row["signatures"]))
            for row in _rows(graph.query(FIND_PROCEDURES))]


def record_trace(graph: Graph, trace: Trace) -> RecordResult:
    """Record a successful distilled trace, reusing shared Step nodes by signature."""
    distilled = distill(trace.events)
    candidates = step_candidates(distilled)
    signatures = [candidate.signature for candidate in candidates]
    known_paths = _matching_paths(graph)
    exact = next((procedure_id for procedure_id, path in known_paths if path == signatures), None)
    now = datetime.now(UTC).isoformat()
    if trace.outcome is Outcome.FAILURE:
        if exact:
            graph.query("MATCH (p:Procedure {id: $id}) SET p.fail_count = p.fail_count + 1", {"id": exact})
        return RecordResult(None, exact, 0, len(candidates) if exact else 0)
    if not candidates:
        return RecordResult(None, None, 0, 0)
    if exact:
        graph.query("MATCH (p:Procedure {id: $id}) SET p.success_count = p.success_count + 1, p.last_used_at = $now", {"id": exact, "now": now})
        return RecordResult(exact, exact, 0, len(candidates))
    def shared_prefix(left: list[str], right: list[str]) -> int:
        return next((index for index, pair in enumerate(zip(left, right)) if pair[0] != pair[1]), min(len(left), len(right)))

    parents = [procedure_id for procedure_id, path in known_paths if shared_prefix(path, signatures) >= 2]
    params = {
        "agent": trace.agent.model_dump(), "task_id": str(uuid4()), "task": trace.task,
        "procedure_id": str(uuid4()), "title": trace.task[:100], "sensitivity": trace.sensitivity.value,
        "now": now, "steps": [{"signature": step.signature, "kind": step.kind, "description": step.description,
                                  "command": step.command, "path": step.path, "order": index}
                                 for index, step in enumerate(candidates)],
        "links": [{"from": signatures[index], "to": signatures[index + 1]} for index in range(len(signatures) - 1)],
        "verify_command": next((event.text for event in reversed(distilled) if event.type is EventType.COMMAND), None),
        "parents": parents,
    }
    graph.query(WRITE_PROCEDURE, params)
    known_signatures = {signature for _, path in known_paths for signature in path}
    return RecordResult(params["procedure_id"], parents[0] if parents else None,
                        sum(step.signature not in known_signatures for step in candidates),
                        sum(step.signature in known_signatures for step in candidates))
