# Documento de póliza (REQUERIDO — no incluido en el repo)

El asistente necesita el PDF de la póliza en esta carpeta, por ejemplo:

```
data/policy/Sample-Life-Insurance-Policy.pdf
```

El caso técnico usó la póliza de muestra de **Principal Life — Group Policy
GL S655** (documento de ejemplo). Cualquier PDF de póliza de vida funciona, pero
ten en cuenta que los valores en `insurance_assistant/domain/policy.py`
(`POLICY_FACTS`: montos, reducción por edad, plazos de claim) están **calibrados a
esa póliza S655**. Para otra póliza, ajusta esos valores y las reglas de fraude.

- Modo `cached` (por defecto): el chatbot lee este PDF directamente.
- Modos `rag` / `hybrid`: indexa primero con
  `python -m insurance_assistant.retrieval.ingest`.
