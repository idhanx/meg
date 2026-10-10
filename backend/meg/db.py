"""FalkorDB connection and tenant graph selection."""

from __future__ import annotations

import re
from typing import Any, Protocol

from falkordb import FalkorDB

from meg.config import Settings

TENANT_PATTERN = re.compile(r"^[a-z0-9_-]+$")


class Graph(Protocol):
    def query(self, query: str, params: dict[str, Any] | None = None) -> Any: ...


def validate_tenant_id(tenant_id: str) -> str:
    """Return a safe tenant id for use in a FalkorDB graph name."""
    if not TENANT_PATTERN.fullmatch(tenant_id):
        raise ValueError("tenant_id must match ^[a-z0-9_-]+$")
    return tenant_id


class FalkorStore:
    """Owns the FalkorDB client and exposes one isolated graph per tenant."""

    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        self.settings = settings or Settings()
        self.client = client or FalkorDB(host=self.settings.falkordb_host, port=self.settings.falkordb_port)

    def graph_for(self, tenant_id: str) -> Graph:
        return self.client.select_graph(f"tenant:{validate_tenant_id(tenant_id)}")
