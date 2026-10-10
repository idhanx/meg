"""Candidate retrieval from FalkorDB, preferring vector search when possible."""

from __future__ import annotations

from typing import Any

from meg.db import Graph
from meg.recall.embed import keywords

VECTOR_CANDIDATES = """
CALL db.idx.vector.queryNodes('Procedure', 'embedding', $limit, vecf32($embedding)) YIELD node, score
OPTIONAL MATCH (node)-[:SOLVES]->(t:Task)
RETURN node.id AS id, node.title AS title, node.summary AS summary, node.sensitivity AS sensitivity,
 node.success_count AS success_count, node.fail_count AS fail_count, node.last_used_at AS last_used_at,
 score AS similarity, t.description AS task
"""
KEYWORD_CANDIDATES = """
MATCH (p:Procedure)-[:SOLVES]->(t:Task)
RETURN p.id AS id, p.title AS title, p.summary AS summary, p.sensitivity AS sensitivity,
 p.success_count AS success_count, p.fail_count AS fail_count, p.last_used_at AS last_used_at,
 t.description AS task
"""


def _rows(result: Any) -> list[Any]:
    return list(getattr(result, "result_set", result or []))


def _as_dict(row: Any, fields: list[str]) -> dict[str, Any]:
    return row if isinstance(row, dict) else dict(zip(fields, row))


def candidates(graph: Graph, task: str, embedding: list[float] | None, limit: int = 10) -> list[dict[str, Any]]:
    """Fetch candidates and calculate lexical similarity when vectors are unavailable."""
    fields = ["id", "title", "summary", "sensitivity", "success_count", "fail_count", "last_used_at", "similarity", "task"]
    if embedding is not None:
        try:
            return [_as_dict(row, fields) for row in _rows(graph.query(VECTOR_CANDIDATES, {"limit": limit, "embedding": embedding}))]
        except Exception:
            pass
    query_words = keywords(task)
    rows = [_as_dict(row, fields[:-2] + ["task"]) for row in _rows(graph.query(KEYWORD_CANDIDATES))]
    for row in rows:
        candidate_words = keywords(" ".join(str(row.get(key) or "") for key in ("title", "summary", "task")))
        row["similarity"] = len(query_words & candidate_words) / max(1, len(query_words | candidate_words))
    return sorted(rows, key=lambda item: item["similarity"], reverse=True)[:limit]
