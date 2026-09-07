"""Reglas determinísticas de fraude/validación, ancladas a cláusulas reales de
la póliza S655. Cada regla es una función pura y testeable.
"""
from __future__ import annotations

from datetime import date

from insurance_assistant.domain.policy import POLICY_FACTS, benefit_for_age
from insurance_assistant.domain.schemas import Flag, LifeClaim, MissingField

REQUIRED_FIELDS = [
    "policy_number",
    "member_name",
    "date_of_death",
    "amount_claimed",
    "beneficiary_name",
]


def find_missing_fields(claim: LifeClaim) -> list[MissingField]:
    missing = []
    for field in REQUIRED_FIELDS:
        if getattr(claim, field) in (None, ""):
            missing.append(
                MissingField(field=field, detail=f"Falta el campo obligatorio '{field}'.")
            )
    return missing


def rule_policy_number(claim: LifeClaim) -> Flag | None:
    expected = POLICY_FACTS["policy_number"]
    if claim.policy_number and claim.policy_number.upper().replace("GL ", "") != expected:
        return Flag(
            rule="policy_number_mismatch",
            severity="high",
            detail=f"Póliza '{claim.policy_number}' no coincide con la póliza {expected}.",
            clause="Title Page / Policy Rider — Group Policy GL S655",
            weight=3,
        )
    return None


def rule_amount_vs_schedule(claim: LifeClaim) -> Flag | None:
    if claim.amount_claimed is None:
        return None
    # El schedule de $10,000 + reducción por edad es de Member Life (Part IV,
    # Sec A). AD&D y Dependent Life tienen sus propios montos, así que no
    # aplicamos esta regla a esas coberturas (evita falsos positivos).
    if claim.coverage_type and claim.coverage_type.lower() not in ("life", "member life"):
        return None
    expected = benefit_for_age(claim.member_age)
    if abs(claim.amount_claimed - expected) > 0.01:
        edad = f" (edad {claim.member_age})" if claim.member_age is not None else ""
        return Flag(
            rule="amount_mismatch",
            severity="high",
            detail=(
                f"Monto reclamado ${claim.amount_claimed:,.0f} ≠ beneficio esperado "
                f"${expected:,.0f}{edad}."
            ),
            clause="Part IV, Section A, Art. 1 — Schedule of Insurance ($10,000) "
                   "+ reducción por edad (70–74: 65%, 75+: 45%)",
            weight=3,
        )
    return None


def rule_coverage_window(claim: LifeClaim) -> Flag | None:
    if claim.date_of_death is None:
        return None
    issue = date.fromisoformat(POLICY_FACTS["date_of_issue"])
    if claim.date_of_death < issue:
        return Flag(
            rule="death_before_coverage",
            severity="critical",
            detail=(
                f"Fecha de muerte {claim.date_of_death} anterior a la vigencia de la "
                f"póliza ({issue})."
            ),
            clause="Part I — Date of Issue (2007-11-01)",
            weight=4,
        )
    if claim.date_of_death > date.today():
        return Flag(
            rule="death_in_future",
            severity="critical",
            detail=f"Fecha de muerte {claim.date_of_death} está en el futuro.",
            clause="Part IV, Section D — Proof of Loss",
            weight=4,
        )
    return None


def rule_physician_relationship(claim: LifeClaim) -> Flag | None:
    rel = (claim.physician_relationship or "").strip().lower()
    if rel and rel not in ("none", "ninguno", "n/a", "unrelated"):
        return Flag(
            rule="physician_related",
            severity="medium",
            detail=(
                f"El médico que firma tiene relación con el asegurado: '{rel}'. "
                "La póliza no reconoce como Physician a familiares/allegados."
            ),
            clause="Part I — Definición de 'Physician' (excluye familiares y "
                   "personas del hogar del Member)",
            weight=2,
        )
    return None


def rule_beneficiary_charged(claim: LifeClaim) -> Flag | None:
    if claim.beneficiary_charged_in_death:
        return Flag(
            rule="beneficiary_charged",
            severity="critical",
            detail="El beneficiario está sospechoso/acusado de la muerte del asegurado.",
            clause="Part IV, Section A, Art. 2 — Death Benefits Payable "
                   "(beneficiario 'suspected or charged with the death')",
            weight=4,
        )
    return None


def rule_dependent_age(claim: LifeClaim) -> Flag | None:
    if (
        claim.coverage_type
        and "dependent" in claim.coverage_type.lower()
        and claim.member_age is not None
        and claim.member_age >= POLICY_FACTS["dependent_child_max_age"]
    ):
        return Flag(
            rule="dependent_not_eligible",
            severity="medium",
            detail=(
                f"Claim de dependiente con edad {claim.member_age} ≥ "
                f"{POLICY_FACTS['dependent_child_max_age']} (fuera de definición)."
            ),
            clause="Part I — Definición de 'Dependent Child' (0 a <26 años)",
            weight=2,
        )
    return None


def rule_proof_of_loss(claim: LifeClaim) -> Flag | None:
    if claim.proof_of_loss_attached is False:
        return Flag(
            rule="no_proof_of_loss",
            severity="medium",
            detail="No se adjuntó prueba de pérdida (Proof of Loss).",
            clause="Part IV, Section D, Art. 3 — Proof of Loss",
            weight=2,
        )
    return None


def rule_filing_timeliness(claim: LifeClaim) -> Flag | None:
    if claim.date_of_death is None or claim.date_filed is None:
        return None
    days = (claim.date_filed - claim.date_of_death).days
    limit = POLICY_FACTS["proof_of_loss_days"]
    if days > limit:
        return Flag(
            rule="proof_of_loss_late",
            severity="medium",
            detail=(
                f"Proof of loss presentado {days} días tras el fallecimiento "
                f"(límite {limit} días)."
            ),
            clause="Part IV, Section D, Art. 3 — Proof of Loss (90 días)",
            weight=2,
        )
    return None


ALL_RULES = [
    rule_policy_number,
    rule_amount_vs_schedule,
    rule_coverage_window,
    rule_physician_relationship,
    rule_beneficiary_charged,
    rule_dependent_age,
    rule_proof_of_loss,
    rule_filing_timeliness,
]


def run_rules(claim: LifeClaim) -> list[Flag]:
    """Ejecuta todas las reglas y devuelve los flags que dispararon."""
    return [flag for rule in ALL_RULES if (flag := rule(claim)) is not None]
