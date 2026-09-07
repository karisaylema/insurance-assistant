"""Caso de uso: revisar un claim (Opción 1 validación + Opción 2 fraude).

Envuelve el grafo de LangGraph y devuelve un FraudAssessment tipado.
"""
from __future__ import annotations

from insurance_assistant.agent.graph import CLAIM_GRAPH
from insurance_assistant.domain.schemas import FraudAssessment


def review_claim(raw_text: str, filename: str = "") -> FraudAssessment:
    final = CLAIM_GRAPH.invoke({"raw_text": raw_text, "filename": filename})
    return FraudAssessment(
        claim=final["claim"],
        missing_fields=final.get("missing_fields", []),
        flags=final.get("flags", []),
        fraud_score=final.get("fraud_score", 0),
        risk_level=final.get("risk_level", "low"),
        decision=final.get("decision", "auto_approve"),
        explanation=final.get("explanation", ""),
    )
