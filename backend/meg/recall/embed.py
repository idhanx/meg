"""Optional MiniLM embeddings with a deterministic keyword fallback."""

from __future__ import annotations

import re
from functools import lru_cache

from meg.config import EMBEDDING_DIMENSION, Settings

TOKEN = re.compile(r"[a-z0-9_.-/]+")


def keywords(text: str) -> set[str]:
    return {token for token in TOKEN.findall(text.lower()) if len(token) > 1}


@lru_cache(maxsize=1)
def _model(model_name: str):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name)


def embed(text: str, settings: Settings | None = None) -> list[float] | None:
    """Return a 384-dimensional embedding, or None when model loading is unavailable."""
    settings = settings or Settings()
    if not settings.embeddings_enabled:
        return None
    try:
        vector = _model(settings.embedding_model).encode(text, normalize_embeddings=True)
        values = [float(value) for value in vector]
        return values if len(values) == EMBEDDING_DIMENSION else None
    except Exception:
        return None
