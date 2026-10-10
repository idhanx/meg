"""Service entry point; later milestones add shared API/MCP operations here."""

from meg.db import FalkorStore
from meg.schema import ensure_schema


def initialize_tenant(store: FalkorStore, tenant_id: str) -> None:
    """Select a tenant graph and ensure its schema exists."""
    ensure_schema(store.graph_for(tenant_id))
