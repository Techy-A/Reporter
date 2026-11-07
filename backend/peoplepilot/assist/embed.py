"""Idea 2, embeddings: optional semantic search with a free local model.

Point PP_EMBED_BASE_URL at any OpenAI-compatible /embeddings endpoint (for free: Ollama with
`ollama pull nomic-embed-text`, URL http://localhost:11434/v1). Clause vectors are computed when
HR activates a policy and stored next to the clause. Without a model, keyword search (BM25) is
used on its own, so nothing breaks.

Only policy text and the (PII-redacted) question are ever sent to the embedding model.
"""
from __future__ import annotations

import logging
import math

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import PolicyClause
from ..security.redact import redact

log = logging.getLogger("peoplepilot.embed")
BATCH = 32


def enabled() -> bool:
    s = get_settings()
    return bool(s.embed_base_url and s.embed_model)


def embed_texts(texts: list[str]) -> list[list[float]] | None:
    s = get_settings()
    if not enabled() or not texts:
        return None
    out: list[list[float]] = []
    try:
        for i in range(0, len(texts), BATCH):
            resp = httpx.post(
                s.embed_base_url.rstrip("/") + "/embeddings",
                headers={"Authorization": f"Bearer {s.embed_api_key}"} if s.embed_api_key else {},
                json={"model": s.embed_model, "input": [t[:2000] for t in texts[i:i + BATCH]]},
                timeout=60,
            )
            resp.raise_for_status()
            data = sorted(resp.json()["data"], key=lambda d: d["index"])
            out.extend([list(map(float, d["embedding"])) for d in data])
    except Exception as exc:
        log.warning("embedding request failed: %s", type(exc).__name__)
        return None
    return out if len(out) == len(texts) else None


def embed_query(question: str) -> list[float] | None:
    vecs = embed_texts([redact(question)[:500]])
    return vecs[0] if vecs else None


def embed_policy_clauses(session: Session, tenant_id: int, policy_id: int) -> int:
    """(Re)compute vectors for one policy's clauses. Returns how many were embedded."""
    if not enabled():
        return 0
    clauses = list(session.scalars(select(PolicyClause).where(
        PolicyClause.tenant_id == tenant_id, PolicyClause.policy_id == policy_id).order_by(PolicyClause.position)))
    vecs = embed_texts([f"{c.heading}\n{c.text}" for c in clauses])
    if not vecs:
        return 0
    model = get_settings().embed_model or ""
    for c, v in zip(clauses, vecs):
        c.embedding, c.embed_model = v, model
    return len(clauses)


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0
