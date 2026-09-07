"""Configuración tipada y validada (Pydantic Settings). Un solo objeto
`settings` centraliza todo lo que antes eran os.getenv sueltos.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Raíz del proyecto (un nivel arriba del paquete).
BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Modelo ---
    llm_provider: Literal["anthropic", "ollama"] = "anthropic"
    anthropic_api_key: str = ""            # se lee de ANTHROPIC_API_KEY (.env)
    anthropic_model: str = "claude-opus-5"
    ollama_model: str = "llama3.1"
    max_tokens: int = 2048

    # --- Estrategia de contexto de la póliza ---
    #   cached = CAG (póliza completa cacheada)
    #   rag    = recuperación de chunks
    #   hybrid = RAG selecciona páginas -> carga esas páginas completas
    policy_mode: Literal["cached", "rag", "hybrid"] = "cached"
    cache_ttl: str = "1h"

    # --- Recuperación ---
    chunk_size: int = 1000
    chunk_overlap: int = 150
    retrieve_k: int = 4

    # --- ChromaDB ---
    chroma_mode: Literal["local", "cloud"] = "local"
    chroma_api_key: str = ""
    chroma_tenant: str = ""
    chroma_database: str = "default_database"
    collection_name: str = "policy_s655"
    narrative_collection: str = "claim_narratives"

    # --- Rutas (derivadas) ---
    @property
    def data_dir(self) -> Path:
        return BASE_DIR / "data"

    @property
    def policy_dir(self) -> Path:
        return self.data_dir / "policy"

    @property
    def claims_dir(self) -> Path:
        return self.data_dir / "claims"

    @property
    def history_file(self) -> Path:
        return self.data_dir / "history" / "claims_history.json"

    @property
    def chroma_dir(self) -> Path:
        return BASE_DIR / ".chroma"

    def model_label(self) -> str:
        return self.ollama_model if self.llm_provider == "ollama" else self.anthropic_model


settings = Settings()
