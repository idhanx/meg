"""Write and query authorization decisions as FalkorDB relationships."""

from __future__ import annotations

from datetime import UTC, datetime

from meg.db import Graph


def audit(graph: Graph, agent_id: str, procedure_id: str, action: str, decision: str, reason: str, query: str) -> None:
    graph.query("MATCH (p:Procedure {id: $procedure_id}) MERGE (a:Agent {id: $agent_id}) CREATE (a)-[:ACCESSED {action:$action, decision:$decision, reason:$reason, ts:$ts, query:$query}]->(p)",
                {"agent_id": agent_id, "procedure_id": procedure_id, "action": action, "decision": decision, "reason": reason, "ts": datetime.now(UTC).isoformat(), "query": query})
