"""Front en Streamlit (capa de presentación, delgada): habla solo con los
servicios de application/. Ejecuta:  streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

from insurance_assistant.application.chat_service import answer
from insurance_assistant.application.claim_service import review_claim
from insurance_assistant.documents.loaders import read_document
from insurance_assistant.domain.policy import POLICY_FACTS
from insurance_assistant.retrieval.ingest import ingest
from insurance_assistant.retrieval.vectorstore import is_ingested
from insurance_assistant.settings import settings

st.set_page_config(page_title="Principal Life — Asistente de Claims", page_icon="🛡️", layout="wide")

SEV_COLOR = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
DECISION_LABEL = {
    "auto_approve": "✅ Auto-aprobar",
    "manual_review": "🟡 Revisión humana",
    "reject": "🔴 Rechazar",
}


with st.sidebar:
    st.header("🛡️ Principal Life")
    st.caption(f"Póliza **{POLICY_FACTS['group_policy_number']}** · {POLICY_FACTS['policyholder']}")
    st.caption(f"Modelo: `{settings.model_label()}`")
    _mode_desc = {
        "cached": " · póliza cacheada 🗄️",
        "rag": " · retrieval",
        "hybrid": " · RAG + páginas completas",
    }
    st.caption(f"Contexto: `{settings.policy_mode}`" + _mode_desc.get(settings.policy_mode, ""))

    if settings.policy_mode in ("rag", "hybrid"):
        st.markdown(f"**ChromaDB** (`{settings.chroma_mode}`)")
        if is_ingested():
            st.success("Póliza indexada ✔")
        else:
            st.warning("Aún no indexada")
        if st.button("📥 (Re)indexar póliza"):
            with st.spinner("Indexando póliza en ChromaDB..."):
                n = ingest()
            st.success(f"{n} fragmentos indexados")
            st.rerun()
    else:
        st.info("Modo CAG: la póliza completa va cacheada en el prompt. No requiere indexar.")


st.title("Asistente de Claims — Seguro de Vida")

if settings.policy_mode in ("rag", "hybrid") and not is_ingested():
    st.info("👈 Primero indexa la póliza con el botón del panel lateral.")

tab_chat, tab_claim = st.tabs(["💬 Preguntas sobre la póliza", "📄 Revisar un claim"])


# --- TAB 1: Chatbot RAG/CAG (Opción 1) ---
with tab_chat:
    st.subheader("Chatbot de la póliza")
    st.caption("Pregunta sobre cobertura, beneficios, exclusiones o el proceso de claim.")

    if "chat" not in st.session_state:
        st.session_state.chat = []   # lista de intercambios {question, answer, sources, usage}

    # Entrada (fija al fondo). Se procesa antes de renderizar para poner lo nuevo arriba.
    if prompt := st.chat_input("Ej: ¿Cuál es el beneficio para un miembro de 76 años?"):
        history = []
        for ex in st.session_state.chat:
            history.append({"role": "user", "content": ex["question"]})
            history.append({"role": "assistant", "content": ex["answer"]})
        with st.spinner("Consultando la póliza..."):
            result = answer(prompt, history)
        st.session_state.chat.append({
            "question": prompt,
            "answer": result["answer"],
            "sources": result["sources"],
            "usage": result.get("usage", {}),
        })

    # Render: más reciente primero (cada intercambio: pregunta → respuesta).
    for ex in reversed(st.session_state.chat):
        with st.chat_message("user"):
            st.markdown(ex["question"])
        with st.chat_message("assistant"):
            st.markdown(ex["answer"])
            u = ex.get("usage", {})
            if u:
                st.caption(
                    f"🗄️ caché: {u.get('cache_read', 0):,} leídos · "
                    f"{u.get('cache_creation', 0):,} escritos · "
                    f"entrada {u.get('input_tokens', 0):,} · salida {u.get('output_tokens', 0):,} tok"
                )
            if ex.get("sources"):
                with st.expander("Fuentes"):
                    for s in ex["sources"]:
                        st.caption(f"📄 {s['source']} · pág. {s['page']}")


# --- TAB 2: Subir claim + fraude (Opción 1 validación + Opción 2 fraude) ---
with tab_claim:
    st.subheader("Revisar un claim")
    st.caption("Sube un claim (PDF, DOCX, JSON o TXT). Se extrae, valida y evalúa el riesgo de fraude.")

    uploaded = st.file_uploader("Documento del claim", type=["pdf", "docx", "json", "txt"])

    if uploaded and st.button("🔍 Analizar claim", type="primary"):
        with st.spinner("Extrayendo y evaluando el claim..."):
            text = read_document(uploaded.getvalue(), uploaded.name)
            st.session_state.assessment = review_claim(text, uploaded.name)

    assessment = st.session_state.get("assessment")
    if assessment:
        c1, c2, c3 = st.columns(3)
        c1.metric("Decisión", DECISION_LABEL.get(assessment.decision, assessment.decision))
        c2.metric("Fraud score", assessment.fraud_score)
        c3.metric("Riesgo", f"{SEV_COLOR.get(assessment.risk_level, '')} {assessment.risk_level}")

        st.markdown("#### 🧠 Explicación")
        st.info(assessment.explanation or "—")

        if assessment.flags:
            st.markdown("#### 🚩 Flags de fraude")
            for f in assessment.flags:
                with st.container(border=True):
                    st.markdown(f"**{SEV_COLOR.get(f.severity, '')} {f.rule}** — {f.detail}")
                    st.caption(f"📖 Cláusula: {f.clause}")
        else:
            st.success("Sin flags de fraude.")

        if assessment.missing_fields:
            st.markdown("#### ⚠️ Campos faltantes")
            for m in assessment.missing_fields:
                st.write(f"- {m.detail}")

        with st.expander("Ver claim extraído (JSON)"):
            st.json(assessment.claim.model_dump(mode="json"))
