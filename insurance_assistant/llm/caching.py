"""Helpers de prompt caching para Claude vía langchain-anthropic.

El caching es 'prefix match': se cachea todo el prefijo hasta el bloque marcado.
Por eso lo estable (instrucciones + póliza) va primero con el breakpoint, y lo
volátil (pregunta, historial) va después sin marcar.
"""
from __future__ import annotations

from langchain_core.messages import SystemMessage

from insurance_assistant.settings import settings


def cached_system(instructions: str, cached_block: str) -> SystemMessage:
    """System message con `cached_block` (la póliza) marcado para cachearse."""
    return SystemMessage(
        content=[
            {"type": "text", "text": instructions},
            {
                "type": "text",
                "text": cached_block,
                "cache_control": {"type": "ephemeral", "ttl": settings.cache_ttl},
            },
        ]
    )


def usage_summary(response) -> dict:
    """Extrae tokens (incluye caché) de una respuesta de ChatAnthropic."""
    meta = getattr(response, "usage_metadata", None) or {}
    details = meta.get("input_token_details", {}) or {}
    return {
        "input_tokens": meta.get("input_tokens", 0),
        "output_tokens": meta.get("output_tokens", 0),
        "cache_read": details.get("cache_read", 0),
        "cache_creation": details.get("cache_creation", 0),
    }
