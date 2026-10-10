"""stdio MCP tools delegating directly to MegService."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from meg.db import FalkorStore
from meg.service import MegService

mcp = FastMCP("meg")
service = MegService(FalkorStore())


@mcp.tool()
def record(trace_json: dict[str, Any]) -> dict[str, Any]:
    result = service.record(trace_json)
    return result.__dict__


@mcp.tool()
def recall(task: str, agent_id: str, tenant_id: str = "default") -> list[dict[str, Any]]:
    return service.recall(tenant_id, agent_id, task)


@mcp.tool()
def explain(procedure_id: str, tenant_id: str = "default") -> dict[str, Any] | None:
    return service.explain(tenant_id, procedure_id)


if __name__ == "__main__":
    mcp.run()
