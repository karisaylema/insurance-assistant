"""Acceso al histórico de claims (IO). Separado del análisis (anomaly.py) para
respetar SRP: aquí solo se carga; la lógica estadística no toca disco.
"""
from __future__ import annotations

import json
from functools import lru_cache

from insurance_assistant.domain.schemas import LifeClaim
from insurance_assistant.settings import settings


@lru_cache(maxsize=1)
def load_history() -> list[LifeClaim]:
    """Carga y valida el histórico de claims. [] si no existe."""
    path = settings.history_file
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [LifeClaim.model_validate(item) for item in raw]
