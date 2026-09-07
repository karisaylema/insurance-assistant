"""Caso de uso: responder preguntas sobre la póliza (Opción 1, chatbot).

La UI habla con este servicio, no con el LLM ni con la estrategia directamente:
así el front (Streamlit hoy, una API mañana) queda desacoplado de la lógica.
"""
from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from insurance_assistant.llm.caching import usage_summary
from insurance_assistant.llm.factory import get_llm, message_text
from insurance_assistant.retrieval.strategies import get_strategy
from insurance_assistant.settings import settings

SYSTEM_PROMPT = (
    "Eres un asistente de la póliza de seguro de vida de Principal Life "
    "(Group Policy S655). Responde SOLO con base en la póliza que se te "
    "entrega. Si la respuesta no está, dilo claramente ('No lo encuentro en "
    "la póliza'). Cita la sección/página cuando sea posible. Sé claro y conciso."
)


def _history_messages(history: list[dict] | None) -> list:
    msgs = []
    for turn in (history or [])[-6:]:
        content = turn.get("content", "")
        if turn.get("role") == "user":
            msgs.append(HumanMessage(content=content))
        else:
            msgs.append(AIMessage(content=content))
    return msgs


def answer(query: str, history: list[dict] | None = None) -> dict:
    """Devuelve {"answer", "sources", "usage", "mode"}."""
    strategy = get_strategy()
    system = strategy.build_system(SYSTEM_PROMPT, query)
    messages = [system, *_history_messages(history), HumanMessage(content=query)]

    resp = get_llm().invoke(messages)
    text = message_text(resp)
    return {
        "answer": text,
        "sources": strategy.sources(query, text),
        "usage": usage_summary(resp),
        "mode": settings.policy_mode,
    }
