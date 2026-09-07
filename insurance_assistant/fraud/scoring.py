"""Agregación de flags -> fraud_score, nivel de riesgo y decisión."""
from __future__ import annotations

from insurance_assistant.domain.schemas import Flag, Severity

REVIEW_THRESHOLD = 2      # >= revisión humana
REJECT_THRESHOLD = 6      # >= rechazo directo

_SEVERITY_ORDER: list[Severity] = ["low", "medium", "high", "critical"]


def score(flags: list[Flag]) -> int:
    return sum(f.weight for f in flags)


def risk_level(flags: list[Flag]) -> Severity:
    if not flags:
        return "low"
    return max((f.severity for f in flags), key=_SEVERITY_ORDER.index)


def decide(total: int, flags: list[Flag]) -> str:
    has_critical = any(f.severity == "critical" for f in flags)
    if has_critical or total >= REJECT_THRESHOLD:
        return "reject"
    if total >= REVIEW_THRESHOLD:
        return "manual_review"
    return "auto_approve"
