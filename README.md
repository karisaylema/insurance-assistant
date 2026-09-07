# Asistente de Claims — Principal Life Insurance

Chatbot con IA para seguros de vida, construido sobre una **póliza real**
(Principal Life, Group Policy GL S655). El enunciado permite combinar sus focos;
esta solución **cubre los tres**, con énfasis en 1 y 2:

| Opción | Foco | Cómo se cubre |
|---|---|---|
| **1** | Claims Processor | Extrae datos de claims subidos (PDF/DOCX/JSON), valida y marca faltantes |
| **2** | Fraud Detection | Detecta fraude en 3 capas y **explica** cada alerta citando la fuente |
| **3** | Policy Manager | Chatbot que responde sobre términos, cobertura y exclusiones |

## Características

- **Chatbot RAG/CAG** sobre la póliza, con citas de página y respuesta "no lo
  encuentro en la póliza" (anti-alucinación).
- **Procesamiento de claims**: extracción a esquema tipado (Pydantic) + validación.
- **Detección de fraude en 3 capas**, todas explicables:
  1. **Reglas de póliza** (código determinístico anclado a cláusulas reales).
  2. **Análisis histórico** (estadística: duplicados, frecuencia, z-score).
  3. **Análisis semántico** (embeddings: narrativas similares).
- **Orquestación con LangGraph**; el modelo **no decide** el fraude (lo deciden
  reglas), solo **lee** el documento y **explica** las alertas.

## Cómo correr

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # añade ANTHROPIC_API_KEY (o LLM_PROVIDER=ollama)

streamlit run app.py          # abre la app (chat + revisar claim)
pytest                        # tests de las reglas de fraude
```

Notas:
- Modelo configurable en `.env` (`ANTHROPIC_MODEL`, ej. `claude-sonnet-5`).
- La póliza va **cacheada en el prompt** por defecto (`POLICY_MODE=cached`), así que
  no requiere indexar. Para el modo `rag`/`hybrid`:
  `python -m insurance_assistant.retrieval.ingest`.
- El análisis histórico usa datos **sintéticos** (`data/history/`), regenerables con
  `python -m scripts.generate_history`.

## Archivos requeridos (no incluidos en el repo)

Por privacidad/licencia, dos archivos **no** se versionan y hay que añadirlos:

| Archivo | Para qué | Cómo obtenerlo |
|---|---|---|
| `data/policy/*.pdf` | La póliza que el asistente lee/indexa | Coloca el PDF de la póliza (ver [data/policy/README.md](data/policy/README.md)). El caso usó la muestra de Principal Life **GL S655**; `POLICY_FACTS` está calibrado a ella. |
| `.env` | Credenciales y configuración | `cp .env.example .env` y añade tu `ANTHROPIC_API_KEY` |

Sin el PDF de la póliza, el chatbot no tiene contexto y la ingesta falla. Los datos
del histórico (`data/history/`) y los claims de ejemplo (`data/claims/`) **sí** están
incluidos (son sintéticos).

## Claims de ejemplo (demo)

Sube estos en la pestaña "Revisar un claim" (`data/claims/`):

| Archivo | Resultado | Qué demuestra |
|---|---|---|
| `claim_clean.json` | ✅ Auto-aprobar | claim consistente |
| `claim_fraud.json` | 🔴 Rechazar | reglas de póliza (monto, médico pariente, beneficiario acusado…) |
| `claim_history_anomaly.json` | 🔴 Rechazar | análisis histórico (beneficiario frecuente, outlier de monto) |
| `claim_semantic.json` | 🟡 Revisión humana | narrativa semánticamente similar a un claim previo |

## Arquitectura

Un motor de contexto sobre la póliza alimenta el chatbot y el razonamiento de
fraude. El pipeline del claim se orquesta con LangGraph:

```
extract → validate → fraud_rules → historical_analysis → semantic_analysis
        → consolidate ─┬─(flags)→ reasoning → END
                       └─(sin flags)→ auto_ok → END
```

- **extract / reasoning** usan el LLM (leer el documento / explicar).
- **fraud_rules / historical / semantic / consolidate** son código → el **veredicto
  no se puede alucinar**.

Organización por capas (la UI solo habla con `application/`, `domain/` no depende
de nada externo):

```
insurance_assistant/
├── settings.py         Config tipada (Pydantic)
├── domain/             Negocio puro: POLICY_FACTS, esquemas Pydantic
├── llm/                Factory del modelo (Claude/Ollama) + prompt caching
├── documents/          Carga de PDF/DOCX + extracción de claims
├── retrieval/          ChromaDB (local/cloud), estrategias de contexto, narrativas
├── fraud/              rules · anomaly · semantic · scoring · history
├── agent/              Grafo de LangGraph
└── application/        Casos de uso (chat_service, claim_service)
app.py                  UI Streamlit
tests/                  pytest
```

### Estrategia de contexto (`POLICY_MODE`)

La póliza (~30K tokens) cabe en contexto, por eso hay tres modos intercambiables:

| Modo | Cómo | Cuándo |
|---|---|---|
| `cached` (def.) | póliza completa cacheada (prompt caching) | 1 póliza; máxima precisión |
| `hybrid` | RAG selecciona páginas → carga las páginas completas | equilibrio; escala mejor |
| `rag` | recupera chunks de ChromaDB | corpus grande |

## Decisiones de diseño

- **Reglas para el veredicto, LLM para leer/explicar.** El fraude se decide con
  código determinístico (auditable, testeable, sin alucinación, inmune a inyección
  en el documento); el LLM extrae datos y redacta el porqué.
- **Estadística para números, embeddings para significado.** El histórico se compara
  con z-scores/conteos; las narrativas similares, con embeddings (ChromaDB). La señal
  semántica es **suave** (peso bajo → revisión, nunca rechazo por sí sola).
- **CAG con caching** en vez de RAG para una póliza pequeña: más precisión sin
  retrieval-miss; RAG/híbrido quedan para escalar.
- **Patrones**: Strategy (modos de contexto), Factory/registro (proveedor LLM),
  capas + SRP, Pydantic Settings.

## Stack

Python · Streamlit · LangGraph · Claude (Anthropic) vía `langchain-anthropic` ·
ChromaDB · Pydantic · pytest.
