"""Extracción de un claim (texto) hacia un objeto Pydantic `LifeClaim` usando
structured output del modelo. Cubre la Opción 1 del challenge.
"""
from __future__ import annotations

import json

from insurance_assistant.domain.schemas import LifeClaim
from insurance_assistant.llm.factory import get_llm

EXTRACT_INSTRUCTION = (
    "Extrae los campos del siguiente claim de seguro de vida. "
    "Si un dato no aparece, déjalo en null. No inventes valores.\n\n"
    "DOCUMENTO DEL CLAIM:\n{text}"
)


def extract_claim(text: str, filename: str = "") -> LifeClaim:
    """Devuelve un LifeClaim. Para .json intenta mapear directo; si no, LLM."""
    if filename.lower().endswith(".json"):
        try:
            return LifeClaim.model_validate(json.loads(text))
        except Exception:
            pass  # cae al camino con LLM

    structured = get_llm().with_structured_output(LifeClaim)
    return structured.invoke(EXTRACT_INSTRUCTION.format(text=text[:8000]))
