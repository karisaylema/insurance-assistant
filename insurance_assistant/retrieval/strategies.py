"""Strategy: cómo se entrega el contexto de la póliza al modelo.

Reemplaza el `if POLICY_MODE == ...` que antes estaba DUPLICADO en el chatbot y
en el nodo de razonamiento del grafo. Ahora la decisión vive en un solo lugar
(`get_strategy`) y añadir un modo nuevo (p. ej. "hybrid") es una clase nueva,
sin tocar a los consumidores (Open/Closed).
"""
from __future__ import annotations

import re
from typing import Protocol

from langchain_core.messages import SystemMessage

from insurance_assistant.documents.loaders import load_pages, load_policy_text
from insurance_assistant.llm.caching import cached_system
from insurance_assistant.retrieval.search import format_context, retrieve
from insurance_assistant.settings import settings

# Detecta páginas citadas por el modelo: "pág. 46", "página 53", "page 12"...
_PAGE_RE = re.compile(r"p[áa]g(?:inas?|s)?\.?\s*(\d+)|page\s*(\d+)", re.IGNORECASE)


def _pages_cited(text: str) -> list[str]:
    seen: list[str] = []
    for m in _PAGE_RE.finditer(text or ""):
        num = m.group(1) or m.group(2)
        if num and num not in seen:
            seen.append(num)
    return seen


class ContextStrategy(Protocol):
    """Construye el system prompt con el contexto de la póliza y sus fuentes."""

    def build_system(self, instructions: str, query: str) -> SystemMessage: ...

    def sources(self, query: str, answer: str = "") -> list[dict]: ...


class CachedPolicyStrategy:
    """CAG: la póliza completa va cacheada en el system prompt (~0.1x/lectura)."""

    def build_system(self, instructions: str, query: str) -> SystemMessage:
        return cached_system(instructions, load_policy_text())

    def sources(self, query: str, answer: str = "") -> list[dict]:
        # No hay chunks; usamos las páginas que el modelo citó en su respuesta.
        pages = _pages_cited(answer)
        if pages:
            return [{"source": "Sample-Life-Insurance-Policy.pdf", "page": p} for p in pages]
        return [{"source": "póliza completa (cacheada)", "page": "—"}]


class _RetrievalStrategy:
    """Base para estrategias que consultan ChromaDB. Memoiza los chunks por
    query (por instancia) para no recuperar dos veces en build_system + sources.
    """

    def __init__(self):
        self._chunks_by_query: dict[str, list[dict]] = {}

    def _chunks(self, query: str) -> list[dict]:
        if query not in self._chunks_by_query:
            self._chunks_by_query[query] = retrieve(query)
        return self._chunks_by_query[query]


class RagStrategy(_RetrievalStrategy):
    """RAG: solo los chunks relevantes recuperados de ChromaDB."""

    def build_system(self, instructions: str, query: str) -> SystemMessage:
        context = format_context(self._chunks(query))
        return SystemMessage(content=f"{instructions}\n\nCONTEXTO:\n{context}")

    def sources(self, query: str, answer: str = "") -> list[dict]:
        return self._chunks(query)


class HybridStrategy(_RetrievalStrategy):
    """Híbrido (parent-document): RAG selecciona qué páginas son relevantes y
    luego se cargan esas páginas COMPLETAS en contexto (no el chunk cortado).
    Precisión de ver la cláusula entera, sin mandar toda la póliza. Escala a
    corpus grandes donde CAG puro no cabría.
    """

    def _relevant_pages(self, query: str) -> list[tuple[str, int]]:
        pages, seen = [], set()
        for c in self._chunks(query):
            key = (c["source"], c["page"])
            if key not in seen:
                seen.add(key)
                pages.append(key)
        return pages

    def build_system(self, instructions: str, query: str) -> SystemMessage:
        context = load_pages(self._relevant_pages(query))
        return SystemMessage(
            content=f"{instructions}\n\nCONTEXTO (secciones completas):\n{context}"
        )

    def sources(self, query: str, answer: str = "") -> list[dict]:
        return [{"source": s, "page": p} for s, p in self._relevant_pages(query)]


_STRATEGIES = {
    "cached": CachedPolicyStrategy,
    "rag": RagStrategy,
    "hybrid": HybridStrategy,
}


def get_strategy() -> ContextStrategy:
    """Única decisión de qué estrategia usar (según settings.policy_mode)."""
    return _STRATEGIES[settings.policy_mode]()
