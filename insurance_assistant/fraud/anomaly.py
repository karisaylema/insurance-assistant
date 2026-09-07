"""Análisis de anomalías: compara un claim contra el HISTÓRICO de claims.

Cubre la Opción 2 del challenge: "compare them with historical data, and flag
suspicious patterns". Técnicas transparentes (no caja negra):
  - duplicado exacto (matching),
  - frecuencia de beneficiario (conteo),
  - outlier estadístico de monto y de días-hasta-reclamar (z-score).

Funciones puras (claim + history -> Flag | None), como fraud/rules.py: sin IO,
testeables, y cada flag lleva un número concreto para ser explicable.
"""
from __future__ import annotations

from statistics import mean, pstdev

from insurance_assistant.domain.schemas import Flag, LifeClaim

FREQUENCY_THRESHOLD = 3      # apariciones del beneficiario para marcar
Z_THRESHOLD = 3.0            # desviaciones estándar para considerar outlier


def _zscore(value: float, values: list[float]) -> float | None:
    """z = (valor - media) / desv. None si no hay muestra suficiente."""
    if len(values) < 2:
        return None
    sd = pstdev(values)
    if sd == 0:
        return None
    return (value - mean(values)) / sd


def check_duplicate(claim: LifeClaim, history: list[LifeClaim]) -> Flag | None:
    for h in history:
        if (
            claim.member_name
            and h.member_name == claim.member_name
            and h.amount_claimed == claim.amount_claimed
            and h.date_of_death == claim.date_of_death
        ):
            return Flag(
                rule="duplicate_claim",
                severity="high",
                detail=(
                    f"Claim idéntico ya en el histórico ({h.claim_id}): mismo "
                    "asegurado, monto y fecha de fallecimiento."
                ),
                clause="Análisis histórico — duplicado exacto",
                weight=3,
            )
    return None


def check_frequent_beneficiary(claim: LifeClaim, history: list[LifeClaim]) -> Flag | None:
    if not claim.beneficiary_name:
        return None
    count = sum(1 for h in history if h.beneficiary_name == claim.beneficiary_name)
    if count >= FREQUENCY_THRESHOLD:
        return Flag(
            rule="frequent_beneficiary",
            severity="medium",
            detail=(
                f"El beneficiario '{claim.beneficiary_name}' aparece {count} veces "
                "en el histórico de claims."
            ),
            clause="Análisis histórico — frecuencia de beneficiario",
            weight=2,
        )
    return None


def check_amount_outlier(claim: LifeClaim, history: list[LifeClaim]) -> Flag | None:
    if claim.amount_claimed is None:
        return None
    values = [h.amount_claimed for h in history if h.amount_claimed is not None]
    z = _zscore(claim.amount_claimed, values)
    if z is not None and abs(z) > Z_THRESHOLD:
        return Flag(
            rule="amount_outlier",
            severity="medium",
            detail=(
                f"Monto ${claim.amount_claimed:,.0f} está a {z:.1f}σ de la media "
                f"histórica (${mean(values):,.0f})."
            ),
            clause="Análisis histórico — outlier estadístico (z-score de monto)",
            weight=2,
        )
    return None


def check_filing_speed_outlier(claim: LifeClaim, history: list[LifeClaim]) -> Flag | None:
    if claim.date_of_death is None or claim.date_filed is None:
        return None
    value = (claim.date_filed - claim.date_of_death).days
    values = [
        (h.date_filed - h.date_of_death).days
        for h in history
        if h.date_of_death and h.date_filed
    ]
    z = _zscore(value, values)
    if z is not None and abs(z) > Z_THRESHOLD:
        return Flag(
            rule="filing_speed_outlier",
            severity="medium",
            detail=(
                f"Días hasta reclamar ({value}) está a {z:.1f}σ de la media "
                f"histórica ({mean(values):.0f} días)."
            ),
            clause="Análisis histórico — outlier estadístico (z-score de tiempo)",
            weight=2,
        )
    return None


ALL_CHECKS = [
    check_duplicate,
    check_frequent_beneficiary,
    check_amount_outlier,
    check_filing_speed_outlier,
]


def run_anomaly_checks(claim: LifeClaim, history: list[LifeClaim]) -> list[Flag]:
    """Corre todas las comparaciones contra el histórico y devuelve los flags."""
    if not history:
        return []
    return [flag for chk in ALL_CHECKS if (flag := chk(claim, history)) is not None]
