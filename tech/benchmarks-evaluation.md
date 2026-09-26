# Tech Spec: Benchmark Evaluation & Gold Dataset Harnesses

_MedRAG v2.0 Clinical Quality Evaluation Specification_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Automated Evaluation Harness (RAGAS & DeepEval)

Clinical generation quality is evaluated using standard RAG evaluation metrics against a curated suite of 50 complex MedQA / PubMedQA scenarios.

### Quality Threshold Gates (CI Blockers)
| Metric Identifier | Minimum Passing Score | Evaluation Method |
|---|---|---|
| **Faithfulness** | `>= 0.95` | Proportion of generated claims entailed by evidence chunks |
| **Context Precision** | `>= 0.88` | Signal-to-noise ratio of retrieved textbook passages |
| **Answer Relevance** | `>= 0.90` | Semantic alignment with clinical prompt inquiry |
| **Contradiction Rate** | `<= 0.01` | Frequency of generated claims conflicting with ground truth |

---

## 2. NLI Threshold Calibration Protocol (Amendment 6)

The 0.85 entailment cutoff is periodically calibrated against a gold validation set of 500 clinical claim-premise pairs:
- **False Negative Rate Target**: `< 5%` (legitimate clinical statements falsely flagged as uncertain).
- **False Positive Rate Target**: `< 0.1%` (hallucinations or contradictions falsely marked as verified).
- Calibration adjustments are logged as versioned threshold policies in configuration.
