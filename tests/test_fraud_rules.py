"""Tests de las reglas de fraude (puras, sin LLM ni red)."""
from __future__ import annotations

from datetime import date, timedelta

from insurance_assistant.domain.policy import benefit_for_age
from insurance_assistant.domain.schemas import LifeClaim
from insurance_assistant.fraud import rules, scoring


def _claim(**kw) -> LifeClaim:
    base = dict(
        policy_number="S655",
        member_name="Robert Miller",
        member_age=58,
        coverage_type="life",
        date_of_death=date(2024, 3, 12),
        beneficiary_name="Susan Miller",
        amount_claimed=10000,
        physician_relationship="none",
        beneficiary_charged_in_death=False,
        proof_of_loss_attached=True,
    )
    base.update(kw)
    return LifeClaim(**base)


def test_benefit_reduction_by_age():
    assert benefit_for_age(58) == 10000
    assert benefit_for_age(72) == 6500   # 65%
    assert benefit_for_age(80) == 4500   # 45%


def test_clean_claim_has_no_flags():
    flags = rules.run_rules(_claim())
    assert flags == []
    assert scoring.decide(scoring.score(flags), flags) == "auto_approve"


def test_amount_mismatch_for_elderly_member():
    # 76 años debería cobrar 45% ($4,500), no $10,000.
    flags = rules.run_rules(_claim(member_age=76, amount_claimed=10000))
    assert any(f.rule == "amount_mismatch" for f in flags)


def test_beneficiary_charged_is_critical_reject():
    flags = rules.run_rules(_claim(beneficiary_charged_in_death=True))
    assert any(f.rule == "beneficiary_charged" and f.severity == "critical" for f in flags)
    assert scoring.decide(scoring.score(flags), flags) == "reject"


def test_death_before_coverage():
    flags = rules.run_rules(_claim(date_of_death=date(2000, 1, 1)))
    assert any(f.rule == "death_before_coverage" for f in flags)


def test_missing_required_field_detected():
    claim = _claim(beneficiary_name=None)
    missing = rules.find_missing_fields(claim)
    assert any(m.field == "beneficiary_name" for m in missing)


def test_amount_rule_only_applies_to_member_life():
    # Un claim AD&D no debe disparar amount_mismatch (tiene su propio schedule).
    flags = rules.run_rules(_claim(coverage_type="ad&d", member_age=76, amount_claimed=10000))
    assert not any(f.rule == "amount_mismatch" for f in flags)


def test_late_proof_of_loss_flagged():
    flags = rules.run_rules(
        _claim(date_of_death=date(2024, 1, 1), date_filed=date(2024, 6, 1))  # ~152 días
    )
    assert any(f.rule == "proof_of_loss_late" for f in flags)


def test_timely_proof_of_loss_not_flagged():
    flags = rules.run_rules(
        _claim(date_of_death=date(2024, 1, 1), date_filed=date(2024, 2, 1))  # 31 días
    )
    assert not any(f.rule == "proof_of_loss_late" for f in flags)


def test_all_context_strategies_registered():
    from insurance_assistant.retrieval.strategies import _STRATEGIES

    assert set(_STRATEGIES) == {"cached", "rag", "hybrid"}


# --- Análisis histórico (anomaly) ------------------------------------------
from insurance_assistant.fraud import anomaly  # noqa: E402


def _history():
    # 5 claims "normales" con montos ~10k (con varianza) y un beneficiario repetido.
    base = date(2023, 1, 1)
    amounts = [9000, 9500, 10000, 10500, 11000]  # media 10k, desv != 0
    return [
        _claim(member_name=f"M{i}", amount_claimed=amt, beneficiary_name="Ann Doe",
               date_of_death=base, date_filed=base + timedelta(days=20))
        for i, amt in enumerate(amounts)
    ]


def test_amount_outlier_detected():
    flags = anomaly.run_anomaly_checks(_claim(amount_claimed=90000), _history())
    assert any(f.rule == "amount_outlier" for f in flags)


def test_frequent_beneficiary_detected():
    flags = anomaly.run_anomaly_checks(_claim(beneficiary_name="Ann Doe"), _history())
    assert any(f.rule == "frequent_beneficiary" for f in flags)


def test_normal_claim_no_anomaly():
    flags = anomaly.run_anomaly_checks(
        _claim(amount_claimed=10000, beneficiary_name="Unique Person"), _history()
    )
    assert flags == []


def test_empty_history_is_safe():
    assert anomaly.run_anomaly_checks(_claim(), []) == []


# --- Análisis semántico (narrativa similar) --------------------------------
from insurance_assistant.fraud import semantic  # noqa: E402


def test_similar_narrative_flagged_above_threshold():
    matches = [{"claim_id": "HX-1005", "similarity": 0.93, "member_name": "X"}]
    assert semantic.flag_from_matches(matches) is not None


def test_similar_narrative_not_flagged_below_threshold():
    matches = [{"claim_id": "HX-1005", "similarity": 0.45, "member_name": "X"}]
    assert semantic.flag_from_matches(matches) is None


def test_similar_narrative_no_matches():
    assert semantic.flag_from_matches([]) is None
