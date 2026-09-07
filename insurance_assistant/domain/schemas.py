"""Esquemas Pydantic para claims, flags y evaluación de fraude."""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

Severity = Literal["low", "medium", "high", "critical"]


class LifeClaim(BaseModel):
    """Claim de seguro de vida extraído de un documento."""

    claim_id: Optional[str] = Field(None, description="Identificador del claim")
    policy_number: Optional[str] = Field(None, description="Número de póliza, ej. S655")
    member_name: Optional[str] = Field(None, description="Nombre del asegurado")
    member_age: Optional[int] = Field(None, description="Edad del asegurado al fallecer")
    coverage_type: Optional[str] = Field(
        None, description="Tipo de cobertura: life, ad&d o dependent_life"
    )
    date_of_death: Optional[date] = Field(None, description="Fecha de fallecimiento")
    date_filed: Optional[date] = Field(None, description="Fecha de presentación del claim")
    cause_of_death: Optional[str] = Field(None, description="Causa del fallecimiento")
    narrative: Optional[str] = Field(
        None, description="Relato libre de las circunstancias del fallecimiento"
    )
    beneficiary_name: Optional[str] = Field(None, description="Nombre del beneficiario")
    beneficiary_relationship: Optional[str] = Field(
        None, description="Parentesco del beneficiario con el asegurado"
    )
    amount_claimed: Optional[float] = Field(None, description="Monto reclamado en USD")
    physician_name: Optional[str] = Field(
        None, description="Médico que firma el proof of loss"
    )
    physician_relationship: Optional[str] = Field(
        None, description="Relación del médico con el asegurado, si existe"
    )
    beneficiary_charged_in_death: Optional[bool] = Field(
        None, description="¿El beneficiario está acusado/sospechoso de la muerte?"
    )
    proof_of_loss_attached: Optional[bool] = Field(
        None, description="¿Se adjuntó prueba de pérdida?"
    )


class Flag(BaseModel):
    """Una señal de fraude o inconsistencia detectada."""

    rule: str = Field(..., description="Nombre corto de la regla")
    severity: Severity
    detail: str = Field(..., description="Qué se detectó, con los valores concretos")
    clause: str = Field(..., description="Cláusula de la póliza que respalda la regla")
    weight: int = Field(..., description="Peso de la señal para el score")


class MissingField(BaseModel):
    field: str
    detail: str


class FraudAssessment(BaseModel):
    """Resultado completo de revisar un claim."""

    claim: LifeClaim
    missing_fields: list[MissingField] = Field(default_factory=list)
    flags: list[Flag] = Field(default_factory=list)
    fraud_score: int = 0
    risk_level: Severity = "low"
    decision: Literal["auto_approve", "manual_review", "reject"] = "auto_approve"
    explanation: str = ""
