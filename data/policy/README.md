# Policy document (REQUIRED — not included in the repo)

The assistant needs the policy PDF in this folder, for example:

```
data/policy/Sample-Life-Insurance-Policy.pdf
```

The technical case used the sample **Principal Life — Group Policy
GL S655** (example document). Any life insurance policy PDF works, but
keep in mind that the values in `insurance_assistant/domain/policy.py`
(`POLICY_FACTS`: amounts, age reduction, claim deadlines) are **calibrated to
that S655 policy**. For a different policy, adjust those values and the fraud rules.

- `cached` mode (default): the chatbot reads this PDF directly.
- `rag` / `hybrid` modes: index first with
  `python -m insurance_assistant.retrieval.ingest`.
