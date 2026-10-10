"""FastAPI transport; business logic stays in MegService."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from meg.db import FalkorStore
from meg.service import MegService
from meg.graphql_api import router as graphql_router


class RecallRequest(BaseModel):
    tenant_id: str
    agent_id: str
    task: str
    k: int = Field(default=3, ge=1, le=10)

class PolicyRequest(BaseModel):
    id: str
    name: str
    effect: str
    action: str
    agent_role: str
    max_sensitivity: str


def create_app(service: MegService | None = None) -> FastAPI:
    app = FastAPI(title="meg", version="0.1.0")
    app.state.service = service

    def get_service() -> MegService:
        if app.state.service is None:
            app.state.service = MegService(FalkorStore())
        return app.state.service

    app.include_router(graphql_router(get_service),prefix="/graphql")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/record")
    def record(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            result = get_service().record(payload)
        except PermissionError as error:
            raise HTTPException(403, str(error)) from error
        return {"procedure_id": result.procedure_id, "merged_into": result.merged_into,
                "new_steps": result.new_steps, "reused_steps": result.reused_steps}

    @app.post("/recall")
    def recall(payload: RecallRequest) -> dict[str, Any]:
        return {"procedures": get_service().recall(payload.tenant_id, payload.agent_id, payload.task, payload.k)}

    @app.get("/procedures/{procedure_id}/explain")
    def explain(procedure_id: str, tenant_id: str) -> dict[str, Any]:
        result = get_service().explain(tenant_id, procedure_id)
        if result is None:
            raise HTTPException(404, "Procedure not found")
        return result

    @app.get("/graph")
    def graph(tenant_id: str) -> dict[str, list]:
        result = get_service().store.graph_for(tenant_id).query("MATCH (n) OPTIONAL MATCH (n)-[r]->(m) RETURN n.id, labels(n), type(r), m.id")
        nodes, links = {}, []
        for row in list(getattr(result, "result_set", result or [])):
            node_id, labels, edge, target = row
            nodes[node_id] = {"id": node_id, "label": labels[0] if labels else "Node"}
            if edge and target: links.append({"source": node_id, "target": target, "label": edge})
        return {"nodes": list(nodes.values()), "links": links}

    @app.get("/audit")
    def audit(tenant_id: str, decision: str | None = None) -> dict[str, Any]:
        return {"entries": get_service().audit_log(tenant_id, decision)}

    @app.get("/policies")
    def policies(tenant_id: str) -> dict[str, Any]:
        return {"policies": get_service().policies(tenant_id)}

    @app.post("/policies")
    def create_policy(tenant_id: str, payload: PolicyRequest) -> dict[str, str]:
        get_service().create_policy(tenant_id, payload.model_dump())
        return {"status": "created", "id": payload.id}

    @app.get("/bench/results")
    def bench_results() -> dict[str, Any]:
        return get_service().benchmark()

    @app.get("/agent/config")
    def active_config(tenant_id: str) -> dict[str, Any]:
        return get_service().active_config(tenant_id)

    @app.get("/reviews")
    def reviews(tenant_id: str) -> dict[str, list]:
        return {"reviews": get_service().reviews(tenant_id)}

    @app.post("/reviews/run")
    def run_review(tenant_id:str,trace_id:str)->dict[str,list[str]]:
        return {"review_ids":get_service().run_review(tenant_id,trace_id)}

    @app.get("/proposals")
    def proposals(tenant_id: str) -> dict[str, list]:
        return {"proposals": get_service().proposals(tenant_id)}

    @app.post("/proposals/{proposal_id}/approve")
    def approve(proposal_id:str,tenant_id:str)->dict[str,str]:
        get_service().proposal_decision(tenant_id,proposal_id,"approved");return {"status":"approved"}
    @app.post("/proposals/{proposal_id}/reject")
    def reject(proposal_id:str,tenant_id:str)->dict[str,str]:
        get_service().proposal_decision(tenant_id,proposal_id,"reject");return {"status":"rejected"}
    @app.post("/proposals/{proposal_id}/rollback")
    def rollback(proposal_id:str,tenant_id:str)->dict[str,str]:
        get_service().proposal_decision(tenant_id,proposal_id,"rolled_back");return {"status":"rolled_back"}
    @app.get("/lineage/{config_version}")
    def lineage(config_version:int,tenant_id:str)->dict[str,list]:return {"lineage":get_service().lineage(tenant_id,config_version)}

    @app.get("/metrics/loop")
    def loop_metrics(tenant_id: str) -> dict[str, list]:
        return {"versions": []}

    return app


app = create_app()
