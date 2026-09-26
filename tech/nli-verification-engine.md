# Tech Spec: Deterministic NLI Claim-to-Evidence Audit Engine

_MedRAG v2.0 Natural Language Inference Verification Architecture_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Sentence-Level Claim Decomposition

The synthesis pipeline does not return raw generative text. The complete output undergoes systematic assertion auditing:

1. **Sentence Boundary Tokenization**:
   - Deconstructs response text into discrete atomic sentences using spaCy clinical tokenizer (`en_core_sci_sm`).
2. **Citation Anchor Binding**:
   - Parses regex patterns `\[\^(\d+)\]` or `\[(\d+)\]` to bind each sentence to its specific cited `chunk_id`.
3. **NLI Inference Execution**:
   - **Premise**: Text content of cited `MedicalChunk`.
   - **Hypothesis**: The generated clinical sentence.
   - **Classifier**: `microsoft/deberta-v3-large-mnli` executed via ONNX Runtime.
   - Output Probabilities: `P(Entailment)`, `P(Neutral)`, `P(Contradiction)`.

---

## 2. Threshold Policies & Verification Status

| Status Classification | Decision Threshold | UI Presentation | Audit Action |
|---|---|---|---|
| **VERIFIED** | `P(Entailment) >= 0.85` | Green Checkmark Badge | Logged as `claim.verified` |
| **UNCERTAIN** | `0.50 <= P(Entailment) < 0.85` | Amber "Clinical correlation advised" | Logged; CMO Override enabled |
| **CONTRADICTED** | `P(Contradiction) >= 0.60` | Redacted Replacement Notice | Logged as `claim.contradicted`; Alert sent |
| **UNGROUNDED** | No citations or `P(Neutral) > 0.70` | Gray Warning Badge | Logged as ungrounded assertion |

---

## 3. Automated Contradiction Redaction Protocol

When `P(Contradiction) >= 0.60`:
1. The violating sentence is permanently stripped from the user-visible synthesis.
2. Replaced with the standard safety tombstone:
   `[Safety Filter: Clinical recommendation redacted — contradicts {source_doc}, Ch. {chapter}, p. {page}]`
3. Domain event `claim.contradicted` is emitted to the audit logger.
4. If a single synthesis contains **3 or more contradicted claims**, the entire report is quarantined, and the user is shown a safety fallback message.
