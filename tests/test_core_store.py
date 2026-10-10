from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from meg.db import FalkorStore, validate_tenant_id
from meg.models import Trace
from meg.schema import SCHEMA_QUERIES, ensure_schema


@dataclass
class FakeGraph:
    seen: set[str] = field(default_factory=set)
    calls: list[str] = field(default_factory=list)

    def query(self, query: str, params: dict | None = None) -> None:
        self.calls.append(query)
        if query in self.seen:
            raise RuntimeError("Index already exists")
        self.seen.add(query)


class FakeClient:
    def __init__(self) -> None:
        self.graphs: dict[str, FakeGraph] = {}

    def select_graph(self, name: str) -> FakeGraph:
        return self.graphs.setdefault(name, FakeGraph())


def test_tenant_graph_isolated_and_schema_is_idempotent() -> None:
    client = FakeClient()
    store = FalkorStore(client=client)
    demo = store.graph_for("demo")
    other = store.graph_for("other")
    ensure_schema(demo)
    ensure_schema(demo)
    assert demo is not other
    assert len(demo.seen) == len(SCHEMA_QUERIES)
    assert len(demo.calls) == len(SCHEMA_QUERIES) * 2


def test_invalid_tenant_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="tenant_id"):
        validate_tenant_id("demo; DROP GRAPH")


def test_trace_validates_canonical_input() -> None:
    trace = Trace.model_validate({
        "tenant_id": "demo",
        "agent": {"id": "agent-a", "name": "Agent A", "role": "developer"},
        "task": "Fix CI environment variable",
        "events": [{"type": "command", "text": "pytest -x", "exit_code": 0}],
        "outcome": "success",
    })
    assert trace.events[0].exit_code == 0
