"""Búsqueda semántica sobre la colección de la póliza (modo RAG)."""
from __future__ import annotations

from insurance_assistant.retrieval.vectorstore import get_collection
from insurance_assistant.settings import settings


def retrieve(query: str, k: int | None = None) -> list[dict]:
    """Recupera los k fragmentos más relevantes de la póliza."""
    k = k or settings.retrieve_k
    res = get_collection().query(query_texts=[query], n_results=k)
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    return [
        {"text": d, "source": m.get("source"), "page": m.get("page")}
        for d, m in zip(docs, metas)
    ]


def format_context(chunks: list[dict]) -> str:
    return "\n\n".join(
        f"[{c['source']} · pág. {c['page']}]\n{c['text']}" for c in chunks
    )
