"""Flag por narrativa semánticamente similar (posible relato reutilizado).

SEÑAL SUAVE, a propósito: la similitud semántica NO es prueba de fraude (dos
claims legítimos de accidente se parecen). Por eso:
  - umbral alto,
  - peso bajo → como mucho lleva a `manual_review`, nunca a `reject` por sí sola.

`flag_from_matches` es pura (recibe los matches ya calculados) → testeable sin
tocar ChromaDB. La búsqueda semántica (IO) vive en retrieval/narratives.py.
"""
from __future__ import annotations

from insurance_assistant.domain.schemas import Flag

# Calibrado al modelo de embeddings (all-MiniLM-L6-v2): con este modelo una
# paráfrasis clara ronda 0.66 y las narrativas no relacionadas ~0.45, así que
# 0.60 separa bien. Un embedder más potente daría una separación más nítida.
SIMILARITY_THRESHOLD = 0.60


def flag_from_matches(matches: list[dict]) -> Flag | None:
    if not matches:
        return None
    top = max(matches, key=lambda m: m["similarity"])
    if top["similarity"] >= SIMILARITY_THRESHOLD:
        return Flag(
            rule="similar_narrative",
            severity="medium",
            detail=(
                f"Narrativa {top['similarity'] * 100:.0f}% similar a un claim previo "
                f"({top['claim_id']}). Posible relato reutilizado — revisar."
            ),
            clause="Análisis semántico — narrativa similar (embeddings)",
            weight=2,
        )
    return None
