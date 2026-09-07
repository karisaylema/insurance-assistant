"""'Fuente de verdad' de la póliza S655, extraída del PDF real. Las reglas de
fraude se anclan a estos valores para ser explicables.
"""
from __future__ import annotations

POLICY_FACTS = {
    "policy_number": "S655",
    "group_policy_number": "GL S655",
    "insurer": "Principal Life Insurance Company",
    "policyholder": "Rhode Island John Doe",
    "state_of_issue": "Rhode Island",
    "date_of_issue": "2007-11-01",
    "updated_effective": "2014-01-01",
    "coverage_types": ["life", "ad&d", "dependent_life"],
    # Schedule of Insurance (Part IV, Section A, Article 1)
    "scheduled_benefit": 10000.0,
    # Reducción por edad (% del Scheduled Benefit)
    "age_reduction": [
        {"min_age": 70, "max_age": 74, "factor": 0.65},
        {"min_age": 75, "max_age": 200, "factor": 0.45},
    ],
    # Límite de dependiente (Part I - Definitions)
    "dependent_child_max_age": 26,
    # Plazos de Claim Procedures (Part IV, Section D)
    "notice_of_claim_days": 20,     # Art. 1
    "proof_of_loss_days": 90,       # Art. 3
    "legal_action_years": 3,        # Art. 7
}


def benefit_for_age(age: int | None) -> float:
    """Beneficio esperado ajustado por edad."""
    base = POLICY_FACTS["scheduled_benefit"]
    if age is None:
        return base
    for band in POLICY_FACTS["age_reduction"]:
        if band["min_age"] <= age <= band["max_age"]:
            return round(base * band["factor"], 2)
    return base
