"""Genera un histórico SINTÉTICO de claims para el análisis de anomalías.

Reproducible (seed fija). Uso:
    python -m scripts.generate_history
Los datos son representativos, no reales — sirven para demostrar el mecanismo
de comparación histórica; con datos reales el mismo código funciona.
"""
from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

from insurance_assistant.domain.policy import benefit_for_age

SEED = 42
N = 40
OUT = Path(__file__).resolve().parents[1] / "data" / "history" / "claims_history.json"

MEMBERS = [
    "Robert Miller", "Linda Torres", "James Cole", "Mary Nguyen", "David Park",
    "Sarah Klein", "Michael Boyd", "Emma Ross", "John Reed", "Nancy Ito",
    "Paul Vance", "Grace Lim", "Henry Ford", "Olivia Shaw", "Peter Munro",
]
# Pool amplio y diverso: la mayoría aparece 1-2 veces. "Patricia Vance" se fuerza
# aparte como el único beneficiario frecuente (señal de anomalía).
BENEFICIARIES = [
    "Carlos Torres", "Emily Cole", "Kevin Nguyen", "Anna Park", "George Ross",
    "Helen Reed", "Daniel Fox", "Laura Beck", "Ryan Hale", "Nina Ford",
    "Oscar Diaz", "Paula Kim", "Victor Lang", "Rosa Melo", "Ian Webb",
    "Tara Snow", "Leo Marsh", "Gina Pratt", "Sam Otto", "Cora Dunn",
    "Iris Vale", "Neil Roy", "Faye Lott", "Owen Hart", "Mia Ray",
    "Cody Sun", "Ruth Bane", "Alex Poe",
]
CAUSES = ["Myocardial infarction", "Stroke", "Cancer", "Accidental fall",
          "Pneumonia", "Traffic accident", "Natural causes"]

NARRATIVES = [
    "The insured suffered a sudden heart attack at home and was pronounced dead on arrival at the hospital.",
    "The policyholder was diagnosed with terminal cancer and passed away after a long illness in palliative care.",
    "The insured was involved in a highway collision when another vehicle ran a red light, and died at the scene.",
    "The member contracted severe pneumonia, was admitted to intensive care, and passed away two weeks later.",
    "The insured had a stroke during the night; despite emergency surgery, he did not recover and died three days later.",
]
# Relato ancla (índice 5) para demostrar el near-duplicate semántico.
STAIRCASE = ("The insured fell down the stairs at his home on the evening of the "
             "incident and was taken to the hospital, where he later died from his injuries.")


def generate() -> list[dict]:
    rng = random.Random(SEED)
    claims = []
    for i in range(N):
        age = rng.randint(28, 82)
        dod = date(2022, 1, 1) + timedelta(days=rng.randint(0, 900))
        days_to_file = rng.randint(5, 85)
        # "Patricia Vance" repetida a propósito -> señal de frecuencia.
        beneficiary = "Patricia Vance" if i % 7 == 0 else rng.choice(BENEFICIARIES)
        narrative = STAIRCASE if i == 5 else rng.choice(NARRATIVES)
        claims.append({
            "claim_id": f"HX-{1000 + i}",
            "policy_number": "S655",
            "member_name": rng.choice(MEMBERS),
            "member_age": age,
            "coverage_type": "life",
            "date_of_death": dod.isoformat(),
            "date_filed": (dod + timedelta(days=days_to_file)).isoformat(),
            "cause_of_death": rng.choice(CAUSES),
            "narrative": narrative,
            "beneficiary_name": beneficiary,
            "amount_claimed": benefit_for_age(age),
        })
    return claims


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data = generate()
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    amounts = [c["amount_claimed"] for c in data]
    from statistics import mean, pstdev
    print(f"✅ {len(data)} claims sintéticos -> {OUT}")
    print(f"   monto: media ${mean(amounts):,.0f} · desv ${pstdev(amounts):,.0f}")
    print(f"   'Patricia Vance' aparece {sum(1 for c in data if c['beneficiary_name']=='Patricia Vance')} veces")
