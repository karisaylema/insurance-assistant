"""Adapter de ChromaDB: elige backend local o cloud según settings.chroma_mode.
El resto del código depende de get_collection(), no del backend concreto.
"""
from __future__ import annotations

import chromadb

from insurance_assistant.settings import settings


def get_client() -> chromadb.ClientAPI:
    if settings.chroma_mode == "cloud":
        return chromadb.CloudClient(
            tenant=settings.chroma_tenant,
            database=settings.chroma_database,
            api_key=settings.chroma_api_key,
        )
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(settings.chroma_dir))


def get_collection(name: str | None = None):
    return get_client().get_or_create_collection(
        name=name or settings.collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def is_ingested() -> bool:
    try:
        return get_collection().count() > 0
    except Exception:
        return False
