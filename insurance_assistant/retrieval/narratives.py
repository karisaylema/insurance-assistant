"""Índice semántico de narrativas de claims (embeddings en ChromaDB).

Aquí es donde ChromaDB SÍ aplica: buscar relatos *semánticamente* parecidos
(paráfrasis) que el match exacto no ve. Colección separada de la póliza.
"""
from __future__ import annotations

from insurance_assistant.domain.schemas import LifeClaim
from insurance_assistant.retrieval.vectorstore import get_collection
from insurance_assistant.settings import settings


def _collection():
    return get_collection(settings.narrative_collection)


def index_narratives(claims: list[LifeClaim]) -> int:
    """Embebe las narrativas del histórico. Idempotente (upsert por claim_id)."""
    col = _collection()
    docs, ids, metas = [], [], []
    for c in claims:
        if c.narrative and c.claim_id:
            docs.append(c.narrative)
            ids.append(c.claim_id)
            metas.append({"member_name": c.member_name or ""})
    if docs:
        col.upsert(documents=docs, ids=ids, metadatas=metas)
    return len(docs)


def ensure_indexed(claims: list[LifeClaim]) -> None:
    """Indexa las narrativas si la colección está vacía (conveniencia demo)."""
    if _collection().count() == 0:
        index_narratives(claims)


def similar_narratives(
    narrative: str | None, k: int = 3, exclude_claim_id: str | None = None
) -> list[dict]:
    """Devuelve [{claim_id, similarity, member_name}] de las narrativas más
    parecidas. similarity = 1 - distancia coseno (0..1)."""
    if not narrative:
        return []
    res = _collection().query(query_texts=[narrative], n_results=k)
    ids = res.get("ids", [[]])[0]
    dists = res.get("distances", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    out = []
    for cid, dist, meta in zip(ids, dists, metas):
        if exclude_claim_id and cid == exclude_claim_id:
            continue
        out.append({
            "claim_id": cid,
            "similarity": max(0.0, 1.0 - dist),
            "member_name": (meta or {}).get("member_name", ""),
        })
    return out
