# Tech Spec: Hybrid Retrieval, Ontology Pre-Filtering & RRF Math

_MedRAG v2.0 Evidence Retrieval Pipeline_  
_Standardized against OnRent Enterprise Governance_

---

## 1. Multi-Stage Retrieval Pipeline

```text
Clinical Question
      │
      ▼
┌─────────────────────────┐
│   Entity Linker Port    │ ──► Extracts SNOMED-CT / RxNorm codes
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ LanceDB Hybrid Query    │
│  - Dense: Cosine IVF-PQ │
│  - Sparse: Tantivy BM25 │
│  - Pre-filter: Tenant   │
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ Reciprocal Rank Fusion  │ ──► Merges top 50 dense + top 50 sparse
│   RRF (k = 60)          │
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ Cross-Encoder Reranker  │ ──► MiniLM re-ranks top 25 candidates
└───────────┬─────────────┘
            ▼
 Top 5 Final Evidence Chunks
```

---

## 2. Reciprocal Rank Fusion (RRF) Formulation

When querying hybrid search, each document `d` receives a score calculated as:

`RRF_Score(d) = 1 / (60 + rank_dense(d)) + 1 / (60 + rank_sparse(d))`

- Constant `k = 60` prevents outlier ranks from dominating the fused distribution.
- Candidates present in both dense and sparse top-50 sets achieve significantly higher composite ranks.

---

## 3. Ontology-Filtered Pre-Retrieval

Before executing vector distance computation, the query is passed through `IEntityLinker` to extract clinical finding and disorder codes. If codes are identified, they are applied as a metadata pre-filter:

```sql
SELECT chunk_id, text_content 
FROM clinical_literature 
WHERE tenant_id IN ('system', :tenant_id)
  AND (array_contains(snomed_codes, :code1) OR array_contains(rxnorm_codes, :drug1))
ORDER BY vector_distance(embedding, :query_vec)
LIMIT 50;
```
Pre-filtering reduces the candidate search space by 90%+, achieving sub-8ms retrieval latency.
