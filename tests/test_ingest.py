from __future__ import annotations

from dataclasses import dataclass, field

from meg.ingest.distill import distill
from meg.ingest.merge import FIND_PROCEDURES, WRITE_PROCEDURE, record_trace, step_candidates
from meg.ingest.parser import parse_claude_code_jsonl
from meg.models import Trace


@dataclass
class Result:
    result_set: list


@dataclass
class FakeGraph:
    paths: list = field(default_factory=list)
    writes: list = field(default_factory=list)

    def query(self, query: str, params: dict | None = None) -> Result:
        if query == FIND_PROCEDURES:
            return Result(self.paths)
        self.writes.append((query, params))
        return Result([])


def trace(verify: str = "pytest -x") -> Trace:
    return Trace.model_validate({
        "tenant_id": "demo", "agent": {"id": "agent-a", "name": "Agent A", "role": "developer"},
        "task": "Fix CI configuration", "outcome": "success",
        "events": [
            {"type": "read", "path": ".github/workflows/ci.yml"},
            {"type": "command", "text": "pytest -x", "exit_code": 1},
            {"type": "edit", "path": ".github/workflows/ci.yml", "summary": "set API_KEY"},
            {"type": "command", "text": verify, "exit_code": 0},
        ],
    })


def test_distill_drops_failed_command_but_keeps_context_and_verified_path() -> None:
    steps = distill(trace().events)
    assert [step.type.value for step in steps] == ["read", "edit", "command"]
    assert all(step.exit_code != 1 for step in steps)


def test_prefix_merge_reuses_shared_steps_and_links_parent() -> None:
    graph = FakeGraph()
    first = record_trace(graph, trace())
    first_steps = [step.signature for step in step_candidates(distill(trace().events))]
    graph.paths = [[first.procedure_id, first_steps]]
    second = record_trace(graph, trace("pytest tests/ci -x"))
    write_query, params = graph.writes[-1]
    assert write_query == WRITE_PROCEDURE
    assert params["parents"] == [first.procedure_id]
    assert second.merged_into == first.procedure_id
    assert second.reused_steps == 2


def test_identical_trace_increments_existing_procedure_without_duplicate() -> None:
    graph = FakeGraph(paths=[["procedure-1", [step.signature for step in step_candidates(distill(trace().events))]]])
    result = record_trace(graph, trace())
    assert result.procedure_id == "procedure-1"
    assert result.new_steps == 0
    assert all(query != WRITE_PROCEDURE for query, _ in graph.writes)


def test_claude_jsonl_parser_maps_known_tool_events() -> None:
    parsed = parse_claude_code_jsonl(
        ['{"tool_name":"Bash","input":{"command":"pytest"},"result":{"exit_code":0}}'],
        {"tenant_id": "demo", "agent": {"id": "a", "name": "A", "role": "developer"}, "task": "test", "outcome": "success"},
    )
    assert parsed.events[0].type.value == "command"
