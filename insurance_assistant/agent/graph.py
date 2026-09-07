r"""Grafo de LangGraph que orquesta la revisión de un claim.

    START -> extract -> validate -> fraud_rules --(flags)--> reasoning -> END
                                                \----------> auto_ok  -> END

Cada nodo es una función; el modelo se invoca dentro (extract, reasoning). Las
reglas de fraude son código puro. El contexto de la póliza para el razonamiento
lo provee la Strategy (cached vs rag), sin condicionales aquí.
"""
from __future__ import annotations

from typing import Literal, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

from insurance_assistant.documents.extraction import extract_claim
from insurance_assistant.fraud import anomaly, rules, scoring, semantic
from insurance_assistant.fraud.history import load_history
from insurance_assistant.llm.factory import get_llm, message_text
from insurance_assistant.retrieval import narratives
from insurance_assistant.retrieval.strategies import get_strategy
from insurance_assistant.domain.schemas import Flag, LifeClaim, MissingField

REASONING_INSTRUCTION = (
    "Eres un analista de fraude de seguros de vida. Explica de forma clara y "
    "breve por qué el claim requiere atención, apoyándote en la póliza. No "
    "inventes cláusulas."
)


class ClaimState(TypedDict, total=False):
    raw_text: str
    filename: str
    claim: LifeClaim
    missing_fields: list[MissingField]
    flags: list[Flag]
    fraud_score: int
    risk_level: str
    decision: str
    explanation: str


def extract_node(state: ClaimState) -> ClaimState:
    return {"claim": extract_claim(state["raw_text"], state.get("filename", ""))}


def validate_node(state: ClaimState) -> ClaimState:
    return {"missing_fields": rules.find_missing_fields(state["claim"])}


def fraud_rules_node(state: ClaimState) -> ClaimState:
    """Reglas ancladas a la póliza (código puro)."""
    return {"flags": rules.run_rules(state["claim"])}


def historical_analysis_node(state: ClaimState) -> ClaimState:
    """Añade flags por comparación estadística con el histórico (números)."""
    extra = anomaly.run_anomaly_checks(state["claim"], load_history())
    return {"flags": state["flags"] + extra}


def semantic_analysis_node(state: ClaimState) -> ClaimState:
    """Añade flag por narrativa semánticamente similar (significado, embeddings)."""
    claim = state["claim"]
    narratives.ensure_indexed(load_history())
    matches = narratives.similar_narratives(claim.narrative, exclude_claim_id=claim.claim_id)
    flag = semantic.flag_from_matches(matches)
    return {"flags": state["flags"] + ([flag] if flag else [])}


def consolidate_node(state: ClaimState) -> ClaimState:
    """Único punto donde se puntúa y decide (flags de póliza + histórico + semántico)."""
    flags = state["flags"]
    total = scoring.score(flags)
    return {
        "fraud_score": total,
        "risk_level": scoring.risk_level(flags),
        "decision": scoring.decide(total, flags),
    }


def reasoning_node(state: ClaimState) -> ClaimState:
    """Explica los flags citando la póliza (contexto vía Strategy)."""
    flags = state["flags"]
    flag_lines = "\n".join(f"- {f.rule} [{f.severity}]: {f.detail}" for f in flags)
    query = flags[0].clause if flags else "claim procedures fraud"
    task = (
        f"FLAGS DETECTADOS:\n{flag_lines}\n\n"
        "Redacta un resumen de 2-4 frases para el revisor, citando la póliza o el "
        "análisis histórico según corresponda."
    )
    system = get_strategy().build_system(REASONING_INSTRUCTION, query)
    resp = get_llm().invoke([system, HumanMessage(content=task)])
    return {"explanation": message_text(resp)}


def auto_ok_node(state: ClaimState) -> ClaimState:
    return {"explanation": "Claim consistente con la póliza S655. Sin flags de fraude."}


def route_after_consolidate(state: ClaimState) -> Literal["reasoning", "auto_ok"]:
    return "reasoning" if state["flags"] else "auto_ok"


def build_graph():
    g = StateGraph(ClaimState)
    g.add_node("extract", extract_node)
    g.add_node("validate", validate_node)
    g.add_node("fraud_rules", fraud_rules_node)
    g.add_node("historical_analysis", historical_analysis_node)
    g.add_node("semantic_analysis", semantic_analysis_node)
    g.add_node("consolidate", consolidate_node)
    g.add_node("reasoning", reasoning_node)
    g.add_node("auto_ok", auto_ok_node)

    g.add_edge(START, "extract")
    g.add_edge("extract", "validate")
    g.add_edge("validate", "fraud_rules")
    g.add_edge("fraud_rules", "historical_analysis")
    g.add_edge("historical_analysis", "semantic_analysis")
    g.add_edge("semantic_analysis", "consolidate")
    g.add_conditional_edges("consolidate", route_after_consolidate)
    g.add_edge("reasoning", END)
    g.add_edge("auto_ok", END)
    return g.compile()


CLAIM_GRAPH = build_graph()


if __name__ == "__main__":
    print(CLAIM_GRAPH.get_graph().draw_mermaid())
