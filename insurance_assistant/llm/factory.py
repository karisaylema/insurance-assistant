"""Factory del modelo. La orquestación (LangGraph) y los servicios solo llaman
a `get_llm()`; cambiar de proveedor es una variable de entorno.

Registro de proveedores (OCP): añadir uno = una función builder + una entrada
en `_PROVIDERS`, sin tocar `get_llm`. Los imports son perezosos para no cargar
la dependencia de un proveedor que no se usa.
"""
from __future__ import annotations

from functools import lru_cache

from insurance_assistant.settings import settings


def _build_anthropic():
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=settings.anthropic_model,
        max_tokens=settings.max_tokens,
        api_key=settings.anthropic_api_key or None,
    )


def _build_ollama():
    from langchain_ollama import ChatOllama

    return ChatOllama(model=settings.ollama_model, temperature=0)


_PROVIDERS = {
    "anthropic": _build_anthropic,
    "ollama": _build_ollama,
}


@lru_cache(maxsize=1)
def get_llm():
    """Devuelve el modelo de chat según settings.llm_provider."""
    return _PROVIDERS[settings.llm_provider]()


def message_text(response) -> str:
    """Extrae solo el texto de una respuesta. Los modelos nuevos devuelven el
    content como lista de bloques (thinking + text); nos quedamos con los text.
    """
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts).strip()
