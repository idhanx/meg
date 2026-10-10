"""Idempotent FalkorDB schema setup for each tenant graph."""

from __future__ import annotations

from meg.config import EMBEDDING_DIMENSION
from meg.db import Graph

# FalkorDB has no portable IF NOT EXISTS form for all supported server versions.
# Re-running these statements is safe because an existing-index error is ignored.
SCHEMA_QUERIES = (
    "CREATE INDEX FOR (p:Procedure) ON (p.id)",
    "CREATE INDEX FOR (s:Step) ON (s.signature)",
    "CREATE INDEX FOR (a:Agent) ON (a.id)",
    "CREATE INDEX FOR (f:File) ON (f.path)",
    "CREATE VECTOR INDEX FOR (p:Procedure) ON (p.embedding) "
    f"OPTIONS {{dimension:{EMBEDDING_DIMENSION}, similarityFunction:'cosine'}}",
    "CREATE VECTOR INDEX FOR (t:Task) ON (t.embedding) "
    f"OPTIONS {{dimension:{EMBEDDING_DIMENSION}, similarityFunction:'cosine'}}",
)


def _already_exists(error: Exception) -> bool:
    message = str(error).lower()
    return "already exists" in message or "index exists" in message


def ensure_schema(graph: Graph) -> None:
    """Create all lookup and vector indexes, tolerating a previously-created one."""
    for query in SCHEMA_QUERIES:
        try:
            graph.query(query)
        except Exception as error:
            if not _already_exists(error):
                raise
