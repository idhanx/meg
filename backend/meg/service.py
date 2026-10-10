"""Shared application service used by both FastAPI and MCP transports."""

from __future__ import annotations

from typing import Any
import json
from pathlib import Path

from meg.db import FalkorStore
from meg.agent.config_store import ConfigStore
from meg.governance.audit import audit
from meg.governance.policy import allowed, policies_for, seed_defaults
from meg.ingest.merge import RecordResult, record_trace
from meg.ingest.parser import parse_trace
from meg.recall.embed import embed
from meg.recall.rank import rank
from meg.recall.search import candidates
from meg.review.worker import ReviewWorker
from meg.gate.proposals import ProposalStore
from uuid import uuid4
from meg.schema import ensure_schema


def initialize_tenant(store: FalkorStore, tenant_id: str) -> None:
    """Select a tenant graph and ensure its schema exists."""
    graph = store.graph_for(tenant_id)
    ensure_schema(graph)
    seed_defaults(graph)


class MegService:
    def __init__(self, store: FalkorStore) -> None:
        self.store = store

    def record(self, payload: dict[str, Any]) -> RecordResult:
        trace = parse_trace(payload)
        initialize_tenant(self.store, trace.tenant_id)
        graph = self.store.graph_for(trace.tenant_id)
        granted, reason = allowed(trace.agent.role, "write", trace.sensitivity.value, policies_for(graph))
        if not granted:
            # There is no Procedure to attach before a denied creation; audit uses a request placeholder node.
            graph.query("MERGE (p:Procedure {id:$id}) ON CREATE SET p.title='Denied write request', p.sensitivity=$sensitivity "
                        "MERGE (a:Agent {id:$agent}) CREATE (a)-[:ACCESSED {action:'write',decision:'denied',reason:$reason,ts:$ts,query:$query}]->(p)",
                        {"id": f"denied:{trace.agent.id}:{trace.task}", "sensitivity": trace.sensitivity.value, "agent": trace.agent.id,
                         "reason": reason, "ts": "", "query": trace.task})
            raise PermissionError(reason)
        result = record_trace(graph, trace)
        vector = embed(trace.task)
        if result.procedure_id and vector:
            # FalkorDB stores embeddings as vecf32, enabling the vector index in recall.
            graph.query("MATCH (p:Procedure {id:$id})-[:SOLVES]->(t:Task) SET p.embedding=vecf32($embedding), t.embedding=vecf32($embedding)",
                        {"id": result.procedure_id, "embedding": vector})
        config_version=ConfigStore(graph).active().version
        trace_id=str(uuid4())
        worker=ReviewWorker(graph)
        worker.store_trace(trace_id,trace.task,trace.outcome.value,[event.model_dump() for event in trace.events],config_version)
        worker.run(trace_id)
        return result

    def recall(self, tenant_id: str, agent_id: str, task: str, k: int = 3) -> list[dict[str, Any]]:
        graph = self.store.graph_for(tenant_id)
        result_rows = candidates(graph, task, embed(task), limit=10)
        role_result = graph.query("MATCH (a:Agent {id:$id}) RETURN a.role", {"id": agent_id})
        role_rows = list(getattr(role_result, "result_set", role_result or []))
        role = (role_rows[0][0] if role_rows and not isinstance(role_rows[0], dict) else (role_rows[0].get("role") if role_rows else "readonly"))
        policies = policies_for(graph)
        visible = []
        for candidate in result_rows:
            granted, reason = allowed(role, "read", candidate.get("sensitivity", "internal"), policies)
            audit(graph, agent_id, candidate["id"], "read", "allowed" if granted else "denied", reason, task)
            if granted:
                visible.append(candidate)
        return rank(visible, task, k)

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

    def audit_log(self, tenant_id: str, decision: str | None = None) -> list[dict[str, Any]]:
        query = "MATCH (a:Agent)-[r:ACCESSED]->(p:Procedure) WHERE $decision IS NULL OR r.decision=$decision RETURN a.id, p.id, r.action, r.decision, r.reason, r.ts, r.query ORDER BY r.ts DESC"
        rows = list(getattr(self.store.graph_for(tenant_id).query(query, {"decision": decision}), "result_set", []))
        return [{"agent_id": r[0], "procedure_id": r[1], "action": r[2], "decision": r[3], "reason": r[4], "ts": r[5], "query": r[6]} for r in rows]

    def policies(self, tenant_id: str) -> list[dict[str, str]]:
        return policies_for(self.store.graph_for(tenant_id))

    def create_policy(self, tenant_id: str, policy: dict[str, str]) -> None:
        graph = self.store.graph_for(tenant_id)
        graph.query("MERGE (p:Policy {id:$id}) SET p.name=$name, p.effect=$effect, p.action=$action, p.agent_role=$agent_role, p.max_sensitivity=$max_sensitivity", policy)

    def benchmark(self) -> dict[str, Any]:
        return json.loads((Path(__file__).parents[2] / "bench/results/latest.json").read_text())

    def active_config(self, tenant_id: str) -> dict[str, Any]:
        initialize_tenant(self.store, tenant_id)
        config = ConfigStore(self.store.graph_for(tenant_id)).active()
        return {"version": config.version, "body": config.body(), "hash": config.digest()}

    def reviews(self,tenant_id:str)->list[dict[str,Any]]:
        rows=list(getattr(self.store.graph_for(tenant_id).query("MATCH (r:Reviewer)-[:WROTE]->(v:Review)-[:GRADES]->(t:Trace) RETURN v.id,r.id,t.id,v.scores,v.overall,v.verdict ORDER BY v.created_at DESC"),"result_set",[]))
        return [{"id":x[0],"reviewer_id":x[1],"trace_id":x[2],"scores":json.loads(x[3]),"overall":x[4],"verdict":x[5]} for x in rows]
    def proposals(self,tenant_id:str)->list[dict[str,Any]]:
        return ProposalStore(self.store.graph_for(tenant_id)).list()
    def run_review(self,tenant_id:str,trace_id:str)->list[str]:
        return ReviewWorker(self.store.graph_for(tenant_id)).run(trace_id)
    def proposal_decision(self,tenant_id:str,proposal_id:str,decision:str)->None:
        from meg.gate.promoter import Promoter
        promoter=Promoter(self.store.graph_for(tenant_id))
        if decision=="reject":promoter.reject(proposal_id,"human rejection")
        else:self.store.graph_for(tenant_id).query("MATCH (p:Proposal {id:$id}) SET p.status=$status",{"id":proposal_id,"status":decision})
    def lineage(self,tenant_id:str,version:int)->list[dict[str,Any]]:
        rows=list(getattr(self.store.graph_for(tenant_id).query("MATCH (p:Proposal)-[:YIELDS]->(c:AgentConfig {version:$version}) OPTIONAL MATCH (d:Decision)-[:FOR]->(p) RETURN p.id,p.status,d.gate,d.reason",{"version":version}),"result_set",[]));return [{"proposal_id":r[0],"status":r[1],"gate":r[2],"reason":r[3]} for r in rows]
