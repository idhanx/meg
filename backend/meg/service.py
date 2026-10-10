"""Shared application service used by both FastAPI and MCP transports."""

from __future__ import annotations

from typing import Any

from meg.db import FalkorStore
from meg.ingest.merge import RecordResult, record_trace
from meg.ingest.parser import parse_trace
from meg.recall.embed import embed
from meg.recall.rank import rank
from meg.recall.search import candidates
from meg.schema import ensure_schema


def initialize_tenant(store: FalkorStore, tenant_id: str) -> None:
    """Select a tenant graph and ensure its schema exists."""
    ensure_schema(store.graph_for(tenant_id))


class MegService:
    def __init__(self, store: FalkorStore) -> None:
        self.store = store

    def record(self, payload: dict[str, Any]) -> RecordResult:
        trace = parse_trace(payload)
        initialize_tenant(self.store, trace.tenant_id)
        return record_trace(self.store.graph_for(trace.tenant_id), trace)

    def recall(self, tenant_id: str, agent_id: str, task: str, k: int = 3) -> list[dict[str, Any]]:
        graph = self.store.graph_for(tenant_id)
        results = candidates(graph, task, embed(task), limit=10)
        return rank(results, task, k)

    def explain(self, tenant_id: str, procedure_id: str) -> dict[str, Any] | None:
        result = self.store.graph_for(tenant_id).query(
            "MATCH (p:Procedure {id: $id}) OPTIONAL MATCH (a:Agent)-[:RECORDED]->(p) "
            "RETURN p.id, p.title, p.summary, p.success_count, p.fail_count, a.id", {"id": procedure_id})
        rows = list(getattr(result, "result_set", result or []))
        if not rows:
            return None
        row = rows[0]
        values = row if isinstance(row, dict) else {"procedure_id": row[0], "title": row[1], "summary": row[2], "success_count": row[3], "fail_count": row[4], "recorded_by": row[5]}
        return values
