"""FastAPI transport; business logic stays in MegService."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from meg.db import FalkorStore
from meg.service import MegService


class RecallRequest(BaseModel):
    tenant_id: str
    agent_id: str
    task: str
    k: int = Field(default=3, ge=1, le=10)


def create_app(service: MegService | None = None) -> FastAPI:
    app = FastAPI(title="meg", version="0.1.0")
    app.state.service = service

    def get_service() -> MegService:
        if app.state.service is None:
            app.state.service = MegService(FalkorStore())
        return app.state.service

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

    return app


app = create_app()
