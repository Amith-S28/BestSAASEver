# Cursor Rule: NLI Sentence Verification & Contradiction Redaction

## Rule Invariant
1. All generated clinical syntheses must be deconstructed into discrete sentences.
2. Every sentence with a citation must be verified against its cited `MedicalChunk` via `INLIVerifier`.
3. If `contradiction_score >= 0.60`, the sentence MUST be replaced with the standard safety redaction notice.

### ✅ DO
```python
if footnote.contradiction_score >= 0.60:
    redacted_claim_count += 1
    safe_text = f"[Safety Filter: Clinical recommendation redacted — contradicts {footnote.source_document}]"
```
