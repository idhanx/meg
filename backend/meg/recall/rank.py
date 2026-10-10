"""Explainable ranking and optional procedure chaining."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

from meg.config import PATH_OVERLAP_WEIGHT, RECENCY_WEIGHT, SIMILARITY_WEIGHT, SUCCESS_RATE_WEIGHT
from meg.recall.embed import keywords


def _recency(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        age_days = max(0.0, (datetime.now(UTC) - datetime.fromisoformat(value.replace("Z", "+00:00"))).total_seconds() / 86400)
        return math.exp(-age_days / 30)
    except ValueError:
        return 0.0


def score(candidate: dict[str, Any], task: str) -> dict[str, float]:
    success = float(candidate.get("success_count") or 0)
    failed = float(candidate.get("fail_count") or 0)
    files = set(candidate.get("files") or [])
    task_words = keywords(task)
    file_overlap = sum(1 for path in files if keywords(path) & task_words) / max(1, len(files))
    parts = {"similarity": float(candidate.get("similarity") or 0), "success_rate": success / (success + failed + 1),
             "recency": _recency(candidate.get("last_used_at")), "path_overlap": file_overlap}
    parts["total"] = (SIMILARITY_WEIGHT * parts["similarity"] + SUCCESS_RATE_WEIGHT * parts["success_rate"] +
                      RECENCY_WEIGHT * parts["recency"] + PATH_OVERLAP_WEIGHT * parts["path_overlap"])
    return parts


def rank(candidates: list[dict[str, Any]], task: str, k: int = 3) -> list[dict[str, Any]]:
    """Return UI-ready, explainable result objects."""
    ranked = []
    for candidate in candidates:
        breakdown = score(candidate, task)
        ranked.append({"procedure_id": candidate["id"], "title": candidate.get("title", "Untitled"),
                       "score": round(breakdown["total"], 5), "score_breakdown": breakdown,
                       "steps": candidate.get("steps", []), "files": candidate.get("files", []),
                       "verify_command": candidate.get("verify_command"),
                       "why": f"{breakdown['similarity']:.0%} task match; {breakdown['success_rate']:.0%} verified success rate.",
                       "path": candidate.get("path", [candidate["id"]])})
    return sorted(ranked, key=lambda result: result["score"], reverse=True)[:k]
